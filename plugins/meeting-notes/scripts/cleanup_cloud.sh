#!/bin/bash
# cleanup_cloud — 클라우드에 있는 오래된 녹음 원본을 정리한다.
#
#   cleanup_cloud.sh            실제 정리 (rclone 기본값에 따라 휴지통으로 이동)
#   cleanup_cloud.sh --dry-run  대상만 출력 (아무것도 건드리지 않음)
#
# cleanup_local.sh 와 다른 점
#   로컬 원본을 지운 뒤에는 클라우드가 **유일한 오디오 원본**이다. 그래서 조건이 더 엄격하다.
#
# 안전 원칙
#   1. **회의록이 실제로 만들어진 파일만** 지운다.
#      NOTES_DIR 안의 문서에서 원본 오디오 파일명을 찾아 대조한다.
#      대조에 실패하면 지우지 않는다 — 아직 처리되지 않은 녹음일 수 있다.
#   2. NOTES_DIR 이 설정되어 있지 않으면 **아무것도 하지 않는다**.
#      회의록 존재를 확인할 방법이 없는 상태에서 유일한 원본을 지울 수는 없다.
#   3. Google Drive 등 휴지통을 지원하는 백엔드에서는 rclone 기본 동작이 휴지통 이동이므로
#      일정 기간 복구할 수 있다. 휴지통이 없는 백엔드(S3 등)에서는 즉시 삭제이니 주의한다.
#   4. CLOUD_RETENTION_DAYS 이 지난 파일만 대상으로 한다. 0 이하면 정리하지 않는다.
#
# 설정: ~/.config/meetingrec/config
# 자동 실행: install.sh 가 하루 한 번 도는 launchd 작업으로 등록한다.

set -uo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

CONFIG="${MEETINGREC_CONFIG:-$HOME/.config/meetingrec/config}"
# shellcheck disable=SC1090
[[ -f "$CONFIG" ]] && source "$CONFIG"

RECORDINGS_DIR="${RECORDINGS_DIR:-$HOME/recordings}"
UPLOAD_DEST="${UPLOAD_DEST:-}"
NOTES_DIR="${NOTES_DIR:-}"
PROCESSED_DIR="${CLOUD_PROCESSED_DIR:-}"
RETENTION_DAYS="${CLOUD_RETENTION_DAYS:-0}"
LOG="$RECORDINGS_DIR/logs/cleanup_cloud.log"

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

mkdir -p "$(dirname "$LOG")"
log() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >>"$LOG"; }

# 안전 기본값: 설정이 없으면 조용히 아무것도 하지 않는다
[[ "${RETENTION_DAYS:-0}" -gt 0 ]] || exit 0
if [[ -z "$NOTES_DIR" ]]; then
    log "NOTES_DIR 미설정 — 회의록 확인 불가로 클라우드 정리를 건너뜁니다"; exit 0
fi
[[ -n "$UPLOAD_DEST" ]] || { log "UPLOAD_DEST 미설정 — 중단"; exit 0; }
command -v rclone >/dev/null || { log "rclone 없음 — 중단"; exit 1; }
remote_name="${UPLOAD_DEST%%:*}"
rclone listremotes 2>/dev/null | grep -q "^${remote_name}:$" || { log "원격 '${remote_name}' 미설정 — 중단"; exit 1; }
[[ -d "$NOTES_DIR" ]] || { log "NOTES_DIR($NOTES_DIR)를 찾을 수 없음 — 안전을 위해 중단"; exit 1; }

# 정리 대상 경로 (처리 완료 하위 폴더가 있으면 그쪽, 없으면 업로드 대상 전체)
target="${UPLOAD_DEST%/}"
[[ "$target" == *: ]] || target="${target}/"
[[ -n "$PROCESSED_DIR" ]] && target="${target}${PROCESSED_DIR}"

# 회의록 색인을 한 번에 만든다 (파일마다 전체 검색하면 매우 느리다)
NOTES_INDEX="$(grep -rh --include="*.md" -E "\.(m4a|mp3|wav|aac)" "$NOTES_DIR" 2>/dev/null)"
if [[ -z "$NOTES_INDEX" ]]; then
    log "NOTES_DIR 에서 오디오 파일명을 참조하는 문서를 찾지 못함 — 안전을 위해 중단"; exit 1
fi

cutoff=$(date -v-${RETENTION_DAYS}d '+%Y-%m-%d' 2>/dev/null || date -d "-${RETENTION_DAYS} days" '+%Y-%m-%d')
[[ -n "$cutoff" ]] || { log "기준일 계산 실패 — 중단"; exit 1; }

removed=0 kept=0 freed=0
while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    size=$(echo "$line" | awk '{print $1}')
    mdate=$(echo "$line" | awk '{print $2}')
    name=$(echo "$line" | sed -E 's/^ *[0-9]+ +[0-9-]+ [0-9:.]+ +//')
    [[ -z "$name" || -z "$mdate" ]] && { kept=$((kept+1)); continue; }

    # 보관 기간 확인 (YYYY-MM-DD 라 사전순 비교가 성립한다)
    if [[ ! "$mdate" < "$cutoff" ]]; then
        kept=$((kept+1)); continue
    fi

    # 회의록 존재 확인
    if ! printf '%s\n' "$NOTES_INDEX" | grep -qF "$name"; then
        log "SKIP(회의록 미확인) $name — 처리 여부를 직접 확인하세요"
        kept=$((kept+1)); continue
    fi

    mb=$(awk -v s="$size" 'BEGIN{printf "%.1f", s/1048576}')
    if $DRY_RUN; then
        printf '  삭제 예정: %-55s %sMB (%s, 회의록 확인됨)\n' "$name" "$mb" "$mdate"
    else
        if rclone deletefile "${target}/${name}" 2>>"$LOG"; then
            log "DELETE $name (${mb}MB, ${mdate}, 회의록 확인됨)"
        else
            log "FAIL(삭제 실패) $name"; kept=$((kept+1)); continue
        fi
    fi
    removed=$((removed+1))
    freed=$(awk -v a="$freed" -v s="$size" 'BEGIN{print a+s}')
done < <(rclone lsl "$target" 2>/dev/null)

freed_mb=$(awk -v s="$freed" 'BEGIN{printf "%.0f", s/1048576}')
if $DRY_RUN; then
    echo "  ─────"
    echo "  삭제 예정 ${removed}개 / ${freed_mb}MB · 유지 ${kept}개 (${RETENTION_DAYS}일 미경과 또는 회의록 미확인)"
else
    [[ "$removed" -gt 0 ]] && log "정리 완료: ${removed}개 삭제, ${freed_mb}MB (유지 ${kept}개)"
    echo "삭제 ${removed}개 / ${freed_mb}MB · 유지 ${kept}개"
fi
