---
name: blog-draft-writer
description: Use when a Clark academy blog post must be written as a draft or revised after fact-check — e.g. "초안 써줘", "블로그 글 작성", "이 주제로 글 써줘", "draft", "blog-run B 단계", "팩트체크 반영해줘", "draft-v2 만들어줘", "blog-run B' 단계". Mode B researches facts with source URLs (research.md) and writes draft.md following knowledge/design-system.md (structure template, image slots, bold/quote frequency, related-link placeholders, CTA, variation vs work/variation-log.md). Mode B' applies factcheck.md, then the blog-naver-seo procedure, swaps [[관련글]] for real pajuclark URLs, adds the final.md frontmatter, and saves draft-v2.md. Do NOT use for fact verdicts (blog-fact-check), topic research (blog-topic-research), image generation (blog-image-director), or upload (blog-naver-upload).
---

# 블로그 초안 작성(B)·수정(B')

## 왜 이 스킬이 있나

이랑이 고른 주제를 **디자인 시스템 한 장(`knowledge/design-system.md`)대로**, 출처 있는 사실만으로 쓰기 위해서다.
쓰는 쪽(이 스킬)과 검토하는 쪽(blog-fact-check)은 분리되어 있다 — 여기서는 사실 판정을 내리지 않고, 결정적 검사는 `lint_post.py`가 센다.

- 수행 주체: `blog-writer` 에이전트(`/clark-blog:blog-run`의 B·B' 단계). 사람이 직접 요청하면 메인이 같은 절차로 수행한다.
- 전제: cwd = 작업 폴더. 지식 파일은 cwd의 `knowledge/`에서만 읽는다(`${CLAUDE_PLUGIN_ROOT}`의 지식 파일은 읽지 않는다).
- 글 폴더: `work/posts/<NNN-slug>/` (아래에서 `P`로 줄여 쓴다).
- 모드: 발주 프롬프트의 `mode: B` 또는 `mode: B'`. 없으면 `P/draft.md`가 없을 때 B, 있고 factcheck 파일이 있으면 B'.

| 모드 | 읽기 | 쓰기(이 파일들만) |
|---|---|---|
| B | `P/gates.md`, `P/topic.md`(topics 표의 해당 행), `knowledge/design-system.md`·`academy-profile.md`·`law-sources.md`, `work/variation-log.md`(없을 수 있음), 이 스킬의 `references/structure-templates.md` | `P/research.md`, `P/draft.md` |
| B' | 위 전부 + `P/research.md`, `P/draft.md`, `P/factcheck.md`(r2면 `P/factcheck-r2.md`), `knowledge/naver-seo-checklist.md`, `work/pajuclark-posts.json`, blog-naver-seo 스킬 `SKILL.md` | `P/draft-v2.md`, `P/seo.md`, `P/research.md`(끝에 `## B' 추가 출처` 절 덧붙이기만) |

**공통 금지**: 위 표의 출력 파일 외에는 어떤 파일도 만들거나 고치지 않는다. `gates.md`는 메인만 쓴다(읽기만). `draft.md`는 B'에서 고치지 않는다(fact-checker가 판정한 원본). `knowledge/`·`work/variation-log.md`·`work/pajuclark-posts.json`도 읽기만. 조회 응답 같은 임시 파일은 작업 폴더 밖(`T=$(mktemp -d)`)에 둔다.

---

## 모드 B — 초안

### B-0. 전제 확인

```bash
ls knowledge/design-system.md knowledge/academy-profile.md knowledge/law-sources.md scripts/lint_post.py
ls work/posts/<NNN-slug>/
```

`knowledge/`가 없으면 "작업 폴더가 아닙니다. 먼저 `/clark-blog:blog-setup`을 실행하세요."로 반환한다. `gates.md`나 `topic.md`가 없으면 추측하지 말고 `## 질문`으로 반환한다.

### B-1. 입력 읽기

- `gates.md`의 `## 선택`: 번호, **유형(정보/홍보)**, **지역 키워드 2개**. 이 세 값은 이랑의 결정이므로 바꾸지 않는다. 유형이 비어 있으면 `topic.md`의 "추천 유형"을 쓰고 리포트에 적는다.
- `topic.md`(topics 표 한 행): 제목안, **핵심 키워드**(그대로 이 글의 keyword), 검색 의도, 추가 리서치 포인트, 변주 제안.
- `design-system.md` ①~⑨ 전부(특히 ③ 구조·소제목, ④ 수치, ⑤ 이미지, ⑥ 마무리, ⑦ 변주, ⑧ 금칙, ⑨ 홍보글 규칙).
- `academy-profile.md`: 학원정보 표·꼭 지켜야 할 점·`## 금칙어` 목록.

### B-2. 추가 리서치 → `research.md`

1. `topic.md`의 "추가 리서치 포인트"와 쓰려는 수치·일정·조항마다 `knowledge/law-sources.md`의 조회처에서 사실을 모은다.
   - 명령: `curl -sL -A "Mozilla/5.0" --max-time 20 "<URL>"`(Bash) 또는 WebFetch. WebFetch가 실패하면 curl로 다시 시도. 요청은 순차, 0.5초 이상 간격.
   - 법령: DRF `lawSearch.do?...&query=<법령명>`로 현행 MST·시행일자 확인 → `lawService.do?...&MST=<MST>&type=XML`에서 조문을 찾는다.
   - 시험 수수료·합격률: 큐넷 종목 탭 조각(`crf00503s02`·`crf00503s01`, jmCd=7875). 시험 일정: 큐넷 월간 일정(`crf021…crf02103`). 종목 탭의 빈 일정 표로 일정을 단정하지 않는다.
   - 국비·내일배움카드: 고용24 상세는 curl로 보이지 않는 것이 정상이다 → 금액·비율은 쓰지 않고, 제도 언급은 "고용24에서 최신 조건 확인" 문구로 쓴다.
   - `law-sources.md` 접근성 기록에서 "껍데기만"인 URL은 사실 확인 근거로 쓰지 않는다.
2. **이번에 실제로 열어서 문구를 확인한 사실만** 표에 적는다. 열지 못했거나 문구를 못 찾은 사실은 글에 쓰지 않는다. 주제에 꼭 필요해서 남겨야 하면 본문에 `[출처 필요]`를 붙인다(fact-checker가 잡고, lint `placeholder_sources`가 FAIL로 센다).
3. `research.md` 형식:

```markdown
# 리서치 — <NNN-slug>

| 사실 | 출처 URL | 조회 일시 |
|---|---|---|
| 지게차운전기능사 실기 수수료 <금액>(<YYYY>년 <M>월 큐넷 기준) | https://www.q-net.or.kr/crf005.do?id=crf00503s02&gSite=Q&gId=&jmCd=7875 | 2026-10-07 10:12 |
| 건설기계관리법 시행규칙 제<n>조 — "<원문 1줄>" (시행 <YYYY-MM-DD>) | https://www.law.go.kr/DRF/lawService.do?OC=test&target=law&MST=<MST>&type=XML | 2026-10-07 10:20 |

## 변주 선택
structure: <…> · intro: <…> · region: [<지역1>, <지역2>] · cta: <…> · type: <정보|홍보>
근거: <한 줄 — 최근 5줄과 각각 몇 개 축이 다른지>

## 출처를 못 찾은 것
- <쓰지 않은 사실 또는 [출처 필요]로 남긴 문장> — <어디를 봤는지 URL>
```

   - 사실 칸에는 출처 원문과 같은 값(숫자·조문 번호·시행일자)을 쓴다. 출처 URL은 전체 주소. 열지 않은 URL은 적지 않는다.
   - 시점이 바뀌는 값(수수료·합격률·일정)은 "YYYY년 M월 큐넷 기준"을 사실 칸과 본문 양쪽에 붙인다(fact-checker는 기준 시점이 없으면 PASS를 주지 않는다).

### B-3. 구조·변주 선택

1. `references/structure-templates.md`의 구조 템플릿 4종 중 1개 + 도입부 유형 4종 중 1개 + CTA 유형 3종 중 1개를 고른다. 지역은 `gates.md`의 2개.
2. `work/variation-log.md`를 읽는다. 형식은 한 줄 `YYYY-MM-DD | posts/NNN-slug | type | structure | intro | region | cta`. 이 형식의 줄 중 **마지막 5줄 각각**과 비교해 4개 축(structure·intro·region·cta) 중 **2개 이상**이 달라야 한다(region은 순서 무시, 두 지역 집합으로 비교). 한 줄이라도 1개 축만 다르면 다시 고른다. 지역은 이랑이 정했으므로 나머지 축을 바꿔 맞춘다. 파일이 없거나 해당 형식의 줄이 없으면 제약 없음.
3. `topic.md`의 "변주 제안"이 위 규칙을 통과하면 그것을 우선 쓴다.
4. ⑨: 유형이 홍보이고 **이번 글을 포함한 최근 4편**(로그 최근 3줄 + 이번 글) 중 홍보가 2편 이상이 되면(로그가 없으면 각 글 `gates.md ## 선택`의 유형으로 센다) 그대로 쓰되 리포트 `## 질문`에 "⑨ 비율 초과 — 정보로 바꿀지" 한 줄을 남긴다.
5. 고른 값과 근거 한 줄을 `research.md`의 `## 변주 선택`에 적는다(B'가 frontmatter로 옮긴다).

### B-4. `draft.md` 작성

frontmatter 없이 첫 줄이 `# 제목`이다(frontmatter는 B'에서 붙인다). 뼈대:

```markdown
# <제목 — keyword를 그대로 포함, 20~40자, 지역 키워드 1개>
![슬롯: <표지 장면 설명>]()
<도입 3문장 — 고른 도입부 유형, 3문장 안에 검색 의도의 답>

## <소제목 1>
![슬롯: <이 절 내용을 요약하는 장면 설명>]()
<본문 250~470자>

…소제목 4~7개…

## <마지막 소제목>
![슬롯: …]()
<본문>
> <절 끝 요약 또는 주의사항>

[[관련글: <주제 1>]]
[[관련글: <주제 2>]]

<CTA 한 단락 3~4문장>
```

규칙(숫자는 `design-system.md` ④가 정본 — lint 블록 값이 바뀌면 그 값을 따른다):

- **제목**: 첫 줄 `# `. `topic.md`의 핵심 키워드를 공백 무시하고 연속 문자열로 포함, 20~40자, 지역 키워드 1개. 본문이 답하지 않는 약속(낚시) 금지.
- **소제목**: `## ` 4~7개, ③의 형태(검색형 명사구 또는 질문, "~방법 / ~순서 / ~비용 / ~기준"). 제목을 소제목으로 반복하지 않는다. 키워드는 소제목 1~2개에 자연스럽게.
- **이미지 슬롯**: 표지 1장은 `# 제목` 바로 다음 줄. **각 소제목 바로 다음 줄**에 요약 이미지 슬롯 1장. 문법은 정확히 `![슬롯: <장면 설명>]()`(경로 비움 — 이미지 단계가 채운다).
  - 장면 설명은 한 줄로 "무엇이 보이는지"(장소·장비·인물 위치·앵글). 글자·간판·숫자·얼굴 클로즈업이 필요한 장면은 쓰지 않는다(⑤). 한 글 안에서 같은 장면을 반복하지 않는다.
  - 총 장수 = 올림(본문 글자수 ÷ 280) 근처, 최소 5장. 이미지 사이 본문이 420자를 넘으면 그 절 중간에 슬롯을 하나 더 넣는다. 중간 절에 **지게차 작업 장면(적재·하역·코스 주행) 최소 1장**.
  - 유형이 홍보면 슬롯은 학원 실사진으로 채울 장면(교육장·장비·실습)으로 쓴다(⑤ "홍보성 글 = 실사진만").
- **분량**: 본문 1700~3500자(공백 제외, 이미지·URL 제외), 소제목당 250~470자. 각 `## ` 절 본문은 `design-system.md` ③의 소제목당 글자수 **상한**(현재 470자 — 숫자는 ③에서 읽는다)을 넘지 않는다. 넘으면 절을 둘로 나누거나(소제목 7개 이내) 줄인다.
- **톤(②)**: 해요체 중심, 짧은 문장, 한 문단 2~4문장, 독자 처지로 말 걸기, 다음 절 예고 한 문장, 어려운 용어는 첫 등장 때 괄호 풀이. ② 금지 표현("~하여야 한다", "합격 보장", "100%", "무조건" 등) 쓰지 않음.
- **강조**: `**굵게**` 1000자당 6~12회 — 핵심 수치·결론·독자 질문 줄에만. 음영 인용 `> ` 글당 1~3개 — 절 끝 요약·주의사항에만(소제목을 인용으로 만들지 않는다).
- **출처**: 숫자·연도·기간·금액·조항 번호가 들어간 **모든** 문장 끝에 `(출처: <URL>)`를 붙인다. 앞에서 이미 인용한 조항을 다시 언급하는 문장("같은 규칙 제n조" 등), 도입부·마무리의 요약 문장도 예외가 아니다(같은 URL을 반복해도 된다). 예외는 `academy-profile.md`의 학원 연락처·주소·과정명을 그대로 쓴 부분뿐이다. URL은 `research.md`의 그 행과 같은 주소(법령은 독자용 `https://www.law.go.kr/법령/<법령명>`을 써도 되며 이때 조문 번호·시행일자를 문장에 적는다). 출처 각주 2개 이상. 출처가 없으면 그 문장을 쓰지 않거나 `[출처 필요]`.
- **관련글 자리**: 본문 끝, CTA 앞에 `[[관련글: <주제>]]` 2~3줄. 주제는 ⑥ 기준(같은 과정·자격 / 다음 단계 / 최근 1년)으로 짐작할 수 있게 쓴다. URL은 B'에서 실제 값으로 바꾼다 — 초안에 URL을 지어 넣지 않는다.
- **CTA(⑥ 2)**: 3~4문장 한 단락. 학원명 "클라크중장비운전학원", 연락처·주소는 `academy-profile.md` 그대로, 수강생 지역 1~2개, 과정 1개, 강점은 "강점" 행 범위 안. 고른 CTA 유형(`structure-templates.md` 3절)의 앞세우는 내용을 쓰되 예문·이전 글 문장을 복사하지 않는다. 정보성 글은 CTA를 짧게.
- **홍보글(⑨)**: 사실은 `academy-profile.md` 범위 안에서만. 수강료·자기부담금·할인 등 수치는 쓰지 않는다.
- **금칙(⑧)**: `academy-profile.md` `## 금칙어`의 단어(공백 무시) 0건. 목록 밖이라도 **학원(우리·저희·이곳)이 주어인 문장에 시험의 장소·장비·코스를 함께 쓰지 않는다**(의미 규칙). 레퍼런스·소스 블로그·자기 기존 글 문장 복붙 금지.

### B-5. 자체 점검 → lint (draft 단계)

lint 전에 아래를 실행해 (a) 숫자·`제n조`가 들어 있는데 `출처:`가 없는 문장(면허 등급 `1종`·`2종`, 톤수 `3톤` 같은 표기가 유일한 숫자인 문장은 제외 — 이 표기의 사실 여부는 fact-checker가 확인)과 (b) ③ 상한을 넘는 절을 찾고, 모두 고친 뒤 다시 실행한다. (a) 0건·(b) 없음이 될 때까지 반복한다(B'에서는 파일명을 `draft-v2.md`로).

```bash
python3 - work/posts/<NNN-slug>/draft.md <<'PY'
import re, sys
t = open(sys.argv[1], encoding="utf-8").read()
t = re.sub(r"\A---\n.*?\n---\n", "", t, flags=re.S)
t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
hi = int(re.search(r"소제목당 본문 \d+~(\d+)자", open("knowledge/design-system.md", encoding="utf-8").read()).group(1))
prof = open("knowledge/academy-profile.md", encoding="utf-8").read().splitlines()
ws = lambda s: re.sub(r"\s+", "", s)
keep = [r.split("|")[2] for r in prof if r.startswith(("| 연락처", "| 주소"))]
keep += [c for r in prof if r.startswith("| 과정") for c in r.split("|")[2].split(",")]
keep = sorted({ws(k) for k in keep if ws(k)}, key=len, reverse=True)  # 공백 무시 비교("3톤 미만" = "3톤미만")
bad = []
for ln in t.splitlines():
    # 빈 줄·제목·이미지·관련글 자리·목록(- / * / 1.) 줄은 건너뛴다
    if not ln.strip() or re.match(r"\s*(#|!\[|\[\[|[-*]\s|\d+\.\s)", ln):
        continue
    for snt in re.split(r"(?<=[.!?])\s+", ln):
        x = ws(snt)
        for k in keep:
            x = x.replace(k, "")
        if re.search(r"(\?|까요[.!]?)$", x):  # 앞 문장의 수치를 되묻는 연결 질문
            continue
        x = re.sub(r"[12]종|\d+(?:\.\d+)?톤", "", x)  # 면허 등급(1종·2종)·톤수(3톤)만 숫자인 문장은 제외
        if re.search(r"\d", x) and "출처:" not in snt and "[출처 필요]" not in snt:
            bad.append(snt.strip())
print("출처 없는 숫자·조항 문장:", len(bad))
for b in bad:
    print("  -", b)
for sec in re.split(r"\n(?=## )", t)[1:]:
    head, _, body = sec.partition("\n")
    # 마지막 절: 관련글 자리(B) 또는 관련글 링크(B')부터 끝(CTA 포함)은 세지 않는다
    body = re.split(r"\n(?=\s*(?:\[\[관련글|.*blog\.naver\.com/pajuclark/))", "\n" + body)[0]
    n = len(ws(re.sub(r"!\[[^\]]*\]\([^)]*\)|https?://\S+", "", body)))
    if n > hi:
        print(f"절 상한 초과({hi}자): {head} = {n}자")
PY
```

```bash
python3 scripts/lint_post.py work/posts/<NNN-slug>/draft.md --stage draft --json
```

- draft 단계는 `frontmatter`·`title_keyword`·`tags_count`·`related_links`·`image_paths`·`h1_once`·`seo_*` 4종을 SKIP한다. 보는 항목: `forbidden`, `chars`, `h2_count`, `images`, `sources`, `placeholder_sources`(`variation`은 frontmatter가 없으니 SKIP).
- FAIL 항목을 고치고 다시 실행한다(재실행 최대 2회). `placeholder_sources` FAIL은 일부러 남긴 `[출처 필요]` 때문이면 그대로 두고 건수를 보고한다. 그 밖의 FAIL이 2회 뒤에도 남으면 남은 항목과 이유를 보고한다.
- **판정을 선언하지 않는다**: "lint 통과했으니 완성" 같은 말을 쓰지 않는다. 마지막 실행의 `pass` 값과 FAIL id·값을 그대로 옮기고, 위 자체 점검의 "출처 없는 숫자·조항 문장" 건수(0이어야 함)와 절 상한 초과 건수도 함께 보고한다. 품질 판정은 fact-checker와 이랑의 몫이다.

### B-6. 반환(메인에게, 10줄 이내)

출력 경로(`research.md`·`draft.md`), 제목, keyword, 변주 선택(structure·intro·region·cta·type), lint 마지막 결과(`pass` 값 + FAIL id·값, stats의 chars·h2_count·images·sources·bold_runs·quotes), 출처 없는 숫자·조항 문장 건수, `[출처 필요]` 건수, 그리고 메인/이랑이 답해야 하는 것이 있으면 `## 질문` 절.

---

## 모드 B' — 수정 + SEO

발주(재개) 메시지가 주는 것: `mode: B'`, factcheck 파일 경로(`P/factcheck.md` 또는 r2면 `P/factcheck-r2.md`), blog-naver-seo `SKILL.md` 절대경로, 그리고 경우에 따라 반영할 게이트 2 피드백(`gates.md ## 초안피드백`) 또는 메인 lint 결과(`P/lint.json`).

### B'-0. 시작 파일

- `P/draft-v2.md`가 **이미 있으면**(메인이 FAIL+출처필요 0건이라 `draft.md`를 복사해 둔 경우, 또는 재개) 그 파일에서 시작한다.
- 없으면 `draft.md` 내용을 그대로 `draft-v2.md`로 만든 뒤(Write) 그 파일을 고친다. `draft.md`는 건드리지 않는다.

### B'-1. 팩트체크 반영

factcheck 파일에서 아래만 반영한다(그 밖의 사실 문장은 건드리지 않는다).

- `## B'에서 반영할 것`의 항목 전부:
  - **FAIL** → 표의 "수정 제안" 문장대로 바꾼다. 출처 URL도 판정 근거의 URL로 맞추고, 바뀐 URL은 직접 다시 열어 문구를 확인한 뒤 `research.md` `## B' 추가 출처`에 행을 추가한다.
  - **출처필요** → 출처를 새로 찾아(B-2와 같은 방법, 실제로 열어 확인) 문장을 고치고 본문 각주 `(출처: <URL>)`를 달거나, 못 찾으면 문장을 삭제하거나, fact-checker가 제안한 "확인 필요" 문구(예: "큐넷/고용24에서 최신 내용 확인")로 바꾼다(수치·단정 없이). 새 출처는 `research.md` 끝 `## B' 추가 출처` 절에 B-2와 같은 표 형식으로 덧붙인다(기존 행은 고치지 않는다 — r2 검토 때 fact-checker가 다시 연다). `[출처 필요]` 표시는 B'에서 0건이 되어야 한다.
  - 항목이 `없음`이면 이 단계는 건너뛴다.
- `## 시점 표기 권고`의 항목: 해당 문장 끝에 "(YYYY년 M월 큐넷 기준)"처럼 기준 시점을 붙인다.
- `## 질문`의 항목은 반영하지 않는다(메인이 이랑에게 묻는다). 메인이 답을 발주 메시지로 주면 그 답대로 반영한다.
- **PASS 문장**: 사실 내용(수치·일정·조항·출처)은 그대로 두고 조사·어순·문체만 손댈 수 있다.
- 새로 찾은 출처로 사실 문장을 바꾸거나 더했다면, 그 문장 id·내용을 리포트의 "사실 문장 변경" 줄에 적는다(메인이 C r2 재발주를 판단한다).

### B'-2. SEO — blog-naver-seo 스킬 절차 적용

발주 메시지가 준 blog-naver-seo `SKILL.md`를 읽고 그 **1~8단계를 `draft-v2.md`에 그대로** 수행한다(keyword 확정 → 제목 A/B안 → 소제목 키워드 → 본문 키워드 3~8회 → 이미지 캡션 → 태그 5~10개 → `--stage final` lint로 SEO 항목만 확인 → `P/seo.md` 셀프 체크표). 이 스킬과 다른 점·보충:

- keyword: `topic.md`의 핵심 키워드. 바꾸지 않는다.
- 제목 B안도 keyword를 그대로 포함하게 쓴다(게이트 2에서 이랑이 B안을 고르면 그대로 title이 되므로 lint `title_keyword`를 통과해야 한다).
- 이미지 캡션: `![슬롯: …]()` 문법과 빈 경로는 그대로 둔다. 슬롯의 장면 설명을 캡션으로도 읽힐 한 줄(무엇을 보여주는지)로 다듬고, 슬롯 중 1개의 설명에 keyword를 1회 넣는다.
- SEO 스킬 7단계의 `--stage final` 실행은 SEO 항목 확인용이다 — `image_paths`·`related_links` FAIL은 정상(슬롯·자리표시 때문)이며 `seo.md`에 "후속 단계 몫"으로 적는다. B'의 최종 lint는 아래 B'-5의 `--stage draft`다.

### B'-3. `[[관련글: …]]` → 실제 링크

`work/pajuclark-posts.json`(배열, 항목 `{blogId, title, category, date, logNo, link}`)에서 2~3개를 골라 각 `[[관련글: …]]` 줄을 바꾼다.

- 고르는 기준(⑥ 1): (a) 같은 과정·자격 주제 (b) 다음 단계 주제(필기 → 실기 → 면허 발급) (c) `date`가 최근 1년 이내 우선. 같은 글을 두 번 걸지 않는다.
- **제외**: 제목에 `academy-profile.md` `## 금칙어` 단어(공백 무시)가 있는 글 — lint `forbidden`은 링크 텍스트도 검사한다.
- 형식: `- [<그 글의 실제 제목>](https://blog.naver.com/pajuclark/<logNo>)`. 제목은 JSON의 `title` 그대로 쓰되 링크 텍스트를 깨는 `[`·`]`는 `(`·`)`로 바꾸고 앞뒤 장식 이모지만 뗄 수 있다. URL은 JSON의 `logNo`로 만든 실제 값만 — 지어낸 URL 금지.
- 관련글 묶음 앞에 한 줄 안내(예: "함께 읽으면 좋은 글")를 둘 수 있다. 위치는 본문 끝, CTA 단락 앞.
- 맞는 글이 2개 미만이면 찾은 만큼만 걸고 남은 `[[`는 지운 뒤 리포트 `## 질문`에 적는다(`[[`가 남으면 업로드가 막힌다).

### B'-4. frontmatter

B'-2(SEO 1·2·6단계)에서 만든 `title`·`keyword`·`tags`와 B안 주석을 포함해, `draft-v2.md` 맨 위 frontmatter를 아래 형식으로 완성한다(첫 줄 `---`, 키 순서·형식 고정, 닫는 `---` 바로 다음 줄이 B안 주석, 그다음 `# 제목`):

```markdown
---
title: <제목 A안>
keyword: <핵심 키워드>
category: 클라크중장비운전학원
tags: [<키워드>, <지역1 포함 태그>, <지역2 포함 태그>, <자격증명>, <과정명>, …]
variation: {type: <정보|홍보>, structure: <절차형|비교형|체크리스트형|Q&A형>, intro: <질문|상황|통계|오해 바로잡기>, region: [<지역1>, <지역2>], cta: <학원 소개|관련글|문의>}
---
<!-- 제목 B안: <제목 B안> -->
# <제목 A안>
```

- `variation.type`은 **`gates.md ## 선택`의 유형** 그대로. 나머지 네 값은 `research.md`의 `## 변주 선택` 그대로.
- `category`는 `gates.md`에 다른 카테고리가 적혀 있으면 그것을 쓴다.
- 이미지 슬롯은 그대로 둔다(메인이 Step 4에서 `final.md`를 만들며 절대경로로 치환한다).

### B'-5. 저장·lint·반환

```bash
python3 scripts/lint_post.py work/posts/<NNN-slug>/draft-v2.md --stage draft --json
```

- lint 전에 B-5의 자체 점검(파일명 `draft-v2.md`)을 먼저 돌려 출처 없는 숫자·조항 문장 0건·절 상한 초과 없음으로 만들고 건수를 보고한다.
- final 단계 검사(이미지 경로 등)는 이미지 치환 뒤 메인이 `final.md`로 돌린다. 여기서는 draft 단계로 `forbidden`·`chars`·`h2_count`·`images`·`sources`·`placeholder_sources`·`variation`(frontmatter가 있으니 PASS여야 함)을 본다. FAIL은 고치고 재실행(최대 2회). `placeholder_sources`는 B'에서 0이어야 한다.
- 판정 선언 금지 — 결과만 옮긴다.
- 반환(메인에게, 10줄 이내): `draft-v2.md`·`seo.md` 경로, 제목 A/B안, 반영한 factcheck 항목 id 목록, **사실 문장 변경**(B'-1에서 factcheck 항목 밖으로 바뀐 사실 문장 — 없으면 "없음"), 관련글 2~3개(제목·logNo), lint 마지막 결과(`pass` + FAIL id·값), `## 질문`(있으면).

### 재개되는 경우 (같은 B' 절차, 범위만 다름)

- **메인 lint FAIL(Step 2)**: 발주 메시지의 `P/lint.json` FAIL 항목만 `draft-v2.md`에서 고치고 B'-5를 다시 한다.
- **게이트 2 피드백**: `gates.md ## 초안피드백`대로 고친다. 이랑이 제목 B안을 고르면 frontmatter `title`·`# 제목`을 B로 바꾸고 주석을 `<!-- 제목 A안(미채택): … -->`로 바꾼다. 사실 문장이 바뀌었으면 "사실 문장 변경"에 적는다(메인이 C r2를 발주한다). 그 뒤 `factcheck-r2.md`가 오면 B'-1부터 그 파일로 다시 한다.

## 하지 말 것

- 출처 없는 수치·일정·조항, 열지 않은 URL, 지어낸 관련글 URL.
- 금칙어·시험 장소 암시(⑧), ② 금지 표현, 복붙.
- 사실 판정·"완성/통과" 선언(자기 승인 금지), 사용자에게 직접 묻기(`## 질문`으로 반환), 서브에이전트 발주.
- 출력 파일 외 파일 수정, `gates.md` 쓰기, B'에서 `draft.md` 수정, 이미지 생성·경로 치환·업로드.
