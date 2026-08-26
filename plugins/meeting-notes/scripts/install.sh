#!/bin/bash
# install — meeting-notes 녹음 레이어를 이 맥에 설치한다.
#
#   ./install.sh          설치
#   ./install.sh --check  현재 상태만 점검
#
# 하는 일: 의존성 확인 → audiodev 빌드 → 폴더 생성 → 설정 파일 생성 →
#          rec 명령 심볼릭 링크 → launchd 업로드 감시 등록

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.config/meetingrec"
CONFIG="$CONFIG_DIR/config"
LABEL="com.meetingrec.upload"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
CHECK_ONLY=false
[[ "${1:-}" == "--check" ]] && CHECK_ONLY=true

ok()   { echo "  ✅ $*"; }
warn() { echo "  ⚠️  $*"; }
bad()  { echo "  ❌ $*"; }

echo "── 의존성 ──"
missing=()
for c in ffmpeg ffprobe rclone SwitchAudioSource swiftc; do
    if command -v "$c" >/dev/null; then ok "$c"; else bad "$c 없음"; missing+=("$c"); fi
done
bh_ver="$(defaults read /Library/Audio/Plug-Ins/HAL/BlackHole2ch.driver/Contents/Info.plist \
          CFBundleShortVersionString 2>/dev/null)"
if [[ -z "$bh_ver" ]]; then
    bad "BlackHole 2ch 없음 → brew install --cask blackhole-2ch"
elif [[ "$(printf '%s\n0.5.0\n' "$bh_ver" | sort -V | head -1)" != "0.5.0" ]]; then
    bad "BlackHole $bh_ver — macOS 15+ 에서 무음이 됩니다. 0.5.0 이상으로 업그레이드하세요"
    echo "     brew install --cask blackhole-2ch && sudo killall coreaudiod"
else
    ok "BlackHole $bh_ver"
fi
if [[ ${#missing[@]} -gt 0 ]]; then
    echo
    echo "설치 명령:"
    echo "  brew install ffmpeg rclone switchaudio-osx"
    echo "  brew install --cask blackhole-2ch     # 관리자 암호 필요"
    echo "  xcode-select --install                # swiftc"
fi
$CHECK_ONLY && { echo; echo "── 상태 ──"
    [[ -f "$CONFIG" ]] && ok "설정: $CONFIG" || warn "설정 없음"
    [[ -x "$HERE/audiodev" ]] && ok "audiodev 빌드됨" || warn "audiodev 미빌드"
    launchctl list 2>/dev/null | grep -q "$LABEL" && ok "업로드 감시 등록됨" || warn "업로드 감시 미등록"
    exit 0; }

echo
echo "── 설치 ──"
# 1) CoreAudio 헬퍼 빌드
if swiftc -O -o "$HERE/audiodev" "$HERE/audiodev.swift" 2>/dev/null; then ok "audiodev 빌드"
else bad "audiodev 빌드 실패 (Xcode Command Line Tools 필요)"; fi
chmod +x "$HERE"/*.sh "$HERE"/*.py 2>/dev/null

# 2) 설정 파일
mkdir -p "$CONFIG_DIR"
if [[ -f "$CONFIG" ]]; then ok "설정 유지: $CONFIG"
else cp "$HERE/config.example" "$CONFIG"; ok "설정 생성: $CONFIG  ← UPLOAD_DEST 를 채우세요"; fi
# shellcheck disable=SC1090
source "$CONFIG"
RECORDINGS_DIR="${RECORDINGS_DIR:-$HOME/recordings}"
mkdir -p "$RECORDINGS_DIR"/{staging,uploaded,failed,logs}
ok "작업 폴더: $RECORDINGS_DIR"

# 3) rec 명령
mkdir -p "$HOME/bin"
ln -sf "$HERE/rec.sh" "$HOME/bin/rec"; ok "rec 명령: ~/bin/rec"
case ":$PATH:" in *":$HOME/bin:"*) ;; *) warn "PATH 에 ~/bin 이 없습니다. 셸 설정에 추가하세요: export PATH=\"\$HOME/bin:\$PATH\"";; esac

# 4) launchd 업로드 감시
cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$HERE/upload_recording.sh</string>
    </array>
    <key>WatchPaths</key>
    <array><string>$RECORDINGS_DIR/staging</string></array>
    <key>StartInterval</key><integer>300</integer>
    <key>StandardOutPath</key><string>$RECORDINGS_DIR/logs/launchd.log</string>
    <key>StandardErrorPath</key><string>$RECORDINGS_DIR/logs/launchd.log</string>
</dict>
</plist>
PLISTEOF
launchctl unload "$PLIST" 2>/dev/null
launchctl load "$PLIST" 2>/dev/null && ok "업로드 감시 등록 ($LABEL)" || bad "launchd 등록 실패"

# 5) launchd 클라우드 정리 (하루 한 번). 설정이 꺼져 있으면 스크립트가 스스로 아무것도 안 한다.
CLOUD_LABEL="${CLOUD_CLEANUP_LABEL:-com.meetingrec.cloud-cleanup}"
CLOUD_PLIST="$HOME/Library/LaunchAgents/$CLOUD_LABEL.plist"
cat > "$CLOUD_PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$CLOUD_LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$HERE/cleanup_cloud.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict><key>Hour</key><integer>4</integer><key>Minute</key><integer>30</integer></dict>
    <key>StandardOutPath</key><string>$RECORDINGS_DIR/logs/launchd_cloud_cleanup.log</string>
    <key>StandardErrorPath</key><string>$RECORDINGS_DIR/logs/launchd_cloud_cleanup.log</string>
</dict>
</plist>
PLISTEOF
launchctl unload "$CLOUD_PLIST" 2>/dev/null
if launchctl load "$CLOUD_PLIST" 2>/dev/null; then
    if [[ "${CLOUD_RETENTION_DAYS:-0}" -gt 0 && -n "${NOTES_DIR:-}" ]]; then
        ok "클라우드 정리 등록 ($CLOUD_LABEL, ${CLOUD_RETENTION_DAYS}일 보관)"
    else
        ok "클라우드 정리 등록 ($CLOUD_LABEL) — 현재 비활성. 켜려면 설정에서 CLOUD_RETENTION_DAYS 와 NOTES_DIR 를 채우세요"
    fi
else
    bad "클라우드 정리 launchd 등록 실패"
fi

echo
echo "── 다음 할 일 ──"
echo "  1. rclone 원격 설정 후 $CONFIG 의 UPLOAD_DEST 채우기"
echo "  2. 녹음 테스트: rec start 테스트 → (소리 재생) → rec stop"
echo "     정지 시 표시되는 채널 레벨이 둘 다 -80dB 보다 크면 정상입니다."
echo "  3. (선택) 보관 정책: 로컬은 기본 3일 뒤 자동 삭제됩니다."
echo "     클라우드 원본도 정리하려면 $CONFIG 에서"
echo "     CLOUD_RETENTION_DAYS 와 NOTES_DIR(회의록 폴더)를 설정하세요."
echo "     무엇이 지워질지 먼저 확인: $HERE/cleanup_cloud.sh --dry-run"
