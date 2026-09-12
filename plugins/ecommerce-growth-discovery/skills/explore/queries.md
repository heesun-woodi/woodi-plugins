# `/ecommerce-growth-discovery:explore` 쿼리 스펙

각 서브커맨드에서 정확히 이 인자로 도구를 호출한다. 모든 인자는 GA4 Data API의 protobuf 필드명(snake_case)을 그대로 쓴다. 공통 규칙(설정 파일·기간·필터·매출)은 `${CLAUDE_PLUGIN_ROOT}/data/rules.md` 참조 — 변수가 없으면 이 파일 위치 기준 `../../data/rules.md`로 읽는다. 아래 표의 `dimension_filter`·`date_ranges`는 그 규칙을 그대로 반영한 것이다.

**도구 이름**: 이름을 하드코딩하지 말고 **접미(suffix)로 찾는다**(`rules.md` §0-2). analytics-mcp의 `run_report` — 플러그인 번들이면 `mcp__plugin_ecommerce-growth-discovery_analytics-mcp__run_report`, 사용자가 직접 등록했으면 `mcp__analytics-mcp__run_report`; **접미 `analytics-mcp__run_report`로 찾는다.** `run_funnel_report`는 접미 `analytics-mcp__run_funnel_report`, Meta 도구는 접미 `meta-ads__ads_get_ad_accounts` · `meta-ads__ads_get_field_context` · `meta-ads__ads_get_ad_entities`로 찾는다. 접미로 찾아도 도구가 없으면 다른 이름을 추측해 호출하지 않고 `rules.md` §6의 실패 응답으로 간다.

## 공통 치환 — 설정 파일에서 읽어 넣는 값

아래 표의 `{config...}` 자리는 cwd의 `growth-discovery.config.json` 값으로 치환한다. config가 없으면 아무 호출도 하지 않는다(`rules.md` §0-1).

| 자리 | 넣는 값 |
|---|---|
| `property_id` | `{config.ga4.property_id}` — 숫자 문자열 그대로. 비어 있으면 호출하지 않고 setup 안내로 멈춘다 |
| `date_ranges` | `[{"start_date": "{config.ga4.date_range.start_date}", "end_date": "{config.ga4.date_range.end_date}"}]` |
| `dimension_filter` | `{config.ga4.exclude_filters[]}`를 `rules.md` §3의 변환 규칙(`and_group.expressions[].not_expression`)으로 바꾼 값. **배열이 비어 있으면 `dimension_filter` 인자를 아예 넘기지 않는다** |
| 매출 metric | `{config.ga4.revenue_metric}` — `purchaseRevenue`(기본) 또는 `itemRevenue`. 분기 규칙은 `rules.md` §2 |

- 모든 호출의 `date_ranges`는 한 세션 안에서 **동일해야 한다.** 서브커맨드마다 기간을 바꾸지 않는다.
- GA4 Data API는 상대 날짜 문자열(`90daysAgo`·`yesterday`)과 고정 날짜(`"2026-06-11"` 형식)를 둘 다 받는다. config 값을 런타임 계산 없이 그대로 넘긴다.

**⚠️ API 제약 1**: `itemRevenue`(item 스코프)와 `sessions`·`ecommercePurchases`(session/event 스코프)를 **한 호출에 같이 넣으면 GA4가 400으로 거부**한다("dimensions & metrics are incompatible"). 따라서 `revenue_metric`이 `itemRevenue`이고 매출이 필요한 단계는 **같은 dimensions·같은 `dimension_filter`·같은 `date_ranges`로 두 번 호출**한다 — (a) `sessions`+`ecommercePurchases`, (b) `itemRevenue`. 두 결과를 dimension 값으로 합쳐 하나의 표로 만든다. 한쪽에만 있는 dimension 값은 다른 쪽을 `0`이 아니라 `—`로 둔다. `revenue_metric`이 `purchaseRevenue`면 한 호출로 끝난다.

**⚠️ API 제약 2**: `run_funnel_report`는 `dimension_filter` 인자를 지원하지 않는다. `exclude_filters`를 적용하지 못하므로 필터 없이 그대로 호출하고, 결과를 보여줄 때 "사용자 기준"(그리고 `exclude_filters[]`가 비어 있지 않으면 "위 제외 필터가 적용되지 않았습니다")을 반드시 함께 말한다. 그래서 벤치마크 대조는 퍼널 표가 아니라 **세션 기준 호출(D-2)** 로 한다.

---

## §1. `baseline`

**도구**: 접미 `analytics-mcp__run_report`

### `revenue_metric`이 `purchaseRevenue`(기본)일 때 — **한 번 호출**

| 인자 | 값 |
|---|---|
| `property_id` | `{config.ga4.property_id}` |
| `date_ranges` | 공통 치환 |
| `dimensions` | `[]` (전체 합계만 필요) |
| `metrics` | `["sessions", "ecommercePurchases", "purchaseRevenue"]` |
| `dimension_filter` | 공통 치환 (비면 생략) |
| `order_bys` | 생략 |
| `limit` | 생략 (합계 1행) |

### `revenue_metric`이 `itemRevenue`일 때 — **두 번 호출**

| 인자 | 호출 (a) | 호출 (b) |
|---|---|---|
| `property_id` | `{config.ga4.property_id}` | 동일 |
| `date_ranges` | 공통 치환 | 동일 |
| `dimensions` | `[]` | `[]` |
| `metrics` | `["sessions", "ecommercePurchases"]` | `["itemRevenue"]` |
| `dimension_filter` | 공통 치환 (비면 생략) | 동일 |
| `order_bys` | 생략 | 생략 |
| `limit` | 생략 | 생략 |

**계산**:
- 전환율(구매÷세션) = `ecommercePurchases` ÷ `sessions` × 100
- 객단가(매출÷구매) = `{revenue_metric}` ÷ `ecommercePurchases`

**표 헤더**: `| 지표 | 우리 몰 | 벤치마크 |` — 행: 세션(트래픽) / 구매 건수 / 전환율(구매÷세션) / 객단가(매출÷구매)

---

## §2. `traffic`

### 2-(1) 채널별 세션·구매 → 구성표 (`## B`)

**도구**: 접미 `analytics-mcp__run_report`

| 인자 | 값 |
|---|---|
| `property_id` | `{config.ga4.property_id}` |
| `date_ranges` | 공통 치환 |
| `dimensions` | `["sessionDefaultChannelGroup"]` |
| `metrics` | `["sessions", "ecommercePurchases", "addToCarts"]` — `revenue_metric`이 `purchaseRevenue`이고 같은 세션에서 `channel-cvr`까지 갈 예정이면 `"purchaseRevenue"`를 함께 넣어도 된다 |
| `dimension_filter` | 공통 치환 (비면 생략) |
| `order_bys` | `[{"metric": {"metric_name": "sessions"}, "desc": true}]` |
| `limit` | 생략 (채널 수가 적음) |

#### 채널 매핑(고정)

원 채널값을 아래 6개 구분으로 접는다. 이 표 밖의 값은 전부 `미분류`로 보낸다.

| 구분 | `sessionDefaultChannelGroup` 값 |
|---|---|
| Paid | Paid Social · Paid Search · Paid Shopping · Paid Video · Paid Other · Display · Cross-network · Affiliates |
| Direct | Direct |
| Owned | Email · SMS · Mobile Push Notifications · Organic Social |
| Referral | Referral · Organic Video · Organic Shopping |
| Organic Search | Organic Search |
| 미분류 | Unassigned 및 매핑 밖 값 |

- Owned 각주(문자 그대로): "Organic Social은 Owned로 접었습니다."
- 미분류 각주(문자 그대로): "미분류는 UTM이 없거나 GA4가 분류 못 한 유입입니다."
- 이 두 줄 말고 태깅 상태에 대한 주의를 덧붙이지 않는다. 우리 몰 사정은 `config.ga4.data_notes[]`에 있을 때만 그 문구를 문자 그대로 낸다(`rules.md` §2-1).

#### 소계 계산 규칙

- 구분별 세션 = 그 구분에 매핑된 모든 채널의 `sessions` 합. 구매도 같은 방식.
- 세션 비중 = 구분 세션 ÷ **합계 세션** × 100. 분모는 항상 합계(미분류 포함).
- 전환율 = 구분 구매 ÷ 구분 세션 × 100.
- **합계 행은 미분류를 포함한다.**
- **non-paid 소계(Direct+Owned+Referral+Organic Search)에는 미분류를 넣지 않는다.**
- 값이 0인 구분도 행을 지우지 않는다 — 0으로 표시한다.
- 상세 표(`| 구분 | 채널 | 세션 | 세션 비중 |`)는 접기 전 원 채널값을 구분별로 묶어서 그대로 나열한다.

#### 담기율 비교표 계산 규칙 (`## B-2`)

같은 호출 결과를 **3행**으로 다시 접는다. 행 고정: `Paid` / `Non-paid` / `미분류`.

- `Paid` = 채널 매핑의 Paid 구분 합. `Non-paid` = Direct + Owned + Referral + Organic Search 합(미분류 제외). `미분류` = Unassigned 및 매핑 밖 값.
- 세션 비중 = 구분 세션 ÷ **합계 세션**(미분류 포함) × 100.
- 장바구니 담기 = 그 구분에 속한 채널의 `addToCarts` 합.
- 담기율 = 구분 `addToCarts` ÷ 구분 `sessions` × 100.
- 전환율 = 구분 `ecommercePurchases` ÷ 구분 `sessions` × 100.
- 표 아래 한 줄: `Non-paid ÷ Paid = N.N배` — Non-paid 담기율 ÷ Paid 담기율, 소수 첫째 자리까지. Paid 담기율이 0이면 `—`.

**표 헤더**: 구성 요약 `| 구분 | 세션 | 세션 비중 | 구매 | 전환율 |` (행 고정: Paid / Direct / Owned / Referral / Organic Search / 미분류 / non-paid 소계 / 합계) + 상세 `| 구분 | 채널 | 세션 | 세션 비중 |` + 담기율 비교 `| 구분 | 세션 | 세션 비중 | 장바구니 담기 | 담기율 | 구매 | 전환율 |` (행 고정: Paid / Non-paid / 미분류)

### 2-(2) 신규 vs 재방문 (`## C`)

**도구**: 접미 `analytics-mcp__run_report`

| 인자 | 값 |
|---|---|
| `property_id` | `{config.ga4.property_id}` |
| `date_ranges` | 공통 치환 |
| `dimensions` | `["newVsReturning"]` |
| `metrics` | `["sessions", "ecommercePurchases", "addToCarts"]` (2-(1)과 동일. `## C` 표는 세션·구매만 쓴다) |
| `dimension_filter` | 공통 치환 (비면 생략) |
| `order_bys` | 생략 |
| `limit` | 생략 (값이 2행뿐) |

**계산**: 세그먼트별 세션 비중 = 세그먼트 세션 ÷ 두 세그먼트 합 × 100 · 전환율 = `ecommercePurchases` ÷ `sessions` × 100.

**표 헤더**: `| 구분 | 세션 | 세션 비중 | 구매 | 전환율 | 벤치마크 |`

---

## §3. `funnel`

### D-1. critical path 퍼널 (기본)

**도구**: 접미 `analytics-mcp__run_funnel_report`

| 인자 | 값 |
|---|---|
| `property_id` | `{config.ga4.property_id}` |
| `date_ranges` | 공통 치환 |
| `funnel_steps` | `[{"name": "세션 시작", "event": "session_start"}, {"name": "상품 조회", "event": "view_item"}, {"name": "장바구니 담기", "event": "add_to_cart"}, {"name": "결제 시작", "event": "begin_checkout"}]` |
| `funnel_next_action` | `{"next_action_dimension": "eventName", "limit": 5}` |
| `dimension_filter` | **지원 안 함 — 넣지 않는다** |

> **구매는 퍼널에 넣지 않는다.** GA4 `purchase`는 태그 중복 기록으로 실주문보다 많게 셀 수 있어(측정 점검 D-3에서 확인) 퍼널 마지막 칸에 두면 마무리가 실제보다 좋아 보인다. 구매 전환율은 D-2 세션 기준 표에만 둔다.

### D-1'. 대안 — `view_item` 시작 (3단계)

**D-1의 `session_start` 단계가 거부되면 이 대안으로 바꾼다.** 나머지 인자는 D-1과 같다.

| 인자 | 값 |
|---|---|
| `funnel_steps` | `[{"name": "상품 조회", "event": "view_item"}, {"name": "장바구니 담기", "event": "add_to_cart"}, {"name": "결제 시작", "event": "begin_checkout"}]` |

대안을 쓰면 퍼널 표는 4행이 아니라 3행이 되고, `세션 시작(session_start)` 행은 만들지 않는다.

**계산(D-1·D-1' 공통)**: 각 단계 사용자 수 → 직전 단계 대비 도달률(%) → 이탈 사용자 = 직전 단계 사용자 − 해당 단계 사용자 → 도달률이 가장 낮은 구간을 최대 이탈 지점으로 표시.

### D-2. 세션 기준 지표 (기본) — 벤치마크와 분모 일치

**도구**: 접미 `analytics-mcp__run_report`

| 인자 | 값 |
|---|---|
| `property_id` | `{config.ga4.property_id}` |
| `date_ranges` | 공통 치환 |
| `dimensions` | `[]` |
| `metrics` | `["sessions", "addToCarts", "checkouts", "ecommercePurchases"]` |
| `dimension_filter` | 공통 치환 (비면 생략) |
| `order_bys` | 생략 |
| `limit` | 생략 (합계 1행) |

### D-2'. 대안 — `eventCount` × `eventName` 필터

**D-2의 `addToCarts`·`checkouts` 메트릭이 거부되면 이 대안으로 바꾼다.** `sessions`·`ecommercePurchases`는 D-2 그대로 받고(메트릭 2개만), 장바구니·결제시작은 아래 호출로 따로 받는다.

| 인자 | 값 |
|---|---|
| `property_id` | `{config.ga4.property_id}` |
| `date_ranges` | 공통 치환 |
| `dimensions` | `["eventName"]` |
| `metrics` | `["eventCount"]` |
| `dimension_filter` | 공통 치환의 `and_group.expressions`에 아래 표현식을 **하나 더 추가**한 것. `exclude_filters`가 비어 있으면 아래 표현식 하나만 넣은 `and_group`을 만든다 |
| `order_bys` | 생략 |
| `limit` | 생략 |

추가할 표현식:

```json
{"filter": {"field_name": "eventName", "in_list_filter": {"values": ["add_to_cart", "begin_checkout"]}}}
```

결과에서 `add_to_cart` 행의 `eventCount` → 장바구니, `begin_checkout` 행의 `eventCount` → 결제 시작으로 쓴다. 이때는 **이벤트 수 기준**이므로 표 아래에 "이 두 값은 세션 수가 아니라 이벤트 수입니다"를 한 줄 붙인다.

D-2'를 쓸 때는 **장바구니 담기율·결제 시작율의 벤치마크 칸을 `—`로 두고 대조하지 않는다**(분모가 이벤트 수라 세션 기준 벤치마크와 맞지 않는다 — `rules.md` §7 "분모가 다른 값을 나란히 놓지 않는다"). 구매 전환율은 `ecommercePurchases` ÷ `sessions` 그대로이므로 벤치마크를 채운다.

### D-3. 측정 점검 — 이벤트 수 ÷ 사용자 수

세션 기준 비율이 태그 중복 기록으로 부풀려졌는지 보는 호출이다. 한 번만 호출한다.

| 인자 | 값 |
|---|---|
| `property_id` | `{config.ga4.property_id}` |
| `date_ranges` | 공통 치환 |
| `dimensions` | `["eventName"]` |
| `metrics` | `["eventCount", "totalUsers"]` |
| `dimension_filter` | 공통 치환 **and** `eventName` `in_list_filter` `["view_item","add_to_cart","begin_checkout","purchase","view_item_list","add_shipping_info","add_payment_info"]` |

- **측정 점검 표에는 앞 4개만** 넣는다 — `view_item` · `add_to_cart` · `begin_checkout` · `purchase`.
- `건/사용자` = `eventCount` ÷ `totalUsers`, 소수 첫째 자리까지. 이 값이 2.0을 넘는 이벤트가 분자인 세션 기준 행은 벤치마크 대조에서 뺀다(SKILL.md §5).
- 뒤 3개(`view_item_list` · `add_shipping_info` · `add_payment_info`)는 표에 넣지 않고 **"측정되지 않는 구간 안내"(SKILL.md §5)의 조건 판정에만** 쓴다. 행이 없거나 `eventCount`가 0이면 해당 안내 줄을 붙인다.

**계산(D-2·D-2' 공통)**:
- 장바구니 담기율(장바구니÷세션) = `addToCarts` ÷ `sessions` × 100
- 결제 시작율(결제시작÷세션) = `checkouts` ÷ `sessions` × 100
- 구매 전환율(구매÷세션) = `ecommercePurchases` ÷ `sessions` × 100

**표 헤더**: 퍼널 `| 단계 | 사용자 | 직전 단계 대비 도달률 | 이탈 사용자 |` (4행) + 세션 기준 `| 지표 | 우리 몰 | 벤치마크 |` (행: 장바구니 담기율(장바구니÷세션) / 결제 시작율(결제시작÷세션) / 구매 전환율(구매÷세션)) + 측정 점검 `| 이벤트 | 이벤트 수 | 사용자 | 건/사용자 |` (4행)

---

## §4. `channel-cvr`

### 4-(1) 채널별 세션·구매

**같은 세션에서 방금 §2-(1)을 호출했을 때만** 재호출하지 않고 그 값을 재사용한다.
저장 파일에서 읽어 오는 경우에는 저장된 `## B` 상세 표 헤더가 `| 구분 | 채널 | 세션 | 세션 비중 |`이라 **채널별 구매 값이 없으므로 §2-(1)을 다시 호출한다.** `## B`가 파일에 아예 없을 때도 §2-(1) 호출을 그대로 다시 실행한다.

### 4-(2) 채널별 매출

`revenue_metric`이 `purchaseRevenue`면 §2-(1) 호출의 `metrics`에 `"purchaseRevenue"`를 함께 넣어 한 번에 받는다. `itemRevenue`면 아래 호출을 **따로** 한다(API 제약 1).

**도구**: 접미 `analytics-mcp__run_report`

| 인자 | 값 |
|---|---|
| `property_id` | `{config.ga4.property_id}` |
| `date_ranges` | 공통 치환 |
| `dimensions` | `["sessionDefaultChannelGroup"]` |
| `metrics` | `["itemRevenue"]` |
| `dimension_filter` | 공통 치환 (비면 생략) |
| `order_bys` | `[{"metric": {"metric_name": "itemRevenue"}, "desc": true}]` |
| `limit` | 생략 |

**병합**: 4-(1)의 행을 최종 표의 행으로 쓰고, 채널명 키로 4-(2)의 매출을 붙인다. 4-(2)에 없는 채널은 매출 칸을 `—`로 둔다. 4-(2) 결과로 새 행을 만들지 않는다.

**계산**: 세션 비중 = 채널 세션 ÷ 전체 세션 × 100 · 구매 비중 = 채널 구매 ÷ 전체 구매 × 100 · 전환율 = 채널 구매 ÷ 채널 세션 × 100. **세션 내림차순 정렬.**

**표 헤더**: `| 채널 | 세션 | 세션 비중 | 구매 | 구매 비중 | 전환율 | 매출 |`

### 4-(3) 광고 효율

"우리" 값은 `rules.md` §8의 순서로 채운다 — **1순위 Meta MCP** → **2순위 cwd `data/ads.csv`** → **3순위 둘 다 없음**. 어느 분기든 **플랫폼별 합계끼리만 비교하고, 캠페인 단위 조인은 하지 않는다**(GA4 캠페인명과 광고 플랫폼 캠페인명이 일치한다는 보장이 없다).

#### 1순위 — Meta MCP (`config.meta.enabled`가 `true`이고 `config.meta.ad_account_id`가 있을 때)

**Meta 호출 공통 규칙**(`rules.md` §0-2): 모든 호출에 **20자 영숫자 `client_conversation_id`**가 필수이고, 한 대화 안에서는 같은 값을 재사용한다. `ad_account_id`는 **`act_` 접두 없는 숫자**만 넣는다(`act_1234567890` ❌ / `1234567890` ✅).

**흐름 — 세 단계, 마지막 호출은 1회.**

**(가) 계정 조회 가능 여부 확인** — 접미 `meta-ads__ads_get_ad_accounts`

- 결과에서 `config.meta.ad_account_id`와 같은 `ad_account_id` 행을 찾는다.
- 그 행의 **`is_queryable`이 `false`면 조회하지 않는다.** `not_queryable_reason`을 한 줄로 옮기고 2순위(CSV)로, 그것도 없으면 3순위로 간다.
- 목록에 그 계정이 없으면 "설정에 적힌 광고 계정이 목록에 없어요" 한 줄 + `/ecommerce-growth-discovery:setup` 안내 후 광고 표만 3순위로 낸다.

**(나) 필드 canonical 이름 확인** — 접미 `meta-ads__ads_get_field_context`

필드명을 추측하지 않는다. 아래 6개를 `field_names`로 넘겨 **canonical `name`을 확인한 뒤** (다)에 쓴다.

| 우리가 필요한 값 | canonical `name` (2026-09 실호출 확인) | 받는 별칭 | `display_name` |
|---|---|---|---|
| 광고비 | `amount_spent` | `spend` | amount spent |
| 노출 | `impressions` | — | impressions |
| 링크 클릭 | `link_click` | `link_clicks` · `actions:link_click` | link clicks |
| 장바구니 담기 | `omni_add_to_cart` | `adds_to_cart` | adds to cart |
| 구매 | `omni_purchase` | `purchases` · `actions:omni_purchase` | purchases |
| 구매 전환 가치 | `omni_purchase_values` | `purchases_conversion_value` | purchases conversion value |

- 위 여섯은 전부 `levels`에 `ad_account`를 포함한다(확인됨).
- `ads_get_field_context`가 위와 다른 이름을 돌려주면 **돌려준 이름을 따른다.** 이 표는 확인 결과이지 고정값이 아니다.
- `unknown_fields`에 들어간 이름은 쓰지 않는다. 예를 들어 `inline_link_clicks` · `actions` · `action_values` · `add_to_cart` · `purchase_value`는 이 서버에서 **해석되지 않는다.**
- 전체 클릭 수가 필요하면 `clicks`(display: clicks (all))를 쓴다. `ctr`·`cpc`는 **전체 클릭 기준**이라 우리 계산식(링크 클릭 기준)과 분모가 다르다 — 쓰지 않고 아래 계산식으로 직접 구한다.

**(다) 수치 1회 조회** — 접미 `meta-ads__ads_get_ad_entities`

| 인자 | 값 |
|---|---|
| `ad_account_id` | `{config.meta.ad_account_id}` (`act_` 없는 숫자) |
| `level` | `"ad_account"` |
| `fields` | (나)에서 확인한 6개 canonical 이름 — 예: `["amount_spent","impressions","link_click","omni_add_to_cart","omni_purchase","omni_purchase_values"]` |
| `time_range` | `'{"since":"{config.ga4.date_range.start_date}","until":"{config.ga4.date_range.end_date}"}'` — **JSON 문자열** 한 개. `YYYY-MM-DD` 두 개가 필요하다. 아래 "기간 규칙"의 고정 날짜 분기에서만 넣는다 |
| `client_conversation_id` | 20자 영숫자, 대화 내 동일 값 |
| `date_preset` | 아래 "기간 규칙"의 상대 날짜 분기에서만 넣는다 |

- `level: "ad_account"`는 **`filtering`·`sort`를 지원하지 않는다.** 넣지 않는다.
- 기간은 `config.ga4.date_range`와 **같은 기간**을 쓴다. 광고 기간과 GA4 기간이 다르면 비교가 깨진다.
- **기간 규칙 — `time_range`와 `date_preset` 중 하나만 보낸다**(둘을 함께 보내면 거부된다).
  - `config.ga4.date_range`가 **상대 날짜**(`NdaysAgo`·`yesterday`)면 같은 길이의 **`date_preset`**을 쓰고 `time_range`는 **생략한다** — `90daysAgo`→`last_90d` · `30daysAgo`→`last_30d` · `7daysAgo`→`last_7d`. 대응되는 preset이 없으면 GA4 기간을 `YYYY-MM-DD`로 환산해 `time_range`에 넣고 `date_preset`을 생략한다.
  - **고정 날짜**(`YYYY-MM-DD`)면 **`time_range`만** 보내고 `date_preset`은 **생략한다.**
  - 어느 쪽을 썼는지 표 아래 한 줄로 밝힌다(예: "광고 기간은 `last_90d`로 맞췄습니다" / "광고 기간은 `{start_date}`~`{end_date}`로 맞췄습니다").
- 응답에 특정 지표가 없으면(해당 기간에 집행이 없었던 경우 등) 그 칸을 `0`이 아니라 `—`로 둔다.
- 호출이 실패하면 **GA4 표는 그대로 진행하고** 광고 표만 2순위 → 3순위로 내린다(`rules.md` §6).

#### 2순위 — cwd의 `data/ads.csv`

cwd 기준 `data/ads.csv` 한 곳만 본다. 플러그인 안을 뒤지지 않는다.

**헤더(문자 그대로)**:

```
platform,export_date,date_range,campaign_id,campaign_name,spend,impressions,clicks,link_clicks,add_to_cart,purchases,purchase_value
```

| 컬럼 | 설명 |
|---|---|
| `platform` | `meta` 또는 `google` **두 값만** 쓴다. 다른 값은 읽지 않는다 |
| `export_date` | export한 날짜 (`YYYY-MM-DD`) |
| `date_range` | 조회 기간. `config.ga4.date_range`와 다르면 표 아래 한 줄로 그 사실을 밝힌다 |
| `campaign_id` | 플랫폼 캠페인 ID. 행 구분용이며 **GA4와 조인하지 않는다** |
| `campaign_name` | 플랫폼 캠페인 이름. 표에 띄우지 않는다 |
| `spend` | 광고비 (부가세 제외 기준으로 통일) |
| `impressions` | 노출 수 |
| `clicks` | 전체 클릭 수 (플랫폼 기본 클릭) |
| `link_clicks` | 링크 클릭 수 — **CTR·CPC 계산에는 이 값을 쓴다** |
| `add_to_cart` | 플랫폼이 집계한 장바구니 담기 전환 수 |
| `purchases` | 플랫폼이 집계한 구매 전환 수 |
| `purchase_value` | 플랫폼이 집계한 구매 전환 가치 |

- 한 행 = 한 플랫폼의 한 캠페인. 플랫폼별로 여러 행이 들어와도 된다. `platform`별로 합계를 낸 뒤 그 합계끼리 비교한다.
- 값이 없는 칸은 비어 있다. 0으로 채우지 않고 `—`로 표시한다.
- `#`로 시작하는 행은 주석이므로 데이터 행으로 세지 않는다.
- 플랫폼 리포트에서 만들 때의 컬럼 대응 — Meta Ads Manager: `spend`=Amount spent · `impressions`=Impressions · `clicks`=Clicks (all) · `link_clicks`=Link clicks · `add_to_cart`=Adds to cart(웹사이트 전환 기준) · `purchases`=Purchases · `purchase_value`=Purchases conversion value. Google Ads: `spend`=Cost · `impressions`=Impr. · `clicks`=`link_clicks`=Clicks(링크 클릭 구분이 없어 같은 값) · `add_to_cart`/`purchases`=Conversions 중 해당 전환 액션만 분리 · `purchase_value`=Conv. value 중 구매 전환분. 두 플랫폼 export는 한 파일로 이어 붙인다(헤더는 한 번만).

#### 3순위 — Meta도 CSV도 없을 때

"우리" 두 열을 모두 `—`로 두고 벤치마크 열만 채운 뒤 한 줄 붙인다: "우리 숫자는 광고 계정에서 확인해 보세요." **없는 숫자를 만들지 않는다.**

#### 계산식(문자 그대로 — 세 분기 공통)

`spend`·`impressions`·`link_clicks`·`add_to_cart`·`purchases`·`purchase_value` 자리에는 1순위면 (나)의 canonical 필드값(`amount_spent`·`impressions`·`link_click`·`omni_add_to_cart`·`omni_purchase`·`omni_purchase_values`), 2순위면 CSV의 같은 이름 컬럼 합계를 넣는다.

| 지표 | 계산식 |
|---|---|
| CTR | `link_clicks` ÷ `impressions` |
| CPC | `spend` ÷ `link_clicks` |
| 장바구니당 비용 | `spend` ÷ `add_to_cart` |
| CPA(플랫폼) | `spend` ÷ `purchases` |
| CPA(GA4) | `spend` ÷ §E Paid 구매 합 |
| ROAS(플랫폼) | `purchase_value` ÷ `spend` |
| ROAS(GA4) | §E Paid 매출 ÷ `spend` |

- `노출`·`클릭`·`광고비`·`장바구니`·`구매`는 플랫폼 값을 그대로 쓴다.
- "우리(광고 플랫폼)" 열은 플랫폼 값과 CTR·CPC·장바구니당 비용·CPA(플랫폼)·ROAS(플랫폼)를 채운다.
- "우리(GA4 기준)" 열은 CPA(GA4)·ROAS(GA4)와 §E Paid 구매 합만 채우고 나머지는 `—`.
- §E Paid = §2-(1) 채널 매핑의 **Paid 구분 합계**이며, `## E` 표 맨 아래 고정 행 `Paid 소계`(세션 · 세션 비중 · 구매 · 전환율 · 매출)에서 읽는다.
- 계산에 필요한 값이 비어 있으면 그 지표 칸은 `—`. 값을 지어내지 않는다.
- 플랫폼 기준 값과 GA4 기준 값은 어트리뷰션이 달라 다르게 나오는 게 정상이다. **둘 다 적고**, 어느 쪽이 맞다고 판정하지 않는다.

#### 벤치마크 열 ↔ `benchmarks.md` §8 행 대응표

광고 효율 표의 `벤치마크` 칸은 `${CLAUDE_PLUGIN_ROOT}/data/benchmarks.md` **§8 광고 효율(Meta 유료광고)** 표에서 아래 행의 값을 그대로 옮긴다. **값은 여기 적지 않는다 — 읽을 위치만 지정한다.** 대응 행이 없거나 그 행의 값이 "없음"인 지표는 칸을 `—`로 두고 지어내지 않는다.

| 광고 효율 표 행 | §8에서 읽는 행 | 비고 |
|---|---|---|
| 노출 | (없음) | `—` |
| 클릭 | (없음) | `—` |
| CTR | `CTR (업종별)` 행에서 `config.industry`의 1차 대조 값 | 1차 대조 값은 `benchmarks.md` 상단 "「industry」별 1차 대조 행" 표의 `Meta CTR (§8)` 줄을 따른다. 폭이 필요하면 `CTR`(DTC 이커머스) 행을 함께 적는다 |
| CPC | `CPC (업종별)` 행에서 `config.industry`의 1차 대조 값 | 같은 표의 `Meta CPC (§8)` 줄. 폭이 필요하면 `CPC`(DTC 이커머스) 행을 함께 적는다 |
| 광고비 | (없음) | `—` |
| 장바구니 | (없음) | `—` |
| 장바구니당 비용 | `장바구니당 비용` 행 (값이 "없음") | 칸은 `—` |
| 구매 | (없음) | `—` |
| 구매당 비용(CPA) | `CPA (구매당 비용)` 행 (DTC 이커머스) | |
| ROAS | `구매 ROAS` 행에서 `config.industry`의 1차 대조 값 | 같은 표의 `Meta ROAS (§8)` 줄. 플랫폼 어트리뷰션 기준 값이다 |

- §8은 달러 기준 값이므로 `config.currency`로 환산하지 않는다. 값을 그대로 적고 통화 표기도 그대로 둔다.
- §8 표의 `비고`·해석 문장은 사용자에게 그대로 읽어 주지 않는다(값만 — `rules.md` §7).

**표 헤더**: `| 지표 | 우리(광고 플랫폼) | 우리(GA4 기준) | 벤치마크 |` (행: 노출 / 클릭 / CTR / CPC / 광고비 / 장바구니 / 장바구니당 비용 / 구매 / 구매당 비용(CPA) / ROAS)

---

## §5. `areas`

**GA4 호출 없음.** 산출 파일(`config.output.dir`의 `explore-findings.md` — `label`이 있으면 `explore-findings-{label}.md`)의 `## A` · `## B` · `## B-2` · `## C` · `## D` · `## E`를 읽어서 **3행** 표를 만든다. 파일 탐색 순서는 cwd → `config.output.dir` 두 곳만이다(`rules.md` §10). 파일에 없는 값은 `—`로 두고 **지어내지 않는다.**

**표 헤더**: `| # | 문제영역 | 근거 숫자 | 벤치마크·대조 | 걸린 규모 | /ecommerce-growth-discovery:screen에서 볼 화면 |`

**행별 근거 섹션(고정)**:

| # | 근거 숫자를 읽는 섹션 |
|---|---|
| (a) | `## D` 퍼널 |
| (b) | `## B-2` 담기율 비교 + `## E` 채널 전환율 |
| (c) | `## B` non-paid 비중 + `## B-2` 담기율 |

---

## 참고

- 모든 `metrics`/`dimensions` 값은 GA4 Data API 표준 이름이다. 실제 호출 시 도구가 이름을 거부하면(스키마 변경 가능성) 대안 쿼리(D-1' / D-2')로 전환하고, 그마저 안 되면 `rules.md` §6의 실패 응답으로 멈춘다. **저장본 CSV는 없다.**
- `run_report`의 인자 이름(`property_id`, `date_ranges`, `dimensions`, `metrics`, `dimension_filter`, `order_bys`, `limit`)과 `run_funnel_report`의 인자 이름(`property_id`, `funnel_steps`, `date_ranges`, `funnel_next_action`)은 이 문서 작성 시점 기준이며, 실제 도구 스키마와 다르면 도구가 요구하는 스키마를 우선한다. Meta 쪽도 같다 — `ads_get_field_context`가 돌려준 이름과 `ads_get_ad_entities`의 실제 인자 스키마를 우선한다.
