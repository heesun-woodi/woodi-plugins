# clark-blog

클라크중장비운전학원 네이버 블로그의 정보성 글을 만드는 Claude Code 플러그인입니다. 주제 리서치부터 초안, 법령·공공기관 근거 검토, 네이버 SEO 다듬기, 이미지까지 진행하고 네이버에 임시저장까지만 합니다. 발행은 사람이 직접 합니다.

## 사전 요구사항

**naver-blog-cli 설치.** 네이버 임시저장은 외부 도구 [naver-blog-cli](https://github.com/spegas/naver-blog-cli)(MIT)에 맡깁니다. uv와 Python 3.11 이상이 있으면 한 줄입니다.

```bash
uv tool install git+https://github.com/spegas/naver-blog-cli
```

설치되면 `naver-blog-cli`가 `~/.local/bin`에 생깁니다(PATH에 없으면 `uv tool update-shell`). 브라우저 조작용 Playwright Chromium이 없다면 `~/.local/share/uv/tools/naver-blog-cli/bin/playwright install chromium`으로 설치합니다. 로그인 스크립트 `login_setup.py`는 이 설치에 들어 있지 않으므로 저장소를 한 번 clone해 둡니다: `git clone https://github.com/spegas/naver-blog-cli ~/naver-blog-cli`.

**로그인은 1회, 사람이 직접.** 작업 폴더에서 `NAVER_STATE="$PWD/playwright-state/storage_state.json" ~/.local/share/uv/tools/naver-blog-cli/bin/python ~/naver-blog-cli/login_setup.py`(`login_setup`)를 실행하면 브라우저가 열립니다. 직접 로그인하고, **로그인 버튼을 누르기 전에 "로그인 상태 유지"를 체크**하세요(체크하지 않으면 몇 시간 뒤 글쓰기만 로그인 페이지로 바뀝니다). CAPTCHA·2차 인증도 사람이 처리합니다. 비밀번호는 어디에도 저장되지 않고 쿠키 파일(`playwright-state/`)만 남으며, 이 파일은 계정 접근권한 그 자체이니 공유하지 마세요. 세션이 만료되면 같은 명령을 다시 실행합니다.

## 설치와 첫 사용

(Task 15에서 채움)

## 워크플로우

(Task 15에서 채움)

## 계정 안전 수칙

(Task 15에서 채움)

## 비용

(Task 15에서 채움)
