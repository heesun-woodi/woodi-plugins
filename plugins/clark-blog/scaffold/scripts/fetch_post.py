#!/usr/bin/env python3
"""네이버 블로그 글 한 편을 마크다운으로 바꾸고 구조 통계를 센다 (표준 라이브러리만 사용).

사용 예:
  python3 scripts/fetch_post.py wati08 224421112396            # 통계 블록(JSON) + 마크다운
  python3 scripts/fetch_post.py wati08 224421112396 --json     # {"stats": ..., "markdown": ...}만
  python3 scripts/fetch_post.py wati08 224421112396 --out ref.md

`PostView.naver`의 스마트에디터ONE 본문(`se-main-container`)만 파싱한다.
변환은 완벽하지 않다. 통계(글자수·소제목·이미지·굵게·인용·링크)가 맞는 것이 우선이다.
통계 키 정의(출력 stats = 계약 11개 키 + bold_lines + oglinks):
  blogId, logNo, title  입력값과 og:title/<title>(" : 네이버 블로그" 제거)
  chars              공백 제외 글자수(문단·소제목·인용·목록·표 셀 텍스트; 캡션·링크카드 제목 제외)
  paragraphs         비어 있지 않은 일반 문단 + 목록 항목 수(소제목·인용 제외, 굵은 줄 포함)
  headings           se-fs-fs24 / se-fs-fs19 글씨가 문단의 80% 이상이거나 se-section-sectionTitle인 문단 수
  images             본문 사진(se-image-resource) 수. 링크카드 썸네일·지도는 제외
  bold_runs          굵게(<b>·<strong>·font-weight:bold) 이웃 조각을 합친 덩어리 수
  bold_lines         소제목이 아닌 문단 중 전체가 굵은 줄 수(목록 항목 제외). paragraphs·bold_runs에도 포함됨
  quotes             인용 블록(se-section-quotation/se-quote) 수
  links_out          본문 링크(문단 안 링크 + 링크카드) 중 blog.naver.com 이외 도메인 수
  links_naver_blog   본문 링크 중 blog.naver.com / m.blog.naver.com 수
  oglinks            링크카드(se-oglink) 수. links_out/links_naver_blog에도 포함됨
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
for _s in (sys.stdout, sys.stderr):  # Windows 콘솔(cp949)에서도 한글·이모지 출력이 죽지 않게
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

UA = "Mozilla/5.0"
TIMEOUT = 20
URL = "https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"
VOID = {"img", "br", "hr", "input", "meta", "link", "source", "wbr", "col", "area", "base", "embed", "param", "track"}
FORMAT_TAGS = {"span", "b", "strong", "a", "u", "i", "em", "font"}
BOLD_STYLE = re.compile(r"font-weight\s*:\s*(bold|[6-9]00)", re.I)
HEADING_STRONG = ("se-fs-fs24", "se-fs-fs19")


def die(msg):
    print(f"오류: {msg}", file=sys.stderr)
    sys.exit(1)


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        die(f"HTTP {e.code} — {url}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        die(f"네트워크 실패({e}) — {url}")


def clean(text):
    return text.replace("​", "").replace("\xa0", " ")


class PostParser(HTMLParser):
    """se-main-container 안쪽만 마크다운 블록으로 모은다."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.og_title = ""
        self._in_title = False
        self.in_main = False
        self.depth = 0
        self.main_depth = 0
        self.markers = []  # (kind, depth)
        self.blocks = []  # (kind, text)
        self.fmt = []  # (tag, bold, heading_class, href)
        self.para = None  # 문단 세그먼트 [(text, bold, href, hclass)]
        self.cell = None  # 표 셀 텍스트 조각
        self.rows = []
        self.row = None
        self.cur_image = None
        self.in_caption = False
        self.og_href = None
        self.og_title_buf = None
        self.stats = {"paragraphs": 0, "headings": 0, "images": 0, "bold_runs": 0,
                      "quotes": 0, "bold_lines": 0, "links_out": 0, "links_naver_blog": 0, "oglinks": 0}
        self.chars = 0

    # --- 보조 ---
    def _in(self, kind):
        return any(k == kind for k, _ in self.markers)

    def _mark(self, kind):
        self.markers.append((kind, self.depth))

    def _count_link(self, href):
        if not href or not href.startswith("http"):
            return
        host = urllib.parse.urlparse(href).netloc.lower()
        if host in ("blog.naver.com", "m.blog.naver.com"):
            self.stats["links_naver_blog"] += 1
        else:
            self.stats["links_out"] += 1

    # --- 파서 이벤트 ---
    def handle_startendtag(self, tag, attrs):
        if tag in VOID:
            self.handle_starttag(tag, attrs)
        else:
            self.handle_starttag(tag, attrs)
            self.handle_endtag(tag)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class") or ""
        if tag == "meta" and a.get("property") == "og:title":
            self.og_title = a.get("content") or ""
        if tag == "title":
            self._in_title = True
        if not self.in_main:
            if tag == "div" and "se-main-container" in cls.split():
                self.in_main = True
                self.depth = 1
                self.main_depth = 1
            return
        if tag in VOID:
            self._void(tag, a, cls)
            return
        self.depth += 1
        if tag == "div":
            if "se-documentTitle" in cls or "se-placesMap" in cls:
                self._mark("skip")
            if "se-section-quotation" in cls or "se-quote" in cls.split():
                if not self._in("quote"):
                    self.stats["quotes"] += 1
                    self._mark("quote")
            if "se-section-horizontalLine" in cls:
                self.blocks.append(("hr", "---"))
            if "se-table" in cls.split() and not self._in("table"):
                self._mark("table")
                self.rows = []
            if "se-section-sectionTitle" in cls:
                self._mark("sectiontitle")
        if self._in("skip"):
            return
        if tag == "tr" and self._in("table"):
            self.row = []
        if tag in ("td", "th") and self._in("table"):
            self.cell = []
        if tag == "li":
            self._mark("li")
        if tag == "p" and "se-text-paragraph" in cls:
            self.para = []
        if tag == "a" and "se-oglink-info" in cls:
            self.og_href = a.get("href") or ""
        if tag == "strong" and "se-oglink-title" in cls:
            self.og_title_buf = []
        if "se-caption" in cls and self.cur_image is not None:
            self.in_caption = True
            self._mark("caption")
        if tag in FORMAT_TAGS:
            bold = tag in ("b", "strong") or bool(BOLD_STYLE.search(a.get("style") or ""))
            hclass = next((c for c in cls.split() if c in HEADING_STRONG), None)
            href = a.get("href") if tag == "a" and (a.get("href") or "").startswith("http") else None
            self.fmt.append((tag, bold, hclass, href))
            if href and self.para is not None and not self._in("table"):
                self._count_link(href)

    def _void(self, tag, a, cls):
        if self._in("skip"):
            return
        if tag == "br":
            if self.para is not None:
                self._add_text("\n")
            return
        if tag == "img" and "se-image-resource" in cls.split():
            src = a.get("data-lazy-src") or a.get("src") or ""
            if src:
                self.stats["images"] += 1
                self.cur_image = {"url": src, "caption": ""}
                self.blocks.append(("img", self.cur_image))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if not self.in_main or tag in VOID:
            return
        # 서식 태그 pop
        if tag in FORMAT_TAGS:
            for i in range(len(self.fmt) - 1, -1, -1):
                if self.fmt[i][0] == tag:
                    del self.fmt[i]
                    break
        if tag == "strong" and self.og_title_buf is not None:
            title = clean("".join(self.og_title_buf)).strip() or self.og_href
            if self.og_href:
                self.blocks.append(("og", f"[{title}]({self.og_href})"))
                self.stats["oglinks"] += 1
                self._count_link(self.og_href)
            self.og_title_buf = None
            self.og_href = None
        if tag == "p" and self.para is not None:
            self._end_paragraph()
        if tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(re.sub(r"\s+", " ", " ".join(self.cell)).strip().replace("|", "\\|"))
            self.cell = None
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        # 마커 종료
        while self.markers and self.markers[-1][1] == self.depth:
            kind = self.markers.pop()[0]
            if kind == "table":
                self._flush_table()
            if kind == "caption":
                self.in_caption = False
                self.cur_image = None
        self.depth -= 1
        if self.depth < self.main_depth:
            self.in_main = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if not self.in_main or self._in("skip"):
            return
        if self.og_title_buf is not None:
            self.og_title_buf.append(data)
        if self.in_caption and self.cur_image is not None:
            self.cur_image["caption"] += clean(data).strip()
            return
        if self.para is not None:
            self._add_text(data)

    # --- 문단 처리 ---
    def _add_text(self, data):
        bold = any(f[1] for f in self.fmt)
        hclass = next((f[2] for f in reversed(self.fmt) if f[2]), None)
        href = next((f[3] for f in reversed(self.fmt) if f[3]), None)
        self.para.append((data, bold, href, hclass))

    def _end_paragraph(self):
        segs, self.para = self.para, None
        plain = clean("".join(s[0] for s in segs))
        compact = re.sub(r"\s", "", plain)
        if not compact:
            return
        if self.cell is not None:
            self.cell.append(plain.strip())
            self.chars += len(compact)
            return
        self.chars += len(compact)
        in_quote = self._in("quote")
        one_line = re.sub(r"\s+", " ", plain).strip()
        # 소제목 판정
        strong = sum(len(re.sub(r"\s", "", clean(s[0]))) for s in segs if s[3] in HEADING_STRONG)
        all_bold = all(s[1] for s in segs if clean(s[0]).strip())
        is_heading = self._in("sectiontitle") or (
            not in_quote and not self._in("li")
            and strong and strong >= 0.8 * len(compact))
        if is_heading:
            self.stats["headings"] += 1
            self.blocks.append(("h", f"## {one_line}"))
            return
        md = self._render_inline(segs)
        if in_quote:
            self.blocks.append(("quote", "\n".join("> " + ln for ln in md.split("\n") if ln.strip())))
            return
        self.stats["paragraphs"] += 1
        if all_bold and not self._in("li"):
            self.stats["bold_lines"] += 1
        if self._in("li"):
            self.blocks.append(("li", "- " + re.sub(r"\s*\n\s*", " ", md)))
        else:
            self.blocks.append(("p", md))

    def _render_inline(self, segs):
        """같은 (굵게, 링크)인 이웃 조각을 합쳐 **…** / [텍스트](href)로 만든다."""
        runs = []
        for text, bold, href, _ in segs:
            text = clean(text)
            if runs and runs[-1][1] == bold and runs[-1][2] == href:
                runs[-1][0] += text
            else:
                runs.append([text, bold, href])
        out = []
        for text, bold, href in runs:
            if not text.strip():
                out.append(text)
                continue
            lead = text[:len(text) - len(text.lstrip())]
            trail = text[len(text.rstrip()):]
            core = text.strip()
            if href:
                core = f"[{core}]({href})"
            if bold:
                core = f"**{core}**"
                self.stats["bold_runs"] += 1
            out.append(lead + core + trail)
        return re.sub(r"[ \t]+", " ", "".join(out)).strip()

    def _flush_table(self):
        rows = [r for r in self.rows if any(r)]
        self.rows = []
        if not rows:
            return
        width = max(len(r) for r in rows)
        lines = []
        for i, r in enumerate(rows):
            r = r + [""] * (width - len(r))
            lines.append("| " + " | ".join(r) + " |")
            if i == 0:
                lines.append("|" + " --- |" * width)
        self.blocks.append(("table", "\n".join(lines)))

    # --- 결과 ---
    def markdown(self):
        parts, prev = [], None
        for kind, val in self.blocks:
            if kind == "img":
                text = f"![{val['caption']}]({val['url']})"
            else:
                text = val
            if parts and kind == "li" and prev == "li":
                parts[-1] += "\n" + text
            elif parts and kind == "hr" and prev == "hr":
                continue
            else:
                parts.append(text)
            prev = kind
        return "\n\n".join(parts).strip() + "\n"

    def page_title(self):
        t = clean(self.og_title or self.title).strip()
        return re.sub(r"\s*:\s*네이버 블로그\s*$", "", t)


def parse_post(html):
    p = PostParser()
    p.feed(html)
    p.close()
    return p


def main():
    ap = argparse.ArgumentParser(
        description="네이버 블로그 글(PostView) 한 편을 마크다운 본문 + 구조 통계로 변환한다.",
        epilog=__doc__[__doc__.index("통계 키 정의"):],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("blogId", help="블로그 아이디 (예: wati08)")
    ap.add_argument("logNo", help="글 번호 (예: 224421112396)")
    ap.add_argument("--out", metavar="FILE", help="결과를 파일로 저장(기본: stdout)")
    ap.add_argument("--json", action="store_true",
                    help='{"stats": ..., "markdown": ...} JSON만 출력한다')
    args = ap.parse_args()

    html = http_get(URL.format(blog_id=args.blogId, log_no=args.logNo))
    p = parse_post(html)
    if not p.blocks and p.chars == 0:
        die(f"본문(se-main-container)을 찾지 못함 — blogId/logNo 확인 또는 구형 에디터 글: {args.blogId}/{args.logNo}")

    s = p.stats
    stats = {
        "blogId": args.blogId,
        "logNo": args.logNo,
        "title": p.page_title(),
        "chars": p.chars,
        "paragraphs": s["paragraphs"],
        "headings": s["headings"],
        "images": s["images"],
        "bold_runs": s["bold_runs"],
        "bold_lines": s["bold_lines"],
        "quotes": s["quotes"],
        "links_out": s["links_out"],
        "links_naver_blog": s["links_naver_blog"],
        "oglinks": s["oglinks"],
    }
    md = p.markdown()
    if args.json:
        out = json.dumps({"stats": stats, "markdown": md}, ensure_ascii=False, indent=2)
    else:
        out = "```json\n" + json.dumps(stats, ensure_ascii=False, indent=2) + "\n```\n\n" + md
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(out + "\n")
        print(f"저장 -> {args.out}", file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
