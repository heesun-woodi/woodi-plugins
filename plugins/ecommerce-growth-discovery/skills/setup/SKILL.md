---
name: setup
version: 0.2.0
description: GA4와 Meta 광고 계정 연결을 점검하고 cwd에 `growth-discovery.config.json`을 만든다 — 빠진 준비물(uv·gcloud·ADC·MCP 도구)은 운영체제에 맞는 명령을 보여 주기만 하고 멈춘다. "/ecommerce-growth-discovery:setup", "세팅", "세팅해줘", "연결 확인", "GA4 연결", "속성 연결", "설정 파일 만들기"라는 요청에 사용한다.
allowed-tools:
  - Read
  - Write
  - Glob
  - Bash(uname:*)
  - Bash(command -v:*)
  - Bash(uv --version)
  - Bash(gcloud --version)
  - Bash(gcloud config get-value:*)
  - Bash(gcloud auth application-default print-access-token)
  - Bash(curl -s "https://oauth2.googleapis.com/tokeninfo*)
  - mcp__plugin_ecommerce-growth-discovery_analytics-mcp__get_account_summaries
  - mcp__plugin_ecommerce-growth-discovery_analytics-mcp__run_report
  - mcp__plugin_ecommerce-growth-discovery_meta-ads__ads_get_ad_accounts
  - mcp__analytics-mcp__get_account_summaries
  - mcp__analytics-mcp__run_report
  - mcp__meta-ads__ads_get_ad_accounts
---

# /ecommerce-growth-discovery:setup — 연결 점검과 설정 파일 만들기

## 이 스킬의 절대 규칙

**설치 명령은 절대 실행하지 않는다. 보여만 준다.**

- `uv`·`gcloud` 설치, ADC 로그인, 패키지 설치, MCP 등록 — 어느 것도 이 스킬이 대신 실행하지 않는다. 명령 블록을 화면에 띄우고, 사용자가 자기 터미널에서 직접 실행하게 한 뒤 **멈춘다.**
- 허용된 Bash는 **점검용 읽기 명령뿐**이다(`uname`, `command -v`, `--version`, `gcloud config get-value`, `print-access-token`, `tokeninfo` 조회). 그 밖의 Bash를 쓰지 않는다.
- 파일 쓰기는 **9단계의 `growth-discovery.config.json` 단 하나**다. 다른 파일을 만들거나 고치지 않는다.
- 자격증명 값(액세스 토큰, 클라이언트 시크릿 파일의 내용)은 **화면에 출력하지 않는다.** 파일 이름까지만 말한다.
- 위 MCP 도구는 전부 읽기 전용 조회이며, 설치·설정 변경 도구는 목록에 없다.

시작하기 전에 `${CLAUDE_PLUGIN_ROOT}/data/rules.md`를 읽고 그 규칙(도구 이름 접미 탐색·config 스키마·매출 지표·톤·개인정보)을 그대로 따른다 — 변수가 없으면 이 SKILL.md 위치 기준 `../../data/rules.md`로 읽는다.

## 진행 방식

| 규칙 | 내용 |
|---|---|
| 한 단계 = 점검 한 번 | 점검 명령을 돌려 통과/실패만 판정한다. |
| 실패하면 | **그 운영체제의 명령 블록 하나만** 보여주고 → "실행한 뒤 다시 `/ecommerce-growth-discovery:setup`을 실행해 주세요." → **거기서 출력을 끝낸다.** 다음 단계로 넘어가지 않는다. |
| 다른 OS 명령 | 보여주지 않는다. 1단계에서 판별한 OS의 블록만 낸다. |
| 재실행 | 이미 통과한 단계는 **한 줄로만** 적고 지나간다. 예: `1단계 OS: macOS ✓` / `2단계 uv: 설치됨 ✓`. 통과한 단계의 설명·명령을 다시 늘어놓지 않는다. |
| 질문 | 한 번에 **하나**만 묻는다. 묻고 나면 답을 기다리며 멈춘다. |
| 실패 보고 | 오류 메시지는 **첫 줄만 원문 그대로** 옮긴다. 토큰·시크릿이 섞인 줄은 옮기지 않는다. |

각 단계를 시작할 때 `N단계 · 제목` 한 줄을 먼저 적는다. 전체 단계는 0~9다.

---

## 0단계 — 이미 있는 설정 파일 확인

cwd에서 `growth-discovery.config.json`을 찾는다(`Glob`).

**없으면** 1단계로 간다.

**있으면** `Read`로 읽고 아래 요약표를 띄운다(값이 비어 있으면 `—`).

| 항목 | 값 |
|---|---|
| 몰 이름 | `{store_name}` |
| 업종(`industry`) | `{industry}` |
| GA4 속성 ID | `{ga4.property_id}` |
| 조회 기간 | `{ga4.date_range.start_date}` ~ `{ga4.date_range.end_date}` |
| 매출 지표 | `{ga4.revenue_metric}` |
| 제외 필터 | N건 |
| 주의 문구 | N건 |
| Meta 광고 | 연결됨 `{meta.ad_account_id}` / 사용 안 함 |
| 저장 위치·라벨 | `{output.dir}` · `{output.label}` |

표 아래에 질문 하나로 멈춘다.

> 이 설정으로 연결만 확인할까요?

- **예**(또는 "확인해줘", "그대로") → **5단계 → 7단계 → 9단계**만 실행한다. 5단계는 속성 목록을 띄우지 않고 도구 호출이 되는지만 본다(6단계 속성 선택은 건너뛴다). 7단계는 `meta.enabled`가 `true`일 때만 계정 조회로 확인하고, `false`면 "Meta는 사용 안 함으로 설정돼 있어요" 한 줄로 지나간다. 8단계 질문은 하지 않는다. 9단계에서 **config를 덮어쓰지 않고** baseline 표만 띄운다.
- **아니오**(또는 "새로 만들래") → 1단계부터 전체를 진행한다. 9단계에서 기존 파일을 덮어쓴다는 것을 그때 한 줄로 알린다.

---

## 1단계 — 운영체제 판별

```
uname -s
```

| 결과 | 이후 쓸 OS |
|---|---|
| `Darwin` | macOS |
| `Linux` | Linux |
| `MINGW…` · `MSYS…` · `CYGWIN…` | Windows |
| 명령 자체가 실패 | Windows (PowerShell에는 `uname`이 없다) |

판별 결과를 한 줄로 적고("운영체제: macOS") 2단계로 간다. **이 뒤의 모든 명령 블록은 여기서 정한 OS의 것만 보여준다.**

---

## 2단계 — uv 설치 확인

```
command -v uv
```

경로가 나오면 통과다(`uv --version`으로 한 번 더 확인해도 된다). 아무것도 안 나오면 아래 블록을 보여준다.

**macOS · Linux**

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell)**

```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

붙이는 안내(문자 그대로):

> 설치가 끝나면 **Claude를 완전히 껐다가 다시 켠 뒤** `/ecommerce-growth-discovery:setup`을 다시 실행해 주세요. 터미널만 새로 열어서는 인식되지 않을 수 있어요.

여기서 멈춘다.

---

## 3단계 — gcloud CLI 설치 확인

```
command -v gcloud
```

경로가 없으면 아래 블록을 보여주고 멈춘다.

**macOS** (Homebrew가 있을 때)

```
brew install --cask google-cloud-sdk
```

Homebrew가 없으면 https://cloud.google.com/sdk/docs/install 에서 macOS용 설치 파일을 내려받아 안내대로 설치한다고 알린다.

**Windows** (winget이 있을 때)

```
winget install --id Google.CloudSDK -e
```

winget이 없으면 https://cloud.google.com/sdk/docs/install 에서 Windows용 설치 파일을 내려받는다고 알린다.

**Linux**: https://cloud.google.com/sdk/docs/install 의 배포판별 안내를 따른다고만 알린다.

붙이는 안내: "설치 후 터미널(또는 PowerShell)을 새로 연 다음 `/ecommerce-growth-discovery:setup`을 다시 실행해 주세요."

**gcloud가 있으면** 프로젝트 설정을 이어서 본다.

```
gcloud config get-value project
```

값이 비어 있거나 `(unset)`이면 아래를 보여주고 멈춘다 — 명령은 실행하지 않는다.

> GA4 조회에는 구글 클라우드 프로젝트 하나와 Analytics Data API 사용 설정이 필요해요.
> 1. https://console.cloud.google.com/projectcreate 에서 프로젝트를 만들거나 기존 프로젝트를 고릅니다.
> 2. 그 프로젝트에서 **Google Analytics Data API**와 **Google Analytics Admin API**를 "사용 설정"합니다.

그리고 질문 하나로 멈춘다.

> GCP 프로젝트 ID를 알려주세요. (구글 클라우드 콘솔 위쪽 프로젝트 선택기에 보이는 값입니다)

답을 받으면 그 **실제 ID가 박힌 완성된 명령**을 보여준다. 예를 들어 답이 `my-ga4-project-123`이라면:

```
gcloud config set project my-ga4-project-123
```

- 4-1과 같은 원칙이다. 꺾쇠나 빈 자리를 명령 안에 남기지 않고, **복사해서 바로 실행되는 명령**만 낸다.
- 명령을 보여준 뒤 "실행한 뒤 `/ecommerce-growth-discovery:setup`을 다시 실행해 주세요." 한 줄을 붙이고 멈춘다.

값이 있으면 "프로젝트: `{값}` ✓" 한 줄로 통과시키고 4단계로 간다.

---

## 4단계 — ADC(구글 인증) 확인

```
gcloud auth application-default print-access-token
```

**토큰 값을 화면에 절대 출력하지 않는다.** 성공/실패와 스코프 판정만 말한다.

### 4-1. 실패했을 때 — 로그인 명령 만들어 보여주기

먼저 cwd에 클라이언트 시크릿 파일이 있는지 본다: `Glob`으로 `client_secret*.json`.

**파일이 없으면** 아래 명령을 그대로 보여준다.

```
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform
```

**파일이 하나 있으면** 그 **실제 파일명**을 끝에 붙인 **완성된 명령**을 보여준다. 예를 들어 찾은 파일이 `client_secret_1234-abcd.apps.googleusercontent.com.json`이라면:

```
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform --client-id-file=client_secret_1234-abcd.apps.googleusercontent.com.json
```

**파일이 둘 이상이면** 번호를 매겨 파일명만 나열하고 "어느 파일로 로그인할까요?" 하나만 묻는다. 답을 받은 뒤 그 파일명을 붙인 완성 명령을 보여준다.

**이 단계에서 반드시 지킬 것**

- 꺾쇠 자리표시자를 명령 안에 남기지 않는다. 꺾쇠를 그대로 붙여넣으면 셸 리다이렉션 오류가 난다. **항상 실제 파일명이 박힌, 복사해서 바로 실행되는 명령**을 낸다.
- 파일명에 공백이 있으면 파일명 전체를 큰따옴표로 감싼 형태로 보여준다.
- 시크릿 파일을 `Read`로 열지 않는다. 파일명만 쓴다.
- `gcloud auth login`과 `gcloud auth application-default login`은 다른 명령이다. 위 명령을 **그대로** 실행해야 한다고 한 줄 덧붙인다.

안내를 붙이고 멈춘다: "브라우저에서 로그인을 마친 뒤 `/ecommerce-growth-discovery:setup`을 다시 실행해 주세요."

### 4-2. 성공했을 때 — 스코프 확인

스코프는 아래 **한 줄 그대로** 조회한다. 토큰은 `$(...)` 안에서 셸이 직접 받아 쓰므로, 4단계에서 본 토큰 값을 이 명령에 옮겨 적지 않는다.

```
curl -s "https://oauth2.googleapis.com/tokeninfo?access_token=$(gcloud auth application-default print-access-token)"
```

- 응답의 `scope` 필드에 `https://www.googleapis.com/auth/analytics.readonly`가 **포함돼 있으면 통과**다. "구글 인증: 확인됨 ✓" 한 줄만 적는다.
- **포함돼 있지 않으면** 스코프 없이 로그인된 상태다. 이 경우 오류 없이 조용히 빈 데이터가 나오므로 반드시 다시 로그인해야 한다. **4-1의 같은 명령**(시크릿 파일이 있으면 붙인 완성형)을 다시 보여주고 멈춘다.
- 토큰 값도, 응답 전문도 화면에 옮기지 않는다. `scope`에 무엇이 있는지 판정 결과만 말한다.
- 위 명령은 **글자 그대로** 낸다. `$(...)` 부분을 실제 토큰 문자열로 바꿔 쓰지 않는다.

---

## 5단계 — analytics-mcp 도구 확인

`rules.md` §0-2의 접미 탐색으로 **`analytics-mcp__get_account_summaries`** 도구를 찾아 호출한다(번들이면 `mcp__plugin_ecommerce-growth-discovery_analytics-mcp__get_account_summaries`, 직접 등록이면 `mcp__analytics-mcp__get_account_summaries`).

| 상황 | 대응 |
|---|---|
| 접미로 찾아도 도구가 목록에 없다 | 아래 안내 후 멈춤. 다른 이름을 추측해 호출하지 않는다. |
| 호출은 됐는데 권한·인증 오류 | 오류 첫 줄을 원문 그대로 적고 **4-1의 로그인 명령을 다시 보여주고 멈춘다.** |
| 계정 목록이 돌아옴 | 통과. 6단계로. |

도구가 없을 때 보여줄 안내:

> `analytics-mcp` 도구가 보이지 않아요. `/mcp`를 실행해 `analytics-mcp`가 목록에 있는지 확인해 주세요. 목록에 없으면 Claude를 완전히 껐다가 다시 켜고 `/ecommerce-growth-discovery:setup`을 다시 실행해 주세요.

---

## 6단계 — GA4 속성 고르기

5단계에서 받은 계정 요약으로 표를 만든다.

| 번호 | 계정 | 속성 | 속성 ID |
|---|---|---|---|
| 1 | … | … | … |

- 속성이 하나뿐이면 그 속성을 쓰겠다고 한 줄로 알리고 확인만 받는다.
- 속성이 없으면 "이 구글 계정으로 볼 수 있는 GA4 속성이 없어요. 속성 권한을 받은 계정으로 로그인을 다시 해 주세요." 하고 **4-1의 로그인 명령을 다시 보여주고 멈춘다.**

질문 하나로 멈춘다.

> 어느 속성을 볼까요? 번호로 알려주세요.

받은 번호의 **속성 ID(숫자만)**를 `ga4.property_id`에 넣는다.

---

## 7단계 — Meta 광고 계정 연결 (선택)

먼저 질문 하나로 묻는다.

> 광고 효율까지 보려면 Meta 광고 계정을 연결할 수 있어요. 연결할까요? 건너뛰어도 나머지는 그대로 됩니다.

- **건너뛰기** → `meta.enabled = false`, `meta.ad_account_id = ""`로 두고 8단계로.
- **연결** → 접미 **`meta-ads__ads_get_ad_accounts`**로 도구를 찾아 호출한다. `rules.md` §0-2의 Meta 공통 규칙을 지킨다 — **20자 영숫자 `client_conversation_id`**를 만들어 이 대화의 모든 Meta 호출에 같은 값을 쓴다.

| 상황 | 대응 |
|---|---|
| 도구가 목록에 없다 | "`meta-ads` 도구가 보이지 않아요. `/mcp`에서 확인해 주세요." → 멈춤 |
| 인증 오류 | 아래 안내 후 **멈춤** |
| 계정 목록이 돌아옴 | `is_queryable=true`인 계정만 표로 |

인증 오류일 때 보여줄 안내:

> `/mcp`를 실행해 `meta-ads`를 고르고 **Authenticate**로 브라우저 로그인을 마친 뒤, `/ecommerce-growth-discovery:setup`을 다시 실행해 주세요.

계정 표(**`is_queryable=false`인 계정은 목록에 아예 올리지 않는다**):

| 번호 | 계정 이름 | 계정 ID |
|---|---|---|
| 1 | … | … |

질문 하나로 멈춘다.

> 어느 광고 계정을 볼까요? 번호로 알려주세요.

받은 계정의 ID를 **`act_` 접두 없는 숫자만** `meta.ad_account_id`에 넣고 `meta.enabled = true`로 둔다. 조회 가능한 계정이 하나도 없으면 "지금 조회할 수 있는 광고 계정이 없어요. Meta는 사용 안 함으로 둘게요." 한 줄을 적고 `meta.enabled = false`로 8단계로 간다.

---

## 8단계 — 매출 지표와 나머지 설정

### 8-1. 매출 지표 고르기

접미 **`analytics-mcp__run_report`**로 도구를 찾아, 6단계에서 정한 속성에 대해 **최근 30일** 두 값을 **각 1행**으로 조회한다. 두 지표는 스코프가 달라 한 호출에 못 섞인다(`rules.md` §2).

- (a) `property_id: {ga4.property_id}` · `date_ranges: [{"start_date": "30daysAgo", "end_date": "yesterday"}]` · `dimensions: []` · `metrics: ["purchaseRevenue"]`
- (b) 같은 속성·같은 기간 · `dimensions: []` · `metrics: ["itemRevenue"]`

결과를 나란히 띄운다.

| 지표 | 최근 30일 값 |
|---|---|
| `purchaseRevenue` (구매 수익) | ₩N |
| `itemRevenue` (상품 수익) | ₩N |

두 값의 차이를 계산한다: 차이 = |a − b| ÷ (둘 중 큰 값) × 100.

- 차이가 **5% 미만**이면 표 아래에 한 줄 덧붙인다: "두 값이 거의 같아요. 기본값인 `purchaseRevenue`를 권합니다."
- 차이가 5% 이상이면 판단어 없이 사실만 적는다: "두 값이 N% 차이 납니다."
- 어느 쪽이 우리 몰의 실주문과 맞는지는 사용자만 안다. 스킬이 대신 고르지 않는다.

질문 하나로 멈춘다.

> 어느 쪽을 매출로 쓸까요? (`purchaseRevenue` / `itemRevenue`)

조회가 실패하면 오류 첫 줄을 원문 그대로 적고 5단계로 되돌린다.

### 8-2. 제외할 유입 — `exclude_filters`

질문 하나로 묻는다.

> 세션 수를 왜곡해서 빼고 싶은 유입이 있나요? (예: 특정 랜딩 페이지, 특정 리퍼럴 도메인) 없으면 "없음"이라고 답해 주세요.

- "없음"이면 `exclude_filters`를 **빈 배열**로 둔다.
- 답이 있으면 각 항목을 `{"field_name": …, "match_type": …, "value": …}`로 만든다. 흔한 매핑:

| 사용자가 말한 것 | `field_name` | `match_type` |
|---|---|---|
| 특정 랜딩 페이지 (경로만) | `landingPage` | `CONTAINS` |
| 특정 랜딩 페이지 (쿼리스트링 포함) | `landingPagePlusQueryString` | `CONTAINS` |
| 특정 리퍼럴 도메인 | `sessionSource` | `CONTAINS` |
| 특정 채널 그룹 | `sessionDefaultChannelGroup` | `EXACT` |

두 랜딩 페이지 필드의 차이: `landingPage`는 `/product/detail.html`처럼 **경로만** 보고, `landingPagePlusQueryString`은 `?cate_no=12`까지 **붙은 채로** 본다 — 사용자가 말한 값에 `?`가 없으면 `landingPage`를 쓴다.

`match_type`은 GA4가 받는 값만 쓴다 — `EXACT` · `BEGINS_WITH` · `ENDS_WITH` · `CONTAINS` · `FULL_REGEXP` · `PARTIAL_REGEXP`. 어느 필드인지 확실하지 않으면 추측해서 넣지 말고, 사용자가 말한 값을 그대로 `value`에 담고 위 표에서 가장 가까운 `field_name`을 쓴 뒤 무엇으로 저장했는지 한 줄로 알린다.

### 8-3. 주의 문구 — `data_notes`

질문 하나로 묻는다.

> 숫자를 볼 때마다 같이 띄울 주의 문구가 있나요? (예: 이미 알고 있는 계측 오류) 없으면 "없음"이라고 답해 주세요.

- "없음"이면 **빈 배열**로 둔다. "주의할 점 없음" 같은 문장을 지어내 넣지 않는다.
- 답이 있으면 **사용자가 쓴 문장 그대로** 배열에 담는다. 요약·의역하지 않는다.

### 8-4. 업종 — `industry`

질문 하나로 묻는다.

> 업종이 어느 쪽에 가깝나요? `fashion`(패션·주얼리) / `home`(리빙·홈) / `general`(그 외)

셋 중 하나가 아니면 `general`로 둔다.

### 8-5. 라벨 — `output.label`

질문 하나로 묻는다.

> 산출 파일 이름 뒤에 붙일 팀 내 구분 라벨이 필요하세요? 없으면 "없음"이라고 답해 주세요. (실명은 쓰지 않습니다)

- "없음"이면 빈 문자열. 답이 있으면 그 값을 쓰되 **실명은 넣지 않는다**(`rules.md` §9).

### 8-6. 몰 이름 — `store_name`

질문 하나로 묻는다.

> 표 제목에 쓸 스토어 이름은? (Enter면 "우리 몰")

- 비워서 답하면(엔터만) `"우리 몰"`을 쓴다. 답이 있으면 그 값을 그대로 쓴다.

---

## 9단계 — 설정 파일 저장과 연결 확인

### 9-1. `Write`로 저장

cwd에 `growth-discovery.config.json`을 아래 스키마 **그대로** 쓴다. 필드 이름·중첩 구조·기본값을 글자 하나 바꾸지 않는다. 묻지 않은 필드는 아래 기본값을 그대로 둔다.

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

채워 넣는 값은 이것뿐이다.

| 필드 | 어디서 |
|---|---|
| `store_name` | 8-6 |
| `industry` | 8-4 |
| `ga4.property_id` | 6단계 (숫자만) |
| `ga4.revenue_metric` | 8-1 |
| `ga4.exclude_filters` | 8-2 |
| `ga4.data_notes` | 8-3 |
| `meta.enabled` · `meta.ad_account_id` | 7단계 |
| `output.label` | 8-5 |

- `version`·`currency`·`ga4.date_range`·`output.dir`은 **기본값 그대로** 둔다.
- 저장한 뒤 한 줄로 알린다: "`growth-discovery.config.json`을 만들었어요. 조회 기간(`ga4.date_range`)은 기본값이니 바꾸고 싶으면 파일에서 직접 고치면 됩니다."
- 0단계에서 "연결만 확인"으로 들어온 경우에는 **저장하지 않고** 9-2로 바로 간다.

### 9-2. baseline 표 4행으로 연결 확인

접미 `analytics-mcp__run_report`로, 방금 저장한 config의 값(`ga4.property_id`·`ga4.date_range`·`ga4.exclude_filters`)을 그대로 써서 조회한다. `revenue_metric`이 `itemRevenue`면 `rules.md` §2대로 두 번 호출한다.

표는 **아래 4행만** 낸다.

| 지표 | 우리 몰 |
|---|---|
| 세션(트래픽) | N |
| 구매 건수 | N |
| 전환율(구매÷세션) | N% |
| 객단가(매출÷구매) | ₩N |

- 전환율 = 구매 ÷ 세션 × 100 · 객단가 = 매출 ÷ 구매
- 표 아래 한 줄로 조회 기간과 쓴 지표를 밝힌다: "조회 기간: `{start_date}` ~ `{end_date}` · 매출 = `{revenue_metric}`".
- `exclude_filters`를 적용했으면 무엇을 뺐는지도 한 줄 적는다(`rules.md` §3).
- **벤치마크 열을 만들지 않는다. 질문하지 않는다. 파일로 저장하지 않는다.** 이 표는 연결이 되는지 보는 용도다.
- `data_notes`가 비어 있지 않으면 표 아래에 각 항목을 **문자 그대로 한 줄씩** 인용 블록(`>`)으로 붙인다. 비어 있으면 아무것도 붙이지 않는다.

### 9-3. 마무리 한 줄

표까지 나왔으면 아래 한 줄로 끝낸다.

> 설정 확인 완료! 다음: /ecommerce-growth-discovery:explore baseline

### 9-4. 조회가 실패했을 때

표를 지어내지 않는다. **오류 첫 줄을 원문 그대로 한 줄** 적고, 되돌아갈 단계 번호를 한 줄 적는다. 토큰·자격증명이 섞인 줄은 옮기지 않는다.

| 오류 | 되돌아갈 곳 |
|---|---|
| 도구가 목록에 없음 | 5단계 |
| 권한·인증 오류 (`PERMISSION_DENIED`, `UNAUTHENTICATED` 등) | 4단계 |
| 속성 ID를 찾을 수 없음 (`NOT_FOUND`) | 6단계 |
| 지표·차원 조합 오류 (`INVALID_ARGUMENT`) | 8-1단계 |
| 그 밖 | 5단계 |

형식은 두 줄이다.

> 조회에 실패했어요. (오류: `오류 메시지 첫 줄 그대로`)
> N단계로 돌아가 다시 확인해 주세요.

---

## 톤

`rules.md` §5를 그대로 따른다.

- 한국어로 응답한다.
- 사용자를 "우리"로 부른다 — "우리 몰", "우리 숫자".
- 사용자가 옆길로 새면 진행 중인 단계로 부드럽게 되돌린다: "지금은 N단계예요. 다음으로 갈까요?"
- 판단어("낮다", "심각하다", "문제다")를 쓰지 않는다. 9-2의 표는 값만 띄운다.
