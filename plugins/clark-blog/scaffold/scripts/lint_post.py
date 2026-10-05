#!/usr/bin/env python3
"""블로그 글 마크다운 결정적 검사기 (LLM 판단 없이 센다). 표준 라이브러리만 사용."""
import argparse
import json
import os
import re
import sys

DEFAULTS = {"min_chars": 1500, "max_chars": 4000, "min_h2": 4, "max_h2": 7,
            "min_images": 3, "min_sources": 2, "tags_min": 5, "tags_max": 10}
DEFAULT_FORBIDDEN = ["실기시험장", "실기 시험장", "실기시험 장소"]
REQUIRED_KEYS = ["title", "keyword", "category", "tags", "variation"]
PAJU_RE = re.compile(r"https://blog\.naver\.com/pajuclark/[^\s)\]>\"']+")

IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]*)\)")
URL_RE = re.compile(r"https?://\S+")
SRC_RE = re.compile(r"출처\s*:\s*https?://|\[출처\]\(\s*https?://")
PLACEHOLDER_RE = re.compile(r"\[출처 필요\]|\(출처 필요\)")
BOLD_RE = re.compile(r"\*\*[^*\n]+\*\*")
NAVER_RE = re.compile(r"https://blog\.naver\.com/")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def find_knowledge(post_path):
    d = os.path.dirname(os.path.abspath(post_path))
    while True:
        cand = os.path.join(d, "knowledge")
        if os.path.isdir(cand):
            return cand
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def load_thresholds(kdir):
    th = dict(DEFAULTS)
    path = os.path.join(kdir, "design-system.md") if kdir else None
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            m = re.search(r"<!--\s*lint:(.*?)-->", f.read(), re.S)
        if m:
            for k, v in re.findall(r"(\w+)=(\d+)", m.group(1)):
                if k in th:
                    th[k] = int(v)
    return th


def load_forbidden(kdir):
    path = os.path.join(kdir, "academy-profile.md") if kdir else None
    if path and os.path.isfile(path):
        words, inside = [], False
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("## "):
                    inside = line.strip() == "## 금칙어"
                elif inside:
                    words += re.findall(r"`([^`]+)`", line)
        if words:
            return words
    return list(DEFAULT_FORBIDDEN)


def parse_frontmatter(lines):
    """(frontmatter dict or None, 본문 시작 인덱스, 오류 or None).
    간단 파서: key: value / 인라인 [a, b](여러 줄 가능) / '- ' 목록."""
    if not lines or lines[0].strip() != "---":
        return None, 0, "첫 줄이 --- 가 아님"
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return None, 0, "닫는 --- 없음"
    fm, key, i = {}, None, 1
    while i < end:
        raw = lines[i]
        i += 1
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", raw)
        if m and not raw[0].isspace():
            key, val = m.group(1), m.group(2).strip()
            if val.startswith("["):
                while "]" not in val and i < end:  # 여러 줄 인라인 리스트
                    val += " " + lines[i].strip()
                    i += 1
                inner = val[1:val.rindex("]")] if "]" in val else val[1:]
                fm[key] = [t.strip().strip("'\"") for t in inner.split(",") if t.strip()]
            else:
                fm[key] = val.strip("'\"") if not val.startswith("{") else val
        elif key is not None:
            s2 = raw.strip()
            if s2.startswith("- "):
                if not isinstance(fm[key], list):
                    fm[key] = []
                fm[key].append(s2[2:].strip().strip("'\""))
            elif fm[key] == "":
                fm[key] = s2  # 들여쓴 하위 값(map 등) -> 존재로 취급
    return fm, end + 1, None


def has_value(v):
    return bool(v) if isinstance(v, (list, str)) else v is not None


def check(cid, value, rule, result, detail=""):
    return {"id": cid, "value": value, "rule": rule, "result": result, "detail": detail}


def lint_text(text, stage, th, forbidden):
    lines = text.lstrip("\ufeff").split("\n")
    fm, body_start, fm_err = parse_frontmatter(lines)
    # 본문 줄 분류 (코드펜스 밖만)
    body, in_fence = [], False
    for i in range(body_start, len(lines)):
        if FENCE_RE.match(lines[i]):
            in_fence = not in_fence
            continue
        if not in_fence:
            body.append(lines[i])
    prose = "\n".join(body)

    # forbidden: 파일 전체(frontmatter·캡션·코드 포함), 공백 제거 비교
    norm_words = [(w, re.sub(r"\s+", "", w)) for w in forbidden]
    hits = []
    for n, ln in enumerate(lines, 1):
        s = re.sub(r"\s+", "", ln)
        for w, nw in norm_words:
            if nw and nw in s:
                hits.append((n, w))
    hit_lines = sorted({n for n, _ in hits})

    chars_text = URL_RE.sub("", IMG_RE.sub("", prose))
    chars = len(re.sub(r"\s+", "", chars_text))
    h2 = sum(1 for ln in body if ln.startswith("## "))
    h1 = sum(1 for ln in body if ln.startswith("# "))
    images = IMG_RE.findall(prose)
    sources = len(SRC_RE.findall(prose))
    placeholders = len(PLACEHOLDER_RE.findall(prose))
    paju = len(set(PAJU_RE.findall(prose)))
    tags = fm.get("tags") if fm else None
    if isinstance(tags, str) and tags and not tags.startswith("{"):
        tags = [t.strip().strip("'\"") for t in tags.split(",") if t.strip()]
    tag_n = len(tags) if isinstance(tags, list) else 0
    final = stage == "final"

    stats = {"chars": chars, "h2_count": h2, "images": len(images), "sources": sources,
             "tags": tag_n, "bold_runs": len(BOLD_RE.findall(prose)),
             "quotes": sum(1 for ln in body if ln.startswith("> ")),
             "links_naver_blog": len(NAVER_RE.findall(prose)), "links_pajuclark": paju,
             "forbidden_hits": len(hits)}

    def rng(cid, v, lo, hi):
        return check(cid, v, f"{lo}~{hi}", "PASS" if lo <= v <= hi else "FAIL")

    def skip(cid, why="draft 단계 제외"):
        return check(cid, None, "-", "SKIP", why)

    c = [
        check("forbidden", len(hits), "0건", "FAIL" if hits else "PASS",
              ("금칙어 %s — 줄 %s" % (", ".join(sorted({w for _, w in hits})), ", ".join(map(str, hit_lines)))) if hits else ""),
        rng("chars", chars, th["min_chars"], th["max_chars"]),
        rng("h2_count", h2, th["min_h2"], th["max_h2"]),
        check("images", len(images), f">={th['min_images']}", "PASS" if len(images) >= th["min_images"] else "FAIL"),
        check("sources", sources, f">={th['min_sources']}", "PASS" if sources >= th["min_sources"] else "FAIL"),
        check("placeholder_sources", placeholders, "0건", "FAIL" if placeholders else "PASS"),
    ]
    var_ok = bool(fm) and has_value(fm.get("variation"))
    if final:
        c.append(check("variation", "있음" if var_ok else "없음", "필수", "PASS" if var_ok else "FAIL"))
    else:
        c.append(check("variation", "있음" if var_ok else "없음", "draft는 선택", "PASS" if var_ok else "SKIP"))

    if not final:
        c += [skip(i) for i in ("frontmatter", "title_keyword", "tags_count", "related_links", "image_paths", "h1_once")]
    else:
        missing = REQUIRED_KEYS if fm is None else [k for k in REQUIRED_KEYS if not has_value(fm.get(k))]
        c.append(check("frontmatter", "누락: " + ", ".join(missing) if missing else "완전",
                       "첫 줄 ---, 키 " + "·".join(REQUIRED_KEYS), "FAIL" if missing else "PASS",
                       (fm_err or "") if fm is None else ""))
        title, kw = (fm or {}).get("title"), (fm or {}).get("keyword")
        if not has_value(title) or not has_value(kw):
            c.append(skip("title_keyword", "title/keyword 없음(frontmatter 항목에서 보고)"))
        elif isinstance(title, str) and isinstance(kw, str):
            ok = re.sub(r"\s+", "", kw) in re.sub(r"\s+", "", title)
            c.append(check("title_keyword", "포함" if ok else "미포함", "keyword ⊂ title", "PASS" if ok else "FAIL"))
        else:
            c.append(check("title_keyword", "문자열 아님", "title·keyword는 문자열", "FAIL", "title 또는 keyword가 단순 문자열이 아님"))
        if not has_value(fm.get("tags") if fm else None):
            c.append(skip("tags_count", "tags 없음(frontmatter 항목에서 보고)"))
        elif isinstance(tags, list):
            c.append(rng("tags_count", tag_n, th["tags_min"], th["tags_max"]))
        else:
            c.append(check("tags_count", "형식 오류", "리스트", "FAIL", "리스트 형식 아님"))
        slots = prose.count("[[")
        c.append(check("related_links", f"[[ {slots}건, 관련글 {paju}개", f"[[ 0건, pajuclark 링크 >=2",
                       "PASS" if slots == 0 and paju >= 2 else "FAIL"))
        bad, notes = [], []
        for cap, path in images:
            p = path.strip().split(" ")[0] if path.strip() else ""
            if not p:
                bad.append(f"빈 경로 ![{cap}]()")
            elif re.match(r"https?://", p):
                notes.append(f"URL 존재검사 생략: {p}")
            elif not os.path.isabs(p):
                bad.append(f"상대경로: {p}")
            elif not os.path.isfile(p):
                bad.append(f"파일 없음: {p}")
        c.append(check("image_paths", len(bad), "빈/상대/없는 경로 0건", "FAIL" if bad else "PASS",
                       "; ".join(bad + notes)))
        c.append(check("h1_once", h1, "정확히 1개", "PASS" if h1 == 1 else "FAIL"))
    return {"stage": stage, "pass": all(x["result"] != "FAIL" for x in c), "checks": c, "stats": stats}


def lint_file(path, stage, knowledge=None):
    kdir = knowledge or find_knowledge(path)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return lint_text(text, stage, load_thresholds(kdir), load_forbidden(kdir)), kdir


def render_table(res):
    rows = [("항목", "측정값", "기준", "결과")]
    for x in res["checks"]:
        v = "-" if x["value"] is None else str(x["value"])
        rows.append((x["id"], v, x["rule"], x["result"]))
    w = [max(len(r[i]) for r in rows) for i in range(3)]
    out = [" | ".join([r[0].ljust(w[0]), r[1].ljust(w[1]), r[2].ljust(w[2]), r[3]]) for r in rows]
    out.insert(1, "-" * len(out[0]))
    for x in res["checks"]:
        if x["detail"]:
            out.append(f"  - {x['id']}: {x['detail']}")
    out.append("통계: " + ", ".join(f"{k}={v}" for k, v in res["stats"].items()))
    out.append("결과: " + ("PASS" if res["pass"] else "FAIL"))
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="블로그 글 마크다운(post.md)의 금칙어·분량·소제목·이미지·출처·frontmatter를 LLM 없이 결정적으로 검사합니다.",
        epilog="종료 코드: 0=PASS, 1=FAIL(하나라도 실패), 2=사용 오류(파일 없음·stage 오류)",
        add_help=False)
    ap._positionals.title, ap._optionals.title = "인자", "옵션"
    ap.add_argument("-h", "--help", action="help", help="도움말을 보여주고 종료")
    ap.add_argument("post", help="검사할 글 마크다운 파일(draft-v2.md 또는 final.md)")
    ap.add_argument("--stage", required=True, choices=["draft", "final"],
                    help="draft: 초안 검사(frontmatter 계열 SKIP) / final: 업로드 직전 전체 검사")
    ap.add_argument("--knowledge", metavar="DIR",
                    help="knowledge 폴더(기본: post.md에서 위로 올라가며 knowledge/ 탐색)")
    ap.add_argument("--json", action="store_true", help="사람용 표 대신 JSON만 출력")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code in (0, None) else 2
    if not os.path.isfile(a.post):
        print(f"오류: 파일을 찾을 수 없습니다: {a.post}", file=sys.stderr)
        return 2
    if a.knowledge and not os.path.isdir(a.knowledge):
        print(f"오류: knowledge 폴더가 없습니다: {a.knowledge}", file=sys.stderr)
        return 2
    try:
        res, kdir = lint_file(a.post, a.stage, a.knowledge)
    except UnicodeDecodeError:
        print(f"오류: UTF-8로 읽을 수 없는 파일입니다: {a.post}", file=sys.stderr)
        return 2
    if kdir is None:
        print("경고: knowledge/ 폴더를 찾지 못해 기본 임계값·금칙어를 사용합니다.", file=sys.stderr)
    else:
        for name in ("design-system.md", "academy-profile.md"):
            if not os.path.isfile(os.path.join(kdir, name)):
                print(f"경고: {kdir}에 {name}이 없어 해당 기본값을 사용합니다.", file=sys.stderr)
    print(json.dumps(res, ensure_ascii=False, indent=2) if a.json else render_table(res))
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
