---
name: blog-naver-seo
description: Use when the Clark blog post needs Naver SEO polishing — e.g. "SEO 다듬어줘", "네이버 상위노출", "제목 추천", "제목 2안", "태그 뽑아줘", "키워드 넣어줘", "blog-naver-seo", "blog-run B' 단계". Fixes the one core keyword, writes two title options, spreads the keyword into headings and body (3~8 times), writes image captions, picks 5~10 tags, runs lint_post.py --stage final, and records a self-check table in seo.md. Do NOT use for fact verdicts (blog-fact-check), image generation (blog-image-director), or upload (blog-naver-upload).
---

# 네이버 SEO 검토·다듬기

## 왜 이 스킬이 있나

글이 정확해도 제목·소제목·태그·이미지 캡션이 검색어와 맞지 않으면 노출되지 않는다. 이 스킬은 **사실은 건드리지 않고** 검색 신호만 맞춘다.
기준은 `knowledge/naver-seo-checklist.md`(필수 전부 PASS)이고, 정량 항목은 `lint_post.py`가 센다. 숫자는 `knowledge/design-system.md` ④(글자수 1700~3500·소제목 4~7·이미지 5장 이상·태그 5~10)와 같다.

- 수행 주체: **blog-writer 에이전트의 B' 단계**(팩트체크 반영 직후). 사람이 "SEO 다듬어줘"라고 하면 메인이 수행.
- 전제: cwd = 작업 폴더. 지식 파일은 cwd의 `knowledge/`만 읽는다.
- 입력: 작업 중인 `draft-v2.md`(해당 글 폴더), `knowledge/naver-seo-checklist.md`, `knowledge/design-system.md`, topics 표의 해당 행.
- 출력: 수정된 `draft-v2.md` + 같은 폴더의 `seo.md`.

## 절차

1. **핵심 키워드 1개 확정**. topics 표 행의 키워드를 우선 쓴다. frontmatter `keyword:`에 적는다(없으면 추가). 한 글에 키워드는 하나만.
2. **제목 2안**. 둘 다 20~40자(공백 포함), 지역 키워드 1개 포함.
   - A안 = 키워드 전방배치형(키워드가 제목 앞 1/3 안). frontmatter `title:`에 A를 넣는다.
   - B안 = 호기심/질문형. frontmatter는 첫 줄이어야 하므로, 닫는 `---` 바로 다음 줄에 HTML 주석 `<!-- 제목 B안: … -->`으로 적는다(키워드 횟수 계산에서는 주석이 제외된다). 본문 `# ` 제목은 A와 같게 둔다.
   - 낚시 금지: 본문이 답하지 않는 약속은 쓰지 않는다.
3. **소제목**에 키워드를 1~2개 분산하고, "~방법 / ~순서 / ~비용 / ~기준" 형태로 쓴다. 소제목은 4~7개를 유지한다.
4. **본문 키워드 3~8회**로 조정한다. 문장이 자연스러워야 하며 억지로 넣지 않는다. **팩트체크 PASS 문장의 사실 내용(수치·일정·조항·출처)은 바꾸지 않는다** — 조사·어순·소제목 표현만 손댄다. 사실 문장이 바뀌면 fact-checker 재발주가 필요하다고 메인에 알린다.
5. **이미지 캡션(alt)**을 모든 이미지에 쓴다. 비어 있으면 안 되고, 캡션 중 하나에는 키워드를 1회 넣는다. 슬롯 `![슬롯: 설명]()` 형태는 이 단계에서 유지한다(경로 치환은 Step 4).
6. **태그 5~10개**: 키워드, 지역 2개, 자격증명, 과정명, "국비지원" 등. frontmatter `tags:` 리스트로 쓴다. 키워드·지역 키워드가 반드시 들어간다.
7. **정량 확인**:
   ```bash
   python3 scripts/lint_post.py work/posts/<NNN-slug>/draft-v2.md --stage final --json
   ```
   draft-v2.md에는 슬롯·관련글 자리표시가 남아 있어 `image_paths`·`related_links` 등은 FAIL일 수 있다. **SEO 항목만 본다**: `title_keyword`, `seo_title_length`, `seo_keyword_body`, `seo_keyword_h2`, `seo_image_captions`, `tags_count`, `chars`, `h2_count`, `forbidden`. 이 중 FAIL을 고치고 재실행한다(최대 3회). 나머지 FAIL은 후속 단계 몫이라고 `seo.md`에 적는다.
8. **셀프 체크표**를 `seo.md`에 쓴다. 체크리스트 필수 항목마다 한 행, 열은 `id | 결과(PASS/수정) | 근거`. lint 항목은 lint 값을 옮기고, "사람" 항목(제목-위치, 사진 원본성, 태그의 키워드·지역 포함, 원본성-출처의 복붙 여부, 원본성-변주, 주제 일관성)은 직접 판단해 근거를 쓴다. 근거 없이 PASS를 쓰지 않는다.

## seo.md 형식

```markdown
# SEO 채점 — <글 제목 A안>
키워드: <keyword> · 제목 A: … · 제목 B: …

| id | 결과 | 근거 |
|---|---|---|
| 제목-키워드 | PASS | lint title_keyword |
| 제목-위치 | PASS | 키워드가 제목 앞 1/3(…번째 글자)에 있음 |
| …필수 항목 전부… | | |

lint(final) 대상 외 FAIL: image_paths, related_links (draft 단계, 후속 단계에서 해결)
```

## 하지 말 것

- 키워드를 3~8회 밖으로 밀어 넣기, 키워드 나열형 문장.
- 팩트체크를 통과한 사실 문장 수정.
- 이미지 생성·경로 치환·업로드 수행(각각 blog-image-director·메인·blog-naver-upload 몫).
- 사용자(이랑)에게 직접 묻기 — 서브에이전트로 돌 때는 판단이 필요한 항목을 `seo.md` 끝 "메인에 전달"에 적는다.
