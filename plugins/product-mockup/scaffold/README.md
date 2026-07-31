# Product Mockup — 작업 폴더

플랫한 제품 디자인(패키지, 인쇄물, 포스터, 책 표지, 라벨, 달력, 카드, 박스아트 등) 원본 한 장을
가지고, 실제 공간에 놓인 듯한 라이프스타일 연출 사진 여러 장을 만드는 작업 폴더입니다. AI 이미지
모델이 장면(조명, 소품, 카메라 앵글)을 그리고, 그 위에 원본 디자인 픽셀을 4점 원근 변환으로
합성해 작은 글자까지 깨지지 않는 최종 이미지를 얻습니다.

이 폴더는 `/product-mockup` 커맨드가 복사해 준 시작 키트입니다. 파이프라인 전체 설명, 프롬프트
패턴, 검수 체크리스트 같은 **레퍼런스 문서는 플러그인 스킬 안에 들어 있습니다.** 따로 받아둘
필요 없이 Claude에게 물어보면 됩니다.

> 왜 AI한테 "글자 정확하게 그려줘"라고 하면 안 되는지 설명해줘.
> 프롬프트 6단계 구조 알려줘.
> 검수 체크리스트 5가지가 뭐야?

## 사전 준비

### 1. Gemini API 키
1. https://aistudio.google.com/apikey 에서 키 발급
2. 이 폴더에서 `.env.example`을 `.env`로 복사하고 키 값을 채웁니다.
   ```bash
   cp .env.example .env
   ```
3. `.env`는 절대 커밋하지 마세요. 키 값은 로그/출력에도 남기지 마세요.

### 2. Python 환경
이 폴더 안에서:
```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install google-genai opencv-python-headless numpy pillow
```

### 3. 준비물 (파일)
- **제품 디자인 고해상도 원본** — 인쇄용 PDF를 내보낸 PNG처럼, 최종 이미지 품질의 상한선이
  되는 파일. `source/`에 넣습니다.
- **제품 실물 참조 사진 1장** — 제본, 스탠드, 액자, 재질 등 원본 디자인 파일만으로는 AI가
  추측할 수 없는 물리적 디테일이 잘 보이는 사진. `source/`에 함께 넣습니다.

## 폴더 구조

아래 경로는 모두 이 작업 폴더(= 이 README가 있는 곳)를 기준으로 합니다.

| 폴더 | 용도 |
|---|---|
| `source/` | 원본 고해상도 디자인 + 물리적 디테일 참조 사진 (직접 채워 넣는 곳) |
| `scenes/` | AI가 생성한 장면 원본 PNG + `metadata.json` (3단계 결과물) |
| `final/` | 합성 완료된 최종 이미지 + `_evidence/`에 글자 왜곡 여부를 증명하는 확대 크롭 |
| `scripts/` | 파이프라인 스크립트 (`generate_scenes.py`, `composite.py`, `zoom_corners.py`, `fit_edges.py`, `probe_occluder.py`)와 `*.example.json` |

작업 중 만드는 설정 파일(`project.json`, `scenes.json`, `prompts.json`)의 위치 규칙은
3단계의 경고 상자를 보세요.

## 진행 순서 (6단계)

각 단계에서 Claude에게 그대로 복붙해서 쓸 수 있는 지시 프롬프트 예시를 붙였습니다. 실제 제품/
공간 이름으로 바꿔서 사용하세요.

### 1단계 — 원본 디자인 정리
소스 파일을 고해상도 PNG로 정리하고, 스캐너 여백/재단선을 잘라내고, 실제 인쇄면의 네
꼭짓점 좌표를 기록합니다.

```
내 제품 인쇄용 PDF는 source/print_ready.pdf에 있어. 이걸 고해상도 PNG로 변환해서
source/design_full.png로 저장해줘. 스캐너 여백이나 재단선은 잘라내고, 실제 인쇄면의
네 꼭짓점 픽셀 좌표(x, y)를 알려줘. 이후 날짜 그리드나 라벨 하단부 같은 하위 영역을
다시 잘라 써야 할 수도 있으니, 그런 구조적 기준점이 있으면 같이 짚어줘.
```

### 2단계 — 장면 프롬프트 설계
스킬의 프롬프트 패턴 레퍼런스에 있는 6단계 프롬프트 구조를 따라, 장면별 프롬프트를 작성합니다.

```
product-mockup 스킬의 prompt-patterns 레퍼런스에 있는 6단계 프롬프트 구조
(배치 -> 장면 설명 -> 보존 지시 -> 결합/구조 설명 -> 카메라/조명 -> 출력 해상도)를 그대로
따라서, source/design_full.png(첫 번째 레퍼런스)와 source/detail_reference.jpg(두 번째
레퍼런스)를 쓰는 장면 프롬프트 8개를 만들어줘. 공간 4종 x 정면/측면 앵글로 구성하고,
scripts/config.example.json의 prompts_file 설명에 나온
{"scenes": [{"id","scene","variant","prompt"}]} 스키마로 scripts/prompts.json에 저장해줘.
```

### 3단계 — 장면 생성
`config.example.json`을 프로젝트용 설정 파일로 복사한 뒤 생성 스크립트를 돌립니다.

> **설정 파일 위치 주의**: `generate_scenes.py`와 `composite.py`는 설정 파일 안의 상대경로를
> **설정 파일 자신이 있는 디렉토리** 기준으로 풉니다. 그러니 복사본(`project.json`,
> `scenes.json`)은 `scripts/`가 아니라 **작업 폴더 루트**에 두세요. `scripts/` 안에 두면
> `source/design_full.png`가 `scripts/source/design_full.png`로 해석돼 조용히 깨집니다.

```
scripts/config.example.json을 참고해서 project.json을 작업 폴더 루트에 만들어줘
(scripts/ 안이 아니라 루트에. ref_image_1은
source/design_full.png, ref_image_2는 source/detail_reference.jpg, prompts_file은
scripts/prompts.json으로). 그다음
.venv/bin/python scripts/generate_scenes.py --config project.json
을 실행해서 8개 장면을 생성해줘. 실패한 장면이 있으면 scenes/metadata.json에서
에러 메시지를 확인하고 알려줘.
```

특정 장면만 다시 만들고 싶을 때:
```bash
.venv/bin/python scripts/generate_scenes.py --config project.json --only living_room_a study_b
```

### 4단계 — 결과 검수
각 장면을 확대해서 5가지 체크리스트로 판정합니다.

```
scripts/zoom_corners.py로 각 장면(scenes/<id>.png)의 제품 네 모서리를 확대한
2x2 몽타주를 만들어줘. 그다음 product-mockup 스킬의 review-checklist 레퍼런스에 있는
5가지 체크(텍스트 충실도 / 아트 충실도 / 제품 구조 / 연출 리얼리즘 / 이커머스 적합성)로
각 장면을 PASS / COMPOSITE / REGEN / FAIL 중 하나로 판정해서 표로 정리해줘.
COMPOSITE로 판정한 장면은 4점 쿼드 좌표(TL,TR,BR,BL)와 원본 전체/서브영역 중
어디를 합성해야 하는지도 같이 적어줘.
```

### 5단계 — 재생성 또는 합성
REGEN은 프롬프트를 보강해 다시 생성하고, PASS/COMPOSITE는 원본을 합성합니다.

```
REGEN으로 판정된 장면은 product-mockup 스킬 prompt-patterns 레퍼런스의
"Regeneration reinforcement catalogue"를 참고해서 결함에 맞는 보강 문장만 추가하고,
--only <scene_id>로 다시 생성해줘. PASS/COMPOSITE로 판정된 장면은
scripts/scenes.example.json 형식을 참고해서 scenes.json을 작업 폴더 루트에
만들고(scripts/ 안이 아니라 루트에. paths.src_path는
source/design_full.png, landmarks.page는 1단계에서 기록한 꼭짓점 좌표로),
.venv/bin/python scripts/composite.py --config scenes.json
을 실행해서 원본 디자인을 합성해줘. final/_evidence/의 확대 크롭을 보고 글자가
왜곡 없이 살아있는지 확인해줘.
```

가림물(램프, 책, 안경 등 제품 앞을 가리는 물체)이 있는 장면은 `occluders`의 임계값을
직접 잡아야 합니다. `scripts/probe_occluder.py`가 폴리곤 안팎의 픽셀 분포를 비교해
`t0`/`softness`를 제안해줍니다.
```bash
# 1) 좌표 읽기용 격자 오버레이 저장 -> 폴리곤 정점을 눈으로 찍는다
.venv/bin/python scripts/probe_occluder.py scenes/study_b.png --overlay

# 2) 찍은 폴리곤으로 임계값 제안 받기
.venv/bin/python scripts/probe_occluder.py scenes/study_b.png \
    --poly 1360,1900 1372,1858 1392,1832 1430,1812 1480,1806 1560,1812 1560,1960 1360,1960 \
    --metric lum
```
`--quad`(제품 면 네 꼭짓점)는 꼭 넘기세요. 없으면 비교 표본이 제품 밖 배경까지 물어서
`t0`가 부풀고, 결국 알파가 1에 도달하지 못하는 설정이 나옵니다.

임계값이 도저히 안 잡히면 **`mode: "poly"`로 시작하세요** — 폴리곤 자체를 마스크로 쓰므로
임계값이 아예 필요 없습니다. 경계가 약간 거칠어져도 일단 동작하고, 제품의 활자가 가림물
너머로 비치는 것보다는 훨씬 작은 결함입니다. `auto`/`soft`/`poly`를 각각 언제 쓰는지는
스킬의 review-checklist 레퍼런스 중 "Choosing an occluder `mode`" 표에 정리돼 있습니다.

특정 장면만 합성하고 싶을 때:
```bash
.venv/bin/python scripts/composite.py --config scenes.json living_room_a study_b
```

### 6단계 — 산출물 정리 및 배치 가이드 작성
```
final/ 폴더의 최종 이미지들을 용도별(히어로샷 / 디테일샷 / 장면별 라이프스타일 컷)로
정리한 배치 가이드를 문서로 써줘. 이미지별로 알려진 한계점(예: "중간 프레임의 작은
글자 영역이 살짝 소프트함 — 이 크기에서는 허용 가능")이 있으면 같이 적고,
final/_evidence/의 크롭 이미지를 글자 충실도 증거로 함께 인용해줘.
```

## 예상 소요

- 생성: 장당 약 30초
- API 비용: 8장 기준 약 $1
- 검수/합성까지 포함한 전체 사이클: 사람이 붙어서 진행 시 1~2시간 내외 (**이 문서를 이미 읽었고
  파이프라인을 한 번 돌려본 경우 기준. 처음이라 스킬 레퍼런스를 읽어가며 진행한다면 학습 시간
  1~2시간을 따로 잡으세요.** 재생성 라운드 수에 따라서도 변동)

## 자주 막히는 지점

1. **`.env`를 못 찾는다는 에러** — `generate_scenes.py`는 `--env`, `<config 폴더>/.env`,
   `<현재 디렉토리>/.env` 순으로 찾습니다. 작업 폴더 루트에서 실행 중인지, `.env` 파일명이
   정확한지(`.env.example`이 아니라 `.env`) 확인하세요.
2. **429/503 오류로 일부 장면만 실패** — 스크립트가 자동으로 최대 3회, 지수 백오프로 재시도
   합니다. 그래도 실패하면 몇 분 후 `--only <실패한 id>`로 재시도하세요. 한 번에 너무 많은
   장면(기본 동시 실행 3개)을 돌리면 더 자주 발생합니다.
3. **작은 글자(요일 헤더, 성분표, 가격 등)가 계속 깨짐** — 이건 프롬프트로 고칠 수 없는, 이
   키트가 원래 전제하는 실패 모드입니다. 세 번째 프롬프트 라운드를 시도하지 말고 바로 5단계
   합성으로 넘어가세요. 자세한 내용은 스킬 prompt-patterns 레퍼런스의 "What did not work" 참고.
4. **`zoom_corners.py` / `fit_edges.py` 사용법** — 두 스크립트 모두 첫 인자로 장면을
   받는데, 확장자가 있으면(`scenes/study_a.png`처럼) 경로 그대로 사용하고, 확장자가 없으면
   (`study_a`처럼) bare scene id로 보고 `--scenes-dir`(기본값: 실행한 디렉토리 기준
   `./scenes`) 밑의 `<id>.png`를 찾습니다. 작업 폴더 루트에서 실행 중이면 별도 옵션
   없이 scene id만 써도 되고, 다른 위치에서 실행하거나 장면 파일이 다른 폴더에 있다면
   `--scenes-dir <경로>`를 넘기거나 스크립트 경로를 직접 지정하세요.
   ```bash
   .venv/bin/python scripts/zoom_corners.py study_a 700,480 1500,470 1490,1810 690,1800
   .venv/bin/python scripts/fit_edges.py study_a bottom=700,1490,1780,1830 top=700,1490,460,500 \
       left=470,1800,690,740 right=470,1800,1480,1530
   ```
   `zoom_corners.py`의 출력 경로는 기본적으로 입력 이미지 폴더 밑의 `_inspect/`이며,
   `--out <경로>`로 바꿀 수 있습니다.

## 막혔을 때 더 볼 곳

플러그인 스킬 안의 레퍼런스들입니다. Claude에게 "product-mockup 스킬의 ~ 열어줘"라고 하면 됩니다.

- **SKILL.md** — 전체 파이프라인과 왜 하이브리드 방식이 필요한지
- **prompt-patterns** — 프롬프트 구조와 보강 문장 카탈로그
- **review-checklist** — 검수 체크리스트와 판정 기준 (가림 처리 `mode` 3종을 언제 쓰는지도 여기)
- **orchestration** — 단계별로 어떤 에이전트에 맡길지, 생성과 검수를 왜 분리하는지

그리고 이 폴더 안:
- `scripts/composite.py`의 모듈 docstring — `scenes.json`의 모든 키(quad, band,
  light_sigma_frac, occluders 등) 설명
- `scripts/scenes.example.json` — 실제로 통과했던 설정값 전체 (좌표는 예시이므로 그대로
  쓰지 말고 본인 장면에서 다시 측정하세요)

## 응용 과제

파이프라인을 한 번 돌려봤다면 `ASSIGNMENT.md`의 응용 과제로 넘어가세요.
