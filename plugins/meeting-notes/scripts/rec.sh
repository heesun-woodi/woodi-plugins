#!/bin/bash
# rec — 회의 녹음 시작/정지 (시스템 오디오 + 마이크를 한 파일로)
#
#   rec start [회의명]   녹음 시작 (오디오 장치 자동 구성 + 출력 전환)
#   rec stop             녹음 정지 (출력 원복, 파일 마무리, 업로드 트리거)
#   rec status           현재 상태
#   rec toggle           안 하고 있으면 시작, 하고 있으면 정지 (단축키·Dock 앱용)
#
# 출력: $RECORDINGS_DIR/staging/YYYY-MM-DD_HHMM_<회의명>.m4a
#       L 채널 = 상대방(시스템 오디오), R 채널 = 나(마이크)
#
# 필요: BlackHole 2ch 0.5+, ffmpeg, switchaudio-osx, audiodev (동봉 Swift 헬퍼)
# 설정: ~/.config/meetingrec/config (config.example 참고)

set -uo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# 심볼릭 링크로 설치된 경우 실제 스크립트 위치까지 따라간다
SELF="${BASH_SOURCE[0]}"
while [[ -L "$SELF" ]]; do
    LINK="$(readlink "$SELF")"
    [[ "$LINK" == /* ]] && SELF="$LINK" || SELF="$(cd "$(dirname "$SELF")" && pwd)/$LINK"
done
HERE="$(cd "$(dirname "$SELF")" && pwd)"

# ── 설정 ────────────────────────────────────────────────────────────
CONFIG="${MEETINGREC_CONFIG:-$HOME/.config/meetingrec/config}"
# shellcheck disable=SC1090
[[ -f "$CONFIG" ]] && source "$CONFIG"

RECORDINGS_DIR="${RECORDINGS_DIR:-$HOME/recordings}"
# 마이크는 이름 대신 UID 로 지정한다 — 장치 이름은 OS 언어에 따라 달라진다
MIC_UID="${MIC_UID:-BuiltInMicrophoneDevice}"
UPLOAD_LABEL="${UPLOAD_LABEL:-com.meetingrec.upload}"
AUDIO_BITRATE="${AUDIO_BITRATE:-96k}"
# 회의 중 감시 주기(초). 2회 연속 무음이면 알린다 → 기본값에서 약 4분 뒤 경고. 0이면 감시 끔
WATCH_INTERVAL="${WATCH_INTERVAL:-120}"

AUDIODEV="${AUDIODEV:-$HERE/audiodev}"
STAGING="$RECORDINGS_DIR/staging"
STATE="$RECORDINGS_DIR/.rec_state"
LOG="$RECORDINGS_DIR/logs/rec.log"

IN_UID="com.meetingrec.input"
OUT_UID="com.meetingrec.output"
IN_NAME="MeetingRec Input"
OUT_NAME="MeetingRec Output"
BLACKHOLE_UID="${BLACKHOLE_UID:-BlackHole2ch_UID}"

mkdir -p "$STAGING" "$(dirname "$LOG")"

log() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >>"$LOG"; }
notify() { osascript -e "display notification \"${2//\"/}\" with title \"${1//\"/}\"" >/dev/null 2>&1 || true; }
die() { echo "❌ $*" >&2; log "ERROR: $*"; notify "회의 녹음 오류" "$*"; exit 1; }

# 에어팟 같은 블루투스 헤드셋은 **같은 이름으로 입력·출력이 별도 장치**로 잡힌다.
# 이름만으로 고르면 목록에서 먼저 나오는 입력 장치를 집어 출력용 다중장치가
# 엉뚱하게 구성된다(출력 0채널 장치가 주 장치가 된다). 그래서 방향까지 보고 고른다.
dev_uid_out() { "$AUDIODEV" list | awk -F'\t' -v n="$1" '$1==n && $4>0 {print $2; exit}'; }
dev_uid_in()  { "$AUDIODEV" list | awk -F'\t' -v n="$1" '$1==n && $3>0 {print $2; exit}'; }
dev_uid() { "$AUDIODEV" list | awk -F'\t' -v n="$1" '$1==n {print $2; exit}'; }
dev_in_ch() { "$AUDIODEV" list | awk -F'\t' -v u="$1" '$2==u {print $3; exit}'; }
dev_exists() { "$AUDIODEV" list | awk -F'\t' -v u="$1" '$2==u {found=1} END {exit !found}'; }

# 회의 중 감시 — 화상회의에서 상대방 목소리가 녹음되지 않는 사고를 실시간으로 잡는다.
#
# 왜 필요한가: 이 파이프라인에서 가장 아픈 실패는 회의가 끝난 뒤에야 "무음이었네"를
# 아는 것이다. 원인은 대부분 녹음 중 시스템 오디오가 BlackHole 로 흐르지 않게 되는 것인데,
# 사용자는 소리가 잘 들리므로 아무 이상을 못 느낀다.
#   - 회의앱(Zoom 등)이 스피커를 특정 장치로 고정해 두면 시스템 출력 전환을 무시한다
#   - 회의 중 블루투스 이어폰 연결/해제로 출력 장치가 바뀐다
#   - 사용자가 출력 장치를 직접 바꾼다
#
# 녹음 중인 파일은 ffmpeg 이 버퍼링해서 디스크에 거의 안 쓰이므로 측정할 수 없다.
# 대신 BlackHole 을 짧게 별도 샘플링한다 (녹음 중 동시 읽기가 가능한 것을 실측 확인).
watchdog() {
    local main_pid="$1"
    local probe="/tmp/meetingrec_probe_$$.wav"
    local silent=0 warned=0 cur lvl

    while kill -0 "$main_pid" 2>/dev/null && [[ -f "$STATE" ]]; do
        sleep "$WATCH_INTERVAL"
        kill -0 "$main_pid" 2>/dev/null || break
        [[ -f "$STATE" ]] || break

        # 1) 출력 장치가 여전히 우리 다중출력인가 (블루투스 연결, 사용자의 수동 변경 등)
        #    경고만 하면 회의가 끝날 때까지 녹음이 비어버린다. 되돌릴 수 있으면 **자동으로 되돌린다**.
        #    특히 집합장치(MeetingRec Input)도 출력 목록에 보이기 때문에 사용자가 실수로
        #    그쪽을 고르기 쉽고, 그러면 소리도 안 들리고 녹음도 안 된다.
        cur="$(SwitchAudioSource -t output -c 2>/dev/null)"
        if [[ -n "$cur" && "$cur" != "$OUT_NAME" ]]; then
            if SwitchAudioSource -t output -s "$OUT_NAME" >/dev/null 2>&1; then
                log "FIX 출력장치가 '$cur' 로 바뀌어 있어 '$OUT_NAME' 으로 되돌림"
                [[ "$warned" -eq 0 ]] && {
                    notify "🔧 녹음 자동 복구" "출력이 '$cur' 로 바뀌어 되돌렸습니다"
                    warned=1; }
            else
                log "WARN 출력장치가 '$cur' 로 바뀜 — 되돌리기 실패, 상대방 오디오가 녹음되지 않습니다"
                [[ "$warned" -eq 0 ]] && {
                    notify "⚠️ 녹음 경고" "출력이 '$cur' 로 바뀌어 상대방 목소리가 안 잡힙니다"
                    warned=1; }
            fi
            continue
        fi

        # 2) BlackHole 에 실제로 신호가 흐르는가 (회의앱이 다른 장치로 직접 재생하는 경우)
        ffmpeg -nostdin -hide_banner -loglevel error -f avfoundation \
               -i ":BlackHole 2ch" -t 5 -y "$probe" >/dev/null 2>&1
        lvl="$(ffmpeg -hide_banner -i "$probe" -af volumedetect -f null - 2>&1 |
               grep max_volume | sed 's/.*max_volume: //; s/ dB//')"
        rm -f "$probe"
        [[ -z "$lvl" ]] && continue

        if awk -v v="$lvl" 'BEGIN{exit !(v+0 < -80)}'; then
            silent=$((silent+1))
            log "WATCH BlackHole 무음 (${silent}회 연속, ${lvl}dB)"
            # 잠깐의 침묵은 정상이므로 연속 2회일 때만 알린다.
            # 대면 회의는 원래 시스템 오디오가 없으므로 한 번만 알리고 반복하지 않는다.
            if [[ "$silent" -ge 2 && "$warned" -eq 0 ]]; then
                notify "⚠️ 상대방 목소리 미감지" "화상회의라면 회의앱 스피커를 '시스템과 동일'로 바꾸세요"
                log "WARN 상대방 오디오 미감지 지속 — 회의앱 스피커 설정 의심"
                warned=1
            fi
        else
            [[ "$silent" -gt 0 ]] && log "WATCH 신호 복구 (${lvl}dB)"
            silent=0
        fi
    done
    rm -f "$probe"
}

cmd_start() {
    [[ -f "$STATE" ]] && die "이미 녹음 중입니다. 먼저 'rec stop' 하세요."
    command -v ffmpeg >/dev/null || die "ffmpeg 이 없습니다 (brew install ffmpeg)"
    command -v SwitchAudioSource >/dev/null || die "SwitchAudioSource 가 없습니다 (brew install switchaudio-osx)"
    [[ -x "$AUDIODEV" ]] || die "audiodev 바이너리가 없습니다. scripts 폴더에서 'swiftc -O -o audiodev audiodev.swift'"
    dev_exists "$BLACKHOLE_UID" || die "BlackHole 2ch 가 없습니다 (brew install --cask blackhole-2ch)"

    local title="${1:-회의}"
    local slug prev_out listen_uid mic_uid total_ch pan outfile
    slug="$(echo "$title" | tr ' /' '--' | tr -cd '[:alnum:]가-힣_-' | tr -s '-' | sed 's/^-//; s/-$//')"
    [[ -z "$slug" ]] && slug="회의"
    outfile="$STAGING/$(date '+%Y-%m-%d_%H%M')_${slug}.m4a"

    # 1) 지금 듣고 있는 출력 장치 = 다중출력의 주 장치 (에어팟이든 스피커든 그대로 들린다)
    prev_out="$(SwitchAudioSource -t output -c)"
    if [[ "$prev_out" == "$OUT_NAME" ]]; then      # 비정상 종료 흔적 방어
        prev_out="$("$AUDIODEV" list | awk -F'\t' '$4>0 && $2!="'"$BLACKHOLE_UID"'" {print $1; exit}')"
    fi
    listen_uid="$(dev_uid_out "$prev_out")"
    [[ -n "$listen_uid" ]] || die "현재 출력 장치($prev_out)의 UID를 찾지 못했습니다"

    # 2) 마이크: 설정된 UID → 없으면 아무 입력 장치
    mic_uid="$MIC_UID"
    if ! dev_exists "$mic_uid"; then
        mic_uid="$("$AUDIODEV" list | awk -F'\t' '$3>0 && $2!="'"$BLACKHOLE_UID"'" {print $2; exit}')"
        [[ -n "$mic_uid" ]] || die "사용 가능한 마이크가 없습니다"
        log "MIC_UID($MIC_UID) 없음 → $mic_uid 사용"
    fi

    # 3) 가상 장치 재생성 (듣는 장치가 매번 달라지므로 항상 새로 만든다)
    "$AUDIODEV" destroy --uid "$IN_UID" 2>/dev/null
    "$AUDIODEV" destroy --uid "$OUT_UID" 2>/dev/null
    "$AUDIODEV" create --name "$IN_NAME" --uid "$IN_UID" \
        --sub "$BLACKHOLE_UID" --sub "$mic_uid" --master "$mic_uid" --drift "$BLACKHOLE_UID" >/dev/null \
        || die "입력 집합장치 생성 실패"
    "$AUDIODEV" create --name "$OUT_NAME" --uid "$OUT_UID" --stacked \
        --sub "$listen_uid" --sub "$BLACKHOLE_UID" --master "$listen_uid" --drift "$BLACKHOLE_UID" >/dev/null \
        || die "다중출력장치 생성 실패"

    # 4) 채널 배치: ch0,ch1 = BlackHole(시스템오디오), 그 뒤 = 마이크
    total_ch="$(dev_in_ch "$IN_UID")"
    if [[ "${total_ch:-0}" -ge 4 ]]; then
        pan="pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c2+0.5*c3"
    elif [[ "${total_ch:-0}" -eq 3 ]]; then
        pan="pan=stereo|c0=0.5*c0+0.5*c1|c1=c2"
    else
        die "집합장치 채널 수가 예상과 다릅니다 (${total_ch:-?}ch)"
    fi

    # 5) BlackHole 음소거 해제 — 음소거면 에러 없이 녹음 전체가 무음이 된다
    [[ "$("$AUDIODEV" ensure-audible --uid "$BLACKHOLE_UID" 2>&1)" == "unmuted" ]] && log "BlackHole 음소거 해제함"

    # 6) 출력 전환 후 녹음 시작 (조각화 MP4 → 강제 종료·크래시에도 파일이 남는다)
    SwitchAudioSource -s "$OUT_NAME" >/dev/null || die "출력 전환 실패"
    nohup ffmpeg -nostdin -hide_banner -loglevel warning \
        -f avfoundation -i ":$IN_NAME" \
        -af "$pan" -c:a aac -b:a "$AUDIO_BITRATE" \
        -movflags +frag_keyframe+empty_moov+default_base_moof \
        -y "$outfile" >>"$LOG" 2>&1 &
    local pid=$!

    sleep 2
    if ! kill -0 "$pid" 2>/dev/null; then
        SwitchAudioSource -s "$prev_out" >/dev/null
        die "ffmpeg 이 시작 직후 종료됐습니다. 로그: $LOG"
    fi

    # 회의 중 감시 시작 — 상대방 오디오가 끊기면 회의가 끝난 뒤가 아니라 지금 알려준다
    local wdog=""
    # stdout/stderr 를 반드시 끊는다: 호출자가 $(rec start ...) 로 출력을 캡처하면
    # 명령치환이 **파이프를 물고 있는 백그라운드 자식까지** 기다린다. 그러면 이 스크립트를
    # 감싸는 GUI 런처(Dock 앱 등)가 녹음 내내 종료되지 않아, 정지하려고 다시 눌러도
    # macOS 가 '이미 실행 중'으로 보고 무시해버린다(실측 확인된 회귀).
    if [[ "${WATCH_INTERVAL:-0}" -gt 0 ]]; then
        watchdog "$pid" >/dev/null 2>&1 &
        wdog=$!
        disown "$wdog" 2>/dev/null
    fi

    { printf 'pid=%s\n' "$pid"
      printf 'wdog=%s\n' "$wdog"
      printf 'file=%q\n' "$outfile"
      printf 'prev_out=%q\n' "$prev_out"
      printf 'started=%s\n' "$(date '+%s')"; } >"$STATE"
    log "START pid=$pid file=$outfile ch=$total_ch listen=$prev_out"
    notify "🔴 회의 녹음 시작" "$title · 다시 누르면 정지됩니다"
    echo "🔴 녹음 시작 — $(basename "$outfile")"
    echo "   상대방=시스템오디오(L) / 나=마이크(R) · 출력장치: $prev_out → $OUT_NAME"
}

cmd_stop() {
    [[ -f "$STATE" ]] || die "녹음 중이 아닙니다"
    # shellcheck disable=SC1090
    source "$STATE"

    # 감시 프로세스를 먼저 정리한다 (샘플링이 종료 처리와 겹치지 않게)
    [[ -n "${wdog:-}" ]] && kill "$wdog" 2>/dev/null

    if kill -0 "$pid" 2>/dev/null; then
        kill -INT "$pid"                     # SIGINT → ffmpeg 이 파일을 정상 마무리
        for _ in $(seq 1 30); do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done
        kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
    fi

    SwitchAudioSource -s "$prev_out" >/dev/null 2>&1 ||
        echo "⚠️  출력 장치 복구 실패 — 수동으로 '$prev_out' 선택하세요" >&2
    "$AUDIODEV" destroy --uid "$IN_UID" 2>/dev/null
    "$AUDIODEV" destroy --uid "$OUT_UID" 2>/dev/null
    rm -f "$STATE"

    [[ -f "$file" ]] || die "녹음 파일이 없습니다: $file"
    local dur size lvl_sys lvl_mic warn=""
    dur="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$file" 2>/dev/null | cut -d. -f1)"
    size="$(du -h "$file" | cut -f1)"
    log "STOP file=$file dur=${dur}s size=$size"
    printf '⏹  녹음 완료 — %s (%s분, %s)\n' "$(basename "$file")" "$(( ${dur:-0} / 60 ))" "$size"

    # 무음 검사 — 몇 시간짜리 무음 파일을 뒤늦게 발견하는 최악의 사고를 여기서 잡는다
    lvl_sys="$(ffmpeg -hide_banner -i "$file" -af "pan=mono|c0=c0,volumedetect" -f null - 2>&1 |
               grep max_volume | sed 's/.*max_volume: //; s/ dB//')"
    lvl_mic="$(ffmpeg -hide_banner -i "$file" -af "pan=mono|c0=c1,volumedetect" -f null - 2>&1 |
               grep max_volume | sed 's/.*max_volume: //; s/ dB//')"
    printf '   레벨 — 상대방(L) %s dB / 나(R) %s dB\n' "$lvl_sys" "$lvl_mic"
    log "LEVEL $(basename "$file") L=${lvl_sys}dB R=${lvl_mic}dB"
    awk -v v="$lvl_sys" 'BEGIN{exit !(v+0 < -80)}' 2>/dev/null && {
        warn="⚠️ 상대방 무음! "; echo "   ⚠️  상대방 오디오가 무음입니다 — BlackHole 음소거/버전을 확인하세요"; }
    awk -v v="$lvl_mic" 'BEGIN{exit !(v+0 < -80)}' 2>/dev/null && {
        warn="${warn}⚠️ 마이크 무음! "; echo "   ⚠️  마이크가 무음입니다 — 마이크 권한을 확인하세요"; }
    notify "⏹ 녹음 완료 ($(( ${dur:-0} / 60 ))분)" "${warn}$(basename "$file")"

    # 업로드 작업을 즉시 깨운다. launchd WatchPaths 는 '폴더에 파일이 추가될 때' 반응하는데
    # 녹음 파일은 시작 시점에 이미 만들어져 있어 정지 후에는 이벤트가 없다.
    if launchctl kickstart "gui/$(id -u)/$UPLOAD_LABEL" >/dev/null 2>&1; then
        echo "   업로드 시작됨"
    else
        echo "   저장 위치: $STAGING"
    fi
}

cmd_status() {
    if [[ -f "$STATE" ]]; then
        # shellcheck disable=SC1090
        source "$STATE"
        printf '🔴 녹음 중 — %s (%d분 경과)\n' "$(basename "$file")" "$(( ($(date '+%s') - started) / 60 ))"
        [[ -f "$file" ]] && echo "   현재 크기: $(du -h "$file" | cut -f1)"
    else
        echo "⚪️ 녹음 중 아님"
        local n; n="$(find "$STAGING" -name '*.m4a' -type f 2>/dev/null | wc -l | tr -d ' ')"
        [[ "$n" -gt 0 ]] && echo "   업로드 대기: ${n}개"
    fi
}

case "${1:-}" in
    start)  shift; cmd_start "$@" ;;
    stop)   cmd_stop ;;
    status) cmd_status ;;
    toggle) shift; [[ -f "$STATE" ]] && cmd_stop || cmd_start "${1:-회의}" ;;
    *) echo "사용법: rec {start [회의명] | stop | status | toggle}" >&2; exit 1 ;;
esac
