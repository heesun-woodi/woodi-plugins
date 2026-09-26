# variant 목업 프롬프트 조립 가이드

> **언제 읽나**: M2(이미지 생성 프롬프트 조립) 직전. 참가자가 E2 4슬롯 명세를 다 채운 뒤, 그 명세를 이미지 생성 모델에 넣을 프롬프트로 바꾸는 단계에서 연다.
>
> **이 가이드의 소관**: `cro-experiment-design` 스킬의 `variant-design-guide.md` §7이 정한 **E2 4슬롯 명세가 정본**이다. 이 가이드는 그 명세를 프롬프트 문장으로 옮기는 **번역기**일 뿐, 명세 내용을 새로 만들거나 바꾸지 않는다. 명세가 비어 있거나 슬롯이 "표기만" 수준이면 이 가이드로 넘어오기 전에 `variant-design-guide.md` §4로 돌아가 먼저 채운다.

---

## ① 대원칙

이 가이드가 만드는 프롬프트는 **control 화면을 그대로 유지하면서, 지정된 요소 하나만 바꾸는** 프롬프트다. `cro-experiment-design`의 E2 규칙(단일 축 변경 원칙)과 같은 원칙을 이미지 생성 쪽으로 옮긴 것뿐이다. AI가 화면 전체를 다시 그리게 만들면 그 결과물은 실패다 — control과 비교할 수 없는 완전히 다른 화면이 나오기 때문이다. 프롬프트는 항상 "이 스크린샷을 편집해줘"로 시작하지, "이런 화면을 그려줘"로 시작하지 않는다.

## ② variant 목업용 6부 프롬프트 구조

`product-mockup` 스킬의 6부 구조(Placement → Scene → Preservation → Binding → Camera → Resolution)를 앱 UI 편집용으로 번안했다. "순서가 전달 가능한 부분"이라는 원칙은 그대로 가져온다 — 뒤에 오는 문장일수록 모델이 덜 주의를 기울이므로, 양보 불가한 지시(Preservation)는 앞·중간에 둔다.

| 순서 | 부 | 역할 | 원본 6부와의 대응 |
|---|---|---|---|
| 1 | **Task 선언** | 이것이 신규 장면 생성이 아니라 기존 스크린샷의 편집임을 먼저 명시 | Placement(어디서 시작하는지) |
| 2 | **Preservation** | 레이아웃·색상·폰트·상태바·내비게이션 등 나머지 전부를 그대로 유지 | Preservation |
| 3 | **Target 지목** | [노출 위치] 슬롯 — 바꿀 영역만 정확히 지목 | Binding(어디를 건드리는지) |
| 4 | **Change 내용** | [헤드라인]/[이미지]/[CTA] 슬롯 — 무엇으로 바뀌는지 | Scene description |
| 5 | **스타일 정합** | 시그널플래너 디자인 가이드(무그림자·단일 강조색 `#501EFF`·카드 16px·Pretendard 2웨이트)에 맞추라는 지시 — `design-rules-for-mockup.md` ③ | Camera and lighting(톤 일치) |
| 6 | **출력 규격** | 입력과 같은 해상도·비율 유지 | Resolution |

원본 6부와 순서가 다른 이유: 제품 목업은 "빈 장면에 제품을 배치"하는 순서지만, 앱 편집은 "이미 완성된 화면 하나를 받아 그 안의 일부만 도려내는" 작업이라 Preservation을 Scene보다 먼저 둬야 한다. Preservation을 뒤로 미루면 모델이 이미 화면 전체를 재구성한 뒤에야 "아 참, 나머지는 유지해야 했지"를 보게 되고, 실측상 이 경우 레이아웃이 흔들린다.

### 각 부의 표준 문장 (영어 — 이유는 ⑤ 참고)

1. **Task 선언**
   ```
   Edit the attached mobile app screenshot.
   ```

2. **Preservation (양보 불가)**
   ```
   Keep the overall layout, colors, fonts, status bar, navigation, and all other UI elements exactly as in the attached screenshot. Do not redesign.
   ```

3. **Target 지목** — [노출 위치] 슬롯을 그대로 옮긴다
   ```
   Only replace the section titled "..." / the area at ...
   ```

4. **Change 내용** — [헤드라인]/[이미지]/[CTA] 슬롯을 그대로 옮긴다. 한글 문구는 따옴표로 정확히 지정한다 (⑤ 참고)

5. **스타일 정합** — 시그널플래너 디자인 가이드 문장을 쓴다. **기본 문장 1개 + 이번 변경에 해당하는 조건 문장(최대 3개)**을 `design-rules-for-mockup.md` ③에서 골라 넣는다. 아래는 기본 문장이다.
   ```
   Match the Signal Planner app design system for the changed area only: flat design with no drop shadows and no outlines around cards; the single accent color is violet #501EFF; text in dark gray #212529 or #495057; Korean sans-serif (Pretendard style) in regular or bold weight only, no oversized display type. Do not restyle anything outside the changed area.
   ```
   - 디자인 가이드는 **바뀌는 영역에만** 적용한다. control의 다른 영역이 가이드와 달라도 고치지 않는다 — 우선순위는 E2 명세 > control 보존 > 디자인 가이드다(`design-rules-for-mockup.md` ①).

6. **출력 규격**
   ```
   Same aspect ratio and resolution as the input.
   ```

## ③ E2 4슬롯 → 프롬프트 조립표

| E2 슬롯 | 조립되는 부 | 비고 |
|---|---|---|
| [노출 위치] | 3부 Target 지목 | 슬롯 값이 "화면 상단" 같은 표기만이면 이 가이드로 넘어오기 전에 명세를 다시 채운다 (§4-1 좋은 예 수준 필요) |
| [헤드라인] | 4부 Change 내용 | 한글 문구는 따옴표 + "Render this Korean text exactly as written" 병기 |
| [이미지] | 4부 Change 내용 | "변경 없음"이면 이 슬롯은 프롬프트에 아예 넣지 않는다 — 없는 것을 "바꾸지 마라"고 쓰면 오히려 모델이 그 영역을 주목하게 만든다. **아이콘·캐릭터·사물이 필요하면 새로 그리게 하지 않고 자리표시로 두며**, 들어갈 브랜드 에셋 파일은 에셋 지정표로 따로 넘긴다 (`design-rules-for-mockup.md` ④) |
| [CTA] | 4부 Change 내용 | "변경 없음"이면 마찬가지로 프롬프트에서 생략 |

### 워크드 예시 (HYP-A-008 소재 — 실제 조립된 프롬프트 전문)

> 아래는 공개된 가설 명세 구조(`hypothesis-backlog-A.md` HYP-A-008)를 이용한 **예시**다. 실측 수치가 아니라 조립 형식 참고용이다.

**E2 명세 입력값**
- control: 점검신청 화면의 「지금 내 보험, 괜찮은 걸까?」 섹션(질문 말풍선 3개)
- [헤드라인] = `"OO님 보험, 여기가 비어 있어요"` — 평서형 단정
- [이미지] = 6개 핵심 보장 아이콘(암·심장·뇌혈관·실손·운전자·치아) 중 부족 항목 표시하는 진단 카드
- [CTA] = 변경 없음
- [노출 위치] = 기존 「지금 내 보험, 괜찮은 걸까?」 섹션 자리 그대로, 레이아웃 위치 유지

**조립된 프롬프트 (영/한 혼용)**
```
Edit the attached mobile app screenshot.

Keep the overall layout, colors, fonts, status bar, navigation, and all
other UI elements exactly as in the attached screenshot. Do not redesign.

Only replace the section titled "지금 내 보험, 괜찮은 걸까?" (the three
speech-bubble question cards) — do not move or resize this section's
position on the screen.

Replace its content with a personal coverage-gap diagnosis card:
- Headline text (render this Korean text exactly as written, in quotes):
  "OO님 보험, 여기가 비어 있어요"
- Below the headline, show 6 coverage-type slots in a row (암/cancer,
  심장/heart disease, 뇌혈관/cerebrovascular, 실손/indemnity,
  운전자/driver, 치아/dental), each slot paired with a small status mark
  distinguishing "충분" (sufficient) from "부족" (insufficient) —
  use a visually distinct but style-consistent mark for the "부족" state
  (e.g. a filled warning dot), not a color outside the app's existing
  palette.

Match the Signal Planner app design system for the changed area only:
flat design with no drop shadows and no outlines around cards; the
single accent color is violet #501EFF; text in dark gray #212529 or
#495057; Korean sans-serif (Pretendard style) in regular or bold weight
only, no oversized display type. Do not restyle anything outside the
changed area.
Any new card has 16px rounded corners, no shadow, no border, and about
20px inner horizontal padding; rows inside a card are separated only by
a thin 1px #E9ECEF horizontal line.
Mark shortfalls in red #F03E3E and surpluses in violet #501EFF; do not
use green, sky blue, or yellow as UI fills.
Where an icon or illustration is needed, do not draw a new one: place a
plain light-gray #E9ECEF rounded placeholder square at the same size as
comparable icons in the screenshot.

Same aspect ratio and resolution as the input.
```

이 예시에서 [CTA]는 "변경 없음"이므로 프롬프트에 CTA 관련 문장이 아예 없다 — ③표의 규칙대로다. 5부에는 기본 문장 + 조건 문장 3개(새 카드 · 부족/잉여 표시 · 아이콘 자리표시)가 들어갔다 — 6개 보장 아이콘은 모델이 그리지 않고 자리표시로 두며, 들어갈 에셋(예: 치아 `obj-tooth-healthy.png`, 운전자 `icon-multicolor-car.png`)은 **에셋 지정표**로 디자이너에게 넘긴다(`design-rules-for-mockup.md` ④). 파일명은 프롬프트에 적지 않는다.

## ④ 참조 이미지 어법

`media-gemini-3-image-prompt`의 reference-images.md 어법을 이 스킬 맥락으로 좁힌 것이다.

- **control 스크린샷 1장이 기본**이다. 프롬프트 안에서 "the attached screenshot"으로 지목하면 충분하고, 별도 "Image 1" 라벨은 필요 없다.
- **참고 시안(무드보드·경쟁사 캡처 등)이 추가로 있으면** Image 1/Image 2 슬롯 어법으로 구분한다:
  ```
  Image 1: the control screenshot to edit (attached).
  Image 2: style reference for the diagnosis card layout — match its
  card shape and icon style, not its copy or colors.
  ```
- **3장 이하로 제한한다.** reference-images.md의 원칙대로, 이 스킬의 편집 작업은 "단순 스타일 전이" 급이라 참조가 많을수록 모델이 우선순위를 잃는다. control 1장 + 참고 시안 최대 2장을 넘기지 않는다.
- 참조 이미지를 여러 장 쓸 때는 각 이미지가 **무엇을 위해** 참조되는지(레이아웃인지, 컬러인지, 카피 톤인지)를 반드시 한 줄로 명시한다. "참고해줘"처럼 역할을 안 적으면 모델이 참조 이미지의 전체를 따라 하려다 control의 레이아웃을 깨뜨린다.

## ⑤ 한글 문구 처리 지침

실측 한계: 같은 계열 작업에서 한글 문구가 두 차례 깨진 사례가 확인됐다 — "슈퍼대디 리얼씬"이 "슈부대디 리열선"으로, "33,660원"이 "33,660은"으로 렌더링됐다. 작은 글자·한글 글리프는 프롬프트만으로 정확도를 보장할 수 없다 (`prompt-patterns.md`(product-mockup 플러그인 동봉 — 이 스킬 폴더에는 없다) "What did not work" 항목과 같은 맥락 — 구조·바인딩은 재생성으로 고쳐지지만 작은 텍스트는 안 고쳐진다).

이 한계를 프롬프트 쪽에서 다루는 규칙 3개다.

**(a) 문구는 짧게, 따옴표로 정확히 지정하고 명시적으로 요구한다.**
```
"OO님 보험, 여기가 비어 있어요" — render this Korean text exactly as written.
```
문구를 서술형으로 풀어 쓰지 않는다("보험이 부족하다는 문구를 넣어줘" 같은 지시는 모델이 문구를 새로 창작하게 만든다).

**(b) 생성 후 글자 단위 대조는 이 가이드의 소관이 아니다.** 생성된 이미지가 지정한 한글 문구와 글자 하나까지 일치하는지 검수하는 게이트는 스킬 본체(SKILL.md)가 맡는다. 이 가이드는 검수를 통과할 가능성을 높이는 **프롬프트 쪽 대비**까지만 다룬다.

**(c) 2회 재생성에도 문구가 계속 깨지면, 그 문구 영역을 비우는 프롬프트로 전환한다.**
```
Leave the headline area as an empty text placeholder box (no text
rendered) so the correct Korean copy can be added separately.
```
세 번째 프롬프트 라운드로 같은 문구를 다시 시도하지 않는다 — `prompt-patterns.md`의 컷오프 규칙과 같은 이유다. 작은 텍스트 결함은 재생성으로 안 풀리는 결함이라는 실측 기록이 있고, 세 번째 라운드는 일정만 갉아먹는다.

**(d) 디자인 절대 규칙 위반이 2회 재생성 뒤에도 남으면, 위반 영역 비움 프롬프트로 전환한다 (계약 §7-19).** 규칙에 맞는 문장 하나를 고르고, 중괄호는 이번 요소로 바꾼다. §7-13 비움(c)과 동시에 필요하면 두 문장을 함께 넣어 **1회**만 생성한다.

| 남은 위반 | 비움 문장 |
|---|---|
| ③ 새로 그린 아이콘·캐릭터·사물 | `Replace the {element} with a plain light-gray #E9ECEF rounded placeholder square of the same position and size — no drawing inside it.` |
| ① 카드 그림자·외곽선 | `Keep the text and layout of the {element}, but render its surface as a completely flat #F1F3F5 area with no shadow and no border.` |
| ② 금지 fill (초록·하늘·노랑 버튼·배지·카드) | `Keep the text and layout of the {element}, but change its fill to flat neutral gray #CED4DA (cards: #F1F3F5) with no green, sky blue, or yellow.` |

①·②는 요소를 통째로 비우지 않는다 — 카드·버튼 안의 헤드라인·CTA까지 사라지기 때문이다. 이 비움 초안도 통과하지 못하면 재시도하지 않고 착지를 포기한다(`없음 — 제작 요청 명세로 대체`).

## ⑥ 재생성 강화 문장 카탈로그

결함 하나당 **문장 1개만 추가**한다. 프롬프트 전체를 다시 쓰지 않는다 — `prompt-patterns.md`의 reinforcement catalogue와 같은 방식이다.

| 결함 | 추가할 문장 |
|---|---|
| 한글 깨짐 (짧은 문구인데도) | "Render the Korean text character-by-character exactly as specified in quotes — do not paraphrase, translate, or invent alternate wording." |
| 레이아웃이 바뀜 | "Do not change the position, size, or spacing of any element outside the specified section — the rest of the screen must be pixel-identical to the input." |
| 지정 안 한 요소까지 바뀜 | "Every UI element not explicitly mentioned above must remain unchanged, including icons, colors, and text elsewhere on the screen." |
| 스타일이 앱과 이질적 | "The new element must use the same corner radius and color palette already visible in the attached screenshot, with no drop shadow — do not introduce a new visual style." |
| 디자인 가이드 이탈 (그림자·외곽선·금지 fill·새로 그린 아이콘 등 — `design-rules-for-mockup.md` ⑤에서 게이트 행 ❌ 위반 또는 권고 행 ⚠️ 이탈인 항목) | "In the changed area, remove the {이탈 항목 — 예: drop shadow / card outline / green fill / drawn icon} — Signal Planner cards are flat white or #F1F3F5 surfaces with 16px corners, and #501EFF is the only accent color." (중괄호는 이번 이탈 항목 하나로 바꿔 쓴다) |
| 비율·해상도 변형 | "Output must have the exact same pixel dimensions and aspect ratio as the input image — do not crop, letterbox, or resize." |
| 텍스트가 흐릿함 | "Render all text at full sharpness and legibility, matching the font weight and size of comparable text elsewhere in the screenshot." |

강화 문장의 공통 패턴: **모호한 재확인("더 정확하게 해줘") 대신 구체적인 대상·개수·기준을 이름으로 지목**한다. `prompt-patterns.md`가 확인한 일반 원칙과 같다 — 막연한 강조는 안 먹히고, 구체적인 지목은 먹힌다.

**같은 결함이 반복될 때 (에스컬레이션)**: 1차 재생성에서 넣은 문장과 같은 문장을 2차에 그대로 재투입하지 않는다 — 상한 2회 중 1회를 낭비하는 일이다. 2차에는 그 문장을 **프롬프트 4부(Change) 맨 앞으로 옮기고** 문두에 `MUST:`를 붙여 우선순위를 올린다 (프롬프트는 앞에 올수록 주의를 더 받는다 — `prompt-patterns.md`의 순서 원칙). 그래도 실패하면 재생성이 아니라 문구 영역 비움 전환이다 (⑤-c).

## ⑦ 하지 말 것

- **화면 전체 리디자인 요청.** "더 예쁘게", "전체적으로 개선해줘" 같은 지시는 control과 비교 불가능한 결과를 만든다. 항상 단일 축 변경으로 좁힌다.
- **브랜드 에셋 흉내 그리기.** 시그널플래너 아이콘·캐릭터 선명이·사물 일러스트를 모델이 새로 그리게 하지 않는다. 자리표시 + 에셋 지정표로 넘긴다 (`design-rules-for-mockup.md` ④).
- **control 영역을 디자인 가이드에 맞춰 "교정".** 지정 밖 영역은 가이드와 달라도 그대로 둔다 — 대조군 보존(§7-15)이 가이드보다 앞선다.
- **실존 브랜드 로고·실사진 인물 합성.** 실제 보험사 로고, 실제 인물 사진을 화면에 합성하도록 요청하지 않는다.
- **확정 안 된 문구 창작.** E2 명세가 정본이다 — 명세에 없는 카피를 모델이 지어내게 하는 프롬프트("적절한 문구를 넣어줘")는 금지한다. 문구가 아직 안 정해졌으면 프롬프트를 조립하지 말고 명세부터 채운다.
- **마스킹 안 된 스크린샷 사용.** 보험 도메인 PII가 담긴 control 스크린샷을 마스킹 없이 외부 API로 보내지 않는다. 이 금지는 스킬 게이트가 기술적으로 막지만, 프롬프트를 조립하는 사람도 마스킹 여부를 프롬프트 작성 전에 스스로 확인해야 한다.
