# naver-blog-cli 명령 레퍼런스

네이버 블로그 임시저장 업로드는 외부 도구 `naver-blog-cli`에만 위임한다. 이 문서는 이 머신에서 실제로 설치해 `--help`와 소스로 확인한 사실만 적는다. 업로드 스크립트(`naver_upload.sh`)와 `/clark-blog:blog-setup`은 아래 호출 형태와 출력 문구를 그대로 인용한다.

- 출처: https://github.com/spegas/naver-blog-cli (README 기준)
- 확인 일자: 2026-10-06
- 확인한 커밋: `fe7b69e8aa7a187e967ca63e59c2b8560a403933` (2026-10-03), 패키지 버전 0.1.0
- 라이선스: MIT (Copyright (c) 2026 jjorae / Johnhyeon / spegas). 원본 `Johnhyeon/naver-blog-mcp`.
- 요구: Python 3.11+, uv, Playwright Chromium

## 먼저 읽어야 할 경고 (README 원문)

> 네이버 계정으로 로그인한 브라우저를 자동 조작합니다. 과도하게 쓰면 계정이 제재될 수 있습니다. 대량 자동 포스팅 용도로 만들지 않았고, 그런 기능을 넣지 마세요.

> 비밀번호는 저장하지 않습니다. 사람이 직접 로그인해서 만든 쿠키 파일만 읽습니다. 그 쿠키 파일(`playwright-state/storage_state.json`)은 계정 접근권한 그 자체입니다.

그래서 이 플러그인은 임시저장까지만 자동화하고 발행은 사람이 한다. `publish-draft`, `delete-draft`, `delete-post`는 스킬에서 호출하지 않는다.

## 설치와 실제 호출 형태

확정된 설치 방법: `uv tool install` (성공).

```bash
uv tool install git+https://github.com/spegas/naver-blog-cli
# -> ~/.local/bin/naver-blog-cli 실행 파일 생성, 도구 venv: ~/.local/share/uv/tools/naver-blog-cli/ (macOS)
#    Windows: %USERPROFILE%\.local\bin\naver-blog-cli.exe, 도구 venv(기본값, 미실측): %APPDATA%\uv\data\tools\naver-blog-cli\ (python·playwright는 Scripts\ 아래)
#    어느 OS든 venv 위치는 `uv tool dir`로 확인
```

**확정된 호출 형태: `naver-blog-cli <서브커맨드> ...`** (PATH에 `~/.local/bin`이 있어야 한다. 없으면 `~/.local/bin/naver-blog-cli`).

- 항상 환경변수 `NAVER_BLOG_ID=<블로그아이디>` 필요 (`pajuclark` 등, `blog.naver.com/<여기>`).
- Playwright Chromium은 (macOS 실측) `~/Library/Caches/ms-playwright/chromium-1243`이 이미 있어 추가 설치 불필요했다. 다른 머신에서는 macOS: `"$(uv tool dir)/naver-blog-cli/bin/playwright" install chromium`, Windows(PowerShell): `& "$(uv tool dir)\naver-blog-cli\Scripts\playwright.exe" install chromium`(캐시는 `%LOCALAPPDATA%\ms-playwright`).
- **로그인 스크립트 `login_setup.py`는 `uv tool install`에 포함되지 않는다.** 저장소 루트에만 있다. 그래서 로그인용으로 저장소를 따로 clone한다 (예: `~/naver-blog-cli`, 같은 커밋). 이 clone은 로그인 한 번에만 쓰고 플러그인에는 vendoring하지 않는다.
- 상세 호출 대안(참고): clone에서 `uv sync && uv run playwright install chromium` 후 `uv run --project <clone> naver-blog-cli ...`도 README가 안내하는 정식 방식이다. 이 플러그인은 위의 `uv tool` 방식을 쓴다.

## 세션 파일과 로그인 (사람이 1회)

- 세션 파일 기본 경로: **현재 작업 디렉터리 기준 상대경로** `playwright-state/storage_state.json` (`session.py`: `NAVER_STATE` 기본값). 환경변수 `NAVER_STATE`로 바꿀 수 있고 README는 **절대경로 권장**. 그래서 CLI는 항상 작업 폴더에서 실행하거나 `NAVER_STATE=<작업폴더>/playwright-state/storage_state.json`을 준다.
- 로그인(사람이 직접, 에이전트·스크립트는 하지 않는다):

  macOS (터미널):

  ```bash
  cd <작업폴더>      # playwright-state/ 가 여기에 생긴다
  NAVER_STATE="$PWD/playwright-state/storage_state.json" \
    "$(uv tool dir)/naver-blog-cli/bin/python" ~/naver-blog-cli/login_setup.py
  # 또는 clone 안에서: uv run python login_setup.py
  ```

  Windows (PowerShell — 셸 스크립트에서 쓸 때는 Git Bash에서 `uv tool dir`을 `cygpath -u`로 바꾸고 `bin/python` 대신 `Scripts/python.exe`를 찾는다):

  ```powershell
  cd <작업폴더 Windows 경로>
  $env:NAVER_STATE = "$PWD\playwright-state\storage_state.json"; & "$(uv tool dir)\naver-blog-cli\Scripts\python.exe" "$HOME\naver-blog-cli\login_setup.py"
  ```

  브라우저 창이 열리면 직접 로그인한다. 인증 쿠키(`NID_AUT`/`NID_SES`)가 생기면 자동 저장 후 창을 닫는다. CAPTCHA·2차 인증·기기등록은 사람이 처리. 5분 안에 로그인하지 않으면 아무것도 저장하지 않고 끝난다.
- **로그인 버튼 전에 "로그인 상태 유지"를 반드시 체크.** 안 하면 몇 시간 뒤(README 실측 약 2.5시간) 블로그 보기는 되는데 글쓰기 화면만 로그인 페이지로 바뀐다. IP 보안이 켜져 있으면 공인 IP가 바뀔 때도 풀린다. 만료되면 `login_setup.py`를 다시 실행.
- 쿠키 파일은 0600으로 저장된다. 계정 접근권한 그 자체이므로 `.gitignore`에 `playwright-state/` 포함, 공유·커밋 금지.

## check-session — 로그인 전 실패 출력 원문과 종료 코드

**종료 코드는 성공·실패 모두 항상 0이다.** CLI는 결과 문자열을 `print`만 하고 `sys.exit`하지 않는다. 따라서 셸은 종료 코드가 아니라 **stdout 첫 줄 문구**로 분기해야 한다. 오류도 stdout으로 나온다 (stderr는 비어 있다).

로그인 전, `NAVER_BLOG_ID=pajuclark`, 작업 디렉터리에 `playwright-state/`가 없을 때 (2026-10-06 실측):

```
$ NAVER_BLOG_ID=pajuclark naver-blog-cli check-session
확인 실패: 세션 파일 없음: playwright-state/storage_state.json
python login_setup.py 를 먼저 실행해서 직접 로그인하세요.
(exit 0, stdout 2줄, stderr 없음)
```

`NAVER_BLOG_ID` 미설정 (모든 브라우저 명령 공통, 실측):

```
NAVER_BLOG_ID 가 설정되지 않았습니다.
환경변수로 NAVER_BLOG_ID=<블로그아이디> 를 설정하세요 (blog.naver.com/<여기>).
(exit 0)
```

로그인 후의 문구는 소스(`core.py check_session`)에서 읽은 것이며 이 태스크에서는 로그인하지 않아 실측하지 않았다:

| 상황 | stdout (첫 줄 기준) |
|---|---|
| 정상 | `세션 정상 (<URL>, 글쓰기 가능)` |
| 쿠키 만료 | `세션 만료 — uv run python login_setup.py 재실행 필요` |
| 보기만 되고 글쓰기 불가(로그인 유지 미체크 등) | `보기는 되지만 글쓰기 불가 — <사유>` |
| 그 외 예외 | `확인 실패: <사유>` |

**주의 — 다른 계정 세션은 `세션 정상 (…, 글쓰기 가능)`으로 통과한다 (2026-10-09 실측).** 테스트 계정(iloveccmel) 세션으로 `NAVER_BLOG_ID=pajuclark check-session`이 정상을 냈지만, `https://blog.naver.com/pajuclark?Redirect=Write`는 `https://blog.naver.com/iloveccmel`(로그인 계정 블로그 홈)로 리다이렉트됐고, 블로그 홈에도 `#mainFrame`이 있어 `wait_for_editor`가 통과했다. 이후 `create-draft-from-folder`는 `작성 실패: 글자 크기 버튼을 못 찾음 — selectors 갱신 필요`, `list-drafts`는 `임시저장 목록 버튼을 못 찾음`. 그래서 셸은 `check-session` 뒤에 `scripts/check_blog_account.py <blogId>`(uv tool python으로 실행 — `naver_blog_cli`를 import해야 하므로)로 글쓰기 화면 URL의 블로그 주인을 확인한다: 0 일치(URL 주인이 대상이고 에디터 제목 영역이 보임) · 20 로그인 페이지/세션 파일 없음 · 21 다른 사람 블로그로 이동 · 22 그 밖의 실패(블로그 주인을 알 수 없는 곳으로 이동·에디터 미표시 등). `goto_editor`의 팝업 닫기 클릭은 하지 않고, `NAVER_KEEP_OPEN`은 무시한다.

분기 규칙(Task 13 셸): 출력이 `세션 정상`으로 시작하고 `글쓰기 가능`을 포함할 때만 통과. 그 외는 전부 실패로 보고 이랑에게 로그인 안내 후 중단. 같은 이유로 `create-draft`도 종료 코드로 성공을 판정하지 않는다.

## 서브커맨드 전체 (`naver-blog-cli --help`)

```
usage: naver-blog-cli [-h]
  {check-session,list-categories,list-drafts,create-draft,ai-draft,verify-draft,create-draft-from-folder,publish-draft,delete-draft,delete-post} ...
MCP 없이 네이버 블로그를 직접 조작하는 CLI. NAVER_BLOG_ID 환경변수가 필요하다.
```

로그인 명령은 서브커맨드가 아니다 (`login-setup`/`login_setup`은 `invalid choice`). 위 "로그인" 절의 `login_setup.py`뿐이다.

| 서브커맨드 | 옵션 | 용도 / 이 플러그인에서의 사용 |
|---|---|---|
| `check-session` | (없음) | 세션 확인. **사용** |
| `list-categories` | (없음) | 카테고리 목록. 하위는 `  - ` 들여쓰기. **사용**(setup에서 카테고리명 확인) |
| `list-drafts` | (없음) | 임시저장 목록, 최신순, 각 줄 `제목  (날짜)`; 없으면 `임시저장된 글이 없습니다`. **사용**(업로드 확인) |
| `create-draft` | `--title TITLE` `--file FILE` `--category CATEGORY` `--tags TAGS` | 마크다운 → 임시저장(발행 안 함). 대표이미지를 지정하지 않아 쓰지 않음 |
| `publish-draft` | `--confirm`(필수) `--title TITLE` `--visibility {,public,neighbor,both_neighbor,private}` | 발행(되돌릴 수 없음). **사용 금지**(사람이 발행) |
| `delete-draft` | `--confirm`(필수) `--title TITLE` `--index INDEX`(list-drafts 순번, 1이 최신) | 임시저장 삭제. 사용 금지 |
| `delete-post` | `--confirm`(필수) `target`(글 URL 또는 logNo, 위치 인자) | 발행글 삭제. 사용 금지 |
| `ai-draft` | `--text/--file`(택1) `--keywords` `--category` `--tags` `--title` `--model` `--length`(기본 1500) `--request` `--out` `--dry-run` `--search` `--search-query` `--verify` `--region` `--upload-anyway` | 로컬 Ollama LLM으로 원고 생성. 이 플러그인은 쓰지 않음(글은 blog-writer가 씀) |
| `verify-draft` | `file`(위치 인자) `--region` `--model` | 네이버 검색+Ollama로 사실 확인. 쓰지 않음(팩트체크는 blog-fact-checker) |
| `create-draft-from-folder` | `folder`(위치 인자) `--markdown-file`(기본 `post.md`) `--title` `--category` `--tags` | 글+이미지가 한 폴더일 때. **사용**(표지 대표이미지 지정 때문에 `create-draft` 대신 이것을 쓴다) |

`NAVER_BLOG_READONLY=1`이면 `publish-draft`/`delete-draft`/`delete-post`가 **명령 목록에서 아예 빠진다**(argparse가 모름). 업로드 셸은 이 변수를 켜 두면 발행이 구조적으로 불가능해진다.

### create-draft 세부 (참고 — 이 플러그인은 아래 from-folder를 쓴다)

```bash
NAVER_BLOG_ID=pajuclark naver-blog-cli create-draft \
  --title "제목" --file /abs/path/body.md \
  --category "클라크중장비운전학원" --tags 지게차운전기능사,지게차실기,의정부지게차학원
```

- `--file` 생략 시 표준입력에서 읽는다. 둘 다 없고 tty면 `마크다운을 --file 로 주거나 표준입력으로 넘기세요.`로 종료(비0).
- `--title`을 비우면 본문 첫 줄 `# 제목`을 제목으로 쓰고 그 줄을 본문에서 뺀다. `--title`을 주고 첫 줄 `# …`가 `--title`과 같은 문자열이면 CLI가 그 줄을 본문에서 뺀다. 같지 않으면 H1이 본문에 그대로 남으므로 `naver_upload.sh`는 H1을 직접 제거한 임시파일을 넘기는 현재 설계를 유지한다.
- `--tags`는 쉼표 구분 문자열(공백은 trim), `--category`는 카테고리 이름(`"상위 > 하위"` 경로형도 허용).
- 성공 출력(소스 기준): `임시저장 완료: <제목> [<메모들>]` / `임시저장 수 <전> -> <후>` / `확인 후 publish_draft 를 호출하세요.` 실패 출력 예: `작성 실패: …`, `임시저장 버튼을 못 찾음 …`, `임시저장이 안 된 것 같습니다 (임시저장 수 N -> N) …`, `설정 실패(…)`가 메모에 붙는 경우(카테고리·태그 실패) 있음. 셸은 `임시저장 완료`를 grep하고, 이어서 `list-drafts`로 제목이 보이는지 확인한다.
- 브라우저 창이 뜬다(기본 `HEADLESS=false`, CAPTCHA 대비). 글 하나에 수 분 걸릴 수 있다.
- **`create-draft`는 대표이미지를 지정하지 않는다**(`set_rep_image`를 호출하지 않음; 첫 이미지가 "대개" 기본 대표일 뿐). 그래서 이 플러그인은 `create-draft`를 쓰지 않고 아래 `create-draft-from-folder`를 쓴다.

### create-draft-from-folder 세부 (이 플러그인이 호출하는 명령)

`naver_upload.sh`는 임시 작업 폴더 `$WORK`에 `body.md`(frontmatter·H1·B안 주석을 뺀 본문)와 `images/00-cover.png`(글 폴더의 표지 복사본)를 만든 뒤 호출한다:

```bash
NAVER_BLOG_ID=pajuclark naver-blog-cli create-draft-from-folder "$WORK" \
  --markdown-file body.md --title="$TITLE" --category="$CATEGORY" --tags="$TAGS"
```

- `find_cover(folder, markdown)`(`core.py`): `<폴더>/images/00-cover.{png,jpg,jpeg,gif}`가 있고 **본문(`body.md`)이 그 파일을 참조하지 않을 때만** 표지로 쓴다(`NAVER_COVER=0/off`로 끔, 다른 경로 지정 가능). 본문이 이미 참조하면 `None`이라 표지를 따로 넣지 않는다 → 업로드본 본문은 표지를 참조하지 않는다(lint `cover_file`).
- 표지는 **본문 맨 앞에 캡션 없이** 넣고 `set_rep_image(0)`로 대표를 지정한다. 본문 이미지는 절대경로 그대로 받는다(`_abs_local`).
- `preflight`(브라우저를 열기 전): 이미지·첨부 존재·10MB·유튜브 주소를 한 번에 검사한다. 걸리면 아무것도 하지 않고 `넣기 전에 걸린 것 (아무것도 하지 않았습니다):` + 줄별 `- 이미지 없음: …` / `- 10MB 초과: …`를 출력한다 → 셸은 exit 30.
- 성공 출력: `임시저장 완료: <제목> [노트, …]`. 노트 문구:

  | 노트 | 의미 |
  |---|---|
  | `0:표지` | 표지를 본문 맨 앞에 넣음. 실패하면 `0:표지 넣기 실패(<사유>)` — 표지만 빠지고 글은 계속 작성됨 |
  | `대표 지정` / `대표 지정 실패` | `set_rep_image(0)` 결과. 실패해도 임시저장은 됨 → 셸은 `경고: 대표이미지 지정 실패 — …` (exit 0) |
  | `<N>:장소(<고른 곳>)` | `:::place 검색어:::`가 검색 결과 첫 번째로 고른 장소(24자까지). 셸이 값을 로그·성공 출력에 `장소: …`로 남기고 `클라크`가 없으면 `경고: 장소 카드 확인 필요 — <값>` |
  | `카테고리=…`, `태그 N개`, `설정 실패(…)` | 발행 레이어 설정 결과. `설정 실패`면 셸이 `경고: 카테고리/태그 설정 실패 …` |
  | `<N>:이미지` 등 | 본문 블록별 기록 |

- 실패 출력: `넣기 전에 걸린 것`(preflight) · `작성 실패: …` · `임시저장이 안 된 것 같습니다 …` · `…을 못 찾음`. 셸은 이 넷과 `임시저장 완료`가 없는 그 밖의 출력을 모두 exit 30으로 본다(출력 tail 5줄 포함).

## 이미지 경로 처리

- 이미지는 **로컬 파일 경로만** 된다(URL 불가). 문법 `![캡션](경로)`. 개당 10MB 제한.
- `create-draft --file`은 경로를 미리 절대경로로 바꿔 주지 않는다. 상대경로는 **CLI를 실행한 현재 디렉터리 기준**(편집기 단에서 `Path(...).resolve()`)으로 해석된다. 마크다운 파일 위치 기준이 아니다. → `final.md`는 이미지 경로를 절대경로로 치환해 두는 설계가 맞다.
- `create-draft-from-folder`만 폴더 기준으로 상대경로를 절대경로로 바꾸고, 브라우저를 열기 전에 파일 존재·10MB를 한 번에 검사한다(문제가 있으면 아무것도 올리지 않음).
- 대표 이미지: 글 폴더에 `images/00-cover.*`가 있고 본문이 참조하지 않으면(`NAVER_COVER`) 본문 맨 앞에 넣고 대표로 지정(`create-draft-from-folder` 경로). `NAVER_COVER=0`/`off`로 끈다.

## 환경변수 (README 표)

| 이름 | 기본값 | 설명 |
|---|---|---|
| `NAVER_BLOG_ID` | (필수) | 블로그 아이디 |
| `NAVER_STATE` | `playwright-state/storage_state.json` | 쿠키 파일 경로(상대는 cwd 기준). 절대경로 권장 |
| `HEADLESS` | `false` | `true`면 창을 띄우지 않음. CAPTCHA가 뜨면 조용히 실패하므로 켜지 않는다 |
| `NAVER_COVER` | `images/00-cover.*` | 대표 이미지. `0`/`off`면 안 넣음 |
| `NAVER_BLOG_READONLY` | (꺼짐) | 켜면 발행·삭제 명령 제거 |
| `NAVER_KEEP_OPEN` | (꺼짐) | 끝나도 창을 닫지 않음(1/true=10분, 숫자=초) |
| `NAVER_TOPIC` | - | 주제 선택(발행 레이어) |
| `NAVER_LLM_MODEL`, `OLLAMA_HOST`, `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` | - | `ai-draft`/`verify-draft` 전용. 이 플러그인은 쓰지 않음 |

## 마크다운 지원 범위 (README 표, 실제 에디터 실측 기준)

| 문법 | 결과 |
|---|---|
| `# ## ###` 제목 | 글자 크기 24 / 19 / 15 |
| `**굵게**` `*기울임*` `~~취소선~~` | 지원 |
| `[텍스트](url)` | 문단·제목 안에서 지원 |
| `> 인용` | 인용구 컴포넌트 |
| `- 목록` / `1. 목록` | 순서/비순서 목록 |
| ```` ```코드``` ```` | 소스코드 컴포넌트 |
| `---` | 구분선 |
| GFM 파이프 표 | 표 컴포넌트(셀 안 서식 유지) |
| `![캡션](로컬경로)` | 사진 + 캡션 |
| `:::file 로컬경로:::` | 파일 첨부(개당 10MB) |
| `:::formula ...:::` | 수식 |
| `:::place 검색어:::` | 장소(검색 결과 첫 번째) |
| `:::video 유튜브 주소:::` | 유튜브 플레이어(watch, youtu.be, shorts만) |
| `:::news` / `:::stock` / `:::book` | 글감 카드(이 플러그인은 쓰지 않음) |

알려진 한계(README 원문 요지):

- **인용문과 표 안의 링크는 사라진다.** 링크는 일반 문단·제목에서만 쓴다. 관련글 링크는 인용·표 밖에 둔다.
- **인라인 코드(`` `code` ``)는 지원하지 않는다**(네이버에 대응 기능 없음). 본문에서 쓰지 않는다.
- 장소는 검색 결과 첫 번째. 수식은 언어·스타일 지정 불가.
- 네이버가 에디터를 바꾸면 `"...을 못 찾음"`이 나온다. 진단은 clone에서 `uv run python verify_selectors.py`. 셀렉터는 `src/naver_blog_cli/selectors.py` 한 파일에만 있다. 이 플러그인은 셀렉터·Playwright 코드를 새로 쓰지 않는다.
