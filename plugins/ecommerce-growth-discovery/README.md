# ecommerce-growth-discovery

**GA4·Meta 계정을 직접 연결해 성장 병목을 찾습니다. 데이터 미포함, 설정과 분석은 사용자 주도입니다.**

이커머스 팀이 실제 데이터(GA4 트래픽·구매·Meta 광고)에서 최우선 실험 대상 3개를 찾는 클로드 스킬입니다. 표와 질문으로 끝나므로, 팀이 함께 합의·판정하는 코칭형입니다.

---

## 1. 설치 (2단계)

**① 마켓플레이스 추가**

```
/plugin marketplace add heesun-woodi/woodi-plugins
```

**② 플러그인 설치**

```
/plugin install ecommerce-growth-discovery@woodi-plugins
/reload-plugins
```

설치 확인: `/plugin` 목록에 `ecommerce-growth-discovery`가 보이면 완료입니다.

> 로컬 폴더로 받은 경우 ① 대신 폴더 경로를 입력하세요:
> `/plugin marketplace add /Users/본인계정/경로/woodi-plugins`

---

## 2. 세팅

새 작업 폴더를 Claude에서 연 뒤 아래를 실행합니다.

```
/ecommerce-growth-discovery:setup
```

### 사전 준비물

| 항목 | 용도 | 필수 |
|---|---|---|
| **uv** (Python 패키지 매니저) | GA4 쿼리 실행 | ✅ |
| **gcloud** (Google Cloud CLI) | GA4 인증 | ✅ |
| **Google 계정** (GA4 조회 권한) | GA4 속성 접근 | ✅ |
| **Meta 광고 계정** (선택) | 광고 효율 추가 | — |

GA4 연결은 Google 공식 `analytics-mcp`(https://github.com/googleanalytics/google-analytics-mcp) 0.7.0을 `uvx`로 실행합니다 — 버전은 플러그인 `.mcp.json`에 고정돼 있으며, 올릴 때는 플러그인 버전과 함께 갱신합니다.

### 설치 명령 (OS별)

**macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
brew install --cask google-cloud-sdk
```

**Windows:**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# Google Cloud SDK: https://cloud.google.com/sdk/docs/install 설치 프로그램 다운로드
```

설치 후 Claude를 완전히 재시작한 뒤 다시 `/ecommerce-growth-discovery:setup`을 실행하세요.

### GA4 인증

`setup` 명령이 ADC(Application Default Credentials) 로그인을 안내합니다.

```bash
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform
```

> OAuth 클라이언트 파일을 받은 경우에만 setup이 실제 파일명이 박힌 완성 명령을 보여줍니다.

### Meta 광고 (선택)

연결하려면: `/mcp` → `meta-ads` → **Authenticate**

연결하지 않으면 광고 효율 표가 벤치마크 값만 표시됩니다.

---

## 3. 스킬 4개

### `/ecommerce-growth-discovery:setup`

한 번 실행 후 작업 폴더에 `growth-discovery.config.json`을 생성합니다. GA4 속성·매출 지표·제외할 랜딩·팀 라벨을 선택하고 저장하는 가이드형 세팅입니다.

### `/ecommerce-growth-discovery:explore [서브커맨드]`

모든 트래픽·퍼널·광고 채널 데이터를 표로 표시하고 각 표 아래 질문을 던집니다. `explore-findings.md`에 각 섹션을 누적 저장합니다.

| 서브커맨드 | 하는 일 |
|---|---|
| `baseline` | 몸 전체 숫자: 세션 · 구매 건수 · 전환율 · 객단가 (4행) |
| `traffic` | 누가 오나: 채널별 트래픽 구성 · Paid vs Non-paid 담기율 비교 · 신규/재방문 |
| `funnel` | 세션 시작 → 상품 조회 → 장바구니 담기 → 결제 시작 (4단계, 구매 단계는 넣지 않는다) |
| `channel-cvr` | 채널×전환율 + 광고 효율: 지출·노출·클릭·구매·ROAS (Meta MCP 또는 `data/ads.csv`) |
| `areas` | 문제영역 3개 중 이번에 볼 1개 선택 |

인자 없으면 5개를 순차 실행합니다 — `explore-findings.md` 생성.

### `/ecommerce-growth-discovery:screen [모드]`

`explore-findings.md`에서 선택한 영역의 실제 화면(URL·스크린샷)을 고객 관점 문제로 바꿉니다. 스텝별 가이드: Fact 전사 → 편향·체크리스트 판정 → 문제 문장 → Impact 계산.

| 모드 | 입력 |
|---|---|
| `상품상세` | 상품 페이지 URL / 모바일 스크린샷 |
| `광고랜딩` | 광고 링크 / 랜딩페이지 스크린샷 |

URL을 주면 자동 판별합니다. `problems-{라벨}.md`로 저장.

### `/ecommerce-growth-discovery:psr`

`problems-{라벨}.md`를 받아 솔루션 발산 → PSR(Problem·Solution·Result) 가설 → ICE(Impact·Confidence·Ease) 우선순위까지 안내합니다. `psr-{라벨}.md`로 저장.

---

## 4. 산출물

```
작업 폴더(또는 config의 output.dir)/
  explore-findings.md    ← /explore 최종 결과. 섹션 A~F 누적 저장
  problems-{라벨}.md      ← /screen 결과. 라벨이 비면 problems.md
  psr-{라벨}.md           ← /psr 결과. 라벨이 비면 psr.md

screens/                 ← /screen 입력용 폴더 (선택)
  01.png, 02.png, …     스크린샷 (png/jpg, 파일명 순서 = 위→아래)
```

라벨이란: 팀 내 구분용(`상품기획`, `마케팅` 등), 선택 항목입니다. 실명 금지.

---

## 5. 설정 파일 스키마

`growth-discovery.config.json` (작업 폴더)

```json
{
  "version": 1,
  "store_name": "우리 몰",
  "currency": "KRW",
  "industry": "general",
  "ga4": {
    "property_id": "",
    "date_range": { "start_date": "90daysAgo", "end_date": "yesterday" },
    "revenue_metric": "purchaseRevenue",
    "exclude_filters": [],
    "data_notes": []
  },
  "meta": { "enabled": false, "ad_account_id": "" },
  "output": { "dir": ".", "label": "" }
}
```

| 필드 | 설명 |
|---|---|
| `store_name` | 표 제목에 표시 (예: "우리 몰") |
| `currency` | 금액 단위 (예: `KRW`, `USD`) |
| `industry` | 벤치마크 선택: `fashion` / `home` / `general` |
| `ga4.property_id` | GA4 속성 ID (setup이 선택하게 함) |
| `ga4.date_range` | 조회 기간. 상대값 `90daysAgo`·`yesterday` 또는 고정날짜 `2026-06-11` |
| `ga4.revenue_metric` | `purchaseRevenue`(구매 수익, 기본) 또는 `itemRevenue`(상품 수익) |
| `ga4.exclude_filters[]` | 제외할 계측 오류 — `{field_name, match_type, value}` |
| `ga4.data_notes[]` | 숫자 아래 붙일 주의 문구 배열 (예: "구매 이벤트 중복 발화로 약 20% 많게 집계") |
| `meta.enabled` | `false`(기본) 또는 `true` — Meta 광고 표 채울지 |
| `meta.ad_account_id` | Meta 계정 ID (숫자만, `act_` 접두 제거) |
| `output.dir` | 산출물 폴더 (기본: 현재 폴더) |
| `output.label` | 파일명 접미 (비면 접미 없음) |

config가 없으면 모든 스킬이 `/ecommerce-growth-discovery:setup`을 먼저 실행하라고 안내합니다.

---

## 6. 개인정보·데이터

### 플러그인 안에는 데이터가 없습니다

고객사 데이터(화면 스크린샷, GA4 속성 ID, Meta 광고 ID, 광고비 CSV)는 어디에도 들어 있지 않습니다. 모든 데이터는 **당신이 연결한 MCP**에서만 조회됩니다.

- **GA4**: `analytics-mcp` via `gcloud` ADC  
- **Meta**: `meta-ads` MCP (OAuth 브라우저 로그인)

### 스크린샷 보호

`/ecommerce-growth-discovery:screen`에서 스크린샷을 업로드하면, 플러그인이 실명·주소·전화·이메일 등 개인정보를 감지해 계속 진행을 멈춥니다. 감지되지 않은 PII는 `problems.md`에 그대로 남을 수 있으므로, 산출물을 팀 내에만 공유하세요.

### 산출물은 로컬 파일입니다

`explore-findings.md`, `problems-{라벨}.md`, `psr-{라벨}.md`는 모두 작업 폴더의 로컬 파일입니다. 네트워크 전송·클라우드 저장 없음. git 버전 관리 또는 팀 드라이브에 수동으로 복사하세요.

---

**버전 0.2.0** · 범용 이커머스 성장 분석용
