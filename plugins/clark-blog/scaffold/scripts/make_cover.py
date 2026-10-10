#!/usr/bin/env python3
"""대표이미지(표지) 합성 — 배경 이미지 위에 브랜드 배지·제목·전화번호를 얹어 1:1 PNG를 만든다.

실행(작업 폴더에서, Pillow 필요):
    uv run --with pillow scripts/make_cover.py --bg work/posts/001-x/images/00-bg.png \\
        --title "지게차 면허 갱신|주기와 준비물" --sub "의정부 중장비학원" \\
        --out work/posts/001-x/images/00-cover.png
    python3 scripts/make_cover.py … --dry-run      # 폰트 경로·줄 목록·줄별 픽셀 폭만 출력, 파일 안 씀

- 비용 없음: API 호출 없이 로컬에서 Pillow(PIL.Image, ImageDraw, ImageFont, ImageFilter)만 쓴다.
  배경(00-bg.png)은 gen_image.py가 만든다(그쪽만 과금).
- 레이아웃: 배경 중앙 1:1 크롭 → 하단 40% 어두운 그라데이션 → 좌상단 브랜드 배지(진녹색 #1F5E3A)
  → 제목 2~3줄(흰 글자 + 검정 외곽선 + 반투명 진녹색 패널) → --sub 작은 줄 → 하단 전화번호.
  전체는 중앙 80% 안전 영역 안. `|`로 받은 줄을 우선 쓰고, 한 줄이 패널 폭을 넘으면 글리프 폭 기준으로 자동 줄바꿈.
- 폰트: --font-dir → ~/Library/Fonts/Pretendard-{ExtraBold,SemiBold}.otf
  → %LOCALAPPDATA%\\Microsoft\\Windows\\Fonts\\Pretendard-*.otf(Windows 사용자 글꼴) → %WINDIR%\\Fonts\\Pretendard-*.otf
  → /System/Library/Fonts/AppleSDGothicNeo.ttc(Bold·SemiBold) → %WINDIR%\\Fonts\\malgunbd.ttf(제목)·malgun.ttf(보조, 맑은 고딕).
  환경변수가 없으면 그 후보는 건너뛴다. 모두 없으면 추측 렌더 없이 exit 2.
  --no-system-fonts는 --font-dir 말고는 모두(사용자·시스템 글꼴 폴더) 끈다.
종료 코드: 0=성공(또는 --dry-run), 2=사용 오류·폰트 없음·배경 없음.
"""
import argparse
import os
import sys
for _s in (sys.stdout, sys.stderr):  # Windows 콘솔(cp949)에서도 한글·이모지 출력이 죽지 않게
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:  # 테스트가 import 실패를 skip으로 처리
    Image = ImageDraw = ImageFilter = ImageFont = None

GREEN = (0x1F, 0x5E, 0x3A)
TITLE_FONT = "Pretendard-ExtraBold.otf"
SUB_FONT = "Pretendard-SemiBold.otf"
USER_FONT_DIR = os.path.expanduser("~/Library/Fonts")
APPLE_TTC = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
MALGUN_TITLE, MALGUN_SUB = "malgunbd.ttf", "malgun.ttf"  # Windows 맑은 고딕(굵게·보통)
NO_FONT_MSG = ("한글 폰트 없음 — Pretendard 설치 또는 --font-dir "
               "(Windows: Pretendard 설치 또는 맑은 고딕(C:\\Windows\\Fonts\\malgunbd.ttf) 확인)")
SAFE = 0.10  # 한쪽 여백 비율(중앙 80% 안전 영역)


def _ttc_index(path, want):
    """AppleSDGothicNeo.ttc에서 스타일 이름이 want인 face의 index(없으면 None)."""
    for i in range(16):
        try:
            f = ImageFont.truetype(path, 20, index=i)
        except (OSError, ValueError):
            break
        if f.getname()[1] == want:
            return i
    return None


def font_candidates(font_dir=None, system=True, env=None):
    """탐색 순서대로 (제목 후보, 보조 후보) 목록. 후보는 (경로, face) — face는 index(int) 또는 TTC 스타일 이름 튜플.

    파일 존재 여부는 보지 않는다(find_fonts가 본다). 환경변수(LOCALAPPDATA·WINDIR)가 없으면 그 후보는 뺀다.
    """
    env = os.environ if env is None else env
    dirs = [font_dir] if font_dir else []
    win = env.get("WINDIR") or env.get("SystemRoot")
    if system:
        dirs.append(USER_FONT_DIR)
        if env.get("LOCALAPPDATA"):
            dirs.append(os.path.join(env["LOCALAPPDATA"], "Microsoft", "Windows", "Fonts"))
        if win:
            dirs.append(os.path.join(win, "Fonts"))
    title = [(os.path.join(d, TITLE_FONT), 0) for d in dirs]
    sub = [(os.path.join(d, SUB_FONT), 0) for d in dirs]
    if system:
        title.append((APPLE_TTC, ("Bold",)))
        sub.append((APPLE_TTC, ("SemiBold", "Bold")))
        if win:
            title.append((os.path.join(win, "Fonts", MALGUN_TITLE), 0))
            sub.append((os.path.join(win, "Fonts", MALGUN_SUB), 0))
    return title, sub


def _pick(cands):
    for path, face in cands:
        if os.path.isfile(path):
            if isinstance(face, tuple):  # TTC: 스타일 이름으로 index를 찾는다
                face = next((i for i in (_ttc_index(path, w) for w in face) if i is not None), 0)
            return path, face
    return None


def find_fonts(font_dir=None, system=True, env=None):
    """(제목 폰트 경로+index, 보조 폰트 경로+index) 반환. 없으면 None."""
    title_c, sub_c = font_candidates(font_dir, system, env)
    title = _pick(title_c)
    if not title:
        return None
    return title, _pick(sub_c) or title


def load(spec, px):
    return ImageFont.truetype(spec[0], px, index=spec[1])


def text_w(font, text):
    return font.getlength(text)


def wrap_line(font, line, max_w):
    """한 줄이 max_w를 넘으면 글리프 폭 기준으로 나눈다(공백이 있으면 공백 우선, 없으면 글자 단위)."""
    line = line.strip()
    if text_w(font, line) <= max_w:
        return [line]
    out, cur = [], ""
    for word in line.split(" "):
        trial = (cur + " " + word).strip()
        if text_w(font, trial) <= max_w:
            cur = trial
            continue
        if cur:
            out.append(cur)
            cur = ""
        if text_w(font, word) <= max_w:
            cur = word
            continue
        for ch in word:  # 단어 하나가 너무 길면 글자 단위
            if cur and text_w(font, cur + ch) > max_w:
                out.append(cur)
                cur = ch
            else:
                cur += ch
    if cur:
        out.append(cur)
    return out


def layout_title(spec, title, size, max_lines=4):
    """(font, lines, px) — 패널 폭 안에 들어가고 줄 수가 max_lines 이하가 될 때까지 글자 크기를 줄인다."""
    raw = [t.strip() for t in title.split("|") if t.strip()]
    max_w = size * (1 - 2 * SAFE) - size * 0.08  # 패널 안쪽 여백 제외
    px = round(size * 0.10)
    while True:
        font = load(spec, px)
        lines = [w for r in raw for w in wrap_line(font, r, max_w)]
        if len(lines) <= max_lines or px <= round(size * 0.05):
            return font, lines, px
        px -= 2


def compose(bg_path, title, sub, phone, brand, size, fonts):
    title_spec, sub_spec = fonts
    im = Image.open(bg_path).convert("RGB")
    w, h = im.size
    s = min(w, h)
    im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)).resize((size, size), Image.LANCZOS)

    # 하단 40% 어두운 그라데이션
    grad = Image.new("L", (1, size), 0)
    top = int(size * 0.6)
    for y in range(top, size):
        grad.putpixel((0, y), int(200 * (y - top) / (size - top)))
    shade = Image.new("RGB", (size, size), (0, 0, 0))
    im = Image.composite(shade, im, grad.resize((size, size)))

    d = ImageDraw.Draw(im, "RGBA")
    m = round(size * SAFE)

    # 좌상단 브랜드 배지: CLARK 소제목 + 학원명
    f_tag, f_brand = load(sub_spec, round(size * 0.034)), load(title_spec, round(size * 0.048))
    pad = round(size * 0.022)
    bw = max(text_w(f_tag, "CLARK"), text_w(f_brand, brand)) + pad * 2
    bh = round(size * 0.034) + round(size * 0.048) + pad * 2 + round(size * 0.008)
    d.rounded_rectangle((m, m, m + bw, m + bh), radius=round(size * 0.02), fill=GREEN + (255,))
    d.text((m + pad, m + pad), "CLARK", font=f_tag, fill=(255, 255, 255, 255))
    d.text((m + pad, m + pad + round(size * 0.034) + round(size * 0.008)), brand, font=f_brand, fill=(255, 255, 255, 255))

    # 하단 전화번호(안전 영역 하단에 맞춤)
    f_phone = load(title_spec, round(size * 0.058))
    pb = size - m
    ph_h = round(size * 0.058)
    d.text((size // 2, pb), phone, font=f_phone, fill=(255, 255, 255, 255), anchor="ms",
           stroke_width=max(2, size // 300), stroke_fill=(0, 0, 0, 255))
    bottom = pb - ph_h - round(size * 0.03)

    # 보조 줄(제목 아래)
    f_sub = load(sub_spec, round(size * 0.04))
    if sub:
        d.text((size // 2, bottom), sub, font=f_sub, fill=(255, 255, 255, 255), anchor="ms",
               stroke_width=max(2, size // 400), stroke_fill=(0, 0, 0, 255))
        bottom -= round(size * 0.04) + round(size * 0.03)

    # 제목 패널
    font, lines, px = layout_title(title_spec, title, size)
    lh = round(px * 1.28)
    ppad = round(size * 0.035)
    ph = lh * len(lines) + ppad * 2 - round(px * 0.28)
    py1 = bottom
    py0 = max(py1 - ph, m + bh + round(size * 0.02))
    d.rounded_rectangle((m, py0, size - m, py1), radius=round(size * 0.025), fill=GREEN + (200,))
    y = py0 + ppad
    stroke = max(2, px // 14)
    for ln in lines:
        d.text((size // 2, y), ln, font=font, fill=(255, 255, 255, 255), anchor="mt",
               stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
        y += lh
    return im


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="배경 이미지 + 제목·브랜드 배지·전화번호를 합성해 대표이미지(1:1)를 만듭니다. 비용 없음(로컬 Pillow).",
        epilog="종료 코드: 0=성공(또는 --dry-run), 2=사용 오류·폰트 없음·배경 없음.", add_help=False)
    ap._positionals.title, ap._optionals.title = "인자", "옵션"
    ap.add_argument("-h", "--help", action="help", help="도움말을 보여주고 종료")
    ap.add_argument("--bg", required=True, help="배경 이미지 경로(예: images/00-bg.png)")
    ap.add_argument("--title", required=True, help='제목. 줄바꿈은 "줄1|줄2|줄3"')
    ap.add_argument("--sub", default="", help="제목 아래 작은 줄(선택)")
    ap.add_argument("--phone", default="031-855-9948", help="하단 전화번호(기본 031-855-9948)")
    ap.add_argument("--brand", default="클라크중장비운전학원", help="배지의 학원명(기본 클라크중장비운전학원)")
    ap.add_argument("--out", required=True, help="출력 PNG 경로(예: images/00-cover.png)")
    ap.add_argument("--size", type=int, default=1000, help="한 변 픽셀(기본 1000)")
    ap.add_argument("--font-dir", metavar="DIR", help="Pretendard-ExtraBold.otf·SemiBold.otf가 든 폴더(우선 탐색)")
    ap.add_argument("--no-system-fonts", action="store_true", help="--font-dir 외의 사용자·시스템 폰트 탐색(~/Library/Fonts·%%LOCALAPPDATA%%·%%WINDIR%%·AppleSDGothicNeo)을 끔")
    ap.add_argument("--dry-run", action="store_true", help="폰트·줄·폭·출력 경로만 출력하고 파일을 쓰지 않음")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code in (0, None) else 2

    if Image is None:
        print("오류: Pillow가 없습니다. `uv run --with pillow scripts/make_cover.py …`로 실행하세요.", file=sys.stderr)
        return 2
    if a.size < 200:
        print("오류: --size는 200 이상이어야 합니다.", file=sys.stderr)
        return 2
    if not [t for t in a.title.split("|") if t.strip()]:
        print("오류: --title이 비어 있습니다.", file=sys.stderr)
        return 2
    if not os.path.isfile(a.bg):
        print(f"오류: 배경 이미지를 찾을 수 없습니다: {a.bg}", file=sys.stderr)
        return 2
    fonts = find_fonts(a.font_dir, system=not a.no_system_fonts)
    if not fonts:
        print(f"오류: {NO_FONT_MSG}", file=sys.stderr)
        return 2
    try:
        font, lines, px = layout_title(fonts[0], a.title, a.size)
        if a.dry_run:
            print(f"제목 폰트: {fonts[0][0]} (index {fonts[0][1]}) · 보조 폰트: {fonts[1][0]} (index {fonts[1][1]})")
            print(f"글자 크기: {px}px · 줄 {len(lines)}개")
            for i, ln in enumerate(lines, 1):
                print(f"  {i}: {ln} ({text_w(font, ln):.0f}px)")
            print(f"출력: {a.out} ({a.size}x{a.size})\n(dry-run) 파일을 쓰지 않았습니다.")
            return 0
        im = compose(a.bg, a.title, a.sub, a.phone, a.brand, a.size, fonts)
    except OSError as e:
        print(f"오류: 이미지·폰트를 읽지 못했습니다: {e}", file=sys.stderr)
        return 2
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    im.save(a.out, "PNG")
    print(f"[OK] {a.out} ({a.size}x{a.size}, 제목 {len(lines)}줄)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
