---
name: blog-image-director
description: Use when a Clark academy blog draft needs its image slots planned and filled — e.g. "이미지 뽑아줘", "사진 어디 넣을까", "이미지 생성", "이미지 계획 짜줘", "슬롯에 사진 넣어줘", "blog-image-director", "blog-run 이미지 단계", "blog-run Step 3". Reads the `![슬롯: …]()` slots in posts/NNN-slug/draft-v2.md, decides per slot whether it gets an AI image (informational scenes) or a real academy photo (promo/CTA), writes images/image-plan.md, runs scripts/gen_image.py (Gemini) for the ai slots, opens and checks each generated image, and returns a gate-3 summary. Do NOT use for writing or revising the post text (blog-draft-writer), fact checking (blog-fact-check), SEO scoring (blog-naver-seo), or uploading to Naver (blog-naver-upload).
---

# 블로그 이미지 디렉터

## 왜 이 스킬이 있나

레퍼런스 3·4가 보여주듯 "소제목마다 요약 이미지 한 장 + 중간 작업 사진"이 글의 읽기 리듬을 만든다(`knowledge/design-system.md` ③·⑤).
이 스킬은 초안의 이미지 슬롯을 하나씩 진단해 **AI 생성(ai)** 과 **학원 실사진(photo)** 을 나누고, ai 슬롯만 Gemini로 생성한다.
홍보성 글에 AI 이미지를 쓰거나, 글자가 박힌 이미지·얼굴 클로즈업·같은 장면 반복이 나가는 것을 여기서 막는다.

- 수행 주체: **메인 세션**(서브에이전트 아님). 전제: cwd = 작업 폴더. 지식 파일은 cwd의 `knowledge/`에서만 읽는다.
- 입력: `work/posts/NNN-slug/draft-v2.md`, `work/posts/NNN-slug/gates.md`(`## 선택`의 유형 = 정보|홍보), `knowledge/design-system.md` ⑤, `photos/` 목록(+있으면 `photos/README.md`), 이 스킬의 `references/prompt-patterns.md`.
- 산출물: `work/posts/NNN-slug/images/image-plan.md`, `images/NN-<slug>.png`(ai 슬롯), 게이트 3용 요약.
- 이 스킬은 **사용자에게 묻지 않는다.** 게이트 3(이미지 승인) 질문과 `gates.md ## 이미지승인` 기록은 `/clark-blog:blog-run`이 한다.

## 0. 전제 확인

```bash
P=work/posts/<NNN-slug>
ls $P/draft-v2.md $P/gates.md knowledge/design-system.md scripts/gen_image.py
mkdir -p $P/images
ls photos/ ; cat photos/README.md 2>/dev/null
```

`draft-v2.md`가 없으면 "B' 단계(draft-v2.md)가 끝나지 않았습니다"라고 보고하고 중단한다. `design-system.md` ⑤를 읽어 둔다(텍스트 렌더링 금지·얼굴 클로즈업 금지·정보성=AI 허용/홍보성=실사진만·재사용 금지·캡션 규칙·"AI 생성" 표기 규정 유무).

## 1. 슬롯 추출 (등장 순서 = 슬롯 번호)

```bash
grep -n '!\[슬롯:' $P/draft-v2.md
```

위에서부터 `01, 02, …`로 번호를 붙인다. 이 번호가 image-plan.md `슬롯` 열, 파일명 `NN-`, 그리고 Step 4의 치환 순서가 된다.
각 슬롯의 `위치`는 바로 위 `## 소제목`(제목 바로 아래 첫 슬롯은 `제목 아래(표지)`).
슬롯 수가 ③·④ 기준(커버 1 + 소제목마다 1, 하한 5)에 못 미쳐도 **초안을 고치지 않는다** — 요약에 "슬롯 부족 N개"로 적어 메인에 넘긴다.

## 2. 슬롯 진단 — 목적과 유형

슬롯마다 **목적**을 하나 정한다: `표지` / `소제목 요약` / `절차 장면` / `장비` / `작업 장면` / `시험` / `서류` / `안전` / `학원 CTA`.
(목적 단어가 파일명 slug가 된다: 표지→cover, 시험→exam, 장비→equipment, 작업→work, 안전→safety, 서류→documents, 학원/CTA→academy …)

**유형 판정 규칙(위에서부터 먼저 맞는 것):**
1. 글 유형이 `홍보`(gates.md `## 선택`) → **모든 슬롯 photo**(⑤ "홍보성 글 = 학원 실사진만").
2. 학원 소개·CTA·수강 안내·교육장 실제 모습 슬롯 → **photo**.
3. `photos/`에 그 장면에 맞는 실사진이 있고 **이전 글에서 쓰지 않았다** → 정보성 장면이라도 **photo 우선**.
4. 정보성 장면(코스 주행·시험·장비·적재/하역·절차·서류·안전) → **ai**.

이전 글 사용 여부(⑤ 재사용 금지) 확인:

```bash
grep -ho 'photos/[^ ,|)`]*' work/posts/*/images/image-plan.md 2>/dev/null | sort | uniq -c
```

현재 글 폴더의 행은 빼고 본다. 이미 쓴 실사진은 후보에서 제외한다.
⑤ "본문 중간 절에 지게차 작업 장면 최소 1장"을 만족하는지 확인한다(작업·주행·적재 장면이 중간 절 슬롯 중 1개 이상).

## 3. ai 슬롯 프롬프트 작성

`references/prompt-patterns.md`의 장면 패턴(1~7)에서 고르고 `{time}`·`{angle}`·`{weather}`를 채운다. 원칙:
- 표의 프롬프트 칸에는 **장면 설명만**(영어 1~2문장, `|` 금지). 공통 접두/접미는 `gen_image.py`가 붙인다 — 중복해 쓰지 않는다.
- 같은 글 안에서 패턴·시간대·앵글이 겹치지 않게 변주한다.
- 글자·숫자·로고·번호판·얼굴 정면이 생길 만한 소재(현수막, 게시판, 시험 결과지, 차량 번호판)를 장면에 넣지 않는다.

## 4. photo 슬롯 후보

`photos/` 파일명과 `photos/README.md` 설명(있으면)으로 장면에 맞는 후보 **1~3개**를 고른다(작업 폴더 기준 경로 `photos/…`).
맞는 사진이 없으면 후보 칸에 `(실사진 없음 — 이랑 지정 필요)`라고 쓰고, 홍보 글이 아니면 ai로 바꿀지를 게이트 3 질문거리로 남긴다(유형을 임의로 바꾸지 않는다).

## 5. `images/image-plan.md` 저장 (포맷 고정 — Step 4가 소비)

```markdown
# 이미지 계획 — posts/NNN-slug
| 슬롯 | 위치(소제목) | 목적 | 유형 | 프롬프트(ai) / 후보 파일(photo) | 캡션(alt) | 파일 | 검수 |
|---|---|---|---|---|---|---|---|
| 01 | 제목 아래(표지) | 표지 | ai | a counterbalance forklift slowly driving through an S-shaped course … | 지게차운전기능사 실기 코스를 주행하는 지게차 | | |
| 02 | ## 소제목1 | 학원 CTA | photo | photos/교육장-01.jpg, photos/교육장-02.jpg | 교육용 지게차가 줄지어 선 실습장 | (게이트 3에서 확정) | |
```

- `유형` ∈ {ai, photo}. 칸 안에 `|`를 쓰지 않는다.
- `캡션(alt)`: 한 줄, 무엇을 보여주는지. 글의 핵심 키워드(`keyword`)는 **캡션 전체에서 1회만**(⑤·prompt-patterns.md 캡션 규칙). "AI 생성" 표기는 ⑤에 규정이 있을 때만 따른다.
- `파일` 경로 규칙: ai = **글 폴더 기준** `images/NN-<slug>.png`(gen_image.py가 채움), photo = **작업 폴더 기준** `photos/<파일>`(게이트 3에서 확정 후 메인이 채움). Step 4는 `images/…`는 글 폴더, `photos/…`는 작업 폴더를 기준으로 절대경로를 만든다.
- `검수` 열은 7단계에서 채운다(처음엔 비워 둔다). gen_image.py는 열 이름으로 찾으므로 열이 추가돼도 동작한다.

## 6. 생성

```bash
python3 scripts/gen_image.py $P/images/image-plan.md --dry-run      # 먼저: 대상 슬롯·최종 프롬프트·파일명 확인(키 불필요)
uv run --with google-genai --with pillow scripts/gen_image.py $P/images/image-plan.md
```

- 키는 작업 폴더 `.env`의 `GEMINI_API_KEY`(없으면 환경변수). 없으면 스크립트가 exit 2 → 생성하지 말고 요약에 **"Gate: GEMINI 키 대기"** 로 적어 메인에 넘긴다.
- 비용: 장당 약 $0.04(추정). 재생성도 과금되므로 한 글당 생성 총량은 ai 슬롯 수 × 3 이내로 한다.
- 실패 슬롯은 stderr에 남고 나머지는 계속된다(exit 1). 실패 슬롯만 `--only 03,05`로 1회 재시도.

## 7. 생성 이미지 검수 — 반드시 열어서 본다

ai 슬롯 이미지를 **Read 도구로 한 장씩 열어** 확인한다(파일 존재만으로 통과시키지 않는다):

| 검사 | 불합격 예 |
|---|---|
| 글자 렌더링 없음 | 간판·차체 문구·번호판·서류 글씨·가짜 한글 |
| 얼굴 클로즈업 없음 | 정면 얼굴이 식별되는 인물 |
| 같은 글 안 장면 중복 없음 | 두 슬롯이 같은 구도·같은 시간대 |
| 장면이 캡션·소제목과 맞음 | 좌식 과정 설명에 입식 지게차 |
| 로고·브랜드 없음 | 제조사 로고, 워터마크 |

판정은 `검수` 열에 `PASS` 또는 `FAIL: <사유>`로 적는다. FAIL이면 프롬프트를 고쳐(원인 소재 제거·앵글 변경) `--only <슬롯>`으로 재생성 — **슬롯당 최대 2회**. 2회 뒤에도 FAIL이면 `FAIL(2회): <사유>`로 남기고 게이트 3에 올린다(photo 전환 후보로 제안).

## 8. 게이트 3용 요약 (메인으로 반환)

```
이미지 계획: work/posts/NNN-slug/images/image-plan.md
| 슬롯 | 위치 | 유형 | 파일 / 후보 | 검수 |
01 표지 ai images/01-cover.png PASS
02 ## … photo 후보: photos/교육장-01.jpg, photos/교육장-02.jpg (선택 필요)
…
특이사항: 슬롯 부족 N개 / 실사진 없음 슬롯 / FAIL(2회) 슬롯 / Gate: GEMINI 키 대기
```

## 9. 게이트 3 이후는 이 스킬 밖

- 게이트 3 질문(교체·재생성·실사진 지정)과 `gates.md ## 이미지승인` 기록은 blog-run(메인)이 한다. 재생성 요청은 `gen_image.py --only NN` 재실행이며 **디스패치가 아니다**.
- 승인 결과 반영(photo 슬롯 `파일` 확정, `draft-v2.md` 슬롯을 절대경로 `![캡션](/abs/…)`로 치환해 `final.md` 작성, `lint_post.py --stage final`)은 **blog-run Step 4(메인)** 가 image-plan.md를 기준으로 한다.

## 금칙

- 홍보성 글·학원 CTA 슬롯에 AI 이미지 금지(⑤).
- 이전 글에서 쓴 실사진·AI 이미지 재사용 금지.
- 이미지에 글자·숫자·로고·번호판·얼굴 클로즈업 금지. "시험장" 표지·암시 장면 금지(금칙어 규칙).
- 이 스킬에서 `draft-v2.md`·`final.md`를 고치지 않는다.
