---
description: 이 맥에 회의 녹음 파이프라인을 설치하고 상태를 점검한다 (BlackHole·ffmpeg·rclone·launchd)
---

meeting-notes 플러그인의 녹음 레이어를 이 맥에 설치한다.

## 절차

1. **현재 상태 점검**

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/scripts/install.sh" --check
   ```

2. 빠진 의존성이 있으면 사용자에게 설치 명령을 안내한다. `brew install --cask blackhole-2ch` 는
   **관리자 암호가 필요하므로 사용자가 직접 실행**해야 한다. BlackHole을 새로 설치·업그레이드했다면
   `sudo killall coreaudiod` 도 반드시 함께 실행하도록 안내한다(이걸 빼먹으면 데몬이 옛 드라이버를
   계속 물고 있어 녹음이 무음이 된다).

3. **설치 실행**

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/scripts/install.sh"
   ```

4. **업로드 대상 설정** — 클라우드 업로드를 쓸 경우에만.
   `rclone config` 는 브라우저 인증이 필요하므로 사용자가 직접 실행해야 한다.
   완료되면 `~/.config/meetingrec/config` 의 `UPLOAD_DEST` 를 채운다.
   업로드가 필요 없으면 비워 두어도 되며, 이때는 로컬 staging 에만 쌓인다.

5. **동작 검증** — 설치 직후 반드시 실제 녹음으로 확인한다.

   ```bash
   rec start 설치테스트
   afplay /System/Library/Sounds/Glass.aiff    # 시스템 오디오 확인용
   sleep 6
   rec stop
   ```

   `rec stop` 이 출력하는 채널 레벨을 확인해 사용자에게 알린다.
   - 두 채널 모두 -80dB 보다 크면 정상
   - 상대방(L)이 무음이면 → BlackHole 버전 · `sudo killall coreaudiod` · 음소거 순으로 점검
     (`skills/meeting-notes/references/macos-recording-setup.md` 의 진단 절차)
   - 마이크(R)가 무음이면 → 시스템 설정 > 개인정보 보호 > 마이크 권한

   테스트로 만든 녹음 파일은 정리한다.

6. 마지막으로 사용법을 안내한다: `rec start "회의명"` / `rec stop`,
   그리고 터미널 없이 쓰려면 단축어 앱에서 `$HOME/bin/rec toggle` 에 키보드 단축키를 지정하는 방법.
