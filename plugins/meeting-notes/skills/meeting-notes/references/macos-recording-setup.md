# macOS 녹음 레이어 설치와 함정

## 왜 이 구성인가

macOS는 **시스템 오디오(상대방 목소리)를 앱이 직접 캡처할 수 없다.** 화면 기록 도구도
마이크만 잡는다. 그래서 가상 오디오 장치(BlackHole)로 출력을 우회시켜 캡처한다.

시중의 무료 GUI 녹음 앱들은 유지보수가 끊기면 새 macOS에서 조용히 깨지므로,
여기서는 **액티브 유지보수 중인 BlackHole + ffmpeg + CoreAudio 직접 제어** 조합을 쓴다.

```
회의앱 ─▶ MeetingRec Output (다중출력) ─┬─▶ 실제 출력장치 (사용자가 듣는다)
                                        └─▶ BlackHole ─┐
마이크 ─────────────────────────────────────────────────┼─▶ MeetingRec Input (집합장치) ─▶ ffmpeg
                                                        ┘
```

집합장치(Aggregate)를 쓰는 이유는 단순히 두 입력을 합치기 위해서가 아니라,
**서로 다른 클럭이 몇 시간에 걸쳐 어긋나는 드리프트를 CoreAudio가 보정**해 주기 때문이다.
ffmpeg으로 두 장치를 따로 잡으면 이 보정이 없다.

`audiodev` (동봉 Swift 헬퍼)가 이 가상 장치들을 녹음할 때마다 만들고 지운다.
Audio MIDI 설정 GUI를 건드릴 필요가 없고, 듣는 장치(에어팟/스피커)가 바뀌어도 알아서 따라간다.

## 설치

```bash
brew install ffmpeg rclone switchaudio-osx
brew install --cask blackhole-2ch      # 관리자 암호 필요
xcode-select --install                 # swiftc (audiodev 빌드용)
./scripts/install.sh
```

그다음 `rclone config` 로 업로드 대상을 만들고 `~/.config/meetingrec/config` 의
`UPLOAD_DEST` 를 채운다.

## 실측으로 확인된 함정 3가지 (macOS 15/26)

셋 다 **에러 없이 무음 파일이 생기는** 유형이라 회의가 끝난 뒤에야 발견된다.
그래서 `rec stop` 이 채널별 레벨을 측정해 -80dB 미만이면 경고한다.

### 1. BlackHole 구버전은 무음

0.2.x 같은 오래된 버전은 최신 macOS에서 장치로는 보이지만 오디오가 흐르지 않는다.

```bash
defaults read /Library/Audio/Plug-Ins/HAL/BlackHole2ch.driver/Contents/Info.plist CFBundleShortVersionString
# 0.5.0 이상이어야 한다
```

### 2. 드라이버를 바꿔도 데몬이 옛 버전을 물고 있다

HAL 플러그인은 **coreaudiod가 기동할 때** 로드된다. 업그레이드 후 반드시:

```bash
sudo killall coreaudiod        # 오디오가 1초 끊겼다 돌아온다
```

파일은 새 버전인데 동작은 구버전이라 원인 파악이 오래 걸리는 함정이다.

### 3. 가상 장치 음소거 ← 가장 위험

macOS는 **출력 장치마다 음소거·볼륨을 독립적으로** 기억한다. BlackHole이 음소거면
들어가는 샘플이 그대로 0이 되는데, 가상 장치라 소리를 들어볼 수 없어 알아챌 방법이 없다.

`rec start` 가 매번 `audiodev ensure-audible` 로 자동 해제한다. 수동 확인:

```bash
./scripts/audiodev list                        # 장치 목록 (이름/UID/입력채널/출력채널)
./scripts/audiodev ensure-audible --uid BlackHole2ch_UID
```

## 진단 순서

무음이 의심되면 위에서부터:

```bash
# 1) 채널별 레벨 (녹음 파일)
./scripts/audio_precheck.sh 녹음.m4a

# 2) BlackHole 자체가 도는지 — 출력을 BlackHole로 돌리고 녹음해 본다
SwitchAudioSource -t output -s "BlackHole 2ch"
ffmpeg -f avfoundation -i ":BlackHole 2ch" -t 5 -y /tmp/t.wav   # 이때 아무 소리나 재생
ffmpeg -i /tmp/t.wav -af volumedetect -f null - 2>&1 | grep max_volume
# -91.0 dB = 완전 무음 → 위 함정 1~3 순서로 점검
```

## 알아둘 것

- **이어폰 사용을 권한다.** 스피커로 들으면 상대방 목소리가 마이크로 다시 들어가
  (이중 수음) 화자분리 품질이 떨어진다. 이어폰이면 L/R이 깔끔하게 갈린다.
- **녹음 중에는 오디오 출력을 바꾸지 않는다.** 시작 시점의 출력 장치로 가상 장치를
  구성하므로, 중간에 블루투스를 연결/해제하면 녹음이 끊길 수 있다.
- 조각화 MP4로 기록하므로 크래시가 나도 파일은 남는다. 업로드 직전에 표준 m4a로
  remux하면서 무결성까지 검증한다.
