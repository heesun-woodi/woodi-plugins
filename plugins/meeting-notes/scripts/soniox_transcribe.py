#!/usr/bin/env python3
"""오디오 파일 → Soniox async STT → raw JSON 저장.

파이프라인의 STT 단계 전체를 담당한다:
업로드 → 전사 생성 → 폴링 → transcript 수신 → 원격 리소스 삭제.

사용:
    python3 soniox_transcribe.py <오디오파일> [--out-dir DIR] [--glossary FILE ...]

출력:
    <out-dir>/<원본이름>_stt_raw.json   (tokens 포함 전체 응답 + 파이프라인 메타)
    성공 시 마지막 줄에 저장 경로를 stdout 으로 출력한다.

환경변수:
    SONIOX_API_KEY   (필수)  ~/.config/meetingrec/secrets.env 에서 로드해 export 해둘 것

주의:
    Soniox 는 업로드 파일과 전사 레코드를 자동 삭제하지 않는다(10GB/1,000파일 한도).
    이 스크립트는 성공·실패와 무관하게 원격 리소스를 정리한다.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("requests 가 필요합니다: pip install requests")

API = "https://api.soniox.com"
MODEL = "stt-async-v5"
MAX_MINUTES = 300          # Soniox 파일당 상한 (5시간)
POLL_INTERVAL = 10         # 초
POLL_TIMEOUT = 3 * 3600    # 3시간이면 어떤 회의든 끝난다

AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".aac", ".flac", ".ogg", ".webm", ".mp4", ".amr", ".aiff"}


def log(msg: str) -> None:
    print(f"[soniox] {msg}", file=sys.stderr)


def audio_duration_minutes(path: Path) -> float | None:
    """ffprobe 로 길이를 잰다. 없으면 None (검사를 건너뛴다)."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=60,
        )
        return float(out.stdout.strip()) / 60
    except (FileNotFoundError, ValueError, subprocess.SubprocessError):
        return None


def load_terms(paths: list[Path]) -> list[str]:
    """용어집 파일들(한 줄 = 한 용어)을 합쳐 중복 제거. '#' 주석 허용."""
    terms: list[str] = []
    for p in paths:
        if not p.exists():
            log(f"용어집 없음, 건너뜀: {p}")
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            term = line.split("#", 1)[0].strip()
            if term and term not in terms:
                terms.append(term)
    # context 는 8,000 토큰(약 1만 자) 상한. 넉넉히 잘라 안전 마진을 둔다.
    budget, kept = 8000, []
    for t in terms:
        if budget - len(t) < 0:
            log(f"용어집이 상한을 넘어 {len(kept)}개까지만 사용")
            break
        kept.append(t)
        budget -= len(t)
    return kept


class Soniox:
    def __init__(self, api_key: str):
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {api_key}"

    def upload(self, path: Path) -> str:
        with path.open("rb") as fh:
            r = self.s.post(f"{API}/v1/files", files={"file": (path.name, fh)}, timeout=3600)
        r.raise_for_status()
        return r.json()["id"]

    def create(self, file_id: str, terms: list[str]) -> str:
        body = {
            "model": MODEL,
            "file_id": file_id,
            "enable_speaker_diarization": True,      # async 모드가 화자분리 정확도 최상
            "enable_language_identification": True,  # 한영 혼용 구간 토큰별 언어 태그
            "language_hints": ["ko", "en"],
        }
        if terms:
            # terms(고유명사 배열)가 회사명·인명 인식에 가장 효과적
            body["context"] = {"terms": terms}
        r = self.s.post(f"{API}/v1/transcriptions", json=body, timeout=120)
        r.raise_for_status()
        return r.json()["id"]

    def wait(self, tid: str) -> None:
        deadline = time.time() + POLL_TIMEOUT
        last = ""
        while time.time() < deadline:
            r = self.s.get(f"{API}/v1/transcriptions/{tid}", timeout=60)
            r.raise_for_status()
            data = r.json()
            status = data.get("status")
            if status != last:
                log(f"상태: {status}")
                last = status
            if status == "completed":
                return
            if status == "error":
                raise RuntimeError(f"전사 실패: {data.get('error_message') or data}")
            time.sleep(POLL_INTERVAL)
        raise TimeoutError(f"폴링 타임아웃({POLL_TIMEOUT}s)")

    def transcript(self, tid: str) -> dict:
        r = self.s.get(f"{API}/v1/transcriptions/{tid}/transcript", timeout=300)
        r.raise_for_status()
        return r.json()

    def cleanup(self, file_id: str | None, tid: str | None) -> None:
        """원격 리소스 정리. 실패해도 파이프라인을 막지 않는다."""
        for url in (f"{API}/v1/transcriptions/{tid}" if tid else None,
                    f"{API}/v1/files/{file_id}" if file_id else None):
            if not url:
                continue
            try:
                self.s.delete(url, timeout=60)
            except requests.RequestException as e:
                log(f"정리 실패(무시): {url} — {e}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Soniox async STT")
    ap.add_argument("audio", type=Path)
    ap.add_argument("--out-dir", type=Path, default=None, help="기본값: 오디오 파일과 같은 폴더")
    ap.add_argument("--glossary", type=Path, action="append", default=[],
                    help="용어집 파일 (여러 번 지정 가능)")
    ap.add_argument("--keep-remote", action="store_true", help="원격 파일·전사 레코드를 남긴다(디버깅용)")
    args = ap.parse_args()

    api_key = os.environ.get("SONIOX_API_KEY")
    if not api_key:
        return log("SONIOX_API_KEY 가 없습니다") or 2
    if not args.audio.exists():
        return log(f"파일 없음: {args.audio}") or 2
    if args.audio.suffix.lower() not in AUDIO_EXTS:
        return log(f"지원하지 않는 확장자: {args.audio.suffix}") or 2

    minutes = audio_duration_minutes(args.audio)
    if minutes and minutes > MAX_MINUTES:
        return log(f"{minutes:.0f}분 — Soniox 상한 {MAX_MINUTES}분 초과. "
                   f"먼저 분할하세요: ffmpeg -i IN -f segment -segment_time 14400 -c copy OUT%03d.m4a") or 2

    out_dir = args.out_dir or args.audio.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.audio.stem}_stt_raw.json"

    terms = load_terms(args.glossary)
    client = Soniox(api_key)
    file_id = tid = None
    try:
        size_mb = args.audio.stat().st_size / 1_048_576
        log(f"업로드 시작: {args.audio.name} ({size_mb:.1f}MB, {minutes:.0f}분)" if minutes
            else f"업로드 시작: {args.audio.name} ({size_mb:.1f}MB)")
        file_id = client.upload(args.audio)

        log(f"전사 생성 (용어 {len(terms)}개)")
        tid = client.create(file_id, terms)

        client.wait(tid)
        result = client.transcript(tid)

        # 파이프라인이 이후 단계에서 참조할 메타를 함께 저장한다
        result["_pipeline"] = {
            "source_audio": str(args.audio.resolve()),
            "duration_minutes": round(minutes, 2) if minutes else None,
            "model": MODEL,
            "glossary_terms": len(terms),
            "transcribed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        tokens = result.get("tokens") or []
        speakers = {t.get("speaker") for t in tokens if t.get("speaker")}
        log(f"완료: 토큰 {len(tokens)}개 · 화자 {len(speakers)}명 · {out_path}")
        print(out_path)
        return 0

    except Exception as e:                      # noqa: BLE001 — 무엇이 실패하든 원격 정리는 해야 한다
        log(f"실패: {e}")
        return 1
    finally:
        if not args.keep_remote:
            client.cleanup(file_id, tid)


if __name__ == "__main__":
    sys.exit(main())
