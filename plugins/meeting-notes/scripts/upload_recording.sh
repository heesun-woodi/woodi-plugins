#!/bin/bash
# upload_recording — staging 의 녹음 파일을 rclone 원격(클라우드)으로 올린다.
# launchd (WatchPaths + 주기 스윕 + rec stop 의 kickstart) 가 호출한다. 수동 실행도 가능.
#
# 안전장치
#   - 녹음 중인 파일은 건너뛴다 (rec 상태파일 + lsof + 크기 안정화 3중 확인)
#   - 조각화 MP4 → 표준 m4a 로 remux 하며 파일 무결성을 검증한 뒤 업로드
#   - 업로드 실패(일시적)는 staging 에 남겨 재시도, 파일 손상(영구적)은 failed/ 로 격리
#     → 깨진 파일 하나가 큐를 영원히 막는 것을 방지한다
#
# 설정: ~/.config/meetingrec/config

set -uo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

CONFIG="${MEETINGREC_CONFIG:-$HOME/.config/meetingrec/config}"
# shellcheck disable=SC1090
[[ -f "$CONFIG" ]] && source "$CONFIG"

RECORDINGS_DIR="${RECORDINGS_DIR:-$HOME/recordings}"
UPLOAD_DEST="${UPLOAD_DEST:-}"          # 예: "meetings:" 또는 "gdrive:MeetingInbox"
SETTLE_WAIT="${SETTLE_WAIT:-15}"        # 크기 안정화 확인 간격(초)
MIN_DURATION="${MIN_DURATION:-5}"       # 이보다 짧으면 녹음 사고로 보고 격리

STAGING="$RECORDINGS_DIR/staging"
UPLOADED="$RECORDINGS_DIR/uploaded"
FAILED="$RECORDINGS_DIR/failed"
WORK="$RECORDINGS_DIR/.remux"
LOG="$RECORDINGS_DIR/logs/upload.log"
LOCK="$RECORDINGS_DIR/.upload.lock"
STATE="$RECORDINGS_DIR/.rec_state"

mkdir -p "$STAGING" "$UPLOADED" "$FAILED" "$WORK" "$(dirname "$LOG")"
log() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >>"$LOG"; }

# 동시 실행 방지 (mkdir 은 원자적)
if ! mkdir "$LOCK" 2>/dev/null; then
    if [[ -n "$(find "$LOCK" -maxdepth 0 -mmin +30 2>/dev/null)" ]]; then
        log "오래된 잠금 회수"; rmdir "$LOCK" 2>/dev/null; mkdir "$LOCK" 2>/dev/null || exit 0
    else
        exit 0
    fi
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

[[ -n "$UPLOAD_DEST" ]] || { log "UPLOAD_DEST 미설정 ($CONFIG) — 중단"; exit 1; }
command -v rclone >/dev/null || { log "rclone 없음 — 중단"; exit 1; }
remote_name="${UPLOAD_DEST%%:*}"
if ! rclone listremotes 2>/dev/null | grep -q "^${remote_name}:$"; then
    log "rclone 원격 '${remote_name}' 미설정 — 'rclone config' 필요. 중단"; exit 1
fi

# 현재 녹음 중인 파일 (상태파일은 %q 이스케이프되어 있으므로 source 로 읽는다)
RECORDING_NOW=""
[[ -f "$STATE" ]] && RECORDING_NOW="$(source "$STATE" 2>/dev/null && printf '%s' "${file:-}")"

shopt -s nullglob
for f in "$STAGING"/*.m4a "$STAGING"/*.mp3 "$STAGING"/*.wav "$STAGING"/*.aac; do
    base="$(basename "$f")"

    [[ "$f" == "$RECORDING_NOW" ]] && { log "SKIP(녹음중) $base"; continue; }
    lsof -- "$f" >/dev/null 2>&1 && { log "SKIP(사용중) $base"; continue; }

    s1=$(stat -f%z "$f" 2>/dev/null) || continue
    sleep "$SETTLE_WAIT"
    s2=$(stat -f%z "$f" 2>/dev/null) || continue
    [[ "$s1" != "$s2" ]] && { log "SKIP(증가중) $base"; continue; }
    [[ "${s2:-0}" -lt 10000 ]] && { log "SKIP(너무 작음 ${s2}B) $base"; continue; }

    # remux + 무결성 검증 (재인코딩 없음). 여기서의 실패는 파일 자체 문제 → 격리
    out="$WORK/$base"
    if ! ffmpeg -nostdin -hide_banner -loglevel error -i "$f" -c copy -movflags +faststart -y "$out" 2>>"$LOG"; then
        log "FAIL(remux) $base → failed/"; rm -f "$out"; mv -f "$f" "$FAILED/$base"; continue
    fi
    dur="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$out" 2>/dev/null | cut -d. -f1)"
    if [[ -z "$dur" || "$dur" -lt "$MIN_DURATION" ]]; then
        log "FAIL(길이이상 ${dur:-?}s) $base → failed/"; rm -f "$out"; mv -f "$f" "$FAILED/$base"; continue
    fi

    dest="${UPLOAD_DEST%/}"; [[ "$dest" == *: ]] && dest="${dest}${base}" || dest="${dest}/${base}"
    if rclone copyto "$out" "$dest" \
         --transfers 1 --retries 3 --low-level-retries 10 --stats-one-line 2>>"$LOG"; then
        mv -f "$f" "$UPLOADED/$base"; rm -f "$out"
        log "OK $base ($((dur/60))분, $(du -h "$UPLOADED/$base" | cut -f1))"
    else
        log "FAIL(업로드) $base — 다음 스윕에서 재시도"; rm -f "$out"
    fi
done
