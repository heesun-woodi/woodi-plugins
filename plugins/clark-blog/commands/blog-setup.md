---
description: 클라크 블로그 자동화 작업 폴더를 준비하고 환경(uv·Python·Playwright·naver-blog-cli·네이버 로그인 세션·API 키·한글 폰트·학원소개 이미지)을 진단합니다.
argument-hint: "[작업 폴더 경로 (선택, 기본 현재 폴더)]"
allowed-tools: Bash, Read, Write, Glob, Skill
---

사용자가 클라크 블로그 자동화의 작업 폴더 셋업을 시작했다. 아래 순서대로 진행하라.
사용자에게 보여주는 모든 안내 문구는 **한국어**로 작성한다.
어떤 단계에서도 비밀번호·API 키 값을 출력하거나 저장하지 않는다. 네이버 로그인은 사람이 직접 한다.

인자: `$ARGUMENTS` (작업 폴더 경로. 비어 있으면 현재 폴더를 쓴다.)

---

## 1. 작업 폴더 확정

`$ARGUMENTS`가 있으면 그 폴더(없으면 만들고)로, 없으면 현재 폴더로 이동한다. `~`·`~/…`는 홈 폴더로 펼친다(따옴표 때문에 셸이 펼치지 않으므로).
**작업 폴더는 플러그인 저장소 밖이어야 한다.** 아래로 확인하고, 걸리면 거부한 뒤 다른 폴더를 요청하고 멈춘다.

```bash
TARGET="$ARGUMENTS"; [ -z "$TARGET" ] && TARGET=.
case "$TARGET" in "~") TARGET="$HOME";; "~/"*) TARGET="$HOME/${TARGET#\~/}";; esac
# 거부 검사를 mkdir보다 먼저 한다 (거부된 경로가 만들어지지 않게). 존재하는 가장 가까운 상위 폴더에서 git 루트를 찾는다.
CHK="$TARGET"; while [ ! -d "$CHK" ] && [ "$CHK" != "/" ] && [ "$CHK" != "." ]; do CHK="$(dirname "$CHK")"; done
ROOT="$(git -C "$CHK" rev-parse --show-toplevel 2>/dev/null)"
if [ -n "$ROOT" ] && { [ -d "$ROOT/.claude-plugin" ] || ls "$ROOT"/plugins/*/.claude-plugin >/dev/null 2>&1; }; then
  echo "REFUSE: 플러그인 저장소 안입니다 ($ROOT)"
else
  mkdir -p "$TARGET" && cd "$TARGET" || { echo "폴더를 만들거나 열 수 없습니다: $TARGET"; exit 1; }
  TARGET="$PWD"   # 절대경로로 고정
  echo "작업 폴더: $TARGET"
fi
```

출력된 `작업 폴더:` **절대경로**를 기억한다. Bash 호출마다 cwd가 처음으로 돌아갈 수 있으므로, 2·3단계 Bash 블록은 첫 줄 `cd "<그 절대경로>" || exit 1`로 시작한다(아래 블록의 `<작업 폴더 절대경로>` 자리에 그대로 넣는다).

`REFUSE`가 나오면 "작업 폴더는 플러그인 저장소 밖(예: ~/clark-blog)이어야 합니다. 다른 폴더를 알려주세요."라고 안내하고 중단한다.

## 2. 환경 진단

한 번의 Bash 호출로 전부 확인하라. 나눠서 여러 번 호출하지 말 것.
`naver-blog-cli`는 **종료 코드가 항상 0**이다. 성공·실패는 종료 코드가 아니라 **stdout 문구**로 판단한다.
키 값은 절대 출력하지 않는다 (존재 여부만).

```bash
cd "<작업 폴더 절대경로>" || exit 1
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
  if echo "$SESS" | grep -q '세션 정상' && echo "$SESS" | grep -q '글쓰기 가능'; then
    # check-session 은 다른 계정 세션도 통과시킨다 → 글쓰기 화면이 $BLOG_ID 블로그로 열리는지 확인 (헤드리스, 글은 안 씀)
    CLI_PY="$(uv tool dir 2>/dev/null)/naver-blog-cli/bin/python"
    CHK="${CLAUDE_PLUGIN_ROOT}/scaffold/scripts/check_blog_account.py"
    if [ -x "$CLI_PY" ] && [ -f "$CHK" ]; then
      ACCT=$("$CLI_PY" "$CHK" "$BLOG_ID" 2>&1); ACCT_RC=$?
      case "$ACCT_RC" in
        0) echo "session: OK (blogId=$BLOG_ID, 계정 확인됨)" ;;
        21) echo "session: WRONG_ACCOUNT (blogId=$BLOG_ID) — $(echo "$ACCT" | tail -1)" ;;
        *) echo "session: LOGIN_NEEDED (blogId=$BLOG_ID) — 계정 확인 실패: $(echo "$ACCT" | tail -1)" ;;
      esac
    else echo "session: LOGIN_NEEDED (blogId=$BLOG_ID) — 계정 확인 불가(naver-blog-cli 의 uv tool python 또는 $CHK 없음 — uv tool install 로 다시 설치)"; fi
  elif echo "$SESS" | grep -q '확인 실패:'; then echo "session: LOGIN_NEEDED (blogId=$BLOG_ID) — $(echo "$SESS" | head -1) (로그인과 무관한 원인일 수 있음 — 예: Chromium 미설치)"
  else echo "session: LOGIN_NEEDED (blogId=$BLOG_ID) — $(echo "$SESS" | head -1)"; fi
else echo "session: SKIPPED (naver-blog-cli 없음)"; fi
echo "--- .env / knowledge ---"
if [ -n "$GEMINI_API_KEY" ]; then echo "GEMINI_API_KEY: env에 있음"
elif [ -f .env ] && grep -q '^GEMINI_API_KEY=.' .env; then echo "GEMINI_API_KEY: .env에 있음"
else echo "GEMINI_API_KEY: MISSING"; fi
[ -f knowledge/design-system.md ] && echo "design-system.md: OK" || echo "design-system.md: MISSING (경고만, 오류 아님)"
echo "--- 표지·마무리 자산 ---"
if [ -f "$HOME/Library/Fonts/Pretendard-ExtraBold.otf" ]; then echo "font: OK (Pretendard)"
elif [ -f /System/Library/Fonts/AppleSDGothicNeo.ttc ]; then echo "font: OK (AppleSDGothicNeo — Pretendard 권장)"
else echo "font: MISSING"; fi
[ -f photos/학원소개.png ] && echo "academy-image: OK" || echo "academy-image: MISSING"
```

## 3. 작업 폴더 준비 (scaffold 복사)

`${CLAUDE_PLUGIN_ROOT}/scaffold/` 를 작업 폴더로 복사한다. 규칙: **scripts는 매번 갱신, knowledge는 보존(스텁만 교체)**.
`scripts/`는 플러그인 코드라 항상 최신본으로 덮어쓴다. `knowledge/`는 이랑이 고친 파일을 보존하고, 아직 `Task N에서 채움` 문구가 남은 스텁만 플러그인 초기값으로 바꾼다. 그 밖의 파일은 없을 때만 복사한다(`cp -n`). 정본은 작업 폴더의 `knowledge/`다.

```bash
cd "<작업 폴더 절대경로>" || exit 1
cp -rn "${CLAUDE_PLUGIN_ROOT}/scaffold/." . || true   # macOS cp -n은 건너뛴 파일이 있으면 exit 1 — 재실행 시 정상
cp -R "${CLAUDE_PLUGIN_ROOT}/scaffold/scripts/." scripts/   # scripts는 항상 최신본
for f in knowledge/*.md; do grep -q 'Task [0-9]*에서 채움' "$f" && cp "${CLAUDE_PLUGIN_ROOT}/scaffold/knowledge/$(basename "$f")" "$f" && echo "스텁 교체: $f"; done
[ -f .env ] || { cp .env.example .env && echo ".env 새로 생성 (키를 채워야 함)"; }
[ -f .env ] && echo ".env: 있음"
[ -f knowledge/design-system.md ] && echo "design-system.md: OK" || echo "design-system.md: MISSING (경고만)"
```

복사 후 새로 생긴 파일, 이미 있어서 건너뛴 파일, 갱신한 `scripts/`·교체한 스텁을 구분해 한 줄로 보고한다.
`.env`는 방금 만들었다면 키를 채우라고 안내한다. `.env`는 이미 `.gitignore`에 포함되어 있어야 하며 채팅에 키를 붙여넣지 않게 한다.

## 4. 진단 결과 표와 조치

2단계(복사 후 상태는 3단계 출력 반영) 결과를 **표**로 보여준다. 항목 | 상태 | 조치. 이미 갖춰진 항목은 "확인됨", 조치 칸은 "-".
세션 `LOGIN_NEEDED`는 오류가 아니라 "로그인 필요"로, `WRONG_ACCOUNT`는 "다른 계정 로그인"으로 표시한다.

| 항목 | 상태 | 조치 |
|---|---|---|
| uv | OK / MISSING | 아래 명령(표지 합성·이미지 생성이 `uv run --with pillow …`로 돈다 — 시스템 python3에는 Pillow가 없음) |
| python3 ≥ 3.11 | OK / MISSING | 3.11 이상 설치 (scaffold 스크립트용. naver-blog-cli는 uv가 자체 Python을 씀) |
| Playwright Chromium | OK / MISSING | 아래 명령 |
| naver-blog-cli | OK / MISSING | 아래 명령 |
| 네이버 세션 | 정상 / 로그인 필요 / 다른 계정 로그인 | 아래 로그인 절차. **다른 계정 로그인**(`WRONG_ACCOUNT` — 세션은 살아 있지만 글쓰기 화면이 다른 블로그로 이동)이면 출력의 이동 주소를 보여 주고 `<blogId>` 블로그 계정으로 로그인 절차를 다시 하라고 안내(기존 세션 파일을 덮어씀). 블로그 주소가 틀렸다면 `knowledge/source-blogs.json`의 `own_blog`를 고친다 |
| GEMINI_API_KEY | OK / MISSING | 아래 안내 |
| 한글 폰트(표지 합성) | OK / MISSING | 아래 안내 |
| photos/학원소개.png | OK / MISSING | 아래 안내 |
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
- 네이버 로그인 (**사람이 직접, 1회**). 로그인 스크립트는 설치본에 없으므로 저장소를 clone해서 쓴다. Claude 입력창이 아니라 **터미널에서**, 반드시 **작업 폴더에서** 실행한다. 세션 파일이 `<작업 폴더>/playwright-state/storage_state.json`에 저장된다.
  ```bash
  [ -d ~/naver-blog-cli ] || git clone https://github.com/spegas/naver-blog-cli ~/naver-blog-cli
  cd "<작업 폴더 절대경로>"
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
- 한글 폰트(표지 합성용, `scripts/make_cover.py`)
  ```
  대표이미지(표지)에 제목을 얹으려면 한글 폰트가 필요합니다. Pretendard를 받아(https://github.com/orioncactus/pretendard/releases)
  Pretendard-ExtraBold.otf·Pretendard-SemiBold.otf를 ~/Library/Fonts/ 에 넣어 주세요.
  (macOS 기본 /System/Library/Fonts/AppleSDGothicNeo.ttc가 있으면 그것으로도 만들 수 있습니다. 둘 다 없으면 /clark-blog:blog-run이 멈춥니다.)
  ```
- photos/학원소개.png
  ```
  모든 글 끝 마무리 블록(📞 문의 헤딩 → 학원소개 이미지 → 장소 카드 → 해시태그)에 들어가는 고정 이미지입니다.
  학원명·연락처·주소가 담긴 학원소개 이미지를 작업 폴더의 photos/학원소개.png 로 넣어 주세요(파일명 그대로).
  이 파일이 없으면 /clark-blog:blog-run이 시작하지 않습니다.
  ```

## 5. 다음 단계 안내

- `knowledge/design-system.md`가 없으면: "design-system.md가 없습니다. `blog-design-system` 스킬로 생성을 요청하세요. (글 검사 `lint_post.py`는 이 파일이 없어도 경고만 냅니다.)"
- `knowledge/design-system.md`가 이미 있으면(예: v0.3 — 레퍼런스 0 자기 글 기준 고정 골격·합니다체·title_region): "디자인 시스템을 고치려면 `blog-design-system` 스킬의 **갱신 모드**를 쓰세요(백업 → `work/design-system/proposed.md` → 이랑 승인 → `knowledge/` 교체). 3단계 복사는 이 파일을 덮어쓰지 않습니다."
- 누락·로그인 필요 항목이 남아 있으면 해결 후 이 커맨드를 다시 실행하라고 안내한다.
- 모두 갖춰졌으면: "준비가 끝났습니다. `/clark-blog:blog-run`으로 글 작성을 시작하세요."
