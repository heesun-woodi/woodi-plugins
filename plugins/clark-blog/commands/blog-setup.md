---
description: 클라크 블로그 자동화 작업 폴더를 준비하고 환경(uv·Python·Playwright·naver-blog-cli·네이버 로그인 세션·API 키)을 진단합니다.
argument-hint: "[작업 폴더 경로 (선택, 기본 현재 폴더)]"
allowed-tools: Bash, Read, Write, Glob, Skill
---

사용자가 클라크 블로그 자동화의 작업 폴더 셋업을 시작했다. 아래 순서대로 진행하라.
사용자에게 보여주는 모든 안내 문구는 **한국어**로 작성한다.
어떤 단계에서도 비밀번호·API 키 값을 출력하거나 저장하지 않는다. 네이버 로그인은 사람이 직접 한다.

인자: `$ARGUMENTS` (작업 폴더 경로. 비어 있으면 현재 폴더를 쓴다.)

---

## 1. 작업 폴더 확정

`$ARGUMENTS`가 있으면 그 폴더(없으면 만들고)로, 없으면 현재 폴더로 이동한다.
**작업 폴더는 플러그인 저장소 밖이어야 한다.** 아래로 확인하고, 걸리면 거부한 뒤 다른 폴더를 요청하고 멈춘다.

```bash
TARGET="$ARGUMENTS"; [ -z "$TARGET" ] && TARGET=.
# 거부 검사를 mkdir보다 먼저 한다 (거부된 경로가 만들어지지 않게). 존재하는 가장 가까운 상위 폴더에서 git 루트를 찾는다.
CHK="$TARGET"; while [ ! -d "$CHK" ] && [ "$CHK" != "/" ] && [ "$CHK" != "." ]; do CHK="$(dirname "$CHK")"; done
ROOT="$(git -C "$CHK" rev-parse --show-toplevel 2>/dev/null)"
if [ -n "$ROOT" ] && { [ -d "$ROOT/.claude-plugin" ] || ls "$ROOT"/plugins/*/.claude-plugin >/dev/null 2>&1; }; then
  echo "REFUSE: 플러그인 저장소 안입니다 ($ROOT)"
else
  mkdir -p "$TARGET" && cd "$TARGET" || { echo "폴더를 만들거나 열 수 없습니다: $TARGET"; exit 1; }
  echo "작업 폴더: $PWD"
fi
```

`REFUSE`가 나오면 "작업 폴더는 플러그인 저장소 밖(예: ~/clark-blog)이어야 합니다. 다른 폴더를 알려주세요."라고 안내하고 중단한다.

## 2. 환경 진단

한 번의 Bash 호출로 전부 확인하라. 나눠서 여러 번 호출하지 말 것.
`naver-blog-cli`는 **종료 코드가 항상 0**이다. 성공·실패는 종료 코드가 아니라 **stdout 문구**로 판단한다.
키 값은 절대 출력하지 않는다 (존재 여부만).

```bash
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
echo "--- uv ---"
if command -v uv >/dev/null 2>&1; then echo "uv: OK ($(uv --version))"; else echo "uv: MISSING"; fi
echo "--- python ---"
if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' 2>/dev/null; then
  echo "python3: OK ($(python3 --version 2>&1))"
else echo "python3: MISSING_OR_OLD (3.11 이상 필요: $(python3 --version 2>&1))"; fi
echo "--- playwright chromium ---"
PW_DIRS=$(ls ~/Library/Caches/ms-playwright ~/.cache/ms-playwright 2>/dev/null | grep -c chromium)
PW_PY=$(python3 -c "import playwright" 2>/dev/null && echo yes || echo no)
if [ "$PW_DIRS" -gt 0 ]; then echo "chromium: OK (ms-playwright 캐시 ${PW_DIRS}개, python playwright 모듈: $PW_PY)"
else echo "chromium: MISSING (python playwright 모듈: $PW_PY)"; fi
echo "--- naver-blog-cli ---"
if command -v naver-blog-cli >/dev/null 2>&1 && naver-blog-cli --help >/dev/null 2>&1; then echo "naver-blog-cli: OK"
else echo "naver-blog-cli: MISSING"; fi
echo "--- naver 세션 ---"
BLOG_ID=pajuclark
[ -f knowledge/source-blogs.json ] && command -v python3 >/dev/null 2>&1 && \
  BLOG_ID=$(python3 -c "import json;o=json.load(open('knowledge/source-blogs.json')).get('own_blog');print((o.get('blogId') if isinstance(o,dict) else o) or 'pajuclark')" 2>/dev/null || echo pajuclark)
if command -v naver-blog-cli >/dev/null 2>&1; then
  SESS=$(NAVER_BLOG_ID="$BLOG_ID" naver-blog-cli check-session 2>&1)
  if echo "$SESS" | grep -q '세션 정상' && echo "$SESS" | grep -q '글쓰기 가능'; then echo "session: OK (blogId=$BLOG_ID)"
  elif echo "$SESS" | grep -q '확인 실패:'; then echo "session: LOGIN_NEEDED (blogId=$BLOG_ID) — $(echo "$SESS" | head -1) (로그인과 무관한 원인일 수 있음 — 예: Chromium 미설치)"
else echo "session: LOGIN_NEEDED (blogId=$BLOG_ID) — $(echo "$SESS" | head -1)"; fi
else echo "session: SKIPPED (naver-blog-cli 없음)"; fi
echo "--- .env / knowledge ---"
if [ -n "$GEMINI_API_KEY" ]; then echo "GEMINI_API_KEY: env에 있음"
elif [ -f .env ] && grep -q '^GEMINI_API_KEY=.' .env; then echo "GEMINI_API_KEY: .env에 있음"
else echo "GEMINI_API_KEY: MISSING"; fi
[ -f knowledge/design-system.md ] && echo "design-system.md: OK" || echo "design-system.md: MISSING (경고만, 오류 아님)"
```

## 3. 작업 폴더 준비 (scaffold 복사)

`${CLAUDE_PLUGIN_ROOT}/scaffold/` 를 현재 작업 폴더로 복사한다. `cp -n`은 기존 파일을 덮어쓰지 않으므로
이랑이 고친 `knowledge/`가 보존된다. 정본은 작업 폴더의 `knowledge/`다.

```bash
cp -rn "${CLAUDE_PLUGIN_ROOT}/scaffold/." . || true   # macOS cp -n은 건너뛴 파일이 있으면 exit 1 — 재실행 시 정상
[ -f .env ] || { cp .env.example .env && echo ".env 새로 생성 (키를 채워야 함)"; }
[ -f .env ] && echo ".env: 있음"
[ -f knowledge/design-system.md ] && echo "design-system.md: OK" || echo "design-system.md: MISSING (경고만)"
```

복사 후 새로 생긴 파일과 이미 있어서 건너뛴 파일을 구분해 한 줄로 보고한다.
`.env`는 방금 만들었다면 키를 채우라고 안내한다. `.env`는 이미 `.gitignore`에 포함되어 있어야 하며 채팅에 키를 붙여넣지 않게 한다.

## 4. 진단 결과 표와 조치

2단계(복사 후 상태는 3단계 출력 반영) 결과를 **표**로 보여준다. 항목 | 상태 | 조치. 이미 갖춰진 항목은 "확인됨", 조치 칸은 "-".
세션 `LOGIN_NEEDED`는 오류가 아니라 "로그인 필요"로 표시한다.

| 항목 | 상태 | 조치 |
|---|---|---|
| uv | OK / MISSING | 아래 명령 |
| python3 ≥ 3.11 | OK / MISSING | 3.11 이상 설치 (scaffold 스크립트용. naver-blog-cli는 uv가 자체 Python을 씀) |
| Playwright Chromium | OK / MISSING | 아래 명령 |
| naver-blog-cli | OK / MISSING | 아래 명령 |
| 네이버 세션 | 정상 / 로그인 필요 | 아래 로그인 절차 |
| GEMINI_API_KEY | OK / MISSING | 아래 안내 |
| knowledge/design-system.md | OK / 없음(경고) | 5단계 안내 |

**누락된 항목에 대해서만** 그대로 실행할 수 있는 명령을 코드블록으로 출력한다.

- uv
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- Playwright Chromium
  ```bash
  uv run --with playwright playwright install chromium
  # naver-blog-cli 설치 후에는: "$(uv tool dir)/naver-blog-cli/bin/playwright" install chromium
  ```
- naver-blog-cli (PATH에 `~/.local/bin` 필요)
  ```bash
  uv tool install git+https://github.com/spegas/naver-blog-cli
  ```
- 네이버 로그인 (**사람이 직접, 1회**). 로그인 스크립트는 설치본에 없으므로 저장소를 clone해서 쓴다. 반드시 **작업 폴더에서** 실행한다. 세션 파일이 `<작업 폴더>/playwright-state/storage_state.json`에 저장된다.
  ```bash
  [ -d ~/naver-blog-cli ] || git clone https://github.com/spegas/naver-blog-cli ~/naver-blog-cli
  cd <작업 폴더>
  NAVER_STATE="$PWD/playwright-state/storage_state.json" \
    "$(uv tool dir)/naver-blog-cli/bin/python" ~/naver-blog-cli/login_setup.py
  ```
  안내 문구: "브라우저 창이 열리면 직접 로그인하세요. **'로그인 상태 유지'를 반드시 체크**하고, 캡차·2단계 인증·기기 등록도 직접 처리해 주세요. 비밀번호는 저장되지 않고 쿠키 파일만 만들어집니다. 쿠키 파일(`playwright-state/`)은 계정 접근권한 그 자체라 공유·커밋하면 안 됩니다. 로그인 뒤 `/clark-blog:blog-setup`을 다시 실행하면 세션이 '정상'으로 바뀝니다."
- GEMINI_API_KEY
  ```
  https://aistudio.google.com/apikey 에서 키를 발급해 작업 폴더의 .env 에 아래 형식으로 넣어 주세요.

      GEMINI_API_KEY=여기에_키

  키 값은 채팅에 붙여넣지 마세요.
  ```

## 5. 다음 단계 안내

- `knowledge/design-system.md`가 없으면: "scaffold 초기값에 포함될 예정입니다. 없으면 `blog-design-system` 스킬로 생성을 요청하세요. (글 검사 `lint_post.py`는 이 파일이 없어도 경고만 냅니다.)"
- 누락·로그인 필요 항목이 남아 있으면 해결 후 이 커맨드를 다시 실행하라고 안내한다.
- 모두 갖춰졌으면: "준비가 끝났습니다. `/clark-blog:blog-run`으로 글 작성을 시작하세요."
