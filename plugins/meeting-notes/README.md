# meeting-notes

맥에서 회의를 녹음해 **transcript와 회의록까지** 자동으로 만드는 파이프라인 플러그인.
온라인 회의(줌·구글밋·팀즈 무관)와 오프라인 회의를 모두 다룬다.

```
녹음(rec)  →  자동 업로드(rclone)  →  Soniox STT  →  세그먼트화(코드)
                                                        ↓
회의록.md  ←  유형별 템플릿(LLM)  ←  transcript.md  ←  교정·화자매핑(LLM)
```

## 이 플러그인이 해결하는 것

- **macOS는 시스템 오디오를 앱이 직접 캡처할 수 없다.** 화면 기록 도구도 마이크만 잡는다.
  가상 오디오 장치와 CoreAudio 집합장치를 코드로 구성해 상대방 목소리 + 내 목소리를 한 파일로 받는다.
- **상대방(L) / 나(R) 채널 분리 기록.** 화자분리 정확도가 올라가고, 나중에 채널별 처리도 가능하다.
- **무음 사고를 회의 직후에 잡는다.** 이 파이프라인의 가장 흔한 실패는 에러 없이
  몇 시간짜리 무음 파일이 만들어지는 것이다. 녹음 종료 시와 STT 직전에 채널별 레벨을 검사한다.
- **원문 보존.** 세그먼트화와 화자 이름 치환은 코드가 결정적으로 처리한다.
  LLM에게 transcript 전체를 재작성시키면 긴 회의일수록 원문이 변형된다.

## 필요한 것

| | |
|---|---|
| OS | macOS 14.2+ (Apple Silicon / Intel) |
| 도구 | `ffmpeg` `rclone` `switchaudio-osx` `swiftc`(Xcode CLT) |
| 드라이버 | [BlackHole 2ch](https://github.com/ExistentialAudio/BlackHole) **0.5.0 이상** |
| API | [Soniox](https://console.soniox.com) API 키 (async STT, 시간당 약 $0.10) |
| 클라우드 | rclone이 지원하는 아무 원격 (구글드라이브·드롭박스·S3 …) — 선택 |

## 설치

```bash
brew install ffmpeg rclone switchaudio-osx
brew install --cask blackhole-2ch      # 관리자 암호 필요
sudo killall coreaudiod                # 드라이버 반영 (중요)
xcode-select --install

# 플러그인 설치 후
"$CLAUDE_PLUGIN_ROOT"/scripts/install.sh
```

`install.sh` 가 하는 일: 의존성 점검 → CoreAudio 헬퍼 빌드 → 작업 폴더 생성 →
설정 파일 생성 → `rec` 명령 링크 → launchd 업로드 감시 등록.

마지막으로 `~/.config/meetingrec/config` 의 `UPLOAD_DEST` 를 채운다
(업로드가 필요 없으면 비워 두면 로컬에만 저장된다).

```bash
rclone config                                    # 원격 만들기
# 구글드라이브 폴더 하나를 alias 로 잡는 예:
rclone config create meetings alias remote "gdrive,root_folder_id=<폴더ID>:"
```

## 사용

```bash
rec start "주간 정례회의"   # 녹음 시작 (출력 장치 자동 전환)
rec status                  # 진행 상황
rec stop                    # 정지 → 무음 검사 → 업로드
rec toggle                  # 시작/정지 토글 (단축키·Dock 앱용)
```

`rec stop` 출력:

```
⏹  녹음 완료 — 2026-01-15_1400_주간-정례회의.m4a (47분, 32M)
   레벨 — 상대방(L) -6.1 dB / 나(R) -21.3 dB
   업로드 시작됨
```

**레벨 숫자를 확인하는 습관을 들일 것.** 어느 쪽이든 -80dB 근처면 무음 사고다.

### 터미널 없이 쓰기

- **Dock 앱**: `rec toggle` 을 실행하는 앱 번들을 만들어 Dock에 두면 클릭 한 번으로 시작/정지된다.
- **키보드 단축키**: 단축어(Shortcuts) 앱 → "셸 스크립트 실행" 에 `$HOME/bin/rec toggle` →
  키보드 단축키 지정 + 메뉴 막대에 고정.

### 보관 정책 (자동 정리)

녹음 원본은 회의 1건당 20~100MB라 그냥 두면 계속 쌓인다. 각 단계는
**"다음 단계에 사본이 있음을 확인한 뒤에만" 지운다.**

| 위치 | 기본 보관 | 삭제 전 확인 | 복구 |
|---|---|---|---|
| 로컬 `uploaded/` | 3일 | 원격에 같은 파일 존재 + 크기 2% 이내 일치 | 원격에 원본 |
| 클라우드 | 끔(기본) | 회의록 폴더에 원본 파일명이 등장 | 백엔드 휴지통 |
| 회의록·transcript | 영구 | — | — |

로컬 정리는 업로드 직후 자동으로 돈다. 클라우드 정리는 **기본적으로 꺼져 있으며**
`CLOUD_RETENTION_DAYS` 와 `NOTES_DIR`(회의록 폴더)를 둘 다 설정해야 동작한다 —
로컬을 지운 뒤에는 클라우드가 유일한 오디오 원본이기 때문이다.

```bash
# 무엇이 지워질지 먼저 확인 (아무것도 건드리지 않음)
"$CLAUDE_PLUGIN_ROOT"/scripts/cleanup_local.sh --dry-run
"$CLAUDE_PLUGIN_ROOT"/scripts/cleanup_cloud.sh --dry-run
```

확인에 실패하면 **항상 "안 지운다"로 실패한다.** 원격 목록을 못 가져오거나
회의록 폴더를 읽을 수 없으면 전체를 중단한다. 회의록에 원본 파일명이 기록되지 않는
워크플로우(예: 휴대폰에서 올린 파일이 다른 이름으로 처리된 경우)에서는 해당 파일이
계속 보류되므로, 쌓이면 직접 확인 후 정리한다.

즉시 삭제(0일)를 기본값으로 두지 않은 이유는, 전사가 중간에 잘리는 것 같은 사후 문제를
진단할 때 로컬 원본이 실제로 필요했기 때문이다. 문제는 보통 며칠 안에 드러난다.

### 전사와 회의록

Claude에게 "이 녹음 회의록으로 정리해줘" 라고 하면 스킬이 다음을 수행한다:
품질 검사 → Soniox 전사 → 세그먼트화 → 교정 → 화자 이름 매핑 → 유형별 회의록.

수동으로 돌리려면:

```bash
export SONIOX_API_KEY=...
S="$CLAUDE_PLUGIN_ROOT/scripts"
$S/audio_precheck.sh 회의.m4a || exit 1            # 무음·손상이면 여기서 중단
$S/soniox_transcribe.py 회의.m4a --out-dir ./stt_raw \
    --glossary ~/.config/meetingrec/glossary/common.txt
$S/transcript_build.py stats ./stt_raw/회의_stt_raw.json
$S/transcript_build.py markdown ./stt_raw/회의_stt_raw.json \
    --speaker-map speakers.json --title "주간 정례회의" -o transcript.md
```

## 구성

```
scripts/
  install.sh              설치·점검
  rec.sh                  녹음 시작/정지/토글
  audiodev.swift          CoreAudio 집합·다중출력 장치 CLI (Audio MIDI 설정 GUI 불필요)
  upload_recording.sh     안정화 확인 → 무결성 검증 → rclone 업로드 (launchd)
  audio_precheck.sh       STT 전 품질 검사 (무음·손상·길이·예상 비용)
  soniox_transcribe.py    업로드 → 전사 → 폴링 → raw JSON → 원격 리소스 정리
  transcript_build.py     토큰 → 세그먼트 → transcript.md (stats / chunks / markdown)
  cleanup_local.sh        원격 확인 후 오래된 로컬 원본 삭제 (업로드 후 자동 실행)
  cleanup_cloud.sh        회의록 확인 후 오래된 클라우드 원본 삭제 (기본 꺼짐, 하루 1회)
skills/meeting-notes/
  SKILL.md                파이프라인 운용 규칙
  references/
    macos-recording-setup.md   설치 상세 + macOS 오디오 함정 3가지와 진단법
    prompt_01_cleanup.md       transcript 교정 프롬프트
    prompt_02_speaker_mapping.md  화자 이름 매핑 (표만 출력 → 코드가 치환)
    prompt_03_templates.md     회의록 / 강의 / 인터뷰 / 워크샵 템플릿
    glossary.example.txt       STT 고유명사 바이어싱 용어집 예시
```

## 화상회의에서 상대방 목소리가 안 잡히는 경우

이 도구에서 가장 흔하고 아픈 실패다. 소리는 잘 들리므로 **회의 중에는 아무 이상을 못 느끼고**,
끝난 뒤에야 무음인 걸 알게 된다. 원인은 셋 중 하나이고, 공통점은 "시스템 오디오가
BlackHole 로 흐르지 않게 된 것"이다.

| 원인 | 설명 | 예방 |
|---|---|---|
| **회의앱이 스피커를 고정** | Zoom·Teams 등에서 스피커를 특정 장치로 지정해 두면, `rec start` 가 시스템 출력을 바꿔도 앱은 그 장치로 직접 재생해 BlackHole 을 통째로 우회한다 | 회의앱 오디오 설정에서 스피커를 **"시스템과 동일(Same as System)"** 로 |
| **회의 중 블루투스 이어폰 연결/해제** | 출력 장치가 다중출력에서 이탈한다 | 이어폰을 **연결한 뒤에** 녹음 시작 |
| **녹음 중 출력 장치 변경** | 위와 같은 결과 | 녹음 중에는 출력 장치를 바꾸지 않는다 |

블루투스 헤드셋(에어팟 등)은 macOS 에서 **같은 이름으로 입력·출력이 별도 장치**로 잡힌다
(예: `AirPods Pro` 입력 1ch / `AirPods Pro` 출력 2ch). 장치를 이름으로만 고르면 출력
0채널짜리 입력 장치를 집어 다중출력이 잘못 구성되므로, `rec.sh` 는 방향(채널 수)까지
확인해 고른다 — v0.3.1 에서 고쳐졌다.

### 두 가상 장치를 직접 고르지 말 것

녹음 중에는 이름이 비슷한 가상 장치 두 개가 만들어지고, **둘 다 소리 설정의 출력
목록에 보인다.** 역할은 정반대다.

| 장치 | 역할 |
|---|---|
| `MeetingRec Output` | 소리가 **나가는** 통로 — 스피커(이어폰)와 BlackHole로 동시에 보낸다. 녹음 중 출력은 항상 이것이어야 한다 |
| `MeetingRec Input` | 소리를 **받는** 통로 — BlackHole + 마이크를 합쳐 ffmpeg에 전달한다. 출력으로 고르면 소리도 안 들리고 녹음도 안 된다 |

`rec start` 가 시작 시점의 출력 장치(스피커든 이어폰이든)를 읽어 알아서 구성하므로
**사용자가 직접 고를 일이 없다.** 실수로 바뀌더라도 감시가 자동으로 되돌린다.

이어폰을 쓸 때만 **연결한 뒤에 녹음을 시작**하면 된다.

**실시간 감시가 기본으로 켜져 있다.** 녹음 중 `WATCH_INTERVAL`(기본 120초)마다
①출력 장치가 여전히 다중출력인지 ②BlackHole 에 실제 신호가 흐르는지 확인하고,
이상하면 **회의 중에 알림**을 띄운다(약 4분 내 감지). 알림을 받으면 그 자리에서
회의앱 스피커 설정을 고치면 된다.

대면 회의는 시스템 오디오가 없는 게 정상이므로 알림이 한 번 뜰 수 있다 — 무시하면 된다.
감시 기록은 `rec.log` 의 `WATCH`/`WARN` 줄에, 종료 시 채널 레벨은 `LEVEL` 줄에 남는다.
`WATCH_INTERVAL="0"` 으로 두면 감시를 끈다.

## 알려진 함정

`references/macos-recording-setup.md` 에 진단 절차와 함께 정리되어 있다. 요약하면:

1. **BlackHole 구버전(0.2.x)은 최신 macOS에서 무음** — 장치로는 보이지만 오디오가 흐르지 않는다
2. **드라이버 교체 후 `sudo killall coreaudiod` 필요** — 파일만 바꾸면 데몬이 옛 버전을 물고 있다
3. **가상 장치 음소거 시 녹음 전체가 무음** — 출력 장치마다 음소거가 독립적이고,
   가상 장치는 소리를 들어볼 수 없어 알아챌 방법이 없다. `rec start` 가 매번 자동 해제한다

그리고 launchd `WatchPaths` 는 파일 *내용* 변경이 아니라 디렉터리 엔트리 변화에 반응하므로,
녹음처럼 오래 열려 있다 닫히는 파일에는 `rec stop` 이 업로드 작업을 직접 깨운다.

## 비용

Soniox async STT 시간당 약 $0.10 (2026년 기준). 월 20시간 회의면 약 $2.
`audio_precheck.sh` 가 파일별 예상 비용을 미리 알려준다.
