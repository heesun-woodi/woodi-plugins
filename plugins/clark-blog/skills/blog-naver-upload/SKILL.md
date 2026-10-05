---
name: blog-naver-upload
description: Use when a finished Clark academy blog post (posts/NNN-slug/final.md, gate 3 passed) must be saved to Naver Blog as a draft — e.g. "네이버에 올려줘", "임시저장", "업로드", "네이버 임시저장해줘", "blog-naver-upload", "blog-run 업로드 단계", "blog-run Step 5". Runs scripts/naver_upload.sh (lint → session check → naver-blog-cli create-draft → list-drafts confirm), then records gates.md and work/variation-log.md. Do NOT use for pressing the publish button (the human publishes), deleting drafts or posts, editing already-uploaded posts, or writing/revising text (blog-draft-writer) or images (blog-image-director).
---

# 네이버 임시저장 업로드

`final.md`를 네이버 블로그 **임시저장**까지만 올린다. 발행은 이랑이 네이버 앱/웹에서 미리보기를 보고 직접 한다.
에디터 조작은 외부 CLI `naver-blog-cli`에만 위임하고(명령·출력 문구: `references/naver-blog-cli.md`), 이 스킬은 Playwright 코드를 쓰지 않는다.

- 수행 주체: **메인 세션이 직접**. 서브에이전트에 맡기지 않는다 — 로그인 만료·2차 인증·CAPTCHA·브라우저 창 개입이 생길 수 있다.
- 전제: cwd = 작업 폴더, 게이트 3(이미지 승인) 통과, `work/posts/NNN-slug/final.md` 존재(frontmatter `title/category/tags/variation`, 이미지 절대경로, 실제 관련글 URL).
- 이 스킬은 사용자에게 묻지 않는다. 종료 보고는 `/clark-blog:blog-run`이 한다.

## 절차

1. 실행 (작업 폴더에서):

   ```bash
   scripts/naver_upload.sh work/posts/NNN-slug/final.md [--blog-id pajuclark] [--category "클라크중장비운전학원"]
   ```

   처음 한 번은 `--dry-run`으로 title/category/tags/이미지 수를 확인해도 된다(이것도 세션 확인까지는 실제로 수행한다).
   스크립트가 하는 일, 순서대로: ① `lint_post.py --stage final` + 금칙어·`[[`·빈 이미지·`[출처 필요]` 이중 검사 → ② `naver-blog-cli check-session` → ③ frontmatter 읽기 → ④ 본문 임시파일 생성(frontmatter·첫 `# ` H1·`<!-- 제목 B안/A안 … -->` 주석 제거, 이미지 절대경로 확인) → ⑤ `create-draft` → ⑥ `list-drafts`에 제목이 보이는지 확인 → ⑦ `work/posts/NNN-slug/upload.log`에 기록.
   창이 뜨고 글 하나에 수 분 걸린다. CAPTCHA가 뜨면 이랑에게 창을 직접 처리하도록 알린다.

2. 종료 코드별 대응:

   | 코드 | 의미 | 대응 |
   |---|---|---|
   | 0 | 임시저장 완료 | 아래 3 진행 |
   | 10 | `lint_post.py` 실패(실패 항목 출력됨) | 본문 문제면 blog-writer를 `SendMessage`로 재개(B', 최대 1회), 이미지 경로·단순 치환이면 메인이 `final.md` 수정 후 `lint_post.py final.md --stage final` 재확인 → 다시 업로드 |
   | 11 | 이중 검사 실패(금칙어·`[[`·빈 이미지·`[출처 필요]`) | lint를 통과했는데 걸렸다면 lint 규칙 구멍이다 — 해당 줄을 고치고 이랑에게 한 줄 보고 |
   | 12 | 이미지 경로가 절대경로가 아니거나(URL 포함) 파일이 없음 | `/clark-blog:blog-run` Step 4(`image-plan.md` 기준 절대경로 치환)를 다시 실행 |
   | 20 | 세션 없음/만료 또는 `naver-blog-cli` 없음 | 이랑에게 로그인 안내: 작업 폴더에서 `python ~/naver-blog-cli/login_setup.py`(자세한 명령은 README), **"로그인 상태 유지" 체크**. 로그인은 사람만 한다. 끝나면 같은 명령 재실행 |
   | 30 | `create-draft` 실패 | 출력된 CLI 문구를 `references/naver-blog-cli.md`의 실패 유형과 대조: 에디터 개편(`…을 못 찾음`) · 이미지 10MB 초과 · 세션 만료. 임시저장 수가 늘었을 수 있으니 `list-drafts`/네이버에서 중복 여부를 확인한 뒤 재시도 |
   | 31 | 저장은 끝났으나 목록에서 제목 확인 불가 | 저장됐을 수 있다. 이랑에게 "네이버 → 글쓰기 → 임시저장 글"에서 직접 확인을 요청하고, 있으면 성공으로 처리 |
   | 2 | 사용 오류(경로·frontmatter) | 인자와 `final.md` frontmatter 확인 |

   같은 오류로 재시도는 한 번까지. 반복 실패하면 멈추고 이랑에게 보고한다(계정 안전).

3. 성공 시 기록 (메인이 직접):
   - `work/posts/NNN-slug/gates.md`의 `## 업로드`에 일시·제목·`upload.log` 경로 추가.
   - `work/variation-log.md`에 한 줄 추가. 형식 `YYYY-MM-DD | posts/NNN-slug | type | structure | intro | region | cta`, 값은 `final.md` frontmatter `variation`에서(`type`은 게이트 1에서 고른 정보/홍보, `region`은 `의정부+양주`처럼 `+`로 연결):

     ```
     2026-10-07 | posts/001-지게차운전기능사-실기-준비 | 정보 | 절차형 | 상황 | 의정부+양주 | 관련글
     ```
   - 이랑에게 안내: "네이버 앱/웹 → 글쓰기 → 임시저장 글 → 미리보기 → 발행".

## 계정 안전 수칙

- 자동화는 **임시저장만**. `publish-draft`·`delete-draft`·`delete-post`는 호출하지 않는다.
- 하루 1~2편 이내. 같은 날 연속 업로드·재시도를 늘리지 않는다.
- `playwright-state/storage_state.json`은 계정 접근권한이다. 출력·커밋·공유 금지.

## 폴백 (2차)

CLI가 네이버 에디터 개편으로 계속 `…을 못 찾음`을 내면, 이랑 승인 아래 aside(AI 브라우저)에 `final.md`와 `images/`를 주고 **"임시저장까지만, 발행 금지"**로 수동 지시한다. 이 경로에서도 로그인·2FA는 이랑이 한다.
