---
name: meeting-notes
description: Use when the user wants to record a meeting on a Mac, transcribe an existing audio recording, or turn a recording/transcript into structured meeting notes — e.g. "회의 녹음 시작해줘", "이 녹음파일 회의록으로 정리해줘", "녹음 STT 해줘", "화상회의 녹음 세팅해줘", "인터뷰 녹취 정리해줘", "강의 녹음 정리", "transcript 만들어줘", "record this meeting", "transcribe this recording", "turn this audio into meeting notes". Covers the whole chain — macOS system-audio+mic recording (BlackHole + ffmpeg), auto-upload to cloud via rclone, Soniox async STT with speaker diarization, token→segment reconstruction, LLM cleanup, speaker-name mapping, and type-specific note templates (meeting / lecture / interview / workshop). Do NOT use for real-time live captioning, or for video editing.
---

# Meeting Notes Pipeline

녹음 → STT → transcript → 회의록. 각 단계에서 **코드가 할 수 있는 일은 코드가**, 판단이 필요한 일만 LLM이 한다.

```
녹음(rec)  →  자동 업로드(rclone)  →  Soniox STT  →  세그먼트화(코드)
                                                        ↓
회의록.md  ←  유형별 템플릿(LLM)  ←  transcript.md  ←  교정·화자매핑(LLM)
```

플러그인 스크립트 위치: `${CLAUDE_PLUGIN_ROOT}/scripts/`

## 0. 설치 여부 먼저 확인

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/install.sh --check
```

미설치면 `install.sh` 를 실행하고, BlackHole·rclone 등 사용자 조치가 필요한 항목은 안내한다.
자세한 설치·함정은 `references/macos-recording-setup.md` 참조.

## 1. 녹음

```bash
rec start "회의명"      # 시작 (출력 장치 자동 전환, 끝나면 자동 복구)
rec status              # 진행 상황
rec stop                # 정지 → 무음 검사 → 업로드 트리거
```

- 회의앱(Zoom/Meet/Teams) 무관하게 **스피커로 나가는 모든 소리 + 마이크**를 잡는다.
- 출력은 **L=상대방(시스템 오디오), R=나(마이크)** 로 분리 기록된다.
- `rec stop` 이 출력하는 채널 레벨을 **반드시 사용자에게 전달**한다. 어느 쪽이든
  -80dB 미만이면 무음 사고이므로 STT로 넘어가지 말고 원인부터 알린다.

## 2. STT 전 검사 (비용을 쓰기 전에)

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/audio_precheck.sh <오디오파일>
```

종료코드 1이면 **STT를 돌리지 않는다**. 무음·손상 파일에 돈을 쓰고 빈 transcript를
받은 뒤 회의록 단계에서야 알게 되는 것이 이 파이프라인의 가장 흔한 사고다.

## 3. Soniox 전사

```bash
export SONIOX_API_KEY=...     # https://console.soniox.com
${CLAUDE_PLUGIN_ROOT}/scripts/soniox_transcribe.py <오디오> --out-dir ./stt_raw \
    --glossary ~/.config/meetingrec/glossary/common.txt
```

- 화자분리 + 한/영 혼용 힌트 + 용어 바이어싱이 기본 적용된다.
- 업로드 파일·전사 레코드는 **자동 삭제되지 않으므로** 스크립트가 항상 정리한다(계정 한도 보호).
- 용어집(회사명·인명·전문용어)이 고유명사 인식률을 크게 좌우한다. `references/glossary.example.txt` 참고.
- raw JSON은 반드시 보존한다. 화자 매핑을 고쳐 재생성할 때 재전사 비용이 들지 않는다.

## 4. 1차 가공 — transcript

Soniox는 **토큰 단위**로만 결과를 준다. 문단 복원은 LLM이 아니라 코드가 한다(결정적).

```bash
S=${CLAUDE_PLUGIN_ROOT}/scripts/transcript_build.py
$S stats  stt_raw/xxx_stt_raw.json                       # 품질 점검 먼저
$S chunks stt_raw/xxx_stt_raw.json --chunk-dir ./chunks   # 교정용 청크
$S markdown stt_raw/xxx_stt_raw.json --speaker-map speakers.json \
    --title "..." --project "..." --date YYYY-MM-DD -o transcript.md
```

순서:
1. `stats` 로 화자 수·저신뢰 비율을 본다. 화자가 8명 넘게 잡히면 과분리를 의심한다.
2. `chunks` 결과를 `references/prompt_01_cleanup.md` 로 교정한다(요약 금지, 원문 보존).
3. `references/prompt_02_speaker_mapping.md` 로 **매핑 표(JSON)만** 만든다.
   캘린더 참석자 명단을 후보로 넣으면 정확도가 크게 오른다.
4. `markdown` 으로 transcript.md 생성 — 이름 치환은 코드가 결정적으로 수행한다.

**LLM에게 transcript 전체를 재작성시키지 않는다.** 긴 회의일수록 원문이 조금씩
변형되어(드리프트) 원문 보존이 깨진다.

## 5. 2차 가공 — 회의록

`references/prompt_03_templates.md` 의 유형 판별 → 템플릿 적용.
회의록 / 강의 / 인터뷰 / 워크샵은 필요한 구조가 다르다.

공통 규칙: transcript에 없는 내용을 추론해 넣지 않는다 · 결정사항과 액션 아이템에는
근거 타임스탬프를 병기한다 · 말한 순서가 아니라 다음 행동이 가능한 구조로 재구성한다.

## 6.5 보관 정책 (자동)

녹음 원본은 각 단계가 **다음 단계에 사본이 있음을 확인한 뒤에만** 지운다.

- 로컬 `uploaded/`: 원격에 같은 파일이 있고 크기가 맞으면 기본 3일 뒤 삭제 (업로드 직후 자동 실행)
- 클라우드: **기본 꺼짐**. `CLOUD_RETENTION_DAYS` 와 `NOTES_DIR` 를 둘 다 설정해야 동작하며,
  회의록 폴더에서 원본 파일명이 확인된 파일만 지운다

사용자가 용량 정리를 요청하면 먼저 `--dry-run` 으로 대상을 보여주고 확인을 받는다.
클라우드 정리는 로컬을 지운 뒤 **유일한 오디오 원본**을 지우는 것이므로 특히 신중하게 다룬다.

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/cleanup_local.sh --dry-run
${CLAUDE_PLUGIN_ROOT}/scripts/cleanup_cloud.sh --dry-run
```

## 6. 저장

transcript와 회의록을 **별도 파일로** 저장하고 서로 링크한다. 요약본만 남기면
AI의 해석이 원문을 대체해버리고, 화자 오인을 나중에 바로잡을 근거가 사라진다.

## 실패했을 때

| 증상 | 원인·조치 |
|---|---|
| 상대방 오디오만 무음 | BlackHole 음소거/구버전/데몬 미재시작 → `references/macos-recording-setup.md` |
| 마이크만 무음 | 시스템 설정 > 개인정보 보호 > 마이크 권한 |
| 업로드가 안 됨 | `~/recordings/logs/upload.log` → rclone 원격·`UPLOAD_DEST` 설정 확인 |
| 전사가 빈 결과 | `audio_precheck.sh` 를 먼저 돌렸는지 확인 |
| 5시간 초과 파일 | Soniox 상한. `ffmpeg -i IN -f segment -segment_time 14400 -c copy OUT%03d.m4a` 로 분할 |
