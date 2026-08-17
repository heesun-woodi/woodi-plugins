#!/usr/bin/env python3
"""Soniox raw JSON → 발화 세그먼트 → transcript.md.

Soniox 는 **토큰 단위**로만 결과를 준다(문단·세그먼트 없음). 이 스크립트가
화자 전환과 침묵 간격을 기준으로 발화 단위를 복원하고, 화자 이름을 적용하고,
Obsidian 에 넣을 transcript.md 를 만든다.

핵심 설계 원칙
    세그먼트화와 화자 이름 치환은 **코드가** 한다. LLM 에게 transcript 전체를
    다시 쓰게 하면 원문이 조금씩 변형(드리프트)되어 '원문 보존'이 깨진다.
    LLM 은 교정과 '화자 매핑 표 생성'까지만 담당한다.

사용:
    # 1) 품질 점검 — STT 결과가 쓸만한지 먼저 본다
    transcript_build.py stats  stt_raw.json

    # 2) LLM 교정 패스에 넣을 청크 (화자 턴 경계로만 분할 + 오버랩)
    transcript_build.py chunks stt_raw.json --chunk-chars 8000 --overlap 0.12

    # 3) 최종 transcript.md
    transcript_build.py markdown stt_raw.json \
        --speaker-map speakers.json --title "주간 정례회의" \
        --project "프로젝트/고객사A" -o transcript.md

speaker-map 형식 (LLM 이 만든 매핑 표를 그대로 저장):
    {"1": {"name": "홍길동", "confidence": "high"},
     "2": {"name": "이팀장", "confidence": "low"}}
    confidence 가 low 면 '화자2(추정: 이팀장)' 로 표기해 오인을 드러낸다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# 세그먼트 분할 기준
GAP_MS = 2000          # 같은 화자라도 이만큼 쉬면 새 발화로 본다
MAX_CHARS = 600        # 너무 긴 발화는 문장 경계에서 자른다
LOW_CONFIDENCE = 0.6   # 이 미만이면 저신뢰 표시

SENTENCE_END = re.compile(r"(?<=[.!?。？！])\s+|(?<=[다요죠])\.\s+")


@dataclass
class Segment:
    speaker: str
    start_ms: int
    end_ms: int
    text: str
    confidences: list[float] = field(default_factory=list)

    @property
    def confidence(self) -> float:
        return sum(self.confidences) / len(self.confidences) if self.confidences else 1.0

    @property
    def timestamp(self) -> str:
        s = self.start_ms // 1000
        return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def load_tokens(path: Path) -> tuple[list[dict], dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    tokens = data.get("tokens") or []
    if not tokens:
        sys.exit(f"토큰이 없습니다: {path} (STT가 실패했거나 무음 파일일 수 있음)")
    return tokens, data


def segment(tokens: list[dict]) -> list[Segment]:
    """토큰 배열 → 발화 세그먼트. 화자 전환 · 침묵 · 길이 세 기준으로 자른다."""
    segments: list[Segment] = []
    cur: Segment | None = None

    for tok in tokens:
        text = tok.get("text", "")
        if not text:
            continue
        speaker = str(tok.get("speaker") or "?")
        start, end = int(tok.get("start_ms", 0)), int(tok.get("end_ms", 0))

        new_speaker = cur is None or speaker != cur.speaker
        long_pause = cur is not None and start - cur.end_ms > GAP_MS
        too_long = cur is not None and len(cur.text) > MAX_CHARS and SENTENCE_END.search(cur.text[-40:])

        if new_speaker or long_pause or too_long:
            cur = Segment(speaker=speaker, start_ms=start, end_ms=end, text=text.lstrip())
            segments.append(cur)
        else:
            cur.text += text
            cur.end_ms = end
        if (c := tok.get("confidence")) is not None:
            cur.confidences.append(float(c))

    for s in segments:
        s.text = re.sub(r"\s+", " ", s.text).strip()
    return [s for s in segments if s.text]


def speaker_label(raw: str, mapping: dict) -> str:
    """매핑 표를 코드가 적용한다. 확신이 낮으면 추정임을 표기해 오인을 드러낸다."""
    info = mapping.get(raw)
    if not info:
        return f"화자{raw}"
    if isinstance(info, str):
        return info
    name, conf = info.get("name"), info.get("confidence", "high")
    if not name:
        return f"화자{raw}"
    return name if conf == "high" else f"화자{raw}(추정: {name})"


def hms(ms: int) -> str:
    s = ms // 1000
    return f"{s // 60}분 {s % 60}초" if s >= 60 else f"{s}초"


def cmd_stats(segments: list[Segment], raw: dict) -> int:
    total_ms = max((s.end_ms for s in segments), default=0)
    speakers: dict[str, int] = {}
    for s in segments:
        speakers[s.speaker] = speakers.get(s.speaker, 0) + (s.end_ms - s.start_ms)
    speaking_ms = sum(speakers.values())     # 침묵을 뺀 실제 발화 시간
    low = [s for s in segments if s.confidence < LOW_CONFIDENCE]
    chars = sum(len(s.text) for s in segments)

    print(f"길이        : {hms(total_ms)} (발화 {hms(speaking_ms)}, 침묵 {hms(total_ms - speaking_ms)})")
    print(f"세그먼트    : {len(segments)}개 · 총 {chars:,}자")
    print(f"화자        : {len(speakers)}명 (비율은 발화 시간 기준)")
    for spk, ms in sorted(speakers.items(), key=lambda kv: -kv[1]):
        share = ms / speaking_ms * 100 if speaking_ms else 0
        print(f"  화자{spk}: {hms(ms)} ({share:.0f}%)")
    print(f"저신뢰 구간 : {len(low)}개 ({len(low) / len(segments) * 100:.0f}%)")

    # 품질 경고 — 회의록을 만들기 전에 사람이 판단해야 하는 신호들
    if total_ms and chars / (total_ms / 60000) < 100:
        print("⚠️  분당 글자 수가 비정상적으로 적습니다. 무음·잡음 구간이 대부분일 수 있습니다.")
    if len(speakers) > 8:
        print("⚠️  화자가 과도하게 분리됐습니다. 화자 매핑 단계에서 병합을 검토하세요.")
    if len(low) / len(segments) > 0.3:
        print("⚠️  저신뢰 구간이 30%를 넘습니다. 녹음 품질을 확인하세요.")
    if pipe := raw.get("_pipeline"):
        print(f"원본        : {pipe.get('source_audio')}")
    return 0


def cmd_chunks(segments: list[Segment], chunk_chars: int, overlap: float, out_dir: Path | None) -> int:
    """LLM 교정용 청크. 반드시 화자 턴 경계에서만 자르고 앞뒤를 겹친다."""
    chunks: list[list[Segment]] = []
    cur: list[Segment] = []
    size = 0
    last_emitted = -1          # 청크에 이미 담긴 마지막 세그먼트 인덱스
    for idx, seg in enumerate(segments):
        cur.append(seg)
        size += len(seg.text)
        if size >= chunk_chars:
            chunks.append(cur)
            last_emitted = idx
            # 오버랩: 직전 청크의 꼬리 일부를 다음 청크 머리로 넘긴다 (문맥 유지)
            keep, acc = [], 0
            for s in reversed(cur):
                if acc >= chunk_chars * overlap:
                    break
                keep.insert(0, s)
                acc += len(s.text)
            cur, size = list(keep), acc
    # 남은 조각이 오버랩뿐이면(새 내용 없음) 버린다 — 같은 구간을 두 번 교정하게 된다
    if cur and len(segments) - 1 > last_emitted:
        chunks.append(cur)

    for i, ch in enumerate(chunks, 1):
        body = "\n".join(f"[{s.timestamp}] 화자{s.speaker}: {s.text}" for s in ch)
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / f"chunk_{i:02d}.txt").write_text(body, encoding="utf-8")
        else:
            print(f"===== chunk {i}/{len(chunks)} =====\n{body}\n")
    if out_dir:
        print(f"{len(chunks)}개 청크 → {out_dir}")
    return 0


def cmd_markdown(segments: list[Segment], raw: dict, args) -> int:
    mapping = json.loads(args.speaker_map.read_text(encoding="utf-8")) if args.speaker_map else {}
    pipe = raw.get("_pipeline", {})
    total_ms = max((s.end_ms for s in segments), default=0)

    speakers_line = ", ".join(
        f"{k}→{v if isinstance(v, str) else v.get('name', '?')}" for k, v in mapping.items()
    ) or "미매핑"

    fm = [
        "---",
        "유형: transcript",
        "출처: local-audio/soniox",
        f"원본오디오: {pipe.get('source_audio', '')}",
        f"회의일: {args.date or ''}",
        f"작성일: {args.date or ''}",
        f"프로젝트: {args.project or ''}",
        f"연결회의록: \"[[{args.title}_회의록]]\"" if args.title else "연결회의록: ",
        f"화자매핑: {speakers_line}",
        f"길이: {hms(total_ms)}",
        "상태: 원문보존",
        "---",
        "",
        f"# {args.title or '회의'} — transcript",
        "",
        "",
    ]

    body = []
    for s in segments:
        mark = " ⚠️저신뢰" if s.confidence < LOW_CONFIDENCE else ""
        body.append(f"## [{s.timestamp}] {speaker_label(s.speaker, mapping)}{mark}\n\n{s.text}\n")

    text = "\n".join(fm) + "\n".join(body)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(args.output)
    else:
        print(text)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Soniox raw JSON → transcript")
    ap.add_argument("command", choices=["stats", "chunks", "markdown"])
    ap.add_argument("raw_json", type=Path)
    ap.add_argument("--speaker-map", type=Path)
    ap.add_argument("--title")
    ap.add_argument("--project")
    ap.add_argument("--date")
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--chunk-chars", type=int, default=8000)
    ap.add_argument("--overlap", type=float, default=0.12)
    ap.add_argument("--chunk-dir", type=Path)
    args = ap.parse_args()

    tokens, raw = load_tokens(args.raw_json)
    segments = segment(tokens)

    if args.command == "stats":
        return cmd_stats(segments, raw)
    if args.command == "chunks":
        return cmd_chunks(segments, args.chunk_chars, args.overlap, args.chunk_dir)
    return cmd_markdown(segments, raw, args)


if __name__ == "__main__":
    sys.exit(main())
