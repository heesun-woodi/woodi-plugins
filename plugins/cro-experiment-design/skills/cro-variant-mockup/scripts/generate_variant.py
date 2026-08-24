#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""control 스크린샷을 기반으로 Gemini/OpenAI image-to-image API로 variant 시안 이미지를 생성한다.

사용 예:
    python3 generate_variant.py --control shot.png --prompt-file prompt.txt \
        --out-dir variants/HYP-A-008 --name VAR-008-a

경고: API 키는 .env 파일에만 두고, 절대 저장소에 커밋하지 않는다.
python3 표준 라이브러리만 사용한다 (pip 설치·venv 불요, Pillow 미사용).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

GEMINI_URL_TMPL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_DEFAULT_MODEL = "gemini-3.1-flash-image"
GEMINI_KEY_URL = "https://aistudio.google.com/apikey"

OPENAI_URL = "https://api.openai.com/v1/images/edits"
OPENAI_DEFAULT_MODEL = "gpt-image-1"
OPENAI_DEFAULT_SIZE = "1024x1536"  # 세로 — 모바일 화면 비율
OPENAI_KEY_URL = "https://platform.openai.com/api-keys"

MAX_RETRIES = 3
RETRY_STATUS_CODES = {429, 503}
BASE_BACKOFF_SECONDS = 2.0
MAX_CONTROL_SIDE = 1536
ALLOWED_EXTS = {".png", ".jpg", ".jpeg"}

STATUS_MESSAGES = {
    400: "요청 형식 또는 이미지 크기를 확인하세요.",
    401: "API 키를 확인하세요 (인증 실패).",
    403: "API 키를 확인하세요 (권한 거부).",
    404: "모델명을 확인하세요 (모델을 찾을 수 없음).",
}


# ---------------------------------------------------------------------------
# 유틸리티
# ---------------------------------------------------------------------------


def redact(text: str, *secrets: str) -> str:
    """주어진 비밀 문자열이 출력에 절대 섞이지 않도록 치환한다."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


def friendly_status_message(status_code: Optional[int]) -> str:
    if status_code is None:
        return "네트워크 오류가 발생했습니다."
    return STATUS_MESSAGES.get(status_code, f"HTTP {status_code} 오류가 발생했습니다.")


def mime_for(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".png":
        return "image/png"
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    raise SystemExit(f"지원하지 않는 이미지 형식입니다: {path.suffix}")


def encode_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


# ---------------------------------------------------------------------------
# .env / 키 처리 — 탐색 순서: --env 인자 → cwd .env → 환경변수
# ---------------------------------------------------------------------------


def parse_env_file(path: Path) -> dict:
    values: dict = {}
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return values
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def resolve_env_file(explicit: Optional[Path]) -> Optional[Path]:
    if explicit is not None:
        if not explicit.exists():
            raise SystemExit(f"지정한 --env 파일을 찾을 수 없습니다: {explicit}")
        return explicit
    cwd_env = Path.cwd() / ".env"
    return cwd_env if cwd_env.exists() else None


def load_provider_keys(explicit_env: Optional[Path]) -> dict:
    env_path = resolve_env_file(explicit_env)
    file_values = parse_env_file(env_path) if env_path else {}
    keys = {}
    for name in ("GEMINI_API_KEY", "OPENAI_API_KEY"):
        value = file_values.get(name) or os.environ.get(name)
        if value:
            keys[name] = value
    return keys


def print_no_key_guidance() -> None:
    print(
        "이미지 생성 API 키가 없습니다. 아래 중 하나를 발급해 .env 파일에 넣으세요.",
        file=sys.stderr,
    )
    print(f"  - Gemini (권장): {GEMINI_KEY_URL}", file=sys.stderr)
    print(f"  - OpenAI (대안): {OPENAI_KEY_URL}", file=sys.stderr)


def print_missing_key_for_provider(provider: str) -> None:
    if provider == "gemini":
        print(
            f"--provider gemini 를 지정했지만 GEMINI_API_KEY 를 찾을 수 없습니다. 발급: {GEMINI_KEY_URL}",
            file=sys.stderr,
        )
    else:
        print(
            f"--provider openai 를 지정했지만 OPENAI_API_KEY 를 찾을 수 없습니다. 발급: {OPENAI_KEY_URL}",
            file=sys.stderr,
        )


def print_ambiguous_provider_guidance() -> None:
    print(
        "GEMINI_API_KEY와 OPENAI_API_KEY가 모두 발견되었습니다. "
        "--provider gemini 또는 --provider openai 로 사용할 제공자를 지정하세요.",
        file=sys.stderr,
    )


def determine_provider(provider_arg: Optional[str], keys: dict) -> tuple[str, str]:
    """(provider, api_key)를 반환한다. 실패 시 안내 출력 후 exit(2)."""
    gemini_key = keys.get("GEMINI_API_KEY")
    openai_key = keys.get("OPENAI_API_KEY")

    if provider_arg:
        if provider_arg == "gemini":
            if not gemini_key:
                print_missing_key_for_provider("gemini")
                raise SystemExit(2)
            return "gemini", gemini_key
        else:
            if not openai_key:
                print_missing_key_for_provider("openai")
                raise SystemExit(2)
            return "openai", openai_key

    if gemini_key and openai_key:
        print_ambiguous_provider_guidance()
        raise SystemExit(2)
    if gemini_key:
        return "gemini", gemini_key
    if openai_key:
        return "openai", openai_key

    print_no_key_guidance()
    raise SystemExit(2)


# ---------------------------------------------------------------------------
# control 이미지 준비 (sips 다운스케일, Pillow 미사용)
# ---------------------------------------------------------------------------


def which_sips() -> Optional[str]:
    return shutil.which("sips")


def get_image_dimensions_via_sips(sips_path: str, path: Path) -> Optional[tuple[int, int]]:
    try:
        proc = subprocess.run(
            [sips_path, "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return None
    width = height = None
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("pixelWidth:"):
            width = int(line.split(":", 1)[1].strip())
        elif line.startswith("pixelHeight:"):
            height = int(line.split(":", 1)[1].strip())
    if width and height:
        return width, height
    return None


def prepare_control_image(path: Path) -> Path:
    """긴 변이 MAX_CONTROL_SIDE를 넘으면 sips로 리사이즈본을 캐시해 반환한다.

    캐시 파일명은 control 이미지 자체 기준 <control-stem>_resized.<ext> —
    같은 control로 재실행 시 재작업을 피하기 위함(generate_scenes.py의
    ref_image 캐시 관례를 따름). sips가 없으면 원본을 그대로 사용한다.
    """
    ext = path.suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise SystemExit(f"control 이미지는 png/jpg/jpeg만 허용됩니다: {path.suffix}")

    sips_path = which_sips()
    if not sips_path:
        print(
            "경고: sips 명령을 찾을 수 없어 control 이미지를 원본 그대로 사용합니다 (다운스케일 생략).",
            file=sys.stderr,
        )
        return path

    dims = get_image_dimensions_via_sips(sips_path, path)
    if dims is None:
        print("경고: 이미지 크기를 확인하지 못해 원본 그대로 사용합니다.", file=sys.stderr)
        return path

    width, height = dims
    if max(width, height) <= MAX_CONTROL_SIDE:
        return path

    resized_path = path.with_name(f"{path.stem}_resized{ext}")
    if resized_path.exists():
        return resized_path

    shutil.copy2(path, resized_path)
    try:
        subprocess.run(
            [sips_path, "-Z", str(MAX_CONTROL_SIDE), str(resized_path)],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception as e:  # noqa: BLE001
        print(f"경고: sips 리사이즈 실패, 원본을 사용합니다: {e}", file=sys.stderr)
        return path
    return resized_path


# ---------------------------------------------------------------------------
# HTTP — 공통 재시도 래퍼 (429/503 + Gemini RESOURCE_EXHAUSTED)
# ---------------------------------------------------------------------------


def http_post(url: str, headers: dict, body: bytes, api_key: str) -> tuple[Optional[int], bytes]:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return resp.getcode(), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except urllib.error.URLError as e:
        raise RuntimeError(f"네트워크 오류: {redact(str(e.reason), api_key)}") from None


def gemini_error_status(raw: bytes) -> Optional[str]:
    try:
        data = json.loads(raw.decode("utf-8"))
        return data.get("error", {}).get("status")
    except Exception:
        return None


def is_gemini_invalid_key_error(raw: bytes) -> bool:
    """Gemini는 잘못된 키에 401/403이 아니라 HTTP 400 + 'API key not valid'로 응답한다(실측).

    상태코드 매핑만으로는 "요청 형식을 확인하라"는 오해의 소지가 있는 안내가 나가므로,
    이 특정 케이스 하나만 에러 본문(키 문자열은 포함되지 않음)을 스니핑해 우선 처리한다.
    """
    try:
        text = raw.decode("utf-8", errors="ignore")
    except Exception:
        return False
    return "API key not valid" in text or "API_KEY_INVALID" in text


def request_with_backoff(make_request, provider: str) -> dict:
    """make_request() -> (status_code, raw_bytes). 429/503(+Gemini RESOURCE_EXHAUSTED)만 재시도."""
    start = time.monotonic()
    status: Optional[int] = None
    raw = b""
    attempt = 0
    for attempt in range(1, MAX_RETRIES + 1):
        status, raw = make_request()
        if status == 200:
            break
        should_retry = status in RETRY_STATUS_CODES
        if provider == "gemini" and not should_retry:
            if gemini_error_status(raw) == "RESOURCE_EXHAUSTED":
                should_retry = True
        if should_retry and attempt < MAX_RETRIES:
            time.sleep(BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)))
            continue
        break
    return {
        "status_code": status,
        "raw": raw,
        "attempts": attempt,
        "elapsed_seconds": round(time.monotonic() - start, 2),
    }


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------


def gemini_request(model: str, api_key: str, control_path: Path, prompt: str) -> tuple[Optional[int], bytes]:
    control_b64 = encode_b64(control_path)
    mime = mime_for(control_path)
    # 순서 중요: 이미지 파트 -> 텍스트 파트
    body = {
        "contents": [
            {
                "parts": [
                    {"inline_data": {"mime_type": mime, "data": control_b64}},
                    {"text": prompt},
                ]
            }
        ],
        # 무조건 지정 — 누락 시 HTTP 200 + 텍스트만 반환되는 조용한 실패가 발생한다.
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    body_bytes = json.dumps(body).encode("utf-8")
    url = GEMINI_URL_TMPL.format(model=model)
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    return http_post(url, headers, body_bytes, api_key)


def parse_gemini_response(raw: bytes) -> tuple[Optional[bytes], Optional[str]]:
    """이미지 파트를 base64 디코드해 반환. 없으면 (None, 텍스트 미리보기)."""
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        return None, None
    text_parts = []
    for cand in data.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"]), None
            if "text" in part:
                text_parts.append(part["text"])
    preview = " ".join(text_parts)[:200] if text_parts else None
    return None, preview


# ---------------------------------------------------------------------------
# OpenAI — multipart/form-data 직접 조립 (표준 라이브러리만)
# ---------------------------------------------------------------------------


def _field_part(boundary: str, name: str, value: str) -> bytes:
    return (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
        f"{value}\r\n"
    ).encode("utf-8")


def _file_part(boundary: str, field_name: str, path: Path, mime: str) -> bytes:
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="{path.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8")
    return header + path.read_bytes() + b"\r\n"


def build_multipart(fields: dict, file_field: str, file_path: Path, file_mime: str) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts = [_field_part(boundary, key, value) for key, value in fields.items()]
    parts.append(_file_part(boundary, file_field, file_path, file_mime))
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def openai_request(
    model: str, api_key: str, control_path: Path, prompt: str, size: str, include_fidelity: bool
) -> tuple[Optional[int], bytes]:
    mime = mime_for(control_path)
    fields = {"model": model, "prompt": prompt, "size": size}
    if include_fidelity:
        fields["input_fidelity"] = "high"  # control 유지 강화 — 미지원 모델이면 400에서 감지 후 제거 재시도
    body, content_type = build_multipart(fields, "image[]", control_path, mime)
    headers = {"Content-Type": content_type, "Authorization": f"Bearer {api_key}"}
    return http_post(OPENAI_URL, headers, body, api_key)


def openai_error_message(raw: bytes) -> str:
    try:
        data = json.loads(raw.decode("utf-8"))
        return data.get("error", {}).get("message", "")
    except Exception:
        return ""


def parse_openai_response(raw: bytes) -> Optional[bytes]:
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        return None
    items = data.get("data", [])
    if items and items[0].get("b64_json"):
        return base64.b64decode(items[0]["b64_json"])
    return None


# ---------------------------------------------------------------------------
# 생성 오케스트레이션
# ---------------------------------------------------------------------------


def generate_image(
    provider: str, model: str, api_key: str, control_path: Path, prompt: str, size: str
) -> dict:
    if provider == "gemini":
        result = request_with_backoff(
            lambda: gemini_request(model, api_key, control_path, prompt), provider
        )
        if result["status_code"] == 200:
            image_bytes, preview = parse_gemini_response(result["raw"])
            if image_bytes is None:
                msg = "Gemini 응답에 이미지 파트가 없습니다 (텍스트만 반환됨)."
                if preview:
                    msg += f" 참고 텍스트: {preview}"
                return {
                    "status": "failed",
                    "error": msg,
                    "attempts": result["attempts"],
                    "elapsed_seconds": result["elapsed_seconds"],
                }
            return {
                "status": "success",
                "image": image_bytes,
                "attempts": result["attempts"],
                "elapsed_seconds": result["elapsed_seconds"],
            }
        # 상태코드 매핑보다 우선: Gemini는 잘못된 키에도 400을 반환하므로, 이 경우만 본문을 확인해
        # "요청 형식을 확인하라"는 오해의 소지가 있는 안내 대신 정확한 키 안내를 낸다.
        if result["status_code"] == 400 and is_gemini_invalid_key_error(result["raw"]):
            return {
                "status": "failed",
                "error": "API 키를 확인하세요 (Gemini는 잘못된 키에 400을 반환합니다).",
                "attempts": result["attempts"],
                "elapsed_seconds": result["elapsed_seconds"],
            }
        friendly = friendly_status_message(result["status_code"])
        return {
            "status": "failed",
            "error": f"HTTP {result['status_code']} — {friendly}",
            "attempts": result["attempts"],
            "elapsed_seconds": result["elapsed_seconds"],
        }

    # openai
    start = time.monotonic()
    include_fidelity = True
    result = request_with_backoff(
        lambda: openai_request(model, api_key, control_path, prompt, size, include_fidelity),
        provider,
    )
    total_attempts = result["attempts"]
    if result["status_code"] == 400 and "input_fidelity" in openai_error_message(result["raw"]).lower():
        include_fidelity = False
        result = request_with_backoff(
            lambda: openai_request(model, api_key, control_path, prompt, size, include_fidelity),
            provider,
        )
        total_attempts += result["attempts"]

    elapsed = round(time.monotonic() - start, 2)
    if result["status_code"] == 200:
        image_bytes = parse_openai_response(result["raw"])
        if image_bytes is None:
            return {
                "status": "failed",
                "error": "OpenAI 응답에 이미지 데이터(b64_json)가 없습니다.",
                "attempts": total_attempts,
                "elapsed_seconds": elapsed,
            }
        return {
            "status": "success",
            "image": image_bytes,
            "attempts": total_attempts,
            "elapsed_seconds": elapsed,
        }
    friendly = friendly_status_message(result["status_code"])
    return {
        "status": "failed",
        "error": f"HTTP {result['status_code']} — {friendly}",
        "attempts": total_attempts,
        "elapsed_seconds": elapsed,
    }


# ---------------------------------------------------------------------------
# 출력 파일 / metadata.json
# ---------------------------------------------------------------------------


def next_output_index(out_dir: Path, name: str) -> int:
    max_n = 0
    for p in out_dir.glob(f"{name}_*.png"):
        suffix = p.stem[len(name) + 1 :]
        if suffix.isdigit():
            max_n = max(max_n, int(suffix))
    return max_n + 1


def merge_metadata(out_dir: Path, new_entries: list) -> None:
    """metadata.json에 병합 — 기존 항목 보존, file 필드로 중복 시 덮어쓴다."""
    metadata_path = out_dir / "metadata.json"
    existing = {"variants": []}
    if metadata_path.exists():
        try:
            loaded = json.loads(metadata_path.read_text(encoding="utf-8"))
            if isinstance(loaded.get("variants"), list):
                existing = loaded
        except (json.JSONDecodeError, OSError):
            pass

    by_key = {}
    for entry in existing["variants"]:
        if isinstance(entry, dict):
            key = entry.get("file") or f"__existing_{uuid.uuid4().hex[:8]}"
            by_key[key] = entry
    for entry in new_entries:
        key = entry.get("file") or f"__failed_{uuid.uuid4().hex[:8]}"
        by_key[key] = entry

    existing["variants"] = list(by_key.values())
    metadata_path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="control 스크린샷 기반 variant 시안 이미지 생성 (Gemini/OpenAI image-to-image)."
    )
    parser.add_argument("--control", required=True, type=Path, help="control 스크린샷 경로 (png/jpg/jpeg)")
    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt-file", type=Path, help="프롬프트 텍스트 파일 경로")
    prompt_group.add_argument("--prompt", type=str, help="프롬프트 텍스트 (직접 입력)")
    parser.add_argument("--out-dir", required=True, type=Path, help="출력 디렉토리, 예: variants/HYP-A-008")
    parser.add_argument("--name", required=True, help="variant 이름, 예: VAR-008-a")
    parser.add_argument("--provider", choices=["gemini", "openai"], default=None, help="이미지 생성 제공자")
    parser.add_argument("--model", default=None, help="모델명 (기본값은 제공자별 권장 모델)")
    parser.add_argument("--env", type=Path, default=None, help="명시적 .env 경로")
    parser.add_argument("--count", type=int, default=1, help="생성할 이미지 수 (기본 1, 순차 생성)")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()

    if args.count < 1:
        raise SystemExit("--count는 1 이상이어야 합니다.")

    control_path = args.control
    if not control_path.exists() or not control_path.is_file():
        raise SystemExit(f"control 이미지를 찾을 수 없습니다: {control_path}")

    if args.prompt_file:
        try:
            prompt_text = args.prompt_file.read_text(encoding="utf-8").strip()
        except OSError as e:
            raise SystemExit(f"프롬프트 파일을 읽을 수 없습니다: {args.prompt_file} ({e})")
    else:
        prompt_text = (args.prompt or "").strip()
    if not prompt_text:
        raise SystemExit("프롬프트가 비어 있습니다.")

    keys = load_provider_keys(args.env)
    provider, api_key = determine_provider(args.provider, keys)

    if args.model:
        model = args.model
    else:
        model = GEMINI_DEFAULT_MODEL if provider == "gemini" else OPENAI_DEFAULT_MODEL

    control_for_api = prepare_control_image(control_path)

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    successes = 0
    for i in range(1, args.count + 1):
        try:
            result = generate_image(provider, model, api_key, control_for_api, prompt_text, OPENAI_DEFAULT_SIZE)
        except Exception as e:  # noqa: BLE001 - http_post는 429/503 이외의 URLError(DNS 실패·연결
            # 거부 등)를 RuntimeError로 던진다. 이걸 못 잡으면 raw traceback으로 죽어서 (a) 한국어
            # 안내가 안 나가고 (b) 아래 metadata 기록도 건너뛰게 되므로, 표준 실패 형태로 정규화한다.
            result = {
                "status": "failed",
                "error": redact(
                    f"네트워크 연결을 확인하세요 (DNS/연결 실패 가능): {type(e).__name__}: {e}", api_key
                ),
                "attempts": 0,
                "elapsed_seconds": 0.0,
            }
        created = time.strftime("%Y-%m-%dT%H:%M:%S%z")

        if result["status"] == "success":
            idx = next_output_index(out_dir, args.name)
            out_path = out_dir / f"{args.name}_{idx}.png"
            out_path.write_bytes(result["image"])
            successes += 1
            entry = {
                "name": args.name,
                "file": out_path.name,
                "provider": provider,
                "model": model,
                "control": str(control_path),
                "prompt_chars": len(prompt_text),
                "elapsed_seconds": result["elapsed_seconds"],
                "attempts": result["attempts"],
                "status": "success",
                "created": created,
            }
            print(f"OK {out_path}")
        else:
            error_msg = redact(result["error"], api_key)
            entry = {
                "name": args.name,
                "file": None,
                "provider": provider,
                "model": model,
                "control": str(control_path),
                "prompt_chars": len(prompt_text),
                "elapsed_seconds": result["elapsed_seconds"],
                "attempts": result["attempts"],
                "status": "failed",
                "created": created,
                "error": error_msg,
            }
            print(f"[{i}/{args.count}] 생성 실패: {error_msg}", file=sys.stderr)

        # iteration마다 즉시 병합 — 이후 iteration이 실패해도 앞선 성공분이 metadata.json에
        # 기록되지 않는 고아 파일이 되지 않는다 (--count>1일 때 특히 중요).
        merge_metadata(out_dir, [entry])

    if successes == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
