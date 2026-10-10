#!/usr/bin/env python3
"""블로그 글 마크다운 결정적 검사기 (LLM 판단 없이 센다). 표준 라이브러리만 사용.

단계(--stage):
- draft  — 초안(draft.md). frontmatter·SEO 계열은 SKIP.
- final  — SEO 확인용(draft-v2.md, 출처·캡션 포함본). 네이버 SEO 정량 검사 4종 추가:
  seo_keyword_body(본문 문단만(제목·소제목·코드·인용·주석·이미지·URL 제외) keyword 출현 kw_min_body~kw_max_body, 기본 3~8),
  seo_keyword_h2(keyword 포함 소제목 >=1), seo_image_captions(모든 이미지 alt 비어 있지 않음),
  seo_title_length(title 글자수 title_min~title_max, 기본 20~40).
- upload — 업로드본(final.md, build_final.py 결과). final 검사에서 sources·seo_image_captions를 SKIP하고
  전용 검사 5종을 더한다: sources_stripped(`출처:`·`[출처](` 0건), captions_empty(alt 있는 이미지 0건),
  cover_file(<글 폴더>/images/00-cover.png 존재 + 본문 미참조), closing_block(`## 📞 문의 및 수강신청` →
  `학원소개` 이미지 → `:::place` → `**#` 순서), h2_spacing(목차 포함 모든 `## ` 바로 윗줄이 빈 줄이고 그 위에 U+3164(ㅤ)만 있는 줄이 1줄 이상 연속 —
  `ㅤ`×N(N>=1, 빌더 기본 2) → 빈 줄 → `## `).

모든 단계 공통: tone(해요체 종결 0건 — `~세요` 권유·필요/중요 같은 명사는 예외; 의문문은 `까요?·나요?·ㅂ니까?/습니까?·인가요?·세요?`만 허용),
source_format(`출처:` 출현 수 == `(출처: https://…)` 단독 괄호 수, 링크형 `[출처](` 0건, 괄호 URL 안 `(` 0건), title_region(frontmatter의
variation.title_region이 academy-profile.md `수강생 지역`에 있고 title에 포함; frontmatter 없으면 SKIP).

카운트 제외 규칙: chars·seo_keyword_body는 `## 📑 목차` 절(다음 `---` 줄까지)·해시태그 줄(`**#…**`/`#태그`)·
U+3164를 빼고 센다. h2_count는 `## 📑 목차`·`## 📞 문의` 줄을, images는 파일명에 `00-cover`·`학원소개`가
든 이미지를 뺀다. 임계값은 design-system.md의 lint 블록 키로 조정한다.
"""
import argparse
import json
import os
import re
import sys
for _s in (sys.stdout, sys.stderr):  # Windows 콘솔(cp949)에서도 한글·이모지 출력이 죽지 않게
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

# lint 블록이 없을 때의 기본 임계값. chars는 목차 절·해시태그 줄·ㅤ 제외, h2는 목차·문의 헤딩 제외,
# images는 표지(00-cover)·학원소개 제외 기준이다(모듈 docstring의 카운트 제외 규칙).
DEFAULTS = {"min_chars": 1500, "max_chars": 4000, "min_h2": 4, "max_h2": 7,
            "min_images": 3, "min_sources": 2, "tags_min": 5, "tags_max": 10,
            "kw_min_body": 3, "kw_max_body": 8, "title_min": 20, "title_max": 40}
DEFAULT_FORBIDDEN = ["실기시험장", "실기 시험장", "실기시험 장소"]
DEFAULT_REGIONS = ["의정부", "서울북부", "양주", "동두천", "포천"]  # academy-profile.md `수강생 지역` 행이 없을 때
REQUIRED_KEYS = ["title", "keyword", "category", "tags", "variation"]
PAJU_RE = re.compile(r"https://blog\.naver\.com/pajuclark/[^\s)\]>\"']+")

IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]*)\)")
URL_RE = re.compile(r"https?://\S+")
SRC_RE = re.compile(r"출처\s*:\s*https?://|\[출처\]\(\s*https?://")
PLACEHOLDER_RE = re.compile(r"\[출처 필요\]|\(출처 필요\)")
BOLD_RE = re.compile(r"\*\*[^*\n]+\*\*")
NAVER_RE = re.compile(r"https://blog\.naver\.com/")
HTMLC_RE = re.compile(r"<!--.*?-->", re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
NONPROSE_RE = re.compile(r"^\s*(#{1,6}\s|>)")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
TABLE_RE = re.compile(r"^\s*\|")
LINK_RE = re.compile(r"\[[^\]]*\]\([^)]*\)")
SRC_LABEL_RE = re.compile(r"출처\s*:")
SRC_PAREN_RE = re.compile(r"\(출처:\s*(https?://\S+?)\)")
SRC_LINK_RE = re.compile(r"\[출처\]\(")  # 링크형 출처 — 기계 제거 대상이 아니므로 금지
IMG_TITLE_RE = re.compile(r"\s+\"[^\"]*\"\s*$")  # ![](경로 "title")의 꼬리 title
Q_OK = ("까요", "나요", "니까", "인가요", "세요")  # 허용 의문문 끝(~할까요?·~하나요?·~ㅂ니까?/습니까?·~인가요?·~세요?)
SENT_SPLIT_RE = re.compile(r"((?<!\d)[.!?](?!\d))")  # 구분자 포함 분리(? 판별용)
TONE_URL_RE = re.compile(r"https?://[^\s)]+")
TRAIL_RE = re.compile(r"[\W_]+$")
HASHTAG_TOKEN_RE = re.compile(r"#[^#\s]\S*")
FILLER = "\u3164"
FILLER_LINE_RE = re.compile(r"^\s*\u3164+\s*$")
TITLE_REGION_RE = re.compile(r"title_region\s*:\s*([^,}\n]+)")
REGION_ROW_RE = re.compile(r"^\|\s*수강생 지역\s*\|([^|]*)\|", re.M)
TOC_H, CONTACT_H, CLOSING_H = "## 📑 목차", "## 📞 문의", "## 📞 문의 및 수강신청"
EXCLUDED_IMAGES = ("00-cover", "학원소개")
NOUN_YO = set("세필중주개수소강")  # ~세요 권유 + 필요·중요·주요·개요·수요·소요·강요(명사)
UPLOAD_ONLY = ("sources_stripped", "captions_empty", "cover_file", "closing_block", "h2_spacing")


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


def load_regions(kdir):
    """academy-profile.md 표의 `수강생 지역` 행 → 지역 목록(괄호 안 설명 제거, 쉼표 분리)."""
    path = os.path.join(kdir, "academy-profile.md") if kdir else None
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            m = REGION_ROW_RE.search(f.read())
        if m:
            regions = [r.strip() for r in re.split(r"[,，、]", re.sub(r"\([^)]*\)", "", m.group(1))) if r.strip()]
            if regions:
                return regions
    return list(DEFAULT_REGIONS)


def is_hashtag_line(ln):
    s = ln.strip()
    if len(s) >= 4 and s.startswith("**") and s.endswith("**"):
        s = s[2:-2].strip()
    toks = s.split()
    return bool(toks) and all(HASHTAG_TOKEN_RE.fullmatch(t) for t in toks)


def toc_indices(body):
    """`## 📑 목차` 줄부터 다음 `---` 줄(포함) 또는 다음 `## ` 직전까지의 줄 번호."""
    out, i = set(), 0
    while i < len(body):
        if body[i].startswith(TOC_H):
            out.add(i)
            i += 1
            while i < len(body) and not body[i].startswith("## "):
                out.add(i)
                i += 1
                if body[i - 1].strip() == "---":
                    break
            continue
        i += 1
    return out


def haeyo_end(seg):
    """문장 끝이 해요체(~요/~죠)면 True. ~세요·필요/중요 류 명사는 제외."""
    s = TRAIL_RE.sub("", seg)
    if s.endswith("죠"):
        return True
    if len(s) < 2 or not s.endswith("요"):
        return False
    if s[-2] in NOUN_YO:
        return False
    return True


def tone_hits(body, skip_idx):
    """본문 문단(소제목·인용·표·이미지·주석·목차 절·해시태그 줄·:::블록 제외)의 해요체 종결 문장 목록.
    `?`로 끝나는 의문문은 끝이 Q_OK(까요·나요·니까·인가요·세요)면 허용, 그 밖의 `요?`·`죠?`는 해요체로 센다."""
    kept = [ln for k, ln in enumerate(body) if k not in skip_idx and not is_hashtag_line(ln)]
    hits = []
    for ln in HTMLC_RE.sub("", "\n".join(kept)).split("\n"):
        if NONPROSE_RE.match(ln) or TABLE_RE.match(ln) or ln.strip().startswith(":::"):
            continue
        ln = LINK_RE.sub("", IMG_RE.sub("", INLINE_CODE_RE.sub("", ln)))
        ln = TONE_URL_RE.sub("", SRC_PAREN_RE.sub("", ln))  # `…해요(출처: URL).`의 문장 끝을 살린다
        parts = SENT_SPLIT_RE.split(ln)  # [문장, 구분자, 문장, 구분자, …, 마지막 문장]
        for j in range(0, len(parts), 2):
            question = (parts[j + 1] if j + 1 < len(parts) else "") == "?"
            if question and TRAIL_RE.sub("", parts[j]).endswith(Q_OK):
                continue
            if haeyo_end(parts[j]):
                hits.append(parts[j].strip())
    return hits


def _img_path(path):
    """이미지 경로에서 꼬리 "title"만 뗀다(폴더명 공백 유지)."""
    return IMG_TITLE_RE.sub("", path.strip())


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
            listval, used = None, 0
            if val.startswith("["):
                if val.endswith("]"):
                    listval = val
                elif "]" not in val:  # 여러 줄 인라인 리스트 후보
                    joined, j = val, i
                    while j < end:
                        nxt = lines[j]
                        if re.match(r"^[A-Za-z_][\w-]*:\s", nxt):
                            break
                        joined += " " + nxt.strip()
                        j += 1
                        if nxt.rstrip().endswith("]"):
                            listval, used = joined, j - i
                            break
            if listval is not None:
                i += used
                fm[key] = [t.strip().strip("'\"") for t in listval[1:-1].split(",") if t.strip()]
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


def lint_text(text, stage, th, forbidden, regions=None, post_dir=None):
    """regions: 수강생 지역 목록(기본 DEFAULT_REGIONS). post_dir: 글 폴더(upload의 cover_file 검사용)."""
    regions = list(regions) if regions else list(DEFAULT_REGIONS)
    lines = text.lstrip("﻿").split("\n")
    fm, body_start, fm_err = parse_frontmatter(lines)
    fm_block = "\n".join(lines[1:body_start - 1]) if fm is not None else ""
    # 본문 줄 분류 (코드펜스 밖만)
    body, in_fence = [], False
    for i in range(body_start, len(lines)):
        if FENCE_RE.match(lines[i]):
            in_fence = not in_fence
            continue
        if not in_fence:
            body.append(lines[i])
    prose = "\n".join(body)
    toc = toc_indices(body)
    # 카운트용 본문: 목차 절·해시태그 줄 제외, ㅤ 제거
    counted = "\n".join(ln.replace(FILLER, "") for k, ln in enumerate(body)
                        if k not in toc and not is_hashtag_line(ln))

    # forbidden: 파일 전체(frontmatter·캡션·코드 포함), 공백 제거 비교
    norm_words = [(w, re.sub(r"\s+", "", w)) for w in forbidden]
    hits = []
    for n, ln in enumerate(lines, 1):
        s = re.sub(r"\s+", "", ln)
        for w, nw in norm_words:
            if nw and nw in s:
                hits.append((n, w))
    hit_lines = sorted({n for n, _ in hits})

    chars_text = URL_RE.sub("", IMG_RE.sub("", counted))
    chars = len(re.sub(r"\s+", "", chars_text))
    h2 = sum(1 for ln in body if ln.startswith("## ") and not ln.startswith((TOC_H, CONTACT_H)))
    h1 = sum(1 for ln in body if ln.startswith("# "))
    all_images = IMG_RE.findall(prose)
    images = [(cap, path) for cap, path in all_images
              if not any(x in os.path.basename(_img_path(path)) for x in EXCLUDED_IMAGES)]
    sources = len(SRC_RE.findall(prose))
    src_labels = len(SRC_LABEL_RE.findall(prose))
    paren_urls = SRC_PAREN_RE.findall(prose)
    src_parens = len(paren_urls)
    src_links = len(SRC_LINK_RE.findall(prose))
    src_bad_url = sum(1 for u in paren_urls if "(" in u)  # 제거하면 괄호가 남는 URL
    placeholders = len(PLACEHOLDER_RE.findall(prose))
    paju = len(set(PAJU_RE.findall(prose)))
    tone = tone_hits(body, toc)
    tags = fm.get("tags") if fm else None
    if isinstance(tags, str) and tags and not tags.startswith("{"):
        tags = [t.strip().strip("'\"") for t in tags.split(",") if t.strip()]
    tag_n = len(tags) if isinstance(tags, list) else 0
    final = stage in ("final", "upload")
    upload = stage == "upload"
    kw_s = (fm or {}).get("keyword")
    kw_n = re.sub(r"\s+", "", kw_s) if isinstance(kw_s, str) else ""
    # 본문 문단만(제목·소제목·코드·인용·주석·이미지·URL·목차 절·해시태그 줄 제외) 줄 단위로 공백을 지우고 keyword 출현을 센다
    keyword_hits = None
    if kw_n:
        para = URL_RE.sub("", IMG_RE.sub("", HTMLC_RE.sub("", counted)))
        keyword_hits = sum(re.sub(r"\s+", "", INLINE_CODE_RE.sub("", ln)).count(kw_n)
                           for ln in para.split("\n") if not NONPROSE_RE.match(ln))
    title_s = (fm or {}).get("title")
    title_len = len(title_s) if isinstance(title_s, str) and title_s else None

    stats = {"chars": chars, "h2_count": h2, "images": len(images), "sources": sources,
             "tags": tag_n, "bold_runs": len(BOLD_RE.findall(prose)),
             "quotes": sum(1 for ln in body if ln.startswith("> ")),
             "links_naver_blog": len(NAVER_RE.findall(prose)), "links_pajuclark": paju,
             "forbidden_hits": len(hits), "keyword_hits": keyword_hits, "title_len": title_len,
             "tone_hits": len(tone)}

    def rng(cid, v, lo, hi):
        return check(cid, v, f"{lo}~{hi}", "PASS" if lo <= v <= hi else "FAIL")

    def skip(cid, why="draft 단계 제외"):
        return check(cid, None, "-", "SKIP", why)

    sf_why = ([f"단독 괄호가 아닌 출처 표기 {src_labels - src_parens}건"] if src_labels != src_parens else []) + \
             ([f"링크형 [출처]( {src_links}건 — (출처: URL)로 바꿀 것"] if src_links else []) + \
             ([f"URL 안에 ( 가 든 출처 괄호 {src_bad_url}건 — 제거 시 괄호가 남음"] if src_bad_url else [])
    c = [
        check("forbidden", len(hits), "0건", "FAIL" if hits else "PASS",
              ("금칙어 %s — 줄 %s" % (", ".join(sorted({w for _, w in hits})), ", ".join(map(str, hit_lines)))) if hits else ""),
        rng("chars", chars, th["min_chars"], th["max_chars"]),
        rng("h2_count", h2, th["min_h2"], th["max_h2"]),
        check("images", len(images), f">={th['min_images']}", "PASS" if len(images) >= th["min_images"] else "FAIL"),
        skip("sources", "upload 단계 제외 — 업로드본은 출처를 지운다(sources_stripped로 확인)") if upload else
        check("sources", sources, f">={th['min_sources']}", "PASS" if sources >= th["min_sources"] else "FAIL"),
        check("placeholder_sources", placeholders, "0건", "FAIL" if placeholders else "PASS"),
        check("tone", len(tone), "해요체 종결 0건", "FAIL" if tone else "PASS",
              ("예: " + " / ".join(tone[:3])) if tone else ""),
        check("source_format", f"출처: {src_labels}건 / (출처: URL) {src_parens}건 / [출처]( {src_links}건",
              "출처: 수 == (출처: URL) 단독 괄호 수, [출처]( 0건, URL 안 ( 0건",
              "FAIL" if sf_why else "PASS", "; ".join(sf_why)),
    ]
    # title_region: frontmatter variation의 title_region ∈ 수강생 지역, title에 포함
    if fm is None:
        c.append(skip("title_region", "frontmatter 없음" + ("(frontmatter 항목에서 보고)" if final else "")))
    else:
        m = TITLE_REGION_RE.search(fm_block)
        tr = m.group(1).strip().strip("'\"") if m else ""
        title_ns = re.sub(r"\s+", "", title_s) if isinstance(title_s, str) else ""
        if not tr:
            why = "variation.title_region 없음"
        elif tr not in regions:
            why = f"'{tr}'이(가) 수강생 지역({', '.join(regions)})에 없음"
        elif re.sub(r"\s+", "", tr) not in title_ns:
            why = f"title에 '{tr}' 없음"
        else:
            why = ""
        c.append(check("title_region", tr or "없음", "수강생 지역 중 하나 + title 포함",
                       "FAIL" if why else "PASS", why))
    var_ok = bool(fm) and has_value(fm.get("variation"))
    if final:
        c.append(check("variation", "있음" if var_ok else "없음", "필수", "PASS" if var_ok else "FAIL"))
    else:
        c.append(check("variation", "있음" if var_ok else "없음", "draft는 선택", "PASS" if var_ok else "SKIP"))

    if not final:
        c += [skip(i) for i in ("frontmatter", "title_keyword", "tags_count", "related_links", "image_paths", "h1_once",
                                                     "seo_keyword_body", "seo_keyword_h2", "seo_image_captions",
                                                     "seo_title_length")]
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
        for cap, path in all_images:
            p = _img_path(path)
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
        lo, hi = th["kw_min_body"], th["kw_max_body"]
        if keyword_hits is None:
            c.append(skip("seo_keyword_body", "keyword 없음(frontmatter 항목에서 보고)"))
            c.append(skip("seo_keyword_h2", "keyword 없음(frontmatter 항목에서 보고)"))
        else:
            c.append(check("seo_keyword_body", keyword_hits, f"{lo}~{hi}회",
                           "PASS" if lo <= keyword_hits <= hi else "FAIL",
                           "" if lo <= keyword_hits <= hi else f"keyword '{kw_s}' 본문 {keyword_hits}회"))
            h2_kw = sum(1 for ln in body if ln.startswith("## ") and kw_n in re.sub(r"\s+", "", ln))
            c.append(check("seo_keyword_h2", h2_kw, ">=1", "PASS" if h2_kw >= 1 else "FAIL"))
        if upload:
            c.append(skip("seo_image_captions", "upload 단계 제외 — 업로드본은 캡션을 비운다(captions_empty로 확인)"))
        else:
            empty = [path.strip() or "(빈 경로)" for cap, path in all_images if not cap.strip()]
            c.append(check("seo_image_captions", len(empty), "alt 빈 이미지 0건", "FAIL" if empty else "PASS",
                           ("alt 없음: " + "; ".join(empty)) if empty else ""))
        if title_len is None:
            c.append(skip("seo_title_length", "title 없음/문자열 아님(frontmatter 항목에서 보고)"))
        else:
            c.append(rng("seo_title_length", title_len, th["title_min"], th["title_max"]))

    if not upload:
        c += [skip(i, "upload 단계 전용") for i in UPLOAD_ONLY]
    else:
        left = src_labels + src_links
        c.append(check("sources_stripped", left, "출처: · [출처]( 0건", "FAIL" if left else "PASS",
                       f"업로드본에 출처 표기 {left}건 남음(출처: {src_labels}, [출처]( {src_links})" if left else ""))
        capped = [f"![{cap}]" for cap, _ in all_images if cap.strip()]
        c.append(check("captions_empty", len(capped), "alt 있는 이미지 0건", "FAIL" if capped else "PASS",
                       "; ".join(capped)))
        refs = sum(1 for _, path in all_images if "00-cover" in os.path.basename(_img_path(path)))
        cover = os.path.join(post_dir, "images", "00-cover.png") if post_dir else None
        exists = bool(cover) and os.path.isfile(cover)
        why = ("글 폴더를 알 수 없음(post_dir 미지정)" if not post_dir else
               f"파일 없음: {cover}" if not exists else
               f"본문이 표지를 {refs}번 참조함(업로드 도구가 맨 앞에 넣으므로 본문에서 빼야 함)" if refs else "")
        c.append(check("cover_file", f"{'있음' if exists else '없음'}, 본문 참조 {refs}건",
                       "images/00-cover.png 존재 + 본문 미참조", "FAIL" if why else "PASS", why))
        steps = [("문의 헤딩", lambda ln: ln.startswith(CLOSING_H)),
                 ("학원소개 이미지", lambda ln: any("학원소개" in _img_path(p) for _, p in IMG_RE.findall(ln))),
                 (":::place", lambda ln: ln.strip().startswith(":::place")),
                 ("**# 해시태그", lambda ln: ln.strip().startswith("**#"))]
        pos, miss = 0, []
        for name, pred in steps:
            k = next((k for k in range(pos, len(body)) if pred(body[k])), None)
            if k is None:
                miss.append(name)
            else:
                pos = k + 1
        c.append(check("closing_block", "누락/순서 오류: " + ", ".join(miss) if miss else "완전",
                       "문의 헤딩 → 학원소개 이미지 → :::place → **#", "FAIL" if miss else "PASS"))
        nospace = [ln.strip() for k, ln in enumerate(body)
                   # 빈 줄 바로 위가 ㅤ 줄이면 그 위로 ㅤ가 몇 줄 더 있어도(N>=1) 통과
                   if ln.startswith("## ") and not (k > 1 and not body[k - 1].strip()
                                                     and FILLER_LINE_RE.match(body[k - 2]))]
        c.append(check("h2_spacing", len(nospace), "모든 ## 위가 ㅤ 줄(1줄 이상) → 빈 줄", "FAIL" if nospace else "PASS",
                       ("ㅤ+빈 줄 없음: " + "; ".join(nospace[:3])) if nospace else ""))
    return {"stage": stage, "pass": all(x["result"] != "FAIL" for x in c), "checks": c, "stats": stats}


def lint_file(path, stage, knowledge=None):
    kdir = knowledge or find_knowledge(path)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return lint_text(text, stage, load_thresholds(kdir), load_forbidden(kdir), load_regions(kdir),
                     os.path.dirname(os.path.abspath(path))), kdir


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
        description="블로그 글 마크다운(post.md)의 금칙어·분량·소제목·이미지·출처·frontmatter·합니다체 톤·제목 지역명과 네이버 SEO 정량 항목(키워드 본문·소제목 출현, 이미지 캡션, 제목 길이), 업로드본 형식(출처·캡션 제거, 표지, 마무리 블록, 소제목 여백)을 LLM 없이 결정적으로 검사합니다.",
        epilog="종료 코드: 0=PASS, 1=FAIL(하나라도 실패), 2=사용 오류(파일 없음·stage 오류)",
        add_help=False)
    ap._positionals.title, ap._optionals.title = "인자", "옵션"
    ap.add_argument("-h", "--help", action="help", help="도움말을 보여주고 종료")
    ap.add_argument("post", help="검사할 글 마크다운 파일(draft.md · draft-v2.md · final.md)")
    ap.add_argument("--stage", required=True, choices=["draft", "final", "upload"],
                    help="draft: 초안(draft.md) — frontmatter·SEO 계열 SKIP / "
                         "final: SEO 확인용(draft-v2.md) — seo_* 4종 포함 / "
                         "upload: 업로드본(final.md) — final에서 sources·seo_image_captions를 SKIP하고 "
                         "sources_stripped·captions_empty·cover_file·closing_block·h2_spacing 추가. "
                         "공통: tone·source_format·title_region")
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
