#!/usr/bin/env python3
"""주제 중복 판정(blog-topic-research §4). 출처 글 제목을 우리 블로그 전체 글 제목과 비교해 ○/△/×를 출력한다."""
import argparse
import json
import re
import sys
for _s in (sys.stdout, sys.stderr):  # Windows 콘솔(cp949)에서도 한글·이모지 출력이 죽지 않게
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
REGIONS = ["서울","경기북부","의정부","양주","동두천","포천","남양주","파주","일산","고양","구리","도봉구","인천","평택","연천","논산","탄현"]
PROMO = ["개강안내","개강","모집안내","모집","일정안내","안내","정원","마감","접수중","수시","재직자","주말반","주중반","야간반","평일반","소수정예반","완성반"]
STRIP = ["중장비학원","중장비운전학원","지게차학원","학원"]
NOTICE = ["개강","모집","일정안내","일정 안내","접수 일정","시험일정","시험 일정"]  # 공지 유형 표지어
GENERIC = {"지게차","중장비"}  # 핵심 토큰 겹침 계산에서 제외(너무 흔함)
def tokens(title):
    title = title.replace("지게차 운전기능사", "지게차운전기능사")
    t = re.sub(r"\d{4}\s*년|\d{1,2}\s*월|\d{1,2}\s*일|\([월화수목금토일]\)", " ", title)
    t = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", t)
    words = t.split()
    out = set()
    for w in words:
        if w in REGIONS or w in PROMO or w in STRIP: continue
        if len(w) > 2 and w[-1] in "은는이가을를의에도로과와": w = w[:-1]  # 조사 1글자 제거
        if len(re.findall(r"[가-힣]", w)) >= 2: out.add(w)
    return out
def judge(src, keyword, posts, notice=False):
    S, K = tokens(src), tokens(keyword) - GENERIC
    if notice:
        for n in NOTICE:  # 소스 제목에 있는 표지어와 같은 표지어를 가진 우리 글(최신순)
            if n in src:
                for p in sorted(posts, key=lambda p: p["date"], reverse=True):
                    if n in p["title"]:
                        return (0.0, 0, "○", p["title"], p["date"])  # 공지 유형 중복
    best = []
    for p in posts:
        O = tokens(p["title"]); u = S | O
        j = len(S & O) / len(u) if u else 0
        core = len(K & O)
        lab = "○" if (j >= 0.5 or core >= 2) else ("△" if j >= 0.25 else "×")
        best.append((j, core, lab, p["title"], p["date"]))
    best.sort(key=lambda x: ({"○":0,"△":1,"×":2}[x[2]], -x[0], -x[1]))
    return best[0]


def main():
    ap = argparse.ArgumentParser(description="출처 글 제목이 우리 블로그(pajuclark) 기존 글과 중복인지 판정한다. ○ 중복 / △ 부분 중복 / × 없음.")
    ap.add_argument("title", help="출처 글 제목")
    ap.add_argument("keyword", help="후보의 핵심 키워드(4어절 이하)")
    ap.add_argument("posts", nargs="?", default="work/pajuclark-posts.json", help="우리 글 목록 JSON(기본: work/pajuclark-posts.json)")
    ap.add_argument("--notice", action="store_true", help="공지 유형 규칙: 개강·모집·일정안내 등 같은 표지어를 가진 우리 글이 있으면 ○")
    a = ap.parse_args()
    with open(a.posts, encoding="utf-8") as f:
        posts = json.load(f)
    j, core, lab, t, d = judge(a.title, a.keyword, posts, a.notice)
    print(f"{lab}\tjaccard={j:.2f}\tcore={core}\t{t} ({d})")


if __name__ == "__main__":
    main()
