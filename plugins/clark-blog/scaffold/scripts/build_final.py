#!/usr/bin/env python3
"""draft-v2.md + images/image-plan.md → 업로드본 final.md (blog-run Step 4). 표준 라이브러리만 사용.

실행(작업 폴더에서):
    python3 scripts/build_final.py work/posts/<NNN-slug> [--photos <폴더>] [--knowledge <폴더>]

변환(draft-v2.md는 건드리지 않는다):
 ① frontmatter·`# 제목` 줄과 그 위(제목 B안/A안) `<!-- … -->` 주석은 그대로 둔다. 그 아래 본문 주석은 지운다
    (네이버에 글자로 올라감). 코드펜스(``` / ~~~) 안은 손대지 않는다.
 ② `![슬롯: …]()` 줄을 등장 순서대로 image-plan 행 01, 02, …(00 표지 행 제외)과 맞춰 `![](<절대경로>)`로(alt 비움).
    `images/…`는 글 폴더 기준, `photos/…`는 --photos의 상위(작업 폴더) 기준. `제거`·`보류`는 줄째 지운다.
 ③ `(출처: URL)` 단독 괄호를 모두 지운다. 그 뒤에도 `출처:`(조항과 섞인 괄호)나 `[출처](URL)` 링크형이 남으면
    변환하지 않는다.
 ④ 본문의 모든 `## `(펜스 밖, 목차 포함) 앞은 직전 줄 종류와 상관없이 항상
    `<직전 비어 있지 않은 줄>` → `ㅤ`(U+3164) H2_FILLER_LINES줄(사이 빈 줄 없음) → 빈 줄 1개 → `## `.
    빈 줄이 소제목에 gap을 줘 앞 문단에 이어 붙지 않게 한다. 이미 있던 빈 줄·`ㅤ` 줄은 이 배치로 다시 맞춘다(멱등).
 ⑤ image-plan `00` 행 캡션 `제목: …; 줄바꿈: 줄1; 줄2`의 제목 값(첫 `;` 앞까지)과 frontmatter title이 공백 무시로 같아야 한다.
 ⑥ 마지막 `## `이 `## 📞 문의 및 수강신청`이어야 하고, 그 뒤에 학원소개 이미지 → `:::place 검색어:::` → 빈 줄 →
    `**#태그 …**`(tags의 앞 `#`·공백 제거)를 붙인다. 검색어는 academy-profile.md `| 장소 검색어 | … |` 행(없으면 기본값).
 ⑦ 연속 빈 줄은 1개로, 파일 끝 개행 1개.
종료 코드: 0=final.md 작성, 1=변환 불가(사유를 줄마다 출력, final.md를 쓰지 않고 이전 final.md는 지움), 2=사용 오류.
"""
import argparse
import os
import re
import sys
for _s in (sys.stdout, sys.stderr):  # Windows 콘솔(cp949)에서도 한글·이모지 출력이 죽지 않게
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gen_image import parse_plan  # noqa: E402
from lint_post import find_knowledge, parse_frontmatter  # noqa: E402

FILLER = "ㅤ"  # 한글 채움 문자 — naver-blog-cli에서 독립 빈 문단이 된다
H2_FILLER_LINES = 2  # 소제목 앞 ㅤ 줄 수(1줄은 문단 사이 간격과 같아 보여 2줄)
DEFAULT_PLACE = "클라크중장비운전학원"
CLOSING_H2 = "## 📞 문의 및 수강신청"
ACADEMY_IMG = "학원소개.png"
SLOT_RE = re.compile(r"\s*!\[슬롯:[^\]]*\]\(\s*\)\s*")
SOURCE_RE = re.compile(r"\s*\(출처:\s*https?://[^)\s]+\)")
LEFT_SOURCE_RE = re.compile(r"출처\s*:")
LINK_SOURCE_RE = re.compile(r"\[출처\]\(")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
COMMENT_RE = re.compile(r"<!--.*?-->")


def md_path(p):
    """본문에 쓰는 이미지 절대경로는 구분자를 / 로 (Windows C:\\a\\b → C:/a/b, macOS는 그대로)."""
    return p.replace(os.sep, "/")


def is_filler(line):
    return line.strip() == FILLER


def read_place_query(kdir):
    path = os.path.join(kdir, "academy-profile.md") if kdir else None
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"^\s*\|\s*장소 검색어\s*\|\s*(.*?)\s*\|", line)
                if m and m.group(1).strip("` "):
                    return m.group(1).strip("` ")
    return DEFAULT_PLACE


def load_plan(path):
    """(00 행 or None, 슬롯 행 목록)."""
    with open(path, encoding="utf-8") as f:
        _, rows = parse_plan(f.read())
    cover = next((r for r in rows if r["slot"] == "00"), None)
    return cover, [r for r in rows if r["slot"] != "00"]


def cover_title(caption):
    m = re.search(r"제목\s*:\s*(.*)", caption)
    if not m:
        return None
    return m.group(1).split(";")[0].strip()


def tag_list(tags):
    if isinstance(tags, str):
        tags = tags.strip("[]").split(",")
    out = [re.sub(r"\s+", "", t.strip("'\" ")).lstrip("#") for t in (tags or [])]
    return [t for t in out if t]


def build(post_dir, photos_dir, kdir):
    """(final 텍스트 or None, 요약 or None, 오류 목록)."""
    errs = []
    draft_path = os.path.join(post_dir, "draft-v2.md")
    plan_path = os.path.join(post_dir, "images", "image-plan.md")
    with open(draft_path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    fm, body_start, fm_err = parse_frontmatter(lines)
    if fm_err:
        return None, None, [f"draft-v2.md frontmatter 오류: {fm_err}"]
    title = fm.get("title") or ""
    if not title:
        errs.append("frontmatter title 없음")
    tags = tag_list(fm.get("tags"))
    if not tags:
        errs.append("frontmatter tags 없음 — 해시태그 줄을 만들 수 없음")

    if not os.path.isfile(plan_path):
        return None, None, errs + [f"image-plan.md 없음: {plan_path}"]
    try:
        cover, rows = load_plan(plan_path)
    except ValueError as e:
        return None, None, errs + [f"image-plan.md 파싱 실패: {e}"]
    plan = {r["slot"]: r for r in rows}

    # ⑤ 표지 제목 대조
    if cover is None:
        errs.append("표지(00) 행 없음 — image-plan.md에 00 cover 행을 추가하고 make_cover.py로 표지를 만드세요")
    else:
        ct = cover_title(cover["caption"])
        if ct is None:
            errs.append("표지(00) 행 캡션에 '제목:' 없음 — 표지 재생성 필요")
        elif re.sub(r"\s+", "", ct) != re.sub(r"\s+", "", title):
            errs.append(f"표지 재생성 필요 — 표지 제목 '{ct}' ≠ title '{title}' (Step 3의 make_cover.py만 다시 실행)")

    photos_base = os.path.dirname(os.path.abspath(photos_dir))
    out = list(lines[:body_start])
    n = n_src = n_fill = 0
    left_src, link_src, h2 = [], [], []
    head, in_comment, in_fence = True, False, False
    for i in range(body_start, len(lines)):
        line, ln = lines[i], i + 1
        # ① 맨 위(`# 제목`까지)의 주석·빈 줄은 그대로
        if head:
            if in_comment or line.lstrip().startswith("<!--") or not line.strip():
                if line.lstrip().startswith("<!--") or in_comment:
                    in_comment = "-->" not in line
                out.append(line)
                continue
            head = False
            if line.startswith("# "):
                out.append(line)
                continue
        # 코드펜스 안은 그대로
        if FENCE_RE.match(line) and not in_comment:
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        # ① 본문 주석 제거(여러 줄 포함)
        orig = line
        if in_comment:
            if "-->" not in line:
                continue
            line, in_comment = line.split("-->", 1)[1], False
        line = COMMENT_RE.sub("", line)
        if "<!--" in line:
            line, in_comment = line.split("<!--", 1)[0], True
        if orig.strip() and not line.strip():
            continue
        line = line.rstrip() if line != orig else line
        # ② 이미지 슬롯
        if SLOT_RE.fullmatch(line):
            n += 1
            k = "%02d" % n
            r = plan.get(k)
            f = (r or {}).get("file", "").strip("` ")
            if r is None:
                errs.append(f"{k}: image-plan.md에 행 없음")
                continue
            if f in ("제거", "보류"):
                continue
            if f.startswith("images/"):
                a = os.path.abspath(os.path.join(post_dir, f))
            elif f.startswith("photos/"):
                a = os.path.abspath(os.path.join(photos_base, f))
            else:
                errs.append(f"{k}: 파일 칸 미확정({f or '빈칸'})")
                continue
            if not os.path.isfile(a):
                errs.append(f"{k}: 파일 없음 {a}")
            out.append(f"![]({md_path(a)})")
            continue
        # ③ 출처 괄호 제거
        line, c = SOURCE_RE.subn("", line)
        n_src += c
        if LEFT_SOURCE_RE.search(line):
            left_src.append(ln)
        if LINK_SOURCE_RE.search(line):
            link_src.append(ln)
        # ④ 소제목 앞 여백
        if line.startswith("## "):
            while len(out) > body_start and (not out[-1].strip() or is_filler(out[-1])):
                out.pop()
            out += [FILLER] * H2_FILLER_LINES + [""]
            n_fill += H2_FILLER_LINES
            h2.append(line)
        out.append(line)

    if n != len(rows):
        errs.append(f"슬롯 수 불일치: draft-v2.md {n}개 / image-plan.md {len(rows)}행(00 제외)")
    if left_src:
        errs.append("혼합 출처 괄호 — lint source_format 참고: draft-v2.md "
                    + ", ".join(f"{x}행" for x in left_src))
    if link_src:
        errs.append("링크형 출처 [출처](URL) — lint source_format 참고: draft-v2.md "
                    + ", ".join(f"{x}행" for x in link_src))

    # ⑥ 마무리 블록
    if not h2 or not h2[-1].startswith(CLOSING_H2):
        errs.append(f"마지막 소제목이 '{CLOSING_H2}'로 시작하지 않음 (지금: {h2[-1] if h2 else '소제목 없음'})")
    academy = os.path.join(os.path.abspath(photos_dir), ACADEMY_IMG)
    if not os.path.isfile(academy):
        errs.append(f"학원소개 이미지 없음: {academy}")
    if errs:
        return None, None, errs

    while out and not out[-1].strip():
        out.pop()
    out += [f"![]({md_path(academy)})", f":::place {read_place_query(kdir)}:::", "",
            "**" + " ".join("#" + t for t in tags) + "**"]

    # ⑦ 연속 빈 줄 정리(ㅤ 줄은 빈 줄이 아니므로 그대로)
    final = []
    for x in out:
        if not x.strip() and final and not final[-1].strip():
            continue
        final.append(x)
    text = "\n".join(final).rstrip("\n") + "\n"
    cnt = lambda v: sum(1 for r in rows if r["file"].strip("` ") == v)  # noqa: E731
    summary = (f"final.md 작성 — 슬롯 {n}개(제거 {cnt('제거')}개, 보류 {cnt('보류')}개) · "
               f"출처 제거 {n_src}개 · 필러 삽입 {n_fill}줄")
    return text, summary, []


def main(argv=None):
    ap = argparse.ArgumentParser(description="draft-v2.md → final.md(업로드본) 빌더")
    ap.add_argument("post", help="글 폴더(work/posts/NNN-slug)")
    ap.add_argument("--photos", default=None, help="photos 폴더(기본 cwd/photos). 상위 폴더가 photos/… 경로의 기준")
    ap.add_argument("--knowledge", default=None, help="knowledge 폴더(기본: 글 폴더에서 위로 찾음)")
    a = ap.parse_args(argv)
    post = os.path.abspath(a.post)
    if not os.path.isdir(post):
        print(f"오류: 글 폴더가 아님: {a.post}", file=sys.stderr)
        return 2
    draft = os.path.join(post, "draft-v2.md")
    if not os.path.isfile(draft):
        print(f"오류: draft-v2.md 없음: {draft}", file=sys.stderr)
        return 2
    photos = a.photos or os.path.join(os.getcwd(), "photos")
    kdir = a.knowledge or find_knowledge(draft)
    text, summary, errs = build(post, photos, kdir)
    final_path = os.path.join(post, "final.md")
    if errs:
        print("final.md를 만들지 않았습니다:", file=sys.stderr)
        for e in errs:
            print(e, file=sys.stderr)
        if os.path.isfile(final_path):
            os.remove(final_path)
            print(f"이전 final.md 삭제: {final_path}", file=sys.stderr)
        return 1
    with open(final_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
