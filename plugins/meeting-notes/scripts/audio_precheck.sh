#!/bin/bash
# audio_precheck — STT 를 돌리기 전에 오디오가 쓸만한지 검사한다.
#
# 왜 필요한가: 무음·초단시간·손상 파일을 그대로 Soniox 에 보내면 비용만 나가고
# 결과는 빈 transcript 가 된다. 게다가 그 사실을 회의록 단계에 가서야 알게 된다.
# 이 검사는 몇 초 만에 끝나고 사고를 앞단에서 잡는다.
#
#   audio_precheck.sh <오디오파일>
#   종료코드 0=정상  1=사용불가(무음/손상/너무짧음)  2=주의(경고만)

set -uo pipefail
f="${1:?사용법: audio_precheck.sh <오디오파일>}"
[[ -f "$f" ]] || { echo "❌ 파일 없음: $f"; exit 1; }

dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f" 2>/dev/null | cut -d. -f1)
ch=$(ffprobe -v error -select_streams a:0 -show_entries stream=channels -of csv=p=0 "$f" 2>/dev/null)
size=$(du -h "$f" | cut -f1)

[[ -z "$dur" ]] && { echo "❌ 오디오 스트림을 읽을 수 없습니다 (파일 손상)"; exit 1; }
printf '파일   : %s (%s, %s분 %s초, %s채널)\n' "$(basename "$f")" "$size" "$((dur/60))" "$((dur%60))" "${ch:-?}"
printf '예상비용: $%.2f (Soniox async $0.10/시간)\n' "$(echo "$dur" | awk '{print $1/3600*0.10}')"

if [[ "$dur" -lt 10 ]]; then
    echo "❌ 10초 미만 — 회의 녹음이 아닙니다"; exit 1
fi

# 전체 레벨
overall=$(ffmpeg -hide_banner -i "$f" -af volumedetect -f null - 2>&1 | grep max_volume | sed 's/.*max_volume: //; s/ dB//')
printf '최대레벨: %s dB\n' "${overall:-?}"
if awk -v v="${overall:-0}" 'BEGIN{exit !(v+0 < -80)}'; then
    echo "❌ 전체 무음 — STT를 돌리지 마세요. 녹음 설정(가상장치 음소거 등)을 확인하세요"; exit 1
fi

# 채널 분리 녹음(L=상대방, R=나)이면 각각 확인
warn=0
if [[ "${ch:-1}" -ge 2 ]]; then
    for i in 0 1; do
        label=$([ $i -eq 0 ] && echo "L(상대방)" || echo "R(나)")
        lvl=$(ffmpeg -hide_banner -i "$f" -af "pan=mono|c0=c$i,volumedetect" -f null - 2>&1 |
              grep max_volume | sed 's/.*max_volume: //; s/ dB//')
        printf '  %-10s %s dB\n' "$label" "${lvl:-?}"
        awk -v v="${lvl:-0}" 'BEGIN{exit !(v+0 < -80)}' && {
            echo "  ⚠️  $label 채널이 무음입니다 — 한쪽 목소리가 빠진 회의록이 됩니다"; warn=1; }
    done
fi

# Soniox 파일당 상한
if [[ "$dur" -gt 18000 ]]; then
    echo "⚠️  5시간 초과 — 분할 필요:"
    echo "   ffmpeg -i \"$f\" -f segment -segment_time 14400 -c copy part%03d.m4a"
    warn=1
fi

[[ "$warn" -eq 1 ]] && { echo "→ 주의사항이 있습니다. 진행 여부를 판단하세요."; exit 2; }
echo "✅ 정상 — STT 진행 가능"
