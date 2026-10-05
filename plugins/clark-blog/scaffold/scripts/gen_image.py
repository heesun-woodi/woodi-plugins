#!/usr/bin/env python3
"""image-plan.md의 ai 슬롯을 Gemini 이미지 모델로 생성해 images/NN-<slug>.png로 저장한다.

실행(작업 폴더에서):
    uv run --with google-genai --with pillow scripts/gen_image.py work/posts/001-x/images/image-plan.md
    python3 scripts/gen_image.py <image-plan.md> --dry-run      # 키·패키지 없이 파싱·프롬프트·파일명만 출력

- 표에서 `유형`이 ai인 행만 처리한다(photo 행은 건드리지 않음). 슬롯 번호 = draft-v2.md의 `![슬롯: …]()` 순서.
- 프롬프트 = PROMPT_PREFIX + 표의 프롬프트 + PROMPT_SUFFIX. 두 문자열은
  skills/blog-image-director/references/prompt-patterns.md의 "공통 접두/접미"와 글자 그대로 같아야 한다.
- 성공한 슬롯은 표의 `파일` 열을 post 폴더 기준 상대경로(images/01-cover.png)로 갱신해 image-plan.md를 다시 쓴다.
- GEMINI_API_KEY: --env → cwd/.env(= 작업 폴더) → image-plan.md 상위 폴더들의 .env → 환경변수.
  키가 실제로 든 첫 파일을 쓴다(`export KEY=…`, 따옴표, 줄 끝 `# 주석` 허용). 값은 출력하지 않는다.
- 비용: 장당 COST_PER_IMAGE_USD(추정치, 검증된 단가 아님 — https://ai.google.dev/pricing 확인). 재생성도 과금된다.
- 의존: google-genai(필수, --dry-run 제외), pillow(선택: 가로 --size px 리사이즈. 없으면 원본 저장 + 경고).
종료 코드: 0=전부 성공(또는 dry-run), 1=실패 슬롯 있음, 2=사용 오류.
"""
import argparse
import base64
import io
import os
import re
import sys
import tempfile
import time

DEFAULT_MODEL = "gemini-3-pro-image"  # product-mockup generate_scenes.py와 같은 모델
MAX_RETRIES = 3
RETRY_STATUS_CODES = {429, 503}
BASE_BACKOFF_SECONDS = 2.0
# 추정치 — gemini-3-pro-image 2K 단가는 요금 페이지에서 확인(https://ai.google.dev/pricing)
COST_PER_IMAGE_USD = 0.04
KINDS = {"ai", "photo"}

# prompt-patterns.md "공통 접두/접미"와 동일하게 유지할 것(tests/test_gen_image.py가 대조).
PROMPT_PREFIX = ("photorealistic, Korean forklift training yard / warehouse, "
                 "no text, no letters, no watermark, no close-up faces")
PROMPT_SUFFIX = ("natural light, wide landscape 3:2 composition, people only seen from behind or far away, "
                 "no brand logos, no readable signs, no license plates, no numbers")

# 목적 → 파일명 slug(앞에서부터 처음 맞는 것). 없으면 목적의 영숫자, 그것도 없으면 "scene".
PURPOSE_SLUGS = [("표지", "cover"), ("커버", "cover"), ("cta", "academy"), ("학원", "academy"),
                 ("시험", "exam"), ("절차", "steps"), ("장비", "equipment"), ("적재", "loading"),
                 ("하역", "loading"), ("작업", "work"), ("주행", "driving"), ("안전", "safety"),
                 ("서류", "documents"), ("자격", "documents"), ("요약", "summary")]

COLS = {"slot": "슬롯", "where": "위치", "purpose": "목적", "kind": "유형",
        "prompt": "프롬프트", "caption": "캡션", "file": "파일"}


def split_row(line):
    s = line.strip()
    if not s.startswith("|"):
        return None
    return [c.strip() for c in s.strip("|").split("|")]


def parse_plan(text):
    """표를 파싱해 (header_index, rows) 반환. rows: dict(slot, purpose, kind, prompt, caption, file, line)."""
    lines = text.splitlines()
    idx, rows, ncols = None, [], 0
    for i, line in enumerate(lines):
        if idx is not None and not line.strip():
            break  # 첫 표가 끝난 뒤 빈 줄 → 그 아래는 읽지 않는다
        cells = split_row(line)
        if cells is None:
            continue
        if idx is None:
            if cells and cells[0].startswith(COLS["slot"]):
                idx = {}
                for key, name in COLS.items():
                    for j, c in enumerate(cells):
                        if c.startswith(name):
                            idx[key] = j
                            break
                missing = [COLS[k] for k in COLS if k not in idx]
                if missing:
                    raise ValueError("image-plan.md 표 머리에 열이 없습니다: " + ", ".join(missing))
                ncols = len(cells)
            continue
        if not re.fullmatch(r"\d{1,2}", cells[0]):
            continue  # 구분선(|---|) 등
        if len(cells) > ncols:
            raise ValueError(f"슬롯 {cells[0]} 행의 칸 수({len(cells)})가 표 머리({ncols})보다 많습니다 — 칸 안에 '|'가 있는지 확인하세요.")
        get = lambda k: cells[idx[k]] if idx[k] < len(cells) else ""
        rows.append({"slot": "%02d" % int(cells[0]), "purpose": get("purpose"),
                     "kind": get("kind").lower(), "prompt": get("prompt"),
                     "caption": get("caption"), "file": get("file"), "line": i})
        if rows[-1]["kind"] not in KINDS:
            print(f"경고: 슬롯 {rows[-1]['slot']}의 유형 '{get('kind')}'은 ai/photo가 아니어서 건너뜁니다.", file=sys.stderr)
    if idx is None:
        raise ValueError("image-plan.md에서 '| 슬롯 | …' 표 머리를 찾지 못했습니다.")
    return idx, rows


def parse_only(value):
    if not value:
        return None
    out = set()
    for tok in value.split(","):
        tok = tok.strip()
        if not tok:
            continue
        if not tok.isdigit():
            raise ValueError(f"--only 값은 슬롯 번호여야 합니다: {tok}")
        out.add("%02d" % int(tok))
    return out


def select_ai_rows(rows, only=None):
    """ai 행만 고르고 --only로 거른다. only에 ai가 아닌/없는 번호가 있으면 ValueError."""
    ai = [r for r in rows if r["kind"] == "ai"]
    if only is None:
        return ai
    known = {r["slot"]: r["kind"] for r in rows}
    bad = sorted(s for s in only if s not in known)
    if bad:
        raise ValueError("표에 없는 슬롯 번호: " + ", ".join(bad))
    notai = sorted(s for s in only if known[s] != "ai")
    if notai:
        raise ValueError("ai 슬롯이 아닙니다(photo는 생성 대상 아님): " + ", ".join(notai))
    return [r for r in ai if r["slot"] in only]


def slug_for(purpose):
    low = purpose.lower()
    for key, slug in PURPOSE_SLUGS:
        if key in low:
            return slug
    ascii_part = re.sub(r"[^a-z0-9]+", "-", low).strip("-")
    return ascii_part[:30] or "scene"


def target_name(row):
    """이미 `파일` 열에 .png 경로가 있으면 그 파일명을 유지(재생성 시 같은 파일 덮어쓰기)."""
    f = row["file"].strip("` ")
    if f.lower().endswith(".png"):
        return os.path.basename(f)
    return f"{row['slot']}-{slug_for(row['purpose'])}.png"


def build_prompt(scene):
    return f"{PROMPT_PREFIX}. {scene.strip().rstrip('.')}. {PROMPT_SUFFIX}."


def rewrite_plan(text, idx, updates):
    """updates: {line_no: 새 파일 경로}. 해당 행의 `파일` 칸만 바꾼다."""
    lines = text.splitlines()
    for ln, value in updates.items():
        cells = split_row(lines[ln])
        while len(cells) <= idx["file"]:
            cells.append("")
        cells[idx["file"]] = value
        lines[ln] = "|" + "|".join(f" {c} " if c else " " for c in cells) + "|"
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def read_env_key(path):
    """.env에서 GEMINI_API_KEY 값을 읽는다(없으면 None). 값은 출력하지 않는다."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            t = line.strip()
            if not t or t.startswith("#"):
                continue
            if t.startswith("export "):
                t = t[len("export "):].lstrip()
            k, sep, v = t.partition("=")
            if not sep or k.strip() != "GEMINI_API_KEY":
                continue
            v = v.strip()
            if v[:1] in ("'", '"'):
                end = v.find(v[0], 1)
                v = v[1:end] if end != -1 else v[1:]
            else:
                v = re.split(r"\s#", v, maxsplit=1)[0].strip()
            if v:
                return v
    return None


def find_api_key(plan_path, env_override=None):
    """순서: --env → cwd/.env → plan 상위 폴더들의 .env → 환경변수. 키가 든 첫 파일을 쓴다."""
    cands = [env_override] if env_override else []
    cands.append(os.path.join(os.getcwd(), ".env"))
    d = os.path.dirname(os.path.abspath(plan_path))
    while True:
        cands.append(os.path.join(d, ".env"))
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    seen = set()
    for p in cands:
        ap = os.path.abspath(p)
        if ap in seen or not os.path.isfile(ap):
            continue
        seen.add(ap)
        v = read_env_key(ap)
        if v:
            return v, p
    v = os.environ.get("GEMINI_API_KEY", "").strip()
    return (v, "환경변수") if v else (None, None)


def write_plan_atomic(path, content):
    """같은 폴더 임시 파일에 쓰고 os.replace — 중간에 끊겨도 image-plan.md가 반쯤 쓰이지 않는다."""
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".image-plan-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def save_image(data, out_path, width):
    try:
        from PIL import Image
    except ImportError:
        print(f"경고: pillow가 없어 리사이즈 없이 원본을 저장합니다: {out_path}", file=sys.stderr)
        with open(out_path, "wb") as f:
            f.write(data)
        return "원본"
    with Image.open(io.BytesIO(data)) as im:
        im = im.convert("RGB")
        w, h = im.size
        if w != width:
            im = im.resize((width, round(h * width / w)), Image.LANCZOS)
        im.save(out_path, "PNG")
        return "%dx%d" % im.size


def generate_one(client, model, prompt):
    from google.genai import errors as genai_errors
    last = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            it = client.interactions.create(model=model, input=[{"type": "text", "text": prompt}],
                                            response_format={"type": "image", "image_size": "2K"})
            img = it.output_image
            if img is None or not img.data:
                raise RuntimeError("응답에 이미지가 없습니다(output_image 비어 있음)")
            return base64.b64decode(img.data)
        except genai_errors.APIError as e:
            code = getattr(e, "code", None)
            last = RuntimeError(f"APIError {code}: {getattr(e, 'message', e)}")
            if code in RETRY_STATUS_CODES and attempt < MAX_RETRIES:
                time.sleep(BASE_BACKOFF_SECONDS * 2 ** (attempt - 1))
                continue
            raise last
    raise last


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="image-plan.md 표의 ai 슬롯을 Gemini로 생성해 NN-<slug>.png로 저장하고 `파일` 열을 갱신합니다.",
        epilog=f"종료 코드: 0=성공(또는 --dry-run), 1=실패 슬롯 있음, 2=사용 오류. 예상 비용(추정치): 장당 약 ${COST_PER_IMAGE_USD:.2f}.",
        add_help=False)
    ap._positionals.title, ap._optionals.title = "인자", "옵션"
    ap.add_argument("-h", "--help", action="help", help="도움말을 보여주고 종료")
    ap.add_argument("plan", help="images/image-plan.md 경로")
    ap.add_argument("--only", metavar="01,03", help="이 슬롯 번호만 (재)생성(쉼표 구분)")
    ap.add_argument("--out-dir", metavar="DIR", help="저장 폴더(기본: image-plan.md가 있는 폴더 = posts/NNN/images)")
    ap.add_argument("--size", type=int, default=1200, help="저장 가로 픽셀(기본 1200, pillow 필요)")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"Gemini 이미지 모델(기본 {DEFAULT_MODEL})")
    ap.add_argument("--env", metavar="PATH", help="GEMINI_API_KEY가 든 .env 경로를 직접 지정")
    ap.add_argument("--dry-run", action="store_true", help="API 호출 없이 슬롯·프롬프트·파일명만 출력")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code in (0, None) else 2

    if a.size <= 0:
        print("오류: --size는 0보다 커야 합니다.", file=sys.stderr)
        return 2
    if not os.path.isfile(a.plan):
        print(f"오류: 파일을 찾을 수 없습니다: {a.plan}", file=sys.stderr)
        return 2
    with open(a.plan, encoding="utf-8") as f:
        text = f.read()
    try:
        idx, rows = parse_plan(text)
        targets = select_ai_rows(rows, parse_only(a.only))
    except ValueError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 2

    plan_dir = os.path.dirname(os.path.abspath(a.plan))
    out_dir = os.path.abspath(a.out_dir) if a.out_dir else plan_dir
    post_dir = os.path.dirname(plan_dir)
    n_photo = sum(1 for r in rows if r["kind"] == "photo")
    print(f"슬롯 {len(rows)}개 (ai {sum(1 for r in rows if r['kind'] == 'ai')}, photo {n_photo}) → 이번 대상 ai {len(targets)}개")
    if not targets:
        print("생성할 ai 슬롯이 없습니다.")
        return 0
    for r in targets:
        if not r["prompt"]:
            print(f"오류: 슬롯 {r['slot']}의 프롬프트 칸이 비어 있습니다.", file=sys.stderr)
            return 2

    if a.dry_run:
        for r in targets:
            out = os.path.join(out_dir, target_name(r))
            print(f"\n[{r['slot']}] 목적: {r['purpose']} | 캡션: {r['caption']}")
            print(f"  파일: {os.path.relpath(out, post_dir)}")
            print(f"  프롬프트: {build_prompt(r['prompt'])}")
        print(f"\n(dry-run) API 호출 없음. 예상 비용(추정치): 약 ${COST_PER_IMAGE_USD * len(targets):.2f}"
              f" (장당 ${COST_PER_IMAGE_USD:.2f} 가정 — https://ai.google.dev/pricing 확인)")
        return 0

    key, src = find_api_key(a.plan, a.env)
    if not key:
        print("오류: GEMINI_API_KEY가 없습니다. 작업 폴더 .env에 GEMINI_API_KEY=… 를 넣으세요"
              "(발급: https://aistudio.google.com/apikey).", file=sys.stderr)
        return 2
    try:
        from google import genai
    except ImportError:
        print("오류: google-genai가 없습니다. `uv run --with google-genai --with pillow scripts/gen_image.py …`로 실행하세요.",
              file=sys.stderr)
        return 2
    print(f"키: {src}에서 읽음 · 모델: {a.model}")
    client = genai.Client(api_key=key)
    os.makedirs(out_dir, exist_ok=True)

    updates, ok, fail = {}, [], []

    def persist():
        if updates:
            write_plan_atomic(a.plan, rewrite_plan(text, idx, updates))

    try:
        for r in targets:
            out = os.path.join(out_dir, target_name(r))
            try:
                data = generate_one(client, a.model, build_prompt(r["prompt"]))
                res = save_image(data, out, a.size)
            except Exception as e:  # noqa: BLE001 — 실패 슬롯은 보고하고 다음으로
                print(f"[FAIL] {r['slot']} {type(e).__name__}: {e}", file=sys.stderr)
                fail.append(r["slot"])
                continue
            rel = os.path.relpath(out, post_dir)
            updates[r["line"]] = rel
            ok.append(r["slot"])
            persist()  # 슬롯마다 저장 — 중간에 끊겨도 완료분은 남는다
            print(f"[OK] {r['slot']} → {rel} ({res})")
    finally:
        persist()  # KeyboardInterrupt 등으로 빠져나가도 완료분 보존
    print(f"\n요약: 성공 {len(ok)} ({', '.join(ok) or '-'}) · 실패 {len(fail)} ({', '.join(fail) or '-'})")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
