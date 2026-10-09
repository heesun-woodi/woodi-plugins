# 프롬프트 패턴 — 지게차 교육 블로그 AI 이미지

`scripts/gen_image.py`가 표의 프롬프트 앞뒤에 아래 공통 접두/접미를 **자동으로** 붙인다. 표의 `프롬프트` 칸에는 장면 설명만 쓴다(영어, 한 문장~두 문장, `|` 문자 금지).

## 공통 접두/접미 (gen_image.py `PROMPT_PREFIX`·`PROMPT_SUFFIX`와 글자 그대로 같아야 함)

- 접두: `photorealistic, Korean forklift training yard / warehouse, no text, no letters, no watermark, no close-up faces`
- 접미: `natural light, wide landscape 3:2 composition, people only seen from behind or far away, no brand logos, no readable signs, no license plates, no numbers`

최종 프롬프트 = `<접두>. <장면 설명>. <접미>.` — 둘 중 하나를 바꾸면 스크립트 상수도 함께 바꾼다(`tests/test_gen_image.py`가 대조한다).

## 장면 유형별 패턴

`{…}`는 글마다 바꾸는 변주 슬롯이다(아래 "변주 지침").

| # | 장면 유형 | 쓰는 슬롯(목적) | 패턴 |
|---|---|---|---|
| 1 | 교육장 코스 주행 | 표지(`00` 배경), 절차 장면 | `a counterbalance forklift slowly driving through an S-shaped course marked with cones and white lines on an outdoor concrete training yard, {time}, {weather}, {angle}` |
| 2 | 실기시험 장면(멀리) | 시험 절 요약 | `a trainee operating a forklift on a practice course seen from far away, an examiner standing in the distance seen from behind holding a clipboard, {time}, {angle}` (심사관·응시자 모두 뒷모습·원거리, 클립보드에 글자 없음) |
| 3 | 전동 입식/좌식 지게차 장비 | 장비 소개, 과정 비교 | `an electric {stand-up reach / sit-down} forklift parked in a clean indoor warehouse aisle with tall racks, {angle}, {time}` (차체 로고·모델명 없음) |
| 4 | 팔레트 적재·하역 작업 | 중간 작업 장면(⑤ 최소 1장) | `forklift forks lifting a wrapped pallet onto a warehouse rack, operator seen from behind, {angle}, {time}` / `unloading pallets from a truck bed at a loading dock, {weather}` |
| 5 | 자격증·서류(글자 없이 추상화) | 접수·서류·자격 절 | `a neat desk with a blank card, a closed folder and a pen beside a small forklift scale model, soft {time} light, shallow depth of field, blank paper with no writing` |
| 6 | 안전 장비 착용 | 안전교육·준비물 절 | `gloved hands fastening a seatbelt inside a forklift cab, hard hat and high-visibility vest on the seat, {angle}` / `a worker seen from behind wearing a hard hat and safety vest walking toward a forklift` |
| 7 | 점검·정비(선택) | 운행 전 점검 절 | `close-up of a forklift mast chain and tire during a pre-operation check, gloved hand pointing, {time}` |

## 변주 지침 (같은 글 안, 그리고 글마다)

- 축 3개를 슬롯마다 바꾼다: **시간대**(`early morning`, `bright midday`, `late afternoon golden hour`, `overcast day`) · **앵글**(`eye-level wide shot`, `high-angle view`, `low-angle view from the ground`, `over-the-shoulder from behind the operator`) · **날씨/계절**(`clear autumn day`, `light drizzle with wet concrete`, `winter morning with breath visible`, `summer haze`).
- 한 글 안에서 같은 패턴 번호를 두 번 쓰면 시간대·앵글 둘 다 달라야 한다. 같은 장면 반복은 검수 불합격.
- 이전 글과의 반복을 줄이려고 `work/variation-log.md` 최근 글과 다른 표지 패턴(1~7)을 고른다.

## 금지

- 글자·숫자 렌더링(간판·현수막·자막·차체 문구·번호판·서류 내용) — 글자는 본문으로.
- 얼굴 클로즈업, 정면 인물 — 뒷모습·원거리·장갑 낀 손·장비 중심.
- 브랜드 로고·제조사 이름(클라크 포함)·실제 번호판.
- 실존 장소·학원 외관 재현, "시험장" 표지(금칙어 규칙과 같은 이유).
- 홍보 슬롯(학원 소개(실사진)·`type=홍보` 글)에는 AI 이미지를 쓰지 않는다 → photo.

## 표지용 배경 패턴 (`00` cover 행)

- 패턴 1·3·4 중에서 고른다. 프롬프트는 **글자 없는 배경 장면**만 쓴다(글자·로고·번호판 금지는 그대로). 제목·배지·전화번호는 `scripts/make_cover.py`가 위에 합성한다.
- 표지는 1:1 중앙 크롭으로 쓰이므로 **피사체를 화면 가운데에** 두는 변주 문구를 넣는다. 예: `..., subject centered in the frame, empty space above and below for text overlay` / `forklift in the middle of the frame, symmetrical composition`.
- 배경 파일은 `images/00-bg.png`에 저장되고 합성 결과가 `images/00-cover.png`다. 배경을 실사진으로 대체하려면 make_cover.py `--bg photos/<파일>`.

## 캡션(alt) 규칙 — 내부 메모

- 캡션은 내부 메모용이며 본문에 노출되지 않는다(업로드본은 캡션 없음). 한 줄로 무엇을 보여주는지만 적는다.
- "이미지는 AI 생성" 표기 여부는 `knowledge/design-system.md` ⑤를 따른다(규정이 없으면 표기하지 않는다).
- 캡션에 수치·일정·법령을 새로 넣지 않는다.
