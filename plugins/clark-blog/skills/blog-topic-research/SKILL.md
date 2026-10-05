---
name: blog-topic-research
description: Use when the user wants fresh topic candidates for the Clark academy blog — e.g. "주제 찾아줘", "이번 주 블로그 주제", "주제 리서치", "오늘 뭐 쓰지", "주제 후보 표 만들어줘", "blog-topic-research", "topic research", "blog-run 1단계". Collects titles from the topic-source academy blogs (RSS) and our own full post list, filters by category, drops topics we already published, groups them by search intent, measures a few source posts, and writes work/topics/<date>-topics.md. Do NOT use for writing a post (blog-draft-writer), SEO scoring (blog-naver-seo), or image work (blog-image-director).
---

# 블로그 주제 리서치

## 왜 이 스킬이 있나

학원 블로그는 "무엇을 쓸까"에서 막힌다. 이 스킬은 경쟁·참고 학원 블로그의 **제목·카테고리·통계만** 읽어 후보 8~10개를 표로 만들고,
이랑이 번호만 고르면 되게 한다. 출처 글 본문은 베끼지 않는다(제목·통계만 사용). 정보성 글이 기본이고, 학원 홍보 주제는 전체의 1/4 이하.

- 수행 주체: 메인 세션(서브에이전트 아님). 전제: cwd = 작업 폴더. 지식 파일은 cwd의 `knowledge/`에서만 읽는다.
- 산출물: `work/topics/<YYYY-MM-DD>-topics.md`. 이 스킬은 **표까지만** 만든다. 번호 선택 게이트(게이트 1)는 `/clark-blog:blog-run`이 잡는다.
- 요청 간 0.5초 간격, 순차 실행. `fetch_post.py` 호출은 최대 10회.

## 0. 전제 확인

```bash
ls scripts/fetch_posts.py scripts/fetch_post.py knowledge/source-blogs.json knowledge/academy-profile.md
mkdir -p work/topics
```

없으면 "작업 폴더가 아닙니다. 먼저 `/clark-blog:blog-setup`을 실행하세요."라고 안내하고 중단한다.
`knowledge/source-blogs.json`에서 `topic_sources[]`(`blogId`, `categories`)와 `own_blog`를 읽고, `knowledge/academy-profile.md`의 금칙어를 확인해 둔다.

## 1. 기발행 글 전체 목록 갱신 (중복 검사용)

```bash
python3 scripts/fetch_posts.py --all pajuclark --out work/pajuclark-posts.json
```

`--all`은 `category`가 비어 있다 — 중복 검사에만 쓰고 카테고리 필터에는 쓰지 않는다. (`pajuclark`는 `own_blog.blogId`.)

## 2. 소스 블로그 RSS 수집

```bash
D=$(date +%F)
python3 scripts/fetch_posts.py --rss <topic_sources의 blogId 전부> --out work/topics/raw-$D.json
```

스키마는 `{blogId,title,category,date,logNo,link}` 배열. 최근 50개씩이라 블로그마다 분량이 다르다.

## 3. 카테고리 필터

각 글을 **자기 블로그의** `categories`에 든 것만 남긴다(예: wati08은 "중장비(지게차)", clark6591은 "지게차 정보센터").
최근 90일 글을 우선하고, 후보가 8개 미만이면 90일 밖 글까지 넓힌다. 수집 건수 → 필터 후 건수를 표 머리에 적는다.

## 4. 중복 판정 (우리 블로그 기준)

출처 글 제목과 `work/pajuclark-posts.json`의 제목을 다음 규칙으로 비교한다. LLM 판단이지만 기준은 고정이다.

1. **정규화**: 제목에서 날짜·연도·"N월", 지역명(의정부·양주·동두천·포천·서울·경기북부·남양주·파주 등), 괄호 안 지역 나열, 이모지·기호(`｜ [] ★ ▶`), 홍보 꼬리말(개강안내·모집·정원)을 제거하고 명사 핵심어 집합을 만든다.
2. **○ 중복(제외)**: 자카드 유사도 ≥ 0.5 이거나 핵심 키워드(예: "시험일정", "국비교육 일정", "재직자")가 같다. 일정·개강 공지는 날짜만 바뀌는 반복 글이므로 ○.
3. **△ 부분 중복(후보로 남기되 각도 변경 명시)**: 유사도 0.25~0.5, 또는 같은 주제지만 우리 글이 1년 이상 지났거나 다른 질문에 답한다. 표에 근거 제목과 "다른 각도"를 적는다.
4. **× 없음**: 유사한 우리 글이 없다.
5. ○는 후보 표가 아니라 "제외한 주제와 이유"로 보낸다. 근거로 우리 글 제목을 반드시 인용한다.
6. 출처 제목의 "실기 시험장 위치" 같은 표현은 `academy-profile.md` 금칙어와 겹치면 그대로 쓰지 않고, 접수·준비물 등으로 재구성한 제목안을 쓴다(제외 표에 "금칙어"로 기록).

## 5. 검색 의도 6종으로 묶고 리서치 포인트 달기

각 후보를 다음 중 하나로 분류한다: **자격증 취득 절차 / 시험 일정·접수 / 국비·내일배움카드 / 면허 종류·갱신 / 취업·실무 / 안전교육**.
후보 8~10개가 최소 4종 이상에 걸치게 고른다. 후보마다 "풍성하게 만들 추가 리서치 포인트" 1~2개를 쓴다 —
어디서 무엇을 확인할지 구체적으로(법령 → law.go.kr 건설기계관리법·시행규칙 조항, 시험 → 큐넷 q-net.or.kr, 훈련·카드 → 고용24 work24.go.kr).
수치·일정·조항은 이 단계에서 지어 쓰지 않는다. 조회할 곳만 적는다.

## 6. 출처 글 통계 측정 (≤ 10회)

후보 한 건당 1회, 총 10회 이하:

```bash
python3 scripts/fetch_post.py <blogId> <logNo> --json    # stats.chars, stats.images 사용
```

`sleep 0.5`로 간격을 둔다. 표에는 `chars / images`를 그대로 적고, **chars < 1500이면 ★**(우리가 더 풍성하게 쓸 여지). 측정하지 않은 후보는 "-"로 둔다(추정 금지).
원값 목록은 `work/topics/stats-<날짜>.txt`에 남겨 근거로 쓴다.

## 7. 후보 표 작성

`work/topics/<YYYY-MM-DD>-topics.md` — 후보 8~10개. **열 10개, 이 순서**:

| 번호 | 제목안 | 핵심 키워드 | 검색 의도 | 출처 글(링크) | 출처 글 chars/images | 우리 블로그 중복 | 추천 유형 | 추가 리서치 포인트 | 변주 제안 |
|---|---|---|---|---|---|---|---|---|---|

- **제목안**: 지역 키워드 1~2개(의정부·양주·동두천·포천·서울북부) 포함. 이 지역 조합이 `final.md`의 `variation.region`이 된다.
- **핵심 키워드**: **단일 키워드 1개**. 그대로 `final.md` frontmatter `keyword:`에 들어가며 린트가 제목에 이 키워드가 포함되는지 검사한다 → 제목안에 그 문자열이 그대로 들어 있어야 한다.
- **출처 글**: `https://blog.naver.com/<blogId>/<logNo>` 링크와 원제.
- **우리 블로그 중복**: ○/△/× + 근거 제목(△는 어떤 각도로 다르게 갈지).
- **추천 유형**: `정보` 또는 `홍보` — `final.md`의 `variation.type`이 된다. 홍보는 후보 전체의 1/4 이하.
- **변주 제안**: 구조 템플릿(절차형/비교형/체크리스트형/Q&A형) · 도입부 유형(질문/상황/통계/오해 바로잡기). `work/variation-log.md` 최근 5줄이 있으면 겹치지 않게 제안한다.

표 아래에 **"제외한 주제와 이유"** 표를 둔다 — 중복 ○는 전부 여기에 올리고(출처 글, 이유, 근거 우리 글 제목), 금칙어·범위 밖 제외도 적는다.

## 8. 이랑에게 선택 요청

표 맨 끝에 한 줄을 붙이고 이 스킬은 끝낸다:

> 이랑, 번호와 유형(정보/홍보), 지역 키워드 2개를 골라주세요. 여러 개 선택해도 됩니다.

선택 이후(`gates.md` 기록, 글 폴더 생성)는 blog-run이 처리한다. 이 스킬 단독 실행 시에는 표 경로와 후보 수·의도 분포만 보고한다.

## 금칙

- 출처 글 **본문을 옮기지 않는다**(제목·통계만).
- 수치·일정·법령 조항을 근거 없이 표에 적지 않는다.
- 학원 홍보 후보는 1/4 이하. 같은 주제의 날짜만 바꾼 후보 금지.
- "실기시험장" 등 `academy-profile.md` 금칙어를 제목안·키워드에 쓰지 않는다.
