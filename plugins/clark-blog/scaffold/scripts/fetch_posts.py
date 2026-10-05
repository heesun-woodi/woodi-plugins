#!/usr/bin/env python3
"""네이버 블로그 글 목록 수집기 (표준 라이브러리만 사용).

두 가지 모드:
  --rss <blogId> [<blogId> ...]   RSS(최근 50개)에서 목록을 읽어 하나의 배열로 합친다.
  --all <blogId>                  PostTitleListAsync를 페이징해 전체 글 목록을 읽는다.

출력(고정 스키마, 다른 스킬·에이전트가 소비한다), date 내림차순:
  [{"blogId", "title", "category", "date"(YYYY-MM-DD), "logNo", "link"}]

사용 예:
  python3 scripts/fetch_posts.py --rss clark6591 wati08 voliskpe --out work/topics-raw.json
  python3 scripts/fetch_posts.py --all pajuclark --out work/pajuclark-posts.json

주의: 네이버는 User-Agent가 없으면 차단한다. 계정·IP 보호를 위해 요청 사이에 0.5초 쉰다.
"""
import argparse
import datetime
import email.utils
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = "Mozilla/5.0"
TIMEOUT = 20
SLEEP = 0.5
PAGE_SIZE = 30
RSS_URL = "https://rss.blog.naver.com/{blog_id}.xml"
LIST_URL = (
    "https://blog.naver.com/PostTitleListAsync.naver?blogId={blog_id}"
    "&currentPage={page}&categoryNo=0&parentCategoryNo=&countPerPage=30&viewdate="
)


def die(msg):
    """stderr에 이유를 쓰고 exit 1."""
    print(f"오류: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_add_date(add_date, today=None):
    """addDate("2026. 9. 12.") -> "2026-09-12". '3시간 전'처럼 상대 표기면 오늘 날짜."""
    m = re.search(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})", add_date or "")
    if m:
        y, mo, d = (int(x) for x in m.groups())
        return f"{y:04d}-{mo:02d}-{d:02d}"
    if re.search(r"방금|분\s*전|시간\s*전", add_date or ""):
        return (today or datetime.date.today()).isoformat()
    raise ValueError(f"해석할 수 없는 addDate: {add_date!r}")


def decode_title(raw):
    """URL-encoded 제목("%ED%95%9C+%EA%B8%80") -> 공백/한글 복원."""
    return urllib.parse.unquote_plus(raw or "")


def make_link(blog_id, log_no):
    return f"https://blog.naver.com/{blog_id}/{log_no}"


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        die(f"HTTP {e.code} — {url}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        die(f"네트워크 실패({e}) — {url}")


def parse_naver_json(text):
    """PostTitleListAsync 응답을 JSON으로 읽는다.

    content-type이 text/html이고 본문에 `\\'` 같은 잘못된 이스케이프가 섞여 있어
    잘못된 이스케이프만 걷어내고 파싱한다.
    """
    fixed = re.sub(
        r"\\(.)",
        lambda m: m.group(0) if m.group(1) in '"\\/bfnrtu' else m.group(1),
        text,
        flags=re.S,
    )
    return json.loads(fixed)


def fetch_rss(blog_id):
    xml_text = http_get(RSS_URL.format(blog_id=blog_id))
    try:
        root = ET.fromstring(xml_text.lstrip())
    except ET.ParseError as e:
        die(f"RSS를 읽을 수 없음(blogId={blog_id} 확인 필요): {e}")
    if not (root.findtext("channel/title") or "").strip():
        die(f"존재하지 않는 블로그이거나 RSS 비공개: blogId={blog_id}")
    posts = []
    for item in root.iter("item"):
        link = (item.findtext("link") or "").strip()
        guid = (item.findtext("guid") or "").strip()
        m = re.search(r"(\d+)(?:\?|$)", guid or link.split("?")[0])
        if not m:
            print(f"경고: logNo를 찾을 수 없어 건너뜀({blog_id}): {link or guid!r}", file=sys.stderr)
            continue
        log_no = m.group(1)
        pub = item.findtext("pubDate")
        try:
            date = email.utils.parsedate_to_datetime(pub).date().isoformat()
        except (TypeError, ValueError):
            die(f"pubDate 해석 실패({blog_id}/{log_no}): {pub!r}")
        posts.append({
            "blogId": blog_id,
            "title": (item.findtext("title") or "").strip(),
            "category": (item.findtext("category") or "").strip(),
            "date": date,
            "logNo": log_no,
            "link": make_link(blog_id, log_no),
        })
    return posts


def fetch_all(blog_id, max_pages):
    posts, seen = [], set()
    total = None
    for page in range(1, max_pages + 1):
        if page > 1:
            time.sleep(SLEEP)
        text = http_get(LIST_URL.format(blog_id=blog_id, page=page))
        try:
            data = parse_naver_json(text)
        except ValueError:
            die(f"JSON이 아닌 응답(차단·점검 가능성, blogId={blog_id}, page={page}): {text[:80]!r}")
        if not isinstance(data, dict):
            die(f"예상하지 못한 응답 형식(blogId={blog_id}, page={page})")
        if data.get("resultCode") != "S":
            die(f"목록 조회 실패(blogId={blog_id}): {data.get('resultMessage') or data.get('resultCode')}")
        batch = data.get("postList") or []
        if total is None:
            try:
                total = int(data.get("totalCount"))
            except (TypeError, ValueError):
                total = None
        if not isinstance(batch, list):
            die(f"예상하지 못한 postList 형식(blogId={blog_id}, page={page})")
        for p in batch:
            try:
                log_no = str(p.get("logNo", ""))
                if not log_no or log_no in seen:
                    continue
                seen.add(log_no)
                posts.append({
                    "blogId": blog_id,
                    "title": decode_title(p.get("title")),
                    "category": decode_title(p.get("categoryName", "")),
                    "date": parse_add_date(p.get("addDate")),
                    "logNo": log_no,
                    "link": make_link(blog_id, log_no),
                })
            except (ValueError, AttributeError) as e:
                die(f"글 항목 해석 실패(blogId={blog_id}, page={page}): {e}")
        if len(batch) < PAGE_SIZE or (total is not None and len(posts) >= total):
            break
    return posts


def main():
    ap = argparse.ArgumentParser(
        description="네이버 블로그 글 목록(제목·카테고리·날짜·logNo·link)을 JSON으로 수집한다.")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--rss", nargs="+", metavar="blogId",
                      help="RSS(최근 50개)에서 읽는다. 여러 블로그면 하나의 배열로 합친다")
    mode.add_argument("--all", metavar="blogId",
                      help="PostTitleListAsync를 페이징해 전체 글 목록을 읽는다")
    ap.add_argument("--out", metavar="FILE", help="결과를 파일로 저장(기본: stdout)")
    ap.add_argument("--max-pages", type=int, default=50, metavar="N",
                    help="--all 모드 최대 페이지 수(기본 50)")
    args = ap.parse_args()

    posts = []
    if args.rss:
        for i, blog_id in enumerate(args.rss):
            if i:
                time.sleep(SLEEP)
            posts.extend(fetch_rss(blog_id))
    else:
        posts = fetch_all(args.all, args.max_pages)

    posts.sort(key=lambda p: (p["date"], p["logNo"]), reverse=True)
    out = json.dumps(posts, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out + "\n")
        print(f"{len(posts)}건 저장 -> {args.out}", file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
