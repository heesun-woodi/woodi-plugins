---
name: blog-design-system
description: Use when the user wants to create or update the Clark academy blog's content design system document (knowledge/design-system.md) from 이랑's design references — e.g. "디자인 시스템 만들어줘", "디자인 시스템 갱신해줘", "레퍼런스 추가했어", "글 스타일 가이드 만들어줘", "블로그 디자인 가이드", "레퍼런스 블로그 분석해서 규칙 만들어줘", "blog-design-system", "build the blog design system", "update the style guide from references". Measures each reference post with scripts/fetch_post.py, turns 이랑's "why" notes into numeric rules, and writes knowledge/design-system.md (sections ①~⑨ + 부록 A/B, with the lint block in ④). Do NOT use for writing a post draft (use blog-draft-writer), for topic research (use blog-topic-research), or for SEO scoring of a draft (use blog-naver-seo).
---

# 블로그 디자인 시스템 만들기·갱신하기

## 왜 이 스킬이 있나

이랑과의 회의 결론은 **"디자인 가이드를 만드는 게 제일 중요하다"**였다. 원칙은 **"레퍼런스는 URL이 아니라 이유"** —
이랑이 레퍼런스마다 적은 메모(why)를 **측정값**으로 바꾸고, 그 측정값에서 **규칙**을 만든다. 규칙마다 어느 메모·어느 수치에서
왔는지 추적할 수 있어야 하며, 그 추적표가 결과 문서의 "부록 A"다. 인상("보기 좋다")만으로 규칙을 만들지 않는다.

- 산출물: 작업 폴더 `knowledge/design-system.md` (이 파일이 **유일한 정본**. 플러그인 scaffold의 것은 설치 시 복사되는 초기값일 뿐).
- 이 문서를 읽는 쪽: blog-writer 에이전트(초안), blog-fact-checker, `scripts/lint_post.py`(④의 lint 블록만 기계적으로 읽음).
- 수행 주체: 메인 세션(또는 우디). 사용자에게 묻는 일은 마지막 8단계 "이랑 검토 요청" 하나뿐이다.
- 템플릿: 이 스킬 폴더의 `references/design-system-template.md` (목차 ①~⑨·부록 A·B 고정, 헤딩 문구를 바꾸지 않는다).

모든 경로는 **작업 폴더(cwd) 기준**이다. 지식 파일을 `${CLAUDE_PLUGIN_ROOT}`에서 읽지 않는다(템플릿 파일만 이 스킬 폴더에서 읽는다).

---

## 0. 전제 확인

```bash
ls -d knowledge scripts && ls knowledge/academy-profile.md knowledge/source-blogs.json scripts/fetch_post.py scripts/fetch_posts.py scripts/lint_post.py
```

하나라도 없으면 "작업 폴더가 아닙니다. 먼저 `/clark-blog:blog-setup`으로 작업 폴더를 준비하세요."라고 안내하고 **중단**한다.

산출물: 없음(확인만).

## 1. 입력 수집과 모드 결정

1. `knowledge/academy-profile.md`를 읽는다 — 학원정보 표, "## 꼭 지켜야 할 점", "## 금칙어"(백틱 단어 전부), "## 홍보/정보 비율".
2. `knowledge/source-blogs.json`에서 `design_references[]`(각 `blogId`, `logNo`, `url`, `why`)와 `own_blog`(`blogId`, `categories.info`)를 읽는다.
   레퍼런스 번호 n은 배열 순서(1부터)다.
3. 모드 결정:
   - `knowledge/design-system.md`가 **없으면 → 생성 모드**.
   - **있으면 → 갱신 모드**. 기존 파일을 `work/design-system/design-system.prev-<YYYY-MM-DD>.md`로 복사해 둔다.
     갱신 모드의 규칙: (a) 이랑이 손으로 고친 문장(특히 ② 예시 문장, ⑧ 금칙)은 **그대로 보존**, (b) 새 측정값 때문에 바뀌는 수치·문장만 바꾼다,
     (c) 결과는 `knowledge/`에 바로 덮지 않고 `work/design-system/design-system.proposed.md`에 쓴다(8단계에서 승인 후 복사).

```bash
mkdir -p work/design-system
[ -f knowledge/design-system.md ] && cp knowledge/design-system.md "work/design-system/design-system.prev-$(date +%F).md" && echo "갱신 모드" || echo "생성 모드"
```

산출물: 모드(생성/갱신), 갱신 모드면 `work/design-system/design-system.prev-<날짜>.md`.

## 2. 레퍼런스·자기 글 측정 (읽기 전용 수집)

각 글에 `python3 scripts/fetch_post.py <blogId> <logNo> --json`을 실행한다. 출력은 `{"stats": {...}, "markdown": "..."}`이고 stats 키는 정확히 다음과 같다:
`blogId, logNo, title, chars, paragraphs, headings, images, bold_runs, bold_lines, quotes, links_out, links_naver_blog, oglinks`.
(`headings`는 fs24/fs19 글씨 또는 sectionTitle 문단만 센다 — 굵은 줄로 만든 소제목은 `bold_lines`에 들어간다. 3단계에서 보정한다.)

- 레퍼런스: `design_references` 전부 → `work/design-system/ref-<n>-<blogId>.json`(원본 JSON)과 `ref-<n>-<blogId>.md`(markdown만).
- 자기 블로그: `python3 scripts/fetch_posts.py --rss <own_blog.blogId>`에서 `category == own_blog.categories.info`("클라크중장비운전학원")인 글을
  `date` 내림차순 **최신 10개** → 각각 fetch_post → `work/design-system/own-<logNo>.json`, `own-<logNo>.md`.
  RSS에 해당 카테고리 글이 10개 미만이면 `python3 scripts/fetch_posts.py --all <own_blog.blogId>`로 다시 걸러 채운다. 그래도 모자라면 있는 만큼만 쓰고 개수를 보고에 적는다.

아래 스크립트를 그대로 실행하면 된다(요청 사이 0.5초 간격, 실패한 글은 건너뛰고 목록을 출력):

```bash
python3 - <<'PY'
import json, subprocess, time, os
D = "work/design-system"; os.makedirs(D, exist_ok=True)
src = json.load(open("knowledge/source-blogs.json", encoding="utf-8"))
own = src["own_blog"]; own_id = own["blogId"]; own_cat = own["categories"]["info"]
jobs = [(r["blogId"], r["logNo"], f"ref-{i}-{r['blogId']}") for i, r in enumerate(src["design_references"], 1)]

def posts(flag):
    out = subprocess.run(["python3", "scripts/fetch_posts.py", flag, own_id], capture_output=True, text=True)
    return json.loads(out.stdout) if out.returncode == 0 and out.stdout.strip() else []
mine = [p for p in posts("--rss") if p["category"] == own_cat]
if len(mine) < 10:
    seen = {p["logNo"] for p in mine}
    mine += [p for p in posts("--all") if p["category"] == own_cat and p["logNo"] not in seen]
mine = sorted(mine, key=lambda p: p["date"], reverse=True)[:10]
jobs += [(own_id, p["logNo"], f"own-{p['logNo']}") for p in mine]

failed = []
for blog, log, stem in jobs:
    r = subprocess.run(["python3", "scripts/fetch_post.py", blog, log, "--json"], capture_output=True, text=True)
    if r.returncode != 0:
        failed.append(f"{stem}: {r.stderr.strip()[:200]}"); continue
    data = json.loads(r.stdout)
    json.dump(data, open(f"{D}/{stem}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(f"{D}/{stem}.md", "w", encoding="utf-8").write(data["markdown"])
    time.sleep(0.5)
print("수집:", len(jobs) - len(failed), "/", len(jobs), "| 자기 글:", len(mine))
print("실패:", failed or "없음")
PY
```

**병렬화(선택)**: 이 수집은 읽기 전용이라 메인 세션이 서브에이전트(explore 또는 general-purpose) 2개로 나눠도 된다 —
예: 하나는 `ref-*` 전부, 하나는 `own-*` 전부. **쓰기 경로가 겹치지 않게**(접두어로 나눔) 하고, 각자 Bash로 위 스크립트의 자기 몫만 실행한다.
레퍼런스 측정이 하나라도 실패하면 그 레퍼런스는 규칙 근거로 쓸 수 없으므로 원인(URL·구형 에디터 등)을 8단계 보고에 적는다.

산출물: `work/design-system/ref-<n>-<blogId>.{json,md}` × 레퍼런스 수, `own-<logNo>.{json,md}` × 최대 10.

## 3. 측정표 작성 → `work/design-system/measurements.md`

먼저 아래 스크립트로 **자동 열**을 계산한다(행 = 글, 레퍼런스 먼저·자기 글 다음, 맨 아래 중앙값 2행).

자동 열 정의:
| 열 | 계산 |
|---|---|
| chars, headings, bold_lines, images, quotes, links_naver_blog | stats 값 그대로 |
| 이미지당 글자수 | chars ÷ images (images=0이면 `-`) |
| 소제목당 글자수 | chars ÷ 소제목 수 (소제목 수 = headings, 0이면 `-`; 3단계 수동 보정 후 다시 계산) |
| bold_runs/1000자 | bold_runs × 1000 ÷ chars, 소수 1자리 |
| 끝부분 관련글 링크 수 | markdown에서 공백 제외 글자 위치가 전체의 마지막 20% 구간에 있는 `blog.naver.com` 출현 수 |
| 해요체 비율 | markdown 문장(마침표·물음표·느낌표·줄바꿈으로 나눔, 링크·이미지 줄 제외) 중 끝이 `요`/`죠`로 끝나는 비율(%) |
| 평균 문장 길이 | 위 문장들의 공백 제외 글자수 평균 |

```bash
python3 - <<'PY'
import json, glob, re, statistics as st, os
D = "work/design-system"
def row(path):
    d = json.load(open(path, encoding="utf-8")); s, md = d["stats"], d["markdown"]
    nows = re.sub(r"\s", "", md); total = len(nows) or 1
    cut, late = total * 0.8, 0
    for m in re.finditer(r"blog\.naver\.com", md):
        if len(re.sub(r"\s", "", md[:m.start()])) >= cut: late += 1
    sents = [x.strip() for x in re.split(r"[.!?\n]+", md) if x.strip() and not x.strip().startswith(("!", "[", "http", "|", "#"))]
    ends = [re.sub(r"[\s\W_]+$", "", x) for x in sents]
    yo = sum(1 for e in ends if e.endswith(("요", "죠")))
    c, h, im = s["chars"], s["headings"], s["images"]
    return {"글": os.path.basename(path)[:-5], "chars": c, "headings": h, "bold_lines": s["bold_lines"], "images": im,
            "이미지당 글자수": round(c / im) if im else "-", "소제목당 글자수": round(c / h) if h else "-",
            "bold_runs/1000자": round(s["bold_runs"] * 1000 / c, 1) if c else "-", "quotes": s["quotes"],
            "links_naver_blog": s["links_naver_blog"], "끝부분 관련글 링크 수": late,
            "해요체 비율": round(100 * yo / len(ends)) if ends else "-",
            "평균 문장 길이": round(st.mean(len(re.sub(r"\s", "", x)) for x in sents)) if sents else "-",
            "도입부 유형": "", "구조 유형": "", "소제목(수동)": ""}
refs = [row(p) for p in sorted(glob.glob(f"{D}/ref-*.json"))]
owns = [row(p) for p in sorted(glob.glob(f"{D}/own-*.json"))]
cols = list((refs or owns)[0].keys())
def med(rows, k):
    v = [r[k] for r in rows if isinstance(r[k], (int, float))]
    return round(st.median(v), 1) if v else "-"
lines = ["# 측정표", "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
for r in refs + owns: lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
for name, rows in (("**중앙값(레퍼런스)**", refs), ("**중앙값(자기 글)**", owns)):
    lines.append("| " + " | ".join([name] + [str(med(rows, c)) if c not in ("도입부 유형", "구조 유형", "소제목(수동)") else "" for c in cols[1:]]) + " |")
open(f"{D}/measurements.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines))
PY
```

그다음 각 `ref-*.md`·`own-*.md`를 읽고 **수동 열 3개**를 채운다:

- **도입부 유형**(첫 3문장 기준, 하나만): `질문`(첫 3문장 안에 독자에게 묻는 `?` 문장) / `상황`(독자 처지 묘사 "~하시는 분", "~하려는데") /
  `통계`(숫자·수치로 시작) / `오해`(통념을 바로잡음 "~라고 알고 계신가요", "사실은") / 어느 것도 아니면 `기타:<한 단어>`.
- **구조 유형**(하나만): `절차형`(단계·순서 소제목) / `비교형`(A vs B·기준 비교) / `체크리스트형`(항목 나열 중심) / `Q&A형`(질문형 소제목) / `기타:<한 단어>`.
- **소제목(수동)**: `headings`가 0이거나 markdown을 읽어 보니 굵은 줄(`bold_lines`)이 소제목 역할을 하면, 소제목 역할을 하는 줄 수를 직접 센다.
  그렇지 않으면 `headings` 값을 그대로 쓴다. 이 열이 이후 모든 "소제목 수" 계산의 기준이다 → 값이 바뀐 행은 "소제목당 글자수"를 chars ÷ 소제목(수동)으로 고치고, 레퍼런스·자기 글 중앙값 행도 다시 계산한다.

표 아래에 "관찰 메모" 절을 만들고 레퍼런스마다 2~4줄로 **구조 사실**을 적는다(예: "소제목 6개, 각 소제목 바로 뒤 이미지 1장 후 본문", "마지막 문단 뒤 링크카드 3개").
이 메모가 부록 A에서 숫자로 못 대는 메모 조각("구성이 보기 좋다")의 근거가 된다.

산출물: `work/design-system/measurements.md` (자동 열 + 수동 열 + 중앙값 2행 + 관찰 메모).

## 4. 메모 → 측정값 → 규칙 추적표 (부록 A 초안)

`design_references`의 `why`를 의미 단위 조각으로 나눈다. 현재 레퍼런스 4개의 기본 쪼개기(**이 10조각을 전부 덮어야 한다**):

| 레퍼런스 | 메모 조각 | 대응 측정값(measurements.md 열) | 들어갈 절 |
|---|---|---|---|
| 1 wati08 | 구성이 보기 좋다 | 소제목(수동), 구조 유형, 관찰 메모 | ③ |
| 1 wati08 | 강조 부분 음영/굵게로 눈에 띔 | bold_runs/1000자, bold_lines, quotes | ④ |
| 1 wati08 | 글 끝에 자기 블로그 연결 링크 2~3개 | 끝부분 관련글 링크 수, links_naver_blog | ⑥ |
| 2 overcome6 | 딱딱하지 않고 자연스러운 흐름 | 해요체 비율, 평균 문장 길이, 도입부 유형 | ②, ⑦ |
| 2 overcome6 | 친근한 느낌 | 해요체 비율, 관찰 메모(말 걸기 표현) | ② |
| 3 magician_e | 소제목 여러 개로 나눠 읽기 편함 | 소제목(수동), 소제목당 글자수 | ③, ④ |
| 3 magician_e | 소제목마다 내용을 이미지 한 장으로 먼저 보여줌 | 관찰 메모(소제목 직후 이미지 여부), images vs 소제목(수동) | ③, ⑤ |
| 3 magician_e | 사진:글 비율 좋음 | 이미지당 글자수 | ④ |
| 4 rojisu0820 | 글과 사진 비율 좋음 | 이미지당 글자수 | ④ |
| 4 rojisu0820 | 중간중간 지게차 작업 사진 | images, 관찰 메모(작업 사진 위치) | ⑤ |

(위 표는 10행 — 3번 "사진:글 비율"과 4번 "글과 사진 비율"은 같은 측정값을 쓰지만 행은 따로 둔다.)
`design_references`가 바뀌었으면(추가·교체) 같은 방식으로 새 why를 쪼개 행을 더한다. why에 없는 내용으로 행을 만들지 않는다.

각 행에 (a) **그 레퍼런스의 실제 수치**(예: "ref-3 이미지당 글자수 180, 소제목(수동) 7, 이미지 9") 또는 숫자가 없는 조각이면 관찰 메모의 구조 사실,
(b) 그것을 바꾼 **규칙 문장**(5단계에서 정한 수치 포함), (c) **반영 절**을 채운다. 이 표가 결과 문서의 "부록 A"가 된다.

산출물: 부록 A 표(5단계에서 문서에 넣음).

## 5. 템플릿 채우기 → `knowledge/design-system.md`

`${CLAUDE_PLUGIN_ROOT}/skills/blog-design-system/references/design-system-template.md`(이 스킬 폴더의 템플릿 — 지식 파일이 아니므로 플러그인 경로에서 읽는다)를 복사해 각 절의 `<!-- 채우는 방법 -->` 지시대로 채운다(갱신 모드면 대상 파일은 `work/design-system/design-system.proposed.md`).
헤딩 문구·순서는 바꾸지 않는다. 다 채우면 "채우는 방법" 주석은 지우고, 맨 위 정본 주석과 ④의 lint 블록만 남긴다.

**수치 결정 공식** — 기준은 **레퍼런스 중앙값**(R). 자기 글 중앙값(O)이 R보다 작으면(짧거나 적으면) R 쪽을 따른다(자기 글로 끌려 내려가지 않는다).
모든 수치 뒤 괄호에 근거를 쓴다: `(레퍼런스 중앙값 2,900자, 자기 글 중앙값 1,400자 → R×0.7 내림 → 하한 2,000)`.

| 규칙 | 공식 | lint 키 |
|---|---|---|
| 본문 글자수 하한 | max(1500, 100단위 내림(R_chars × 0.7)) | `min_chars` |
| 본문 글자수 상한 | max(min_chars + 1000, 100단위 올림(R_chars × 1.4)) | `max_chars` |
| 소제목 수 | 기본 4~7(⑦ 변주 축 범위). R_소제목(수동)이 7보다 크면 상한 = R 반올림, 4보다 작아도 하한은 4 유지(레퍼런스 3 "소제목 여러 개") | `min_h2`, `max_h2` |
| 이미지 수 하한 | max(3, min_h2 + 1) — 소제목마다 1장 + 커버(레퍼런스 3) | `min_images` |
| 권장 이미지 수(문장 규칙) | 반올림((min_chars+max_chars)/2 ÷ R_이미지당글자수), 단 min_images 이상 | — |
| 이미지당 글자수 | 목표 ≤ R_이미지당글자수, 상한 = R × 1.5 (레퍼런스 3·4) | — |
| 소제목당 글자수 | R_소제목당글자수 × 0.7 ~ × 1.3 (반올림 10단위) | — |
| 강조(굵게) 빈도 | 1000자당 bold_runs: 반올림(R × 0.7) ~ 반올림(R × 1.3), 최소 1 (레퍼런스 1) | — |
| 음영 인용 | 글당 max(1, 반올림(R_quotes)) 개 내외, 핵심 요약·주의사항에만 (레퍼런스 1) | — |
| 관련글 링크 | 2~3개 고정(레퍼런스 1 메모 원문). ref-1 "끝부분 관련글 링크 수"를 근거로 병기 | — |
| 출처 각주 | 2 — 레퍼런스와 무관, "지어내기 금지" 원칙. 근거에 그렇게 적는다 | `min_sources` |
| 태그 수 | 5~10 — `knowledge/naver-seo-checklist.md`에 태그 기준이 있으면 그 값을 따른다 | `tags_min`, `tags_max` |
| 톤 | 해요체 비율 목표 ≥ 5% 단위 내림(ref-2 해요체 비율), 평균 문장 길이 R ± 10자 | — |
| 정보:홍보 | academy-profile.md 값 그대로(정보성 3 : 홍보 1 이하) | — |

R 값이 `-`(분모 0 등)인 항목은 계산하지 말고 기본값(lint 기본값 또는 위 고정값)을 쓴 뒤 "이랑 검토 요청"에 올린다.
②의 예시 문장은 `own-*.md`에서 **그대로 복사**하고 `(logNo)`를 붙인다 — 고치거나 지어내지 않는다.
부록 A에는 4단계 표를, 부록 B에는 measurements.md 중앙값 2행 + 차이 행 + "가장 큰 차이 3가지"를 넣는다.
분량 목표: A4 4~6장. writer가 매번 읽는 문서이므로 길게 설명하지 말고 규칙을 짧은 문장·표로.

산출물: `knowledge/design-system.md` (생성 모드) 또는 `work/design-system/design-system.proposed.md` (갱신 모드).

## 6. lint 블록 배치

④ 헤딩 **바로 다음 줄**에 정확히 이 형식으로 한 줄(값은 정수, 5단계 공식 결과, ④ 규칙 문장의 숫자와 동일):

```
<!-- lint: min_chars=2000 max_chars=4100 min_h2=4 max_h2=7 min_images=5 min_sources=2 tags_min=5 tags_max=10 -->
```

(위 숫자는 형식 예시일 뿐이다. 실제 값은 측정에서 계산한다.)
`scripts/lint_post.py`는 파일에서 **처음 나오는** `<!-- lint:` 주석 하나만 읽고 `키=정수`만 인식한다. 따라서 파일 안 다른 곳(정본 주석·다른 절·부록)에
`<!-- lint:`로 시작하는 주석을 두지 않는다. 다른 스킬이 키를 추가할 수 있으므로(예: SEO 키), 갱신 모드에서는 기존 블록에 있던 다른 키를 지우지 않는다.

산출물: ④의 lint 블록 1줄.

## 7. 자체 점검

아래를 전부 확인하고 하나라도 실패하면 고친 뒤 다시 확인한다(대상 파일 F = `knowledge/design-system.md` 또는 갱신 모드의 proposed 파일).

```bash
F=knowledge/design-system.md   # 갱신 모드: F=work/design-system/design-system.proposed.md
python3 - "$F" <<'PY'
import re, sys
t = open(sys.argv[1], encoding="utf-8").read()
heads = ["## ① ", "## ② ", "## ③ ", "## ④ ", "## ⑤ ", "## ⑥ ", "## ⑦ ", "## ⑧ ", "## ⑨ ", "## 부록 A", "## 부록 B"]
print("헤딩 누락:", [h for h in heads if h not in t] or "없음")
blocks = re.findall(r"<!--\s*lint:(.*?)-->", t, re.S)
print("lint 블록 수(1이어야 함):", len(blocks))
s4, s5 = t.find("## ④"), t.find("## ⑤")
first = t.find("<!-- lint:")
print("lint 블록이 ④ 안:", s4 < first < s5)
print("lint 값:", dict(re.findall(r"(\w+)=(\d+)", blocks[0])) if blocks else None)
print("남은 {{자리표시}}:", re.findall(r"\{\{[^}]*\}\}", t) or "없음")
print("남은 '채우는 방법' 주석(0이어야 함):", t.count("채우는 방법"))
words = []
inside = False
for line in open("knowledge/academy-profile.md", encoding="utf-8"):
    if line.startswith("## "): inside = line.strip() == "## 금칙어"
    elif inside: words += re.findall(r"`([^`]+)`", line)
sec8 = t[t.find("## ⑧"):t.find("## ⑨")]
print("⑧에 빠진 금칙어:", [w for w in words if w not in sec8] or "없음")
PY
```

그리고 lint가 실제로 이 값을 읽는지 확인한다(아무 짧은 샘플로 chars 규칙 문자열만 본다):

```bash
mkdir -p work/design-system/_lintcheck && printf -- '---\ntitle: t\n---\n본문\n' > work/design-system/_lintcheck/sample.md
python3 scripts/lint_post.py work/design-system/_lintcheck/sample.md --stage draft --json | python3 -c "import json,sys; print([c['rule'] for c in json.load(sys.stdin)['checks'] if c['id']=='chars'])"
rm -rf work/design-system/_lintcheck
```
(출력 범위가 lint 블록의 `min_chars~max_chars`와 같아야 한다. 갱신 모드에서는 승인·복사 후에 확인한다.)

눈으로 확인할 목록:
- [ ] ⑧ 금칙어 절에 academy-profile.md 금칙어 **전부**(위 스크립트 "빠진 금칙어: 없음").
- [ ] ⑦ 변주 축 **5개**(도입부 유형·소제목 수·구조 템플릿·지역 키워드 조합·마무리 CTA) + "최근 5편(work/variation-log.md)과 겹치지 않게".
- [ ] ⑤에 "텍스트 렌더링 금지", "얼굴 클로즈업 금지", "정보성 = AI 허용", "홍보성 = 실사진" 4개 모두.
- [ ] ⑥에 관련글 링크 **2~3개** + CTA 단락(연락처·지역, 금칙어 언급 금지).
- [ ] ⑨에 정보성 3 : 홍보 1 비율.
- [ ] ④ 규칙 문장의 숫자 = lint 블록의 숫자(키마다 대조).
- [ ] 부록 A가 **레퍼런스 전부 × why 조각 전부**를 덮음(4단계 표의 행이 모두 있음), 각 행에 실제 수치 또는 관찰 사실.
- [ ] ② 예시 문장마다 `(logNo)`가 있고 해당 `own-<logNo>.md`에 그 문장이 그대로 있음(`grep -F`로 확인).
- [ ] 모든 수치 규칙 뒤에 근거 괄호.

산출물: 점검 통과한 문서.

## 8. 결과 보고 (사용자에게)

다음을 한국어로 보고한다:
1. 모드, 측정한 글 수(레퍼런스 n/전체, 자기 글 n), 수집 실패 목록.
2. 변경 요약: 핵심 수치(글자수 범위·소제목 수·이미지 하한·이미지당 글자수·관련글) 한 줄씩, 근거 포함.
   갱신 모드면 `diff -u work/design-system/design-system.prev-<날짜>.md work/design-system/design-system.proposed.md`를 절 단위로 요약(바뀐 수치·추가/삭제 문장).
3. **이랑 검토 요청** 문구 — 그대로 포함:
   > 이랑님, 디자인 시스템 초안을 확인해 주세요. 특히 세 가지를 봐 주세요.
   > 1) ② 톤 예시 문장이 평소 이랑님 말투가 맞는지 (아니면 바꾸고 싶은 문장을 알려 주세요)
   > 2) ④ 분량 범위(글자수·소제목 수·이미지 수)가 부담스럽지 않은지
   > 3) ⑧ 금칙·주의에 빠진 것이 없는지 (계약상 쓰면 안 되는 표현이 더 있다면 알려 주세요)
4. 갱신 모드: 사용자가 승인하면 `cp work/design-system/design-system.proposed.md knowledge/design-system.md` 후 7단계 lint 확인을 다시 실행한다. 승인 전에는 `knowledge/`를 바꾸지 않는다.

이랑의 답을 받아 고친 내용은 `knowledge/design-system.md`에 직접 반영하고 머리말 "이랑 검토"를 날짜로 바꾼다.

산출물: 보고 메시지(+ 갱신 모드 승인 후 `knowledge/design-system.md` 교체).
