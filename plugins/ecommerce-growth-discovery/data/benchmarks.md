# 이커머스 벤치마크 — GA4 대조용

작성일: 2026-09-03 · 용도: 자기 GA4 숫자를 옆에 놓고 비교하는 기준표
대상 맥락: 중소 D2C 자사몰, 유료 소셜광고 비중이 있는 이커머스

> **이 파일의 값은 출처 링크의 공개 자료를 옮긴 것이다.** 값만 옮겨 쓰고, 해석은 `rules.md` §7의 규칙을 따른다.

## 이 문서를 읽는 법 (3줄)

1. **벤치마크는 방향 감각용이지 정답이 아니다.** 같은 "전환율"도 출처마다 1.3%부터 2.7%까지 나온다. 우리 숫자가 그 띠 안에 있느냐, 완전히 밖에 있느냐만 본다.
2. **내부 비교(채널 간·기간 간·기기 간)가 외부 비교보다 훨씬 중요하다.** "우리 paid social이 organic의 1/3"은 외부 벤치마크가 없어도 그 자체로 진단이 된다.
3. **출처마다 분모·정의가 다르다. ±로 봐라.** 세션 기준 vs 사용자 기준 vs PV 기준, Shopify 중소몰 vs 글로벌 대형몰, 12개월 평균 vs 특정 분기. 표의 "비고"에 정의를 적어두었다.

### 출처 신뢰도 표기
- **[A]** 자체 트래픽 데이터를 가진 1차 벤더 (Dynamic Yield, Littledata, Contentsquare, IRP Commerce, Klaviyo, Similarweb, Statista, 통계청, Top Growth Marketing, Superads, LocaliQ/WordStream)
- **[B]** 1차 연구를 모은 메타분석 (Baymard)
- **[C]** 2차 집계·블로그, **또는 1차 데이터이나 표본 수·수집 기간이 공개되지 않은 것**. 원 출처를 따라갈 수 있으면 표에 그 경로를 적었고, 원 데이터가 벤더 비공개인 경우(예: Lebesgue)는 비고에 그렇게 적었다
- **출처 미확인**: 수치는 돌아다니지만 원 데이터를 못 찾음. 인용 금지, "그런 말이 있다" 수준

### `industry`별 1차 대조 행

`growth-discovery.config.json`의 `industry` 값으로 **먼저 볼 행**이 정해진다(`rules.md` §1-2). 아래 표에 없는 지표는 세 값 모두 같은 행을 본다.

| 지표 | `fashion` | `home` | `general` |
|---|---|---|---|
| 전체 CVR (§1) | 패션 Shopify **1.9%** (Littledata) · 띠 1.5~2.8% | Home & Furniture **1.22%** (Dynamic Yield) · 띠 1.2~3.3% | Shopify 전체 **1.4%** (Littledata) · 띠 1.3~2.7% |
| ATC율, 세션 기준 (§2) | 패션 **5.4%** (Littledata) | 공개값 없음 → 전체 평균 **4.6~6%** | 전체 **4.6%** (Littledata) |
| 장바구니 이탈률 (§3) | 패션 **72%** (72~80%) | 홈·가구 **76%** (73~80%) | **70.22%** (Baymard) / 77.55% (Dynamic Yield) |
| 결제 시작 → 구매 (§3) | **45%** (Littledata) | **45%** (Littledata) | **45%** (Littledata) |
| 유료 트래픽 비중 (§6) | 패션 **54%** (Contentsquare) | 공개값 없음 → 전 업종 **42%** | 전 업종 **42%** (Contentsquare) |
| non-paid 비중 (§6) | 패션 **46%** (역산) | 공개값 없음 → 전 업종 **58%** | 전 업종 **58%** (역산) |
| Meta CTR (§8) | 패션·주얼리 **1.29%** (LocaliQ, 트래픽 캠페인) | 가구 **1.39%** · 홈 **1.28%** (LocaliQ) · 홈·리빙 2.03% (Lebesgue) | 이커머스 **2.05%** (Superads) / **2.68%** 중앙값 (TGM) |
| Meta CPC (§8) | 패션·주얼리 **$0.86** (LocaliQ) | 가구 **$0.85** · 홈 **$0.99** (LocaliQ) · 홈·리빙 $0.61 (Lebesgue) | **$0.57** 중앙값 (TGM) / **$0.69** 평균 (Superads) |
| Meta ROAS (§8) | 공개값 없음 → 전체 **2.96** 중앙값 (TGM) | 홈·리빙 **4.17x** (Lebesgue, AOV $100~200) | **2.96** 중앙값 (TGM) |
| 재구매율 (§5, 참고) | 패션 **20~26%** | 홈·데코 **18~25%** · 가구 14~15% | 두 값 사이 |

- `industry` 값이 비었거나 셋 중 하나가 아니면 `general`로 본다.
- "공개값 없음 → …"인 칸은 **대체값임을 표에 밝히고** 쓴다. 업종 값이 있는 것처럼 말하지 않는다.
- Meta 광고 값은 전부 **미국·글로벌 달러 기준**이다. §8 머리말의 경고를 먼저 읽는다 — 절대값 대조는 하지 않는다.

---

## 1. 전체 전환율 (세션 → 구매)

| 지표 | 벤치마크 값(범위) | 카테고리 | 출처(링크) | 연도 | 비고 |
|---|---|---|---|---|---|
| 전체 CVR | **2.72%** (글로벌 평균) | 이커머스 전체 | [A] [Dynamic Yield XP² Benchmarks](https://marketing.dynamicyield.com/benchmarks/conversion-rate/) | 2025.08~2026.07 (12개월) | 세션 기준. 대형 브랜드 고객사 위주라 높게 나오는 편 |
| 전체 CVR | **1.51%** (APAC) | 이커머스 전체·아시아 | [A] Dynamic Yield (위와 동일 페이지, 지역 필터) | 동일 | 한국 단독 수치는 없음. APAC과 글로벌의 차이가 1.2%p라는 점만 참고 |
| 전체 CVR | **1.4%** (평균) / 3.2%+ (상위 20%) / 4.7%+ (상위 10%) | Shopify 중소몰 전체 | [A] [Littledata](https://www.littledata.io/average/ecommerce-conversion-rate) | 2023 (2,800개 몰) | 세션 기준. 중소 D2C 규모에 가장 가까운 표본 |
| 전체 CVR | **1.3%** (글로벌 방문 대비 구매) | 이커머스 전체 | [A] [Statista, Online shopper conversion rate worldwide](https://www.statista.com/statistics/439576/online-shopper-conversion-rate-worldwide/) | 2026 Q2 | 방문(visit) 기준. 국가별 수치는 유료 |
| 전체 CVR | **2.26%** (시장 전체) | 이커머스 전체·영국 | [A] [IRP Commerce Market Data](https://www.irpcommerce.com/en/gb/ecommercemarketdata.aspx) | 2026.07 | 영국 IRP 플랫폼 머천트. 매월 갱신 |
| 패션 CVR | **2.77%** | 패션·액세서리·의류 | [A] Dynamic Yield (업종 필터) | 2025.08~2026.07 | 글로벌 대형 브랜드 |
| 패션 CVR | **1.9%** (평균) / 4.3%+ (상위 20%) / 6.1%+ (상위 10%) | 패션 (Shopify) | [A] [Littledata](https://www.littledata.io/average/ecommerce-conversion-rate) | 2023 | 중소 D2C 패션 기준. **`industry: fashion` 1차 대조 행** |
| 패션 CVR | **1.81%** (2025.07은 1.36%) | Fashion Clothing & Accessories·영국 | [A] IRP Commerce | 2026.07 | 전년 대비 +33% |
| 홈·리빙 CVR | **1.22%** | Home & Furniture | [A] Dynamic Yield (업종 필터) | 2025.08~2026.07 | **`industry: home` 1차 대조 행.** 가구 포함 카테고리라 단가가 낮은 하위 카테고리(침구·홈텍스타일 등)는 이보다 높게 나올 가능성 |
| 홈·리빙 CVR | **3.34%** | Kitchen & Home Appliances·영국 | [A] IRP Commerce | 2026.07 | 가전 포함이라 홈텍스타일과는 거리 있음. 참고만 |
| 한국 전체 CVR | 1.33% | 국내 이커머스 | **출처 미확인** — [ditoday 칼럼](https://ditoday.com/%EA%B5%AD%EB%82%B4-%EC%9D%B4%EC%BB%A4%EB%A8%B8%EC%8A%A4-%ED%8F%89%EA%B7%A0-%EC%A0%84%ED%99%98%EC%9C%A8-%EB%AC%B8%EC%A0%9C%EC%9D%98-%ED%8C%8C%EC%95%85-%EA%B7%B8%EB%A6%AC%EA%B3%A0-%ED%9D%AC%EB%A7%9D/) | 2021.01 | 빅인(마케팅 자동화 솔루션) 운영 경험 기반이라고만 되어 있고 조사 방법·표본 없음. 한국 숫자로 자주 인용되지만 근거 없음 |
| 한국 전체 CVR | 1.8% (국내 쇼핑몰 평균), 가전 3.7%, 화장품 2.4% | 국내 쇼핑몰 | **출처 미확인** — [waveon 블로그](https://www.waveon.io/blog/ecommerce-conversion-rate) | 2024.05 | "몇몇 국내 기업 지표에 따르면"이라고만 표기. 원 출처 추적 불가 |
| 카페24 몰 PV 대비 CVR | 0.54% (특정 서비스 도입 전) | 카페24 중소몰 | [A-] [서울경제TV, 카페24 '다해드림' 기사](https://www.sentv.co.kr/article/view/sentv202608130060) | 2026.08 | **페이지뷰 기준**이라 세션 기준과 직접 비교 불가. 카페24 몰의 실측치가 공개된 드문 예라 넣음. 표본 수 미공개 |

> 주의: GA4 "세션 전환율"(sessionConversionRate)과 "사용자 전환율"은 다르다. 위 벤치마크는 전부 **세션 또는 방문 기준**이다. GA4 "사용자 전환율"을 그대로 들고 오면 숫자가 1.3~1.5배 높게 보인다.

---

## 2. 상품 상세 → 장바구니 담기율 (Add-to-Cart Rate)

| 지표 | 벤치마크 값(범위) | 카테고리 | 출처(링크) | 연도 | 비고 |
|---|---|---|---|---|---|
| ATC율 (세션 기준) | **6.08%** (글로벌) / **3.24%** (APAC) | 이커머스 전체 | [A] [Dynamic Yield, Add-to-Cart Rate](https://marketing.dynamicyield.com/benchmarks/add-to-cart-rate/) | 2025.08~2026.07 | 장바구니 담은 세션 ÷ 전체 세션. 럭셔리 1.76% ~ 뷰티 9.56% |
| ATC율 (기기별) | 모바일 6.35% / 데스크톱 5.21% | 이커머스 전체 | [A] Dynamic Yield (기기 필터) | 동일 | 모바일이 담기는 더 많이 하고 결제는 덜 한다 (3장 참고) |
| ATC율 (세션 기준) | **4.6%** (평균) / 7.5%+ (상위 20%) / 9.6%+ (상위 10%) | Shopify 중소몰 전체 | [A] [Littledata, Add to Cart Rate](https://www.littledata.io/average/add-to-cart-rate) | 2023 (2,800개 몰) | 장바구니 담기 ÷ 세션 |
| ATC율 (패션) | **5.4%** | 패션 (Shopify) | [A] Littledata (동일 페이지) | 2023 | **`industry: fashion` 1차 대조 행** |
| ATC율 (패션) | 6.6~7.1% | 패션·의류 | [C] Dynamic Yield 업종 필터를 인용한 2차 집계 ([Opensend](https://www.opensend.com/post/add-to-cart-rate-statistics-ecommerce)) | 2025 | Dynamic Yield 페이지에서 패션 수치를 직접 확인 못함. 2차 인용 |
| ATC율 (홈·리빙) | — | Home & Furniture | 출처 없음 | — | Dynamic Yield 필터에는 존재하나 공개 페이지에 수치 미표기. `industry: home`은 전체 평균(4.6~6%)으로 대체 |
| ATC율 (**view_item 대비**) | **없음** | 이커머스 전체 | 출처 없음 — Dynamic Yield 상품페이지 지표·Baymard·Contentsquare 재확인 | 2026.09 재확인 | 공개된 ATC 벤치마크는 전부 세션 분모. [C] Lebesgue의 10.85%는 **Meta 유입 기준(분모 미공개)**이라 세션·클릭 어느 쪽과도 대조할 수 없다 |

> **정의 주의 (중요):** 흔히 보는 "view_item 대비 add_to_cart"는 위 벤치마크와 **분모가 다르다**. 벤치마크는 전부 **전체 세션 대비**다. view_item 대비로 계산하면 숫자가 훨씬 크게 나온다(상세페이지를 본 세션만 분모이므로). 공개된 "view_item 대비" 벤치마크는 **찾지 못했다**. 비교하려면 GA4에서 `add_to_cart 세션 ÷ 전체 세션`도 같이 뽑아야 한다. 정확히는 GA4 탐색 > 유입경로 탐색 분석에서 `view_item → add_to_cart` 단계별 비율을 직접 계산하고, 두 숫자 모두 적어 둔다. (2026-09 재확인 결과도 동일하다. Dynamic Yield 상품페이지 지표·Baymard·Contentsquare 모두 세션 분모다.)

---

## 3. 장바구니 → 결제 시작 → 구매 완료

| 지표 | 벤치마크 값(범위) | 카테고리 | 출처(링크) | 연도 | 비고 |
|---|---|---|---|---|---|
| 장바구니 이탈률 | **70.22%** (50개 연구 평균) | 이커머스 전체 | [B] [Baymard Institute, Cart Abandonment Rate](https://baymard.com/lists/cart-abandonment-rate) | 2025.09.22 갱신 | 가장 많이 인용되는 기준값. 2006년 이후 ~70%에서 거의 불변. 즉 장바구니→구매는 **약 30%** |
| 장바구니 이탈률 | **77.55%** (글로벌) / **81.53%** (APAC) | 이커머스 전체 | [A] [Dynamic Yield, Cart Abandonment](https://marketing.dynamicyield.com/benchmarks/cart-abandonment-rate/) | 2025.08~2026.07 | 실측 세션 데이터. Baymard보다 7%p 높음 → 장바구니→구매 **약 22%** |
| 장바구니 이탈률 (기기별) | 모바일 **79.84%** / 태블릿 72.67% / 데스크톱 **69.48%** | 이커머스 전체 | [A] Dynamic Yield (기기 필터) | 동일 | 모바일이 10%p 더 이탈. 소셜 유입은 거의 모바일이라 소셜 비중이 큰 몰은 상단 쪽 |
| 장바구니 이탈률 (패션) | 72% (72~80%) | 패션·의류 | [C] Baymard 유료 데이터를 인용한 2차 집계 ([Eightx 정리](https://eightx.co/blog/average-ecommerce-cart-abandonment-rate-by-vertical-2026), 원 인용 Zipchat 2026) | 2025~26 | Baymard는 업종별 표를 무료로 공개하지 않음. 2차 경로라 ± 크게 봐야 함 |
| 장바구니 이탈률 (홈·가구) | 76% (73~80%) | Home & Furniture | [C] 위와 동일 경로 | 2025~26 | 고단가일수록 이탈 높음. 홈·리빙 하위 카테고리도 같은 방향으로 볼 것 |
| 결제 시작 → 구매 완료 (Checkout completion) | **45%** (평균) / 59%+ (상위 20%) / 66%+ (상위 10%) | Shopify 중소몰 전체 | [A] [Littledata, Checkout Completion Rate](https://www.littledata.io/average/checkout-completion-rate) | 2023 (2,800개 몰) | 결제 시작 세션 중 주문 완료. 즉 **결제 단계 이탈 ≈ 55%** |
| 결제 완료율 (기기별) | 모바일 **44%** (상위 10% 64%+) / 데스크톱 **49%** (상위 10% 70%+) | Shopify 전체 | [A] Littledata (동일 페이지) | 2023 | |
| 장바구니 → 결제 시작 (계산값) | 약 **50~65%** | 이커머스 전체 | 계산: (장바구니→구매 22~30%) ÷ (결제→구매 45%) | — | 직접 공개된 벤치마크 없음. 위 두 값에서 역산한 추정치라 참고만 |

---

## 4. 채널별 전환율

| 지표 | 벤치마크 값(범위) | 카테고리 | 출처(링크) | 연도 | 비고 |
|---|---|---|---|---|---|
| Paid Search CVR | **2.8%** | 전 업종 (리테일 포함) | [A] [Contentsquare 2026 Digital Experience Benchmark – Conversions](https://contentsquare.com/guides/digital-experience-benchmark/conversions/) | 2025 데이터 (990억 세션, 6,000+ 사이트) | 유료 채널 중 최고 |
| Organic Social CVR | **0.7%** | 전 업종 | [A] Contentsquare 2026 (동일) | 동일 | 주요 채널 중 최저 |
| Paid Social CVR | 0.4% (분기별 동일) | 전 업종 | [A] Contentsquare 2025 분기 데이터 ([MarketingCharts 요약](https://www.marketingcharts.com/digital-237967)) | 2025 | 원문 페이지가 봇 차단으로 직접 확인 못함. 검색 요약에서 확보한 수치라 **±로 볼 것** |
| Organic Search CVR | 1.7~1.8% | 전 업종 | [A] Contentsquare 2025 분기 (동일 경로) | 2025 | 위와 같은 주의 |
| Paid Search vs Paid Social | Paid Search가 Paid Social의 **4배** 전환, Paid Social은 이탈(bounce) 확률 **41% 높음** | 전 업종 | [A] [Contentsquare 2024 DXB, eMarketer 보도](https://www.emarketer.com/content/paid-search-outperforms-paid-social-with-latter-far-more-likely-bounce) | 2024.02 (2022~23 데이터) | 채널 격차의 가장 신뢰할 만한 단일 근거 |
| 채널별 CVR 종합 | Email 4.2% (4.0~5.3) · Referral 4.2% · Direct 3.0% · Organic Search 2.8% (2.1~4.0) · Paid Search 2.5% · **Meta Paid Social 1.1% (0.5~2.1)** | 이커머스 (Shopify 혼합 1.4% 기준) | [C] [Eightx 집계](https://eightx.co/blog/average-ecommerce-conversion-rate-by-traffic-source-2026) — Littledata 등 2차 종합 | 2026 | 2차 집계지만 채널 순서·배수는 A급 출처와 일치. **Organic Search : Paid Social ≈ 2.5 : 1, Email : Paid Social ≈ 4 : 1** |
| 채널별 CVR (리테일) | Paid Search 2.1 · Organic 2.0 · Social Paid 2.3 · Social Organic 1.74 · Email 2.3 · Direct 2.3 · Referral 2.0 | Retail & eCommerce | [A] [Ruler Analytics 2026](https://www.ruleranalytics.com/blog/insight/conversion-rate-by-industry/) | 2026 (500만+ 전환) | **주의**: Ruler는 폼 제출·전화(리드) 전환을 세는 툴이라 구매 전환과 다름. Paid Social이 높게 나온 건 그 때문. 순위 비교용으로만 |
| Email (Klaviyo) 주문율 | 캠페인 **0.16%** (의류 0.12%) / 자동화 플로우 **2.11%** (의류 2.15%) | 이커머스·의류 | [A] [Klaviyo 2026 Benchmarks](https://www.klaviyo.com/uk/blog/email-marketing-benchmarks-open-click-and-conversion-rates) | 2026 (183,000+ 브랜드) | **수신자 대비 주문**이라 세션 CVR과 분모가 다름. GA4 email 세션 CVR과 직접 비교 금지. 플로우(장바구니 리마인드 등)가 캠페인 대비 13배라는 비율만 가져갈 것 |

---

## 5. 신규 vs 재방문

| 지표 | 벤치마크 값(범위) | 카테고리 | 출처(링크) | 연도 | 비고 |
|---|---|---|---|---|---|
| 재방문 트래픽 비중 | **52.8%** (전 업종) / **51%** (리테일) | 전 업종·리테일 | [A] [Contentsquare 2026 – Traffic](https://contentsquare.com/guides/digital-experience-benchmark/traffic/) · [Retail guide](https://contentsquare.com/guides/retail-digital-experience/) | 2025 데이터 | 대형 브랜드 위주 표본이라 재방문 비중이 높게 나옴. 가전 리테일은 60% |
| 신규/재방문 CVR | 재방문 **2.9%** vs 신규 **1.7%** (1.7배) | 전 업종 | [A] Contentsquare 2026 – Conversions | 2025 | 신규 CVR 전년 대비 -8%, 재방문 -4% |
| 재방문 세션 비중 (D2C) | **18.8%** (중앙값) — 즉 신규 81.2% | DTC 중소 브랜드 24곳 | [A] [Top Growth Marketing DTC Benchmark](https://topgrowthmarketing.com/dtc-ecommerce-benchmarks/returning-vs-new-customers/) | 2025.07~2026.06 (GA4 API, 1,850만 세션) | 표본은 작지만(24개 몰) **광고 의존 D2C의 실제 모습**. 광고 의존 중소 D2C는 이쪽에 가까울 가능성 높음 |
| 신규/재방문 CVR (D2C) | 재방문 **2.17%** vs 신규 **0.85%** (**2.6배**) | DTC 중소 브랜드 | [A] 위와 동일 | 동일 | 재방문은 세션 18.8%로 매출 **36.5%** (범위 19~58%) 담당 |
| 재구매율 (고객 기준·12개월) | 홈·데코 **18~25%** · 가구 **14~15%** · 패션 **20~26%** | 홈·데코/가구/패션 | [C] [Eightx, Repeat Purchase Rate by Vertical](https://eightx.co/blog/average-repeat-purchase-rate-by-vertical) | 2025~26 | **분모가 세션이 아니라 고객**(재구매 고객 ÷ 전체 고유 고객). 재방문 세션 비중과 다른 지표다(스킬은 이 행을 표시하지 않는다) |

---

## 6. 트래픽 믹스 (Direct·Paid·Organic 비중)

| 지표 | 벤치마크 값(범위) | 카테고리 | 출처(링크) | 연도 | 비고 |
|---|---|---|---|---|---|
| 채널 비중 (미국 상위 1,000 이커머스) | Direct **57.66%** · Organic Search **23.56%** · Paid Search 6.88% · Social 6.04% | 이커머스 (대형) | [A] Similarweb 2025 SEO Benchmark Report ([SEO Sherpa 정리](https://seosherpa.com/ecommerce-seo-statistics/), [보고서 페이지](https://www.similarweb.com/corp/reports/seo-benchmarking-report/)) | 2024.01~11 | 상위 1,000개 대형몰이라 Direct가 과대. 중소 D2C 기준으로는 쓰기 어려움 |
| 채널 비중 (글로벌 이커머스) | Direct 56.1% · Organic Search 25.7% · Paid Search 5.8% · Referral 5.7% · Social 3.7% · Email 2.1% · Display 1.0% | 이커머스 전체 | [A] [Similarweb eCommerce Benchmarks](https://www.similarweb.com/blog/ecommerce/retail-insights/ecommerce-benchmarks-metrics/) | 2022.01 | 오래됐지만 전 채널이 다 나온 유일한 무료 표 |
| 유료 트래픽 비중 (전 업종) | **42%** (2025) ← 39% (2024) ← 37% (2023) | 전 업종 | [A] Contentsquare 2026 – Traffic · [2025 보도자료](https://contentsquare.com/press/2025-digital-experience-benchmarks/) | 2023~2025 | 매년 2~3%p씩 오르는 중. Direct 29.42%, Paid Search 25.15%, Paid Social 10.5% (+18% YoY) |
| Paid Social 비중 (리테일) | **13%** of 리테일 트래픽 (+18% YoY) | 리테일 | [A] Contentsquare Retail guide | 2025 | |
| 유료 트래픽 비중 (패션) | **54%** | Fashion & Specialty Retail | [A] Contentsquare Retail guide (2,200+ 리테일 사이트) | 2025 | **패션은 원래 유료 의존이 높은 업종.** `industry: fashion` 1차 대조 행 |
| 채널별 매출 기여 (영국) | Paid Search 62.5% · Direct 21.2% · Email 9.2% · Affiliate 4.7% · Paid Social **0.4%** | 이커머스·영국 | [A] IRP Commerce | 2026.07 | 트래픽이 아니라 **매출 기여 비중**. 영국 IRP 머천트는 검색광고 중심이라 인스타 중심 한국 D2C와 구조가 다름. "paid social 매출 기여가 원래 작다"는 참고만 |
| Paid 의존 휴리스틱 기준 | 휴리스틱 기준: 유료 세션 **50%↑** 및 공헌이익률 **40%↓** / 마케팅비 대 매출 **15~17%↑** (상장 D2C는 Revolve 14.3% · Wayfair 11.4%) | D2C 일반 | [C] [Eightx 정리](https://eightx.co/blog/average-ecommerce-paid-traffic-share-by-vertical-2026) — 10-K 공시 인용 | 2025~26 | **공식 벤치마크가 아닌 휴리스틱.** 저자도 "업종별 트래픽 소스 벤치마크를 무료로 내는 곳은 없다"고 명시 |
| **non-paid 비중** (전 업종) | **58%** (= 100 − 유료 42%) | 전 업종 | [A] [Contentsquare 2026 – Traffic](https://contentsquare.com/guides/digital-experience-benchmark/traffic/) — 유료 비중에서 역산 | 2025 데이터 (990억 세션·6,000+ 사이트) | 유료로 분류되지 않은 **나머지 전부(미분류 포함)**. Contentsquare가 공개하는 개별 값은 Direct 29.42% · Paid Search 25.15% · Paid Social 10.5%뿐이라 잔여 58%의 구성은 알 수 없다 — 소계로만 비교 가능 |
| **non-paid 비중** (패션) | **46%** (= 100 − 유료 54%) | Fashion & Specialty Retail | [A] [Contentsquare Retail guide](https://contentsquare.com/guides/retail-digital-experience/) — 유료 비중에서 역산 | 2025 (2,200+ 리테일 사이트) | 패션 D2C의 non-paid 기준선. **`industry: fashion` 1차 대조 행** |
| **non-paid 비중** (글로벌 이커머스·대형) | **89.6%** (Direct 56.1 + Organic Search 25.7 + Referral 5.7 + Email 2.1) | 이커머스 전체 | [A] [Similarweb eCommerce Benchmarks](https://www.similarweb.com/blog/ecommerce/retail-insights/ecommerce-benchmarks-metrics/) — 위 행 표에서 합산 | 2022.01 | 대형몰 표본이라 **상한선**. 광고를 거의 안 쓰는 몰의 모습이라 중소 D2C 대조값으로는 부적합 |
| D2C 업종별 채널 믹스 | **없음** | D2C | 확인 못 함 (Contentsquare·Similarweb·Shopify·Littledata 재확인) | 2026.09 확인 | 업종별로 Direct/Organic/Email/Referral을 각각 낸 무료 표는 없다. non-paid **소계**로만 비교할 것 |

---

## 7. 모바일 vs 데스크톱

| 지표 | 벤치마크 값(범위) | 카테고리 | 출처(링크) | 연도 | 비고 |
|---|---|---|---|---|---|
| 기기별 CVR (Shopify) | 모바일 **1.2%** (상위 10% 3.9%+) / 데스크톱 **1.9%** (상위 10% 6.5%+) | Shopify 중소몰 | [A] [Littledata](https://www.littledata.io/average/ecommerce-conversion-rate) | 2023 | 데스크톱이 1.6배 |
| 기기별 CVR (대형 브랜드) | 모바일 **2.88%** / 태블릿 2.85% / 데스크톱 **2.37%** | 이커머스 전체 | [A] Dynamic Yield (기기 필터) | 2025.08~2026.07 | **역전 사례.** 앱·모바일 최적화가 된 대형 브랜드 표본에서는 모바일이 더 높음. 정답이 아니라는 증거 |
| 기기별 CVR 격차 | 데스크톱이 모바일보다 **74%** 높음 (전 업종) / 리테일은 **40~70%** 높음 | 전 업종·리테일 | [A] Contentsquare 2026 – Conversions · Retail guide | 2025 | 리테일 모바일 트래픽 비중 **77%** |
| 기기별 장바구니 이탈 | 모바일 79.84% / 데스크톱 69.48% | 이커머스 전체 | [A] Dynamic Yield (3장 참고) | 2025~26 | 담기는 모바일이 더 많이, 결제는 데스크톱이 더 많이 |
| 기기별 결제 완료율 | 모바일 44% / 데스크톱 49% | Shopify | [A] Littledata (3장 참고) | 2023 | |
| 한국 모바일 쇼핑 비중 | 온라인쇼핑 거래액 중 모바일 **75.9%** (2025.09) · **77.8%** (2025.06) | 한국 전체 온라인쇼핑 | [A] [통계청(국가데이터처) 온라인쇼핑동향](https://www.kostat.go.kr/board.es?mid=a10301120300&bid=241&tag=&act=view&list_no=439110&ref_bid=) | 2025 | 트래픽이 아니라 **거래액** 비중. 한국은 모바일 결제 비중이 글로벌보다 높음 |

---

## 8. 광고 효율 (Meta 유료광고)

> 이 장의 값은 **전부 미국·글로벌 계정 기준의 달러 값**이며 어트리뷰션도 Meta 기준이다. 한국 CPM은 경매 참여자 수·인구 규모가 달라 **절대값 대조는 하지 않는다.** 아래 값은 "자릿수가 맞는가"와 방향만 보고, 판단은 **내부 추이(전월·전분기 대비)**로 한다. 홈·리빙 대조값(CPM·CPC·CTR·CAC·ROAS·ATC율)은 **전부 Lebesgue 단일 출처**이고 표본 수·수집 기간이 공개돼 있지 않다. 우리 값은 `rules.md` §8의 순서(Meta MCP 우선, cwd `data/ads.csv` 차선)로 구해 계산한다(CTR = link_clicks ÷ impressions, CPC = spend ÷ link_clicks, 장바구니당 비용 = spend ÷ add_to_cart, CPA = spend ÷ purchases, ROAS = 매출 ÷ spend).

| 지표 | 벤치마크 값(범위) | 카테고리 | 분모 정의 | 출처(링크) | 연도 | 비고 |
|---|---|---|---|---|---|---|
| CTR | **2.68%** (중앙값) · IQR 1.78~2.91% · 전범위 0.94~6.00% | DTC 이커머스 | 클릭 ÷ 노출 | [A] [Top Growth Marketing, Meta Ads Benchmarks](https://topgrowthmarketing.com/dtc-ecommerce-benchmarks/meta-ads-benchmarks/) | 2025.07~2026.06 | Meta Ads API 계정 단위·동일가중 백분위. DTC 15개 브랜드, 광고비 $2,464,453 · 노출 1억 7,088만 · 클릭 456만 · 구매 92,051. USD 계정·기간 내 $10,000 이상만 포함. **대행사가 자체 관리하는 클라이언트 계정 15개이며 원문도 "업계 평균이 아니다"라고 명시한다.** **"링크 클릭"인지 "전체 클릭"인지 페이지에 명시 없음** — 우리 `link_clicks`와 정의가 다를 수 있다 |
| CTR | **2.05%** (평균) · 월별 1.22~2.93% | 이커머스 전체 | 클릭 ÷ 노출 | [A] [Superads, Facebook Ads CTR — E-commerce](https://www.superads.ai/facebook-ads-costs/ctr-click-through-rate/e-commerce) | 2025.07~2026.07 (13개월) | Facebook 광고비 $3B·수천 개 계정. "노출 중 광고를 클릭한 비율"로만 정의돼 링크 클릭 구분 없음 |
| CTR (업종별) | 패션·주얼리 **1.29%** · 가구 **1.39%** · 홈/홈임프루브먼트 **1.28%** | 패션·가구·홈 | 클릭 ÷ 노출 | [A] [LocaliQ, Facebook Advertising Benchmarks](https://localiq.com/blog/facebook-advertising-benchmarks/) | 2025 | 미국 LocaliQ 관리 계정. **트래픽 캠페인 한정**(구매 최적화 캠페인이 아님) — 구매 캠페인보다 CTR이 낮게 나오는 구간이다. 표본 수·CTR 정의 미공개 |
| CTR (한국) | **없음** | 한국 이커머스 | — | 확인 못 함 — 나스미디어·메조미디어 2026 리포트 확인 | 2026.09 확인 | 국내 리포트는 시장 규모·광고비 총액·트렌드만 다루고 CTR/CPM 단가 벤치마크를 내지 않는다 |
| CPA (구매당 비용) | **$49.04** (중앙값) · IQR $16.65~$108.30 · 전범위 $6.63~$195.17 | DTC 이커머스 | 광고비 ÷ 구매 (Meta 어트리뷰션) | [A] Top Growth Marketing (위와 동일) | 2025.07~2026.06 | 객단가와 CPA는 같은 방향으로 움직인다. **CPA 절대값보다 CPA ÷ 객단가로 봐야 한다** |
| CPA (구매당 비용) | **$34.34** (평균) · 월별 $16.51~$55.75 | 이커머스 전체 | 광고비 ÷ 구매 | [A] [Superads, Cost per Purchase — E-commerce](https://www.superads.ai/facebook-ads-costs/cost-per-purchase/e-commerce) | 2025.07~2026.07 (13개월) | 시계열 양끝은 2025.07 약 $35.03 · 2026.07 $16.51. 단조 감소가 아니며 2025.12는 약 $37.19 |
| CAC (홈·리빙) | **$20.55** (AOV $100~200 구간) | Home & Lifestyle | 광고비 ÷ 신규 고객 | [C] [Lebesgue, Meta Ads Benchmarks by Industry and AOV](https://lebesgue.io/facebook-ads/meta-ads-benchmarks-by-industry-and-aov) | 2026 (수집 기간 미공개) | 자사 연결 스토어 중앙값이라고만 표기. **표본 수·기간 미공개라 [A]로 쓰지 않는다** |
| CPA (한국 원화) | **없음** | 한국 | — | 확인 못 함 | 2026.09 확인 | 달러 값을 환율로 환산하면 시장·객단가·경매 차이가 섞인다. 환산 인용 금지 |
| **장바구니당 비용** | **없음** (공개 벤치마크 자체가 없다) | 이커머스 | — | 확인 못 함 — Superads·Top Growth Marketing·LocaliQ·Triple Whale 확인 | 2026.09 확인 | 광고 벤더는 CPM·CPC·CPA까지만 공개한다. 장바구니는 중간 단계라 표로 내는 곳이 없다 |
| CPC | **$0.57** (중앙값) · IQR $0.33~$1.01 · 전범위 $0.21~$2.44 | DTC 이커머스 | 광고비 ÷ 클릭 | [A] Top Growth Marketing (위와 동일) | 2025.07~2026.06 | |
| CPC | **$0.69** (평균) · 월별 $0.37~$1.02 | 이커머스 전체 | 광고비 ÷ 클릭 | [A] [Superads, CPC — E-commerce](https://www.superads.ai/facebook-ads-costs/cpc-cost-per-click/e-commerce) | 2025.07~2026.07 | 전 업종 평균 $1.05 대비 약 34% 아래 |
| CPC (업종별) | 패션·주얼리 **$0.86** · 가구 **$0.85** · 홈/홈임프루브먼트 **$0.99** | 패션·가구·홈 | 광고비 ÷ 클릭 | [A] LocaliQ (위와 동일) | 2025 | 트래픽 캠페인 한정 |
| CPM | **$13.52** (중앙값) · IQR $11.04~$22.90 · 전범위 $5.83~$31.09 | DTC 이커머스 | 광고비 ÷ 노출 × 1,000 | [A] Top Growth Marketing (위와 동일) | 2025.07~2026.06 | |
| CPM | **$13.88** (평균) · 월별 $11.21~$21.96 | 이커머스 전체 | 광고비 ÷ 노출 × 1,000 | [A] [Superads, CPM — E-commerce](https://www.superads.ai/facebook-ads-costs/cpm-cost-per-mille/e-commerce) | 2025.07~2026.07 (13개월) | 11월(블랙프라이데이) $21.96로 급등. 전 업종 평균 $20.59 대비 33% 아래 |
| CPM·CPC·CTR (홈·리빙) | CPM **$10.77** · CPC **$0.61** · CTR **2.03%** (AOV $100~200) | Home & Lifestyle | 위 정의와 동일 | [C] Lebesgue (위와 동일) | 2026 (수집 기간 미공개) | 자사 연결 스토어 중앙값. **표본 수·수집 기간 미공개** |
| CPC·CPM (한국) | **없음** | 한국 | — | 확인 못 함 | 2026.09 확인 | 위 값은 전부 미국·글로벌 계정. **한국 CPM 절대값 대조 금지**, 내부 추이만 |
| 구매 ROAS | **2.96** (중앙값) · IQR 2.50~5.30 · 전범위 1.00~31.49 | DTC 이커머스 | 광고 플랫폼 기준 매출 ÷ 광고비 | [A] Top Growth Marketing (위와 동일) | 2025.07~2026.06 | **Meta 어트리뷰션 기준**이라 GA4 기준보다 높게 나온다. 플랫폼 기준 `purchase_value ÷ spend`와 GA4 기준 매출 ÷ spend를 둘 다 적어 둘 것 |
| 구매 ROAS (홈·리빙) | **4.17x** (AOV $100~200) | Home & Lifestyle | 매출 ÷ 광고비 | [C] Lebesgue (위와 동일) | 2026 (수집 기간 미공개) | **표본 수·수집 기간 미공개.** AOV 구간이 맞아야 의미가 있다. 우리 객단가를 먼저 확인하고 쓸 것 |
| 클릭 → 구매 전환율 | **1.24%** (중앙값) · IQR 0.65~3.24% · 전범위 0.26~6.84% | DTC 이커머스 | 구매 ÷ **광고 클릭** | [A] Top Growth Marketing (위와 동일) | 2025.07~2026.06 | **분모가 세션이 아니라 광고 클릭이다.** §1의 세션 CVR과 직접 비교 금지. 클릭 대비 세션이 20~40% 유실되므로 세션 기준 값이 더 낮게 나온다(분모 차이) |

---

## 부록 A. 찾지 못한 것 / 쓰지 말아야 할 것

- **한국 이커머스 세션 CVR의 공식 벤치마크는 없다.** 카페24·나스미디어·메조미디어·DMC 리포트 모두 전환율을 공개하지 않는다. 메조미디어 [2025 이커머스 업종 분석 리포트](https://lib.mezzomedia.co.kr/newsletter/202511/01_MezzoMedia_2025_Industrial_Report_ecommerce.pdf)(2025.11)는 시장 규모(242조, 통계청)·광고비(3,867억, 리서치애드)·소비자 설문(471명)만 있고 퍼널 지표는 없다. 돌아다니는 "국내 평균 1.33%", "1.8%", "중소몰 1.2~1.8%·대형 3~5%"는 전부 출처 미확인.
- **침구 단독 벤치마크는 없다.** Home & Furniture(가구 포함)로 대체했고, 침구는 가구보다 단가가 낮아 실제로는 그보다 높을 가능성이 있다.
- **view_item 대비 add_to_cart 벤치마크는 없다.** 모든 공개 ATC 벤치마크는 세션 대비다. (2026-09 재확인 결과 동일 — Dynamic Yield 상품페이지 지표·Baymard·Contentsquare 모두 세션 분모였다. Lebesgue의 ATC율 10.85%는 [C]이고, 원문 정의가 "Meta에서 유입된 쇼퍼"뿐이라 분모가 클릭인지 세션인지 랜딩뷰인지 공개돼 있지 않다.)
- **장바구니 → 결제 시작 단계만 따로 낸 벤치마크는 없다.** 역산 추정치(50~65%)만 있다.
- **Paid Social CVR의 A급 절대값**은 Contentsquare 2025 분기 데이터(0.4%)뿐인데 원문 페이지를 직접 열지 못했다. 배수(Paid Search의 1/4, eMarketer 보도)는 확인됨.
- Statista의 기기별·국가별 CVR은 유료 벽 뒤에 있어 확인하지 못했다.
- **Meta 광고 장바구니당 비용(cost per add-to-cart) 벤치마크는 없다.** (2026-09 확인) Superads·Top Growth Marketing·LocaliQ·Triple Whale 모두 CPM·CPC·CPA까지만 공개한다. CPC ÷ Lebesgue ATC율로 역산했던 §8 참고 행은 **분모 미공개 값 위에 얹은 추정**이라 2026-09-10 삭제했다.
- **한국 Meta 광고 CTR·CPC·CPM·CPA 벤치마크는 없다.** (2026-09 확인) 나스미디어 2026 디지털 미디어·마케팅 전망, CJ메조미디어 2026 트렌드 리포트 모두 시장 규모·광고비 총액·트렌드만 다루고 매체 단가·퍼널 지표를 내지 않는다. 돌아다니는 "한국 메타 CPM" 수치는 전부 미국·글로벌 값의 재인용이다.
- **침구 단독 재구매율도 없다.** 홈·데코(18~25%)와 가구(14~15%) 사이로 대체했다.
- **D2C 업종별 채널 믹스(Direct/Organic/Email/Referral 각각의 비중)를 낸 무료 표는 없다.** non-paid **소계**로만 비교 가능하다.
- Triple Whale의 이커머스·Facebook 광고 벤치마크 페이지는 봇 차단(HTTP 403)으로 직접 열지 못했다. 검색 요약에만 나오는 수치(예: 40,000개 브랜드 중앙값 CPA $31.26)는 **인용하지 않았다**.
- 쿠팡·네이버의 공식 수수료 안내 페이지는 로그인·봇 차단으로 직접 확인하지 못했다.

## 부록 B. 출처 목록

1. Dynamic Yield XP² Benchmarks — https://marketing.dynamicyield.com/benchmarks/conversion-rate/ (전환율), /add-to-cart-rate/ (장바구니), /cart-abandonment-rate/ (이탈)
2. Littledata Shopify Benchmarks — https://www.littledata.io/average/ecommerce-conversion-rate , /add-to-cart-rate , /checkout-completion-rate
3. Baymard Institute — https://baymard.com/lists/cart-abandonment-rate
4. Contentsquare 2026 Digital Experience Benchmark — https://contentsquare.com/guides/digital-experience-benchmark/ (traffic, conversions), https://contentsquare.com/guides/retail-digital-experience/ , 2025 보도자료 https://contentsquare.com/press/2025-digital-experience-benchmarks/
5. eMarketer (Contentsquare 2024 DXB 보도) — https://www.emarketer.com/content/paid-search-outperforms-paid-social-with-latter-far-more-likely-bounce
6. IRP Commerce Market Data — https://www.irpcommerce.com/en/gb/ecommercemarketdata.aspx
7. Statista — https://www.statista.com/statistics/439576/online-shopper-conversion-rate-worldwide/
8. Similarweb — https://www.similarweb.com/blog/ecommerce/retail-insights/ecommerce-benchmarks-metrics/ , https://www.similarweb.com/corp/reports/seo-benchmarking-report/
9. Ruler Analytics — https://www.ruleranalytics.com/blog/insight/conversion-rate-by-industry/
10. Klaviyo — https://www.klaviyo.com/uk/blog/email-marketing-benchmarks-open-click-and-conversion-rates
11. Top Growth Marketing DTC Benchmark — https://topgrowthmarketing.com/dtc-ecommerce-benchmarks/returning-vs-new-customers/
12. 통계청 온라인쇼핑동향 — https://www.kostat.go.kr/board.es?mid=a10301120300&bid=241&tag=&act=view&list_no=439110&ref_bid=
13. CJ메조미디어 2025 이커머스 업종 분석 리포트 — https://lib.mezzomedia.co.kr/newsletter/202511/01_MezzoMedia_2025_Industrial_Report_ecommerce.pdf
14. 서울경제TV 카페24 기사 — https://www.sentv.co.kr/article/view/sentv202608130060
15. (2차) Eightx — https://eightx.co/blog/average-ecommerce-conversion-rate-by-traffic-source-2026 , /average-ecommerce-cart-abandonment-rate-by-vertical-2026 , /average-ecommerce-paid-traffic-share-by-vertical-2026
16. (2차) SEO Sherpa — https://seosherpa.com/ecommerce-seo-statistics/ · MarketingCharts — https://www.marketingcharts.com/digital-237967 · Opensend — https://www.opensend.com/post/add-to-cart-rate-statistics-ecommerce
17. Top Growth Marketing Meta Ads Benchmark — https://topgrowthmarketing.com/dtc-ecommerce-benchmarks/meta-ads-benchmarks/
18. Superads Facebook Ads Cost Benchmarks — https://www.superads.ai/facebook-ads-costs/ctr-click-through-rate/e-commerce , /cpc-cost-per-click/e-commerce , /cpm-cost-per-mille/e-commerce , /cost-per-purchase/e-commerce
19. LocaliQ Facebook Advertising Benchmarks — https://localiq.com/blog/facebook-advertising-benchmarks/
20. (2차) Lebesgue Meta Ads Benchmarks by Industry and AOV — https://lebesgue.io/facebook-ads/meta-ads-benchmarks-by-industry-and-aov
21. (2차) Eightx Repeat Purchase Rate by Vertical — https://eightx.co/blog/average-repeat-purchase-rate-by-vertical · Rivo Repeat Purchase Rate Guide — https://www.rivo.io/blog/repeat-purchase-rate-complete-guide
22. (출처 미확인) ditoday 2021 — https://ditoday.com/ (국내 1.33%) · waveon 2024 — https://www.waveon.io/blog/ecommerce-conversion-rate (국내 1.8%)
