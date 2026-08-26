#!/bin/bash
# cleanup_local — 업로드가 확인된 오래된 녹음 원본을 로컬에서 지운다.
#
#   cleanup_local.sh            실제 삭제
#   cleanup_local.sh --dry-run  삭제 대상만 출력 (아무것도 지우지 않음)
#
# upload_recording.sh 끝에서 자동 호출되므로 따로 실행할 필요는 없다.
#
# 안전 원칙 — "다음 단계에 사본이 있음을 확인한 뒤에만 지운다"
#   1. 업로드 로그를 믿지 않는다. 원격에 같은 이름의 파일이 실제로 있는지 매번 확인한다
#   2. 크기도 비교한다 — 이름만 있고 잘려서 올라간 경우를 걸러낸다
#      (업로드 시 remux 로 컨테이너가 바뀌어 수십 KB 차이는 정상이므로 2% 허용)
#   3. 처리 후 하위 폴더로 옮겨지는 워크플로우를 고려해 원격 전체를 재귀 검색한다
#   4. LOCAL_RETENTION_DAYS 이 지난 파일만 지운다. 0일(즉시 삭제)을 기본으로 두지 않는 이유는,
#      전사 누락 같은 사후 문제를 진단할 때 로컬 원본이 필요한 경우가 실제로 있기 때문이다
#   5. 확인에 실패하면 지우지 않고 경고만 남긴다. 원격 목록 자체를 못 가져오면 전체 중단한다
#
# 설정: ~/.config/meetingrec/config

set -uo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

CONFIG="${MEETINGREC_CONFIG:-$HOME/.config/meetingrec/config}"
# shellcheck disable=SC1090
[[ -f "$CONFIG" ]] && source "$CONFIG"

RECORDINGS_DIR="${RECORDINGS_DIR:-$HOME/recordings}"
UPLOAD_DEST="${UPLOAD_DEST:-}"
RETENTION_DAYS="${LOCAL_RETENTION_DAYS:-3}"
SIZE_TOLERANCE=2                       # 원격/로컬 크기 허용 오차(%)

UPLOADED="$RECORDINGS_DIR/uploaded"
LOG="$RECORDINGS_DIR/logs/cleanup_local.log"

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

mkdir -p "$UPLOADED" "$(dirname "$LOG")"
log() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >>"$LOG"; }

[[ -n "$UPLOAD_DEST" ]] || { log "UPLOAD_DEST 미설정 — 원격 확인 불가로 중단"; exit 0; }
command -v rclone >/dev/null || { log "rclone 없음 — 중단"; exit 1; }
remote_name="${UPLOAD_DEST%%:*}"
rclone listremotes 2>/dev/null | grep -q "^${remote_name}:$" || { log "원격 '${remote_name}' 미설정 — 중단"; exit 1; }

# 원격 목록은 한 번만 받는다 (파일마다 조회하면 느리고 API 호출도 낭비)
REMOTE_LIST="$(rclone lsl "${remote_name}:" 2>/dev/null)"   # lsl 은 기본이 재귀
if [[ -z "$REMOTE_LIST" ]]; then
    log "원격 목록을 가져오지 못했습니다 — 안전을 위해 중단"; exit 1
fi

freed=0 kept=0 deleted=0
shopt -s nullglob
for f in "$UPLOADED"/*.m4a "$UPLOADED"/*.mp3 "$UPLOADED"/*.wav "$UPLOADED"/*.aac; do
    base="$(basename "$f")"
    local_size=$(stat -f%z "$f" 2>/dev/null) || continue

    if [[ -z "$(find "$f" -mtime +${RETENTION_DAYS} 2>/dev/null)" ]]; then
        kept=$((kept+1)); continue
    fi

    remote_size=$(printf '%s\n' "$REMOTE_LIST" | awk -v n="$base" '
        { line=$0; sub(/^ *[0-9]+ +[0-9-]+ [0-9:.]+ +/, "", line)
          if (line ~ n"$") { print $1; exit } }')

    if [[ -z "$remote_size" ]]; then
        log "SKIP(원격에 없음) $base — 업로드 상태를 확인하세요"
        kept=$((kept+1)); continue
    fi

    diff_pct=$(awk -v a="$local_size" -v b="$remote_size" \
        'BEGIN { d=(a>b)?a-b:b-a; printf "%.2f", (a>0)? d*100/a : 100 }')
    if awk -v d="$diff_pct" -v t="$SIZE_TOLERANCE" 'BEGIN{exit !(d+0 > t)}'; then
        log "SKIP(크기 불일치 ${diff_pct}%) $base — 로컬 ${local_size} / 원격 ${remote_size}"
        kept=$((kept+1)); continue
    fi

    mb=$(awk -v s="$local_size" 'BEGIN{printf "%.1f", s/1048576}')
    if $DRY_RUN; then
        printf '  삭제 대상: %-55s %sMB (원격 확인됨)\n' "$base" "$mb"
    else
        rm -f "$f" && log "DELETE $base (${mb}MB, 원격 확인됨)"
    fi
    freed=$(awk -v a="$freed" -v s="$local_size" 'BEGIN{print a+s}')
    deleted=$((deleted+1))
done

freed_mb=$(awk -v s="$freed" 'BEGIN{printf "%.0f", s/1048576}')
if $DRY_RUN; then
    echo "  ─────"
    echo "  삭제 예정 ${deleted}개 / ${freed_mb}MB · 유지 ${kept}개 (${RETENTION_DAYS}일 미경과 또는 확인 실패)"
else
    [[ "$deleted" -gt 0 ]] && log "정리 완료: ${deleted}개 삭제, ${freed_mb}MB 확보 (유지 ${kept}개)"
    echo "삭제 ${deleted}개 / ${freed_mb}MB 확보 · 유지 ${kept}개"
fi
