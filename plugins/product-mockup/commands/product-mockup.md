---
description: 제품 디자인 원본을 라이프스타일 연출 사진으로 만드는 워크플로우를 시작합니다. 환경을 진단하고 작업 폴더를 준비한 뒤 product-mockup 스킬로 진입합니다.
argument-hint: "[제품 설명 / 작업 폴더 경로 (선택)]"
allowed-tools: Bash, Read, Write, Glob, Skill
---

사용자가 제품 목업 워크플로우를 시작했다. 아래 순서대로 진행하라.
사용자에게 보여주는 모든 안내 문구는 **한국어**로 작성한다.

인자: `$ARGUMENTS` (제품 설명이나 작업 폴더 경로가 들어올 수 있다. 비어 있으면 3단계에서 물어본다.)

---

## 1. 환경 진단

먼저 한 번의 Bash 호출로 전부 확인하라. 개별적으로 나눠서 여러 번 묻지 말 것.

```bash
echo "--- python ---"
for p in .venv/bin/python venv/bin/python python3; do
  command -v "$p" >/dev/null 2>&1 && { echo "found: $p"; PY="$p"; break; }
  [ -x "$p" ] && { echo "found: $p"; PY="$p"; break; }
done
echo "PY=${PY:-none}"
echo "--- packages ---"
"${PY:-python3}" - <<'EOF' 2>/dev/null || echo "python 실행 실패"
import importlib.util as u
for mod, pkg in [("google.genai","google-genai"),("cv2","opencv-python-headless"),("numpy","numpy"),("PIL","pillow")]:
    print(f"{pkg}: {'OK' if u.find_spec(mod) else 'MISSING'}")
EOF
echo "--- api key ---"
if [ -n "$GEMINI_API_KEY" ]; then echo "GEMINI_API_KEY: env에 있음"
elif [ -f .env ] && grep -q '^GEMINI_API_KEY=.' .env; then echo "GEMINI_API_KEY: .env에 있음"
else echo "GEMINI_API_KEY: MISSING"; fi
```

결과를 해석해서 **없는 것만** 안내하라. 이미 갖춰진 항목은 "확인됨" 한 줄로만
언급하고, 다시 설치하라고 시키지 않는다. 값이 실제로 무엇인지는 절대 출력하지
않는다 (API 키는 존재 여부만 확인한다).

부족한 항목별 안내 문구:

- **가상환경 없음**
  ```
  가상환경이 없습니다. 작업 폴더에서 아래를 실행해 주세요.

      python3 -m venv .venv
  ```
- **패키지 누락** — 누락된 것만 나열해서 한 줄로 묶어라.
  ```
  아래 패키지가 없습니다: <누락 목록>

      .venv/bin/pip install <누락 목록>
  ```
- **GEMINI_API_KEY 없음**
  ```
  Gemini API 키가 필요합니다. https://aistudio.google.com/apikey 에서 발급한 뒤
  작업 폴더의 .env 파일에 아래 형식으로 넣어 주세요.

      GEMINI_API_KEY=여기에_키

  .env는 .gitignore에 포함되어야 합니다. 키 값은 채팅에 붙여넣지 마세요.
  ```

하나라도 빠졌으면 여기서 멈추고 사용자가 처리할 때까지 기다린다.
전부 갖춰졌으면 "환경 확인 완료"만 알리고 2단계로 넘어간다.

## 2. 작업 폴더 준비

`${CLAUDE_PLUGIN_ROOT}/scaffold/` 의 내용을 현재 작업 폴더로 복사한다.

```bash
ls -A "${CLAUDE_PLUGIN_ROOT}/scaffold/"
```

복사 전에 **같은 이름이 이미 있는지 반드시 먼저 확인**하고, 있으면 덮어쓰지
말고 건너뛴 뒤 사용자에게 알린다.

```bash
cp -rn "${CLAUDE_PLUGIN_ROOT}/scaffold/." .
```

`cp -n`은 기존 파일을 덮어쓰지 않는다. 복사 후 어떤 파일이 새로 생겼고 어떤
파일이 이미 있어서 건너뛰어졌는지 목록으로 보고하라. 건너뛴 파일이 있으면:

```
아래 파일은 이미 있어서 그대로 두었습니다: <목록>
스캐폴드 최신본으로 바꾸려면 말씀해 주세요.
```

## 3. 준비물 확인

사용자에게 두 가지를 요청한다. 이미 `$ARGUMENTS`나 대화에서 경로를 받았다면
다시 묻지 말고 파일 존재만 확인하라.

```
시작하려면 두 가지가 필요합니다.

1. 제품 디자인 고해상도 원본
   인쇄용 PDF를 인쇄 DPI로 내보낸 PNG 정도면 좋습니다. 이 파일이 모든
   결과물 화질의 상한선입니다. 저해상도 이미지로는 마지막 합성 단계에서
   글자가 뭉개집니다.

2. 제품 실물 참조 사진 한 장
   평면 디자인만으로는 알 수 없는 물리적 구조가 찍힌 사진입니다.
   제본 방식, 걸이, 거치대 경첩, 액자, 포장 형태 등 — 딱 그 부분이
   보이면 됩니다. 이걸 빼면 1라운드 결과물의 제품 구조가 틀리게 나옵니다.

추가로, 원하시는 장면 목록이 있으면 알려주세요.
(예: 거실 / 서재 / 주방 / 사무실 × 정면·측면 = 8장)
없으면 제품과 타깃에 맞춰 제안해 드리겠습니다.
```

받은 경로는 실제로 존재하는지, 해상도가 충분한지 확인하고 결과를 알린다.

## 4. 워크플로우 진입

준비물이 모두 확보되면 `product-mockup` 스킬을 호출해 본편 워크플로우로
넘어간다. 스킬의 6단계 파이프라인과 `references/orchestration.md`의 에이전트
디스패치 규칙을 그대로 따른다.

사용자에게는 앞으로의 흐름을 짧게 예고한다.

```
이제 시작합니다. 진행 순서는 이렇습니다.

  1. 원본 추출     디자인 원본을 정리하고 네 모서리 좌표를 잡습니다
  2. 장면 설계     구매 동기별로 장면 프롬프트를 만듭니다
  3. 생성          장면별로 이미지를 생성합니다
  4. 검수          원본과 대조해 확대 검수하고 판정합니다
  5. 합성          원본 디자인을 원근 변환해 제품면에 정확히 얹습니다
  6. 정리          결과물을 상세페이지 배치 순서로 정리합니다

미리 알려드릴 점이 하나 있습니다. 1라운드에서 작은 글씨가 깨져 나오는 것은
정상이고, 프롬프트로는 고쳐지지 않습니다. 5단계 합성이 바로 그걸 고치는
단계입니다. 실패가 아니라 설계된 흐름입니다.
```
