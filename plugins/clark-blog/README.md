# clark-blog

클라크중장비운전학원(`pajuclark`) 네이버 블로그의 **정보성 글**을 만드는 Claude Code 플러그인입니다. 주제 리서치 → 디자인 시스템 기준 초안 → 법령·공공기관 근거 검토 → 네이버 SEO 다듬기 → 이미지 → 네이버 **임시저장**까지 진행하고, **발행은 사람(이랑)이 네이버에서 직접** 합니다. 이 플러그인은 발행 버튼을 누르지 않습니다.

## 왜 이렇게 만들었나

**소스를 먼저 정의합니다.** 글의 품질은 무엇을 보고 따라 쓰느냐에서 갈립니다. 주제는 지게차 교육을 하는 학원 블로그 3곳에서 찾고(`clark6591` 정보성 글 월 3~4편으로 가장 좋은 소스, `wati08` 거의 매일 발행, `voliskpe` 2025-02 이후 정지라 "지게차" 카테고리만), 글의 모양은 이랑이 "왜 좋은지"를 적어 준 레퍼런스 4편에서 가져옵니다(구성·음영 강조·자연스러운 흐름·소제목마다 이미지 한 장·사진과 글의 비율). 이 목록은 작업 폴더 `knowledge/source-blogs.json`에 있고, 바꾸고 싶으면 거기서 고칩니다.

**디자인 시스템 문서 한 장이 정본입니다.** 레퍼런스에서 잰 수치(글자 수 1700~3500자, 소제목 4~7개, 이미지 5장 이상, 이미지 한 장당 글자 수 420자 이하, 굵게 1000자당 6~12회, 인용 1~3개)와 말투·이미지·마무리·변주 규칙을 `knowledge/design-system.md`에 모아 둡니다. 정본은 **작업 폴더의 `knowledge/` 하나뿐**입니다. 플러그인의 `scaffold/knowledge/`는 설치할 때 한 번 복사되는 초기값이고, 이후에는 이랑이 작업 폴더에서 직접 고칩니다. 스킬과 에이전트는 항상 작업 폴더의 `knowledge/`만 읽습니다.

**쓰는 쪽과 검토하는 쪽을 분리합니다.** 글은 `blog-writer` 에이전트가 쓰고, 사실 검토는 `blog-fact-checker` 에이전트가 따로 합니다. fact-checker는 Edit 도구가 없어 초안을 고치지 못하고 `factcheck.md` 리포트만 씁니다. 쓴 쪽이 자기 글을 승인하지 못하게 하려는 구조입니다. 사용자에게 묻는 일(게이트 3개)은 전부 메인 세션이 하고, 에이전트끼리는 파일 경로로만 넘깁니다. 수치·일정·수수료·법령 조항은 출처 URL이 없으면 초안에 넣지 않습니다.

**결정적인 검사는 스크립트가, 판단은 모델이 합니다.** 금칙어, 자리표시(`[[`) 잔존, 빈 이미지 경로, `[출처 필요]` 잔존, 분량, 소제목 수, 이미지 수, 출처 각주 수는 `lint_post.py`가 셉니다. 업로드 스크립트 `naver_upload.sh`가 같은 핵심 검사를 한 번 더 합니다. 금칙어에는 `실기시험장`이 들어 있습니다. 학원이 실기시험장이라는 사실은 블로그·홈페이지에 쓰면 안 되는 계약 조항이라, 이 표현과 그것을 암시하는 문장을 lint가 막습니다.

**변주가 요구사항입니다.** 네이버는 복붙·사진 재사용·날짜만 바꾼 반복 글을 낮게 평가합니다. 그래서 글마다 구조 템플릿(절차형/비교형/체크리스트형/Q&A형), 도입부 유형, 지역 키워드 2개(의정부·양주·동두천·포천·서울북부), 마무리(학원 소개/관련글/문의)를 `work/variation-log.md` 최근 5줄과 다르게 고르고, 업로드가 성공할 때마다 로그에 한 줄을 더합니다.

**임시저장까지만 자동입니다.** 네이버 블로그 글쓰기 공식 API는 종료됐습니다. 그래서 오픈소스 `naver-blog-cli`가 Playwright로 스마트에디터ONE을 조작하는 경로를 쓰는데, 이 도구도 "과도하게 쓰면 계정이 제재될 수 있다"고 경고합니다. 업로드 스크립트는 `NAVER_BLOG_READONLY=1`을 켜서 발행·삭제 명령이 CLI에서 아예 빠지게 합니다. 에디터 조작 코드는 새로 쓰지 않고 `naver-blog-cli`에만 맡깁니다.

## 사전 요구사항

**naver-blog-cli 설치.** 네이버 임시저장은 외부 도구 [naver-blog-cli](https://github.com/spegas/naver-blog-cli)(MIT)에 맡깁니다. uv와 Python 3.11 이상이 있으면 한 줄입니다.

```bash
uv tool install git+https://github.com/spegas/naver-blog-cli
```

설치되면 `naver-blog-cli`가 `~/.local/bin`에 생깁니다(PATH에 없으면 `uv tool update-shell`). 브라우저 조작용 Playwright Chromium이 없다면 `"$(uv tool dir)/naver-blog-cli/bin/playwright" install chromium`으로 설치합니다. 로그인 스크립트 `login_setup.py`는 이 설치에 들어 있지 않으므로 저장소를 한 번 clone해 둡니다: `git clone https://github.com/spegas/naver-blog-cli ~/naver-blog-cli`.

**로그인은 1회, 사람이 직접.** **터미널**(Claude 입력창 아님)에서 작업 폴더로 이동한 뒤 아래 명령을 실행하면 브라우저가 열립니다.

```bash
cd ~/clark-blog-work
NAVER_STATE="$PWD/playwright-state/storage_state.json" \
  "$(uv tool dir)/naver-blog-cli/bin/python" ~/naver-blog-cli/login_setup.py
```

직접 로그인하고, **로그인 버튼을 누르기 전에 "로그인 상태 유지"를 체크**하세요(체크하지 않으면 몇 시간 뒤 글쓰기만 로그인 페이지로 바뀝니다). CAPTCHA·2차 인증도 사람이 처리합니다. 비밀번호는 어디에도 저장되지 않고 쿠키 파일(`playwright-state/`)만 남으며, 이 파일은 계정 접근권한 그 자체이니 공유하지 마세요. 세션이 만료되면 같은 명령을 다시 실행합니다.

**GEMINI_API_KEY(이미지 생성용).** https://aistudio.google.com/apikey 에서 발급받아 작업 폴더의 `.env`에 넣습니다. **Gemini 키는 결제(Billing)가 설정된 Google Cloud 프로젝트에서 발급해야 이미지 생성이 됩니다**(무료 키는 429 쿼터 초과로 실패합니다). `/clark-blog:blog-setup`이 `.env.example`을 복사해 주므로 값만 채우면 됩니다. `.env`는 커밋하지 마세요. 키가 없어도 `/clark-blog:blog-run`은 중단되지 않고 "키 없음 모드"로 진행합니다. 이 경우 AI 이미지 슬롯은 `보류`가 되고 실사진 슬롯만 처리됩니다. 단 `photos/`의 실사진이 5장 미만이면 이미지 수 기준(5장 이상)을 채우지 못해 **임시저장까지 가지 못합니다**. 시작할 때 "초안까지만 진행"할지 묻고, 이미지 단계(Step 3) 뒤에서 멈춥니다. 키나 실사진을 준비한 뒤 `/clark-blog:blog-run resume <NNN>`으로 이어 갑니다. 이미지는 장당 약 $0.04(추정치, [비용](#비용) 참고)입니다.

```
GEMINI_API_KEY=여기에_키
```

**학원 실사진 폴더.** 교육장·실습·장비 사진을 작업 폴더의 `photos/`에 넣어 두세요. 홍보성 글의 이미지는 실사진만 쓰고, 정보성 글은 AI 이미지를 쓰되 실사진이 맞는 슬롯에는 이 폴더의 사진이 매칭됩니다. 이전 글에 쓴 사진은 다시 쓰지 않습니다.

**uv·Python·Chromium.** `uv`가 있어야 하고, 작업 폴더의 스크립트용으로 `python3` 3.11 이상이 필요합니다(스크립트는 표준 라이브러리만 쓰고, 이미지 생성 때만 `uv run --with google-genai --with pillow`로 패키지를 받습니다). Playwright Chromium은 위 설치 안내를 따릅니다. `/clark-blog:blog-setup`이 이 항목들을 한 번에 진단해 줍니다.

## 설치와 첫 사용

아래 `/`로 시작하는 것들은 **터미널이 아니라 Claude Code 입력창**에 그대로 칩니다. `bash` 코드블록은 **터미널**에서 실행합니다.

```
/plugin marketplace add heesun-woodi/woodi-plugins
/plugin install clark-blog@woodi-plugins
/reload-plugins
```

플러그인을 설치한 뒤에는 아래 순서로 진행합니다.

1. uv가 없다면 **터미널**에서 먼저 설치합니다.

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **터미널**에서 작업 폴더를 만들고, 그 폴더에서 Claude Code를 엽니다. 작업 폴더는 **플러그인 저장소 밖**이어야 하고, 글 작업을 할 때는 **매번** 이 폴더에서 Claude Code를 엽니다.

   ```bash
   mkdir -p ~/clark-blog-work && cd ~/clark-blog-work && claude
   ```

3. Claude Code 입력창에서 셋업합니다.

   ```
   /clark-blog:blog-setup ~/clark-blog-work
   ```

   환경(uv·Python·Chromium·naver-blog-cli·네이버 세션·`GEMINI_API_KEY`)을 진단해 표로 보여 주고, 빠진 항목마다 실행할 명령을 출력합니다. 이어서 `scaffold/`를 작업 폴더로 복사합니다. `scripts/`는 매번 최신본으로 갱신하고, `knowledge/`는 보존합니다(이랑이 고친 파일은 덮어쓰지 않고, 아직 채워지지 않은 스텁만 교체).
4. 진단표가 알려 준 설치·로그인 명령은 **터미널에서** 실행합니다(Claude 입력창이 아님). 네이버 로그인은 **1회, 사람이 직접** 하고 "로그인 상태 유지"를 반드시 체크합니다(위 "로그인은 1회" 참고). `.env`에 `GEMINI_API_KEY`를 채웁니다(채팅에 키를 붙여넣지 마세요).
5. Claude Code 입력창에서 `/clark-blog:blog-setup ~/clark-blog-work`를 다시 실행해 모든 항목이 "확인됨"인지 봅니다.
6. `knowledge/design-system.md`(초기값)와 `knowledge/academy-profile.md`를 한 번 훑어보고, 고칠 것이 있으면 작업 폴더에서 직접 고칩니다. 레퍼런스를 추가했다면 `blog-design-system` 스킬로 문서를 갱신합니다.
7. 글을 시작합니다.

   ```
   /clark-blog:blog-run
   ```

   주제 번호를 미리 알면 `/clark-blog:blog-run 3`, 이미 만든 글의 진행 상황은 `/clark-blog:blog-run report 001`, 로그인이 안 돼 업로드를 미룬 글(또는 키·실사진이 없어 이미지 단계에서 멈춘 글)은 준비가 끝난 뒤 `/clark-blog:blog-run resume 001`로 이어서 합니다. 한 번 실행에 글은 **한 편**입니다.

## 워크플로우

`/clark-blog:blog-run` 한 번이 글 한 편입니다. `●`는 이랑이 답해야 하는 게이트입니다.

| 단계 | 수행 주체 | 산출 파일 | 사용자 게이트 |
|---|---|---|---|
| Step 0 preflight | 메인 | `work/pajuclark-posts.json`(기발행 글 목록) | - (키·세션이 없으면 경고 후 단계적으로 저하) |
| Step 1 주제 리서치 | 메인 + `blog-topic-research` 스킬 | `work/topics/<날짜>-topics.md` | ● 게이트 1: 번호·정보/홍보 유형·지역 키워드 2개 선택 |
| B 초안 | `blog-writer` 에이전트 + `blog-draft-writer` 스킬 | `research.md`, `draft.md` | - |
| C 근거 검토 | `blog-fact-checker` 에이전트 + `blog-fact-check` 스킬 | `factcheck.md` (PASS/FAIL/출처필요/시점확인) | - |
| B' 수정 + SEO | `blog-writer` 재개 + `blog-naver-seo` 스킬 | `draft-v2.md`, `seo.md` | - |
| Step 2 lint | 메인 + `lint_post.py` | `lint.json` | - |
| 게이트 2 | 메인 | `gates.md` `## 초안피드백` | ● 제목 A/B안·톤·길이 피드백 |
| Step 3 이미지 | 메인 + `blog-image-director` 스킬 + `gen_image.py` | `images/image-plan.md`, `images/NN-*.png` | ● 게이트 3: 슬롯별 승인/재생성/실사진 교체/제거 |
| Step 4 final 생성 | 메인 + `lint_post.py` | `final.md`, `lint.json` | - |
| Step 5 업로드 | 메인 + `blog-naver-upload` 스킬 + `naver_upload.sh` | `upload.log`, `gates.md` `## 업로드`, `work/variation-log.md` 한 줄 | - |
| 종료 보고 | 메인 | - | 이랑이 네이버에서 임시저장 → 미리보기 → 발행 |

- **디스패치 예산**: 글 한 편에 에이전트 호출은 기본 3회(B·C·B'), 재작업을 포함해 최대 7회입니다. 8회째가 필요해지면 멈추고 보고합니다.
- C에서 FAIL과 출처필요가 0건이면 `draft.md`를 `draft-v2.md`로 복사하고, B'는 SEO 다듬기와 관련글 링크 치환만 합니다.
- 게이트 2의 수정은 한 번만 돕니다. 사실 문장이 바뀌었으면 C를 한 번 더(`r2`) 돌립니다.
- 업로드(Step 5)는 로그인·2단계 인증·CAPTCHA가 끼어들 수 있어 서브에이전트에 맡기지 않고 메인이 직접 합니다.
- 끝나면 임시저장 제목·카테고리·태그·이미지 수와 "네이버 앱/웹 → 글쓰기 → 임시저장 글 → 미리보기 → 발행" 안내가 나옵니다.

## 작업 폴더 구조

`/clark-blog:blog-setup`이 만드는 폴더(예: `~/clark-blog-work/`)입니다. 다시 실행하면 `scripts/`는 플러그인 최신본으로 덮어쓰고, `knowledge/`는 이미 있는 파일을 보존합니다(`Task N에서 채움` 문구가 남은 스텁만 교체). 그 밖의 파일은 없을 때만 복사합니다.

```
.env  .env.example  .gitignore  README.md
knowledge/                      # 정본. 여기서 직접 고친다
  design-system.md              # 글 디자인 시스템(①~⑨, ④에 lint 수치)
  academy-profile.md            # 학원 기본정보 + 금칙어
  source-blogs.json             # 주제 소스·레퍼런스·자기 블로그
  law-sources.md                # 법령·기관 출처, 주장 유형별 매핑
  naver-seo-checklist.md        # 네이버 SEO 필수/권장 항목
scripts/
  fetch_posts.py  fetch_post.py  dedupe_check.py
  lint_post.py  gen_image.py  naver_upload.sh
photos/                         # 학원 실사진(커밋 제외)
playwright-state/               # 로그인 세션(로그인 뒤 생성, 커밋 금지)
work/
  pajuclark-posts.json          # 기발행 글 목록(중복 검사·관련글 링크)
  variation-log.md              # 업로드 성공마다 한 줄
  topics/<날짜>-topics.md       # 주제 후보 표
  posts/NNN-slug/
    topic.md  gates.md          # gates: ## 선택 · ## 초안피드백 · ## 이미지승인 · ## 업로드
    research.md  draft.md  factcheck.md  seo.md
    draft-v2.md                 # 팩트 반영 + SEO + 관련글 실제 URL
    images/image-plan.md  images/NN-*.png
    final.md                    # frontmatter(title/category/tags/variation) + 본문, 이미지는 절대경로
    lint.json  upload.log
```

게이트 2 이후 사실 문장이 바뀌면 `factcheck-r2.md`가 추가로 생깁니다.

## 계정 안전 수칙

- **하루 1~2편 이내.** 네이버 계정을 자동화된 브라우저로 조작하는 방식이라 과도하게 쓰면 계정이 제재될 수 있습니다. `naver-blog-cli`의 경고 원문은 "과도하게 쓰면 계정이 제재될 수 있습니다. 대량 자동 포스팅 용도로 만들지 않았고, 그런 기능을 넣지 마세요."입니다.
- **임시저장까지만.** 발행은 이랑이 네이버 앱/웹에서 미리보기를 보고 직접 합니다. 업로드 스크립트는 `NAVER_BLOG_READONLY=1`로 발행·삭제 명령을 제거한 상태로만 CLI를 부릅니다.
- **세션 파일은 비밀번호에 준해 다룹니다.** `playwright-state/storage_state.json`은 계정 접근권한 그 자체입니다. 공유·커밋하지 말고(`.gitignore`에 포함돼 있습니다) 다른 사람 컴퓨터로 옮기지 마세요. 비밀번호는 어디에도 저장되지 않습니다.
- **로그인·CAPTCHA·2단계 인증은 사람이.** 에이전트와 스크립트는 로그인을 하지 않습니다.
- **같은 오류로 반복 재시도하지 않습니다.** 업로드 실패는 한 번만 다시 시도하고, 그래도 안 되면 멈추고 보고합니다.

## 비용

- **이미지**: 장당 약 $0.04입니다. 이 값은 `gen_image.py`의 `COST_PER_IMAGE_USD`에 적힌 **추정치**이고 검증된 단가가 아닙니다. 실제 요금은 https://ai.google.dev/pricing 에서 확인하세요. 재생성도 과금됩니다. 글 한 편에 이미지가 5~13장 필요하므로(글자 수 기준), 이미지 비용은 대략 $0.2~0.5(추정치 기준)로 어림할 수 있습니다. `gen_image.py --dry-run`으로 API 호출 없이 예상 비용을 먼저 볼 수 있습니다.
- **모델 사용량**: 글 한 편에 opus 에이전트가 기본 3회(B·C·B'), 재작업까지 최대 7회 돕니다. 메인 세션의 주제 리서치·이미지 검수도 따로 듭니다. 토큰 사용량은 글 길이와 재작업 횟수에 따라 크게 달라지고 요금제마다 과금 방식이 달라, 이 문서에서는 금액을 단정하지 않고 "opus 호출 3~7회" 정도로만 안내합니다.
- 네이버 임시저장과 법령 조회(law.go.kr DRF)는 비용이 없습니다.

## 문제 해결

**`naver_upload.sh` 종료 코드**

`naver-blog-cli`는 성공·실패와 무관하게 종료 코드가 항상 0이라, 스크립트는 종료 코드가 아니라 CLI의 **stdout 문구**로 판정합니다.

| 코드 | 의미 | 할 일 |
|---|---|---|
| 0 | 임시저장 완료 | 네이버에서 미리보기 후 발행 |
| 2 | 사용 오류(경로·frontmatter) | 인자와 `final.md` 머리말 확인 |
| 10 | `lint_post.py` 실패 | 출력된 FAIL 항목 수정(본문은 writer 재개, 이미지는 Step 3/4) |
| 11 | 이중 검사 실패(금칙어·`[[`·빈 이미지·`[출처 필요]`) | 출력된 줄을 고친 뒤 재실행 |
| 12 | 이미지 경로가 절대경로가 아니거나 파일 없음 | Step 4(절대경로 치환) 재실행 |
| 20 | 세션 없음/만료 또는 `naver-blog-cli` 없음 | `/clark-blog:blog-setup`의 로그인 절차 |
| 30 | `create-draft` 실패 | 출력 문구 확인(에디터 변경·이미지 10MB·세션 만료). 중복 임시저장이 생겼는지 확인 후 재시도는 1회 |
| 31 | 저장은 됐으나 목록에서 제목 확인 불가 | 네이버 → 글쓰기 → 임시저장 글에서 직접 확인 |

`--dry-run`을 붙이면 lint·머리말·이미지 경로만 확인하고 네이버에는 접속하지 않습니다.

**이미지 생성이 429(쿼터 초과)로 멈출 때.** `gen_image.py`가 `APIError 429`와 함께 남은 슬롯을 중단했다면, Gemini 이미지 모델을 쓸 수 없는 키입니다. https://aistudio.google.com/apikey 에서 그 키의 Google Cloud 프로젝트에 결제(Billing)가 설정돼 있는지 확인하세요. 무료 키는 기다려도 풀리지 않습니다. 결제를 설정한 뒤 Step 3(이미지)부터 다시 진행합니다.

**세션 만료.** 몇 시간 뒤 글쓰기만 로그인 페이지로 바뀌거나 공인 IP가 바뀌면 세션이 풀립니다. "로그인 상태 유지"를 체크하지 않은 경우가 가장 흔합니다. 터미널에서 작업 폴더로 이동해 위 로그인 명령(`login_setup.py`)을 다시 실행하고, 로그인이 끝나면 `/clark-blog:blog-run resume <NNN>`으로 업로드만 이어갑니다. 세션이 없을 때 `/clark-blog:blog-run`은 Step 4까지 진행하고 업로드만 미룹니다.

**네이버가 에디터를 개편했을 때.** `naver-blog-cli`가 `…을 못 찾음`을 계속 내면 CLI의 셀렉터가 낡은 것입니다. 이 플러그인은 셀렉터·Playwright 코드를 새로 쓰지 않으므로 `naver-blog-cli`의 업데이트를 기다리는 것이 기본입니다. 급할 때는 이랑 승인 아래 aside(AI 브라우저)에 `final.md`와 `images/`를 주고 "임시저장까지만, 발행 금지"로 수동 지시하는 폴백이 있습니다(로그인·2단계 인증은 이 경우에도 이랑이 합니다).

**팩트체크 출처 사이트에 접근할 수 없을 때.** law.go.kr DRF 오픈API는 비교적 안정적이지만, 큐넷·고용24·한국산업인력공단의 세부 페이지는 JavaScript 렌더링이라 조회가 안 될 수 있습니다. 그런 주장은 지어내지 않고 `출처필요` 또는 `시점확인`으로 판정되며, **이랑이 직접 확인**한 뒤 답을 주면 그 답이 `gates.md`에 기록되고 다음 수정에 반영됩니다. 네이버 블로그 페이지는 WebFetch가 막히므로 스크립트가 `curl`로 가져옵니다.

## 2차 범위

지금 버전(0.1.0)에 없는 것: 스케줄 실행(정해진 시간에 주제 리서치·초안까지 자동으로 돌리기), OpenAI 이미지 폴백(Gemini가 안 될 때), 글 반응(조회·공감)을 읽어 주제 후보에 가중치를 주는 기능. 글을 발행하는 자동화는 계정 안전상 범위에 넣지 않습니다.
