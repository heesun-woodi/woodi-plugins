---
name: synthetic-why-debrief
description: >-
  Runs the post-experiment "why" debrief — an experiment has already launched and finished, the
  real outcome is known, but nobody knows why it happened. This skill assembles a laddering
  interview scenario from the real result (with the numbers stripped out so the persona never
  hears them), gates it for boundary violations, hands the assembled script to a human interviewer
  to run with `/nemotron-personas-korea:persona-interviewee`, then helps distill the transcript
  into at most 3 "why" candidates for the experiment's Notion doc §4. Use this ONLY after an
  experiment has real results — NOT before launch (that's synthetic-concept-test) and NOT for
  designing new problems (that's the problem-definition interview). Trigger on Korean phrases like
  "실험이 끝나고 왜 그렇게 나왔는지 모르겠다", "이 결과 왜 이렇게 나온 거지", "실험 결과 디브리프",
  "왜 이탈했는지 알아보자", and English "why did this experiment result happen", "post-experiment
  debrief", "find out why the result came out this way". Do NOT trigger before an experiment has
  launched or while it is still running — route those to synthetic-concept-test instead. Do NOT
  trigger for backlog entry, ICE scoring, or final KPI analysis — those are human decisions and a
  separate future results-analysis skill, both out of this skill's scope.
---

# Synthetic Why-Debrief (post-experiment "why" candidate generator)

> ⚠️ **이 스킬은 뼈대입니다.** 계약 v0.1(`_specs/wd-output-contract.md`) 기준으로 **STEP 0~4까지 동작**하며, W2 문안 실례·laddering 질문의 실험 맥락별 변형·W5 교차 확인 경계 사례("다른 장면"의 판정 기준)는 SP1 실험 결과가 나온 뒤 v1.0에서 확정됩니다.

**정본은 `references/output-contract.md`다.** 표 이름·열 순서·값 도메인·판정 질문이 이 문서와 다르면
계약이 이긴다. 아래 각 STEP의 판정 질문은 계약 §7의 문구를 **그대로** 옮긴 것 — 스킬이 실행 시점에
반드시 이 질문을 출력한다.

## What this skill is — and is NOT

An experiment has already run and produced a real number: a drop-off point, a conversion that
didn't happen, a step people skipped. That number tells you *what* happened. It does not tell you
*why*. This skill exists to close that gap **without letting the synthetic interview cheat** —
synthetic respondents don't push back on a false premise, and if you hand them the real numbers or
ask them to explain the result, they'll happily fabricate a clean-sounding reason that means
nothing (킷 §6-③·§9-1).

So this skill does three things and refuses to do a fourth:

1. Turns the real result into a scenario a persona can *live through* — with every number, every
   mention of "the experiment," stripped out.
2. Runs a boundary check + a domain-expert gate before anything goes near a persona.
3. After a human-led interview comes back, helps distill it into **at most 3** "why" candidates.
4. **Refuses** to decide anything past that — no backlog entry, no ICE score, no confirmed cause,
   no confidence upgrade, no reliability grade above `C`.

```
launched experiment → real result → THIS SKILL → 'why' candidates → HUMAN decides backlog entry
                                      (scenario + gate + distill)
```

## The one rule that breaks everything if ignored

> Synthetic personas do not argue with a false premise. Show one a made-up scenario and it will
> perform that scenario flawlessly, producing clean, confident-sounding data that hides the error
> (실측 사례: 100명 전원이 비현실적 시나리오를 그대로 연기해 그럴듯한 숫자를 만들었다 — 킷 §6-③).
> The same failure mode applies here in reverse: if you let the real number or the word "실험"
> reach the persona, they'll rationalize backward from it instead of reacting to a lived scene.

That is why STEP 1, STEP 2, and GATE exist as hard checks with literal pass/fail questions, not
narrative suggestions.

## STEP ↔ 표 ↔ 파일 ↔ 착지 대응 (계약 §1)

| STEP | 표 | 파일 | 착지 |
|---|---|---|---|
| STEP 0 | **W0** 인테이크 (2열 6행) | `intake.md` | ✗ 대화 + 파일 |
| STEP 1 | **W1** 경계 선언 체크 (3열) ★하드 | `intake.md`에 이어 기록 | ✗ 대화 + 파일 |
| STEP 2 | **W2** 시나리오 명세 (3열) ★하드 | `scenario.md` | ✗ 대화 + 파일 |
| STEP 2 | **W3** 표집 조건 (2열 5행) | `scenario.md`에 병기 | ✗ 대화 + 파일 |
| STEP 2 | **W4** laddering 스크립트 (3열) | `scenario.md`에 병기 | ✗ 대화 + 파일 (참가자에게 전달) |
| — | (인터뷰 — 참가자 주도, 스킬 외부) | `persona-interviewee --save` 트랜스크립트 | — |
| STEP 3 | **W5** '왜' 후보 (4열, 최대 3행) ★하드 | `candidates.md` | ✅ W6a 경유 |
| STEP 4 | **W6a** 노션 4장 착지 블록 (코드블록) ★착지 | — | ✅ 노션 4장 「'왜' 후보」 |

### run 디렉토리 (계약 §1 — ct보다 가볍다)

```
${SQR_RUNS_DIR:-research/runs}/<YYYY-MM-DD>-<slug>-wd/
├── intake.md      # W0 + W1
├── scenario.md    # W2 + W3 + W4 — GATE 통과 후 잠긴다
├── <ts>-<uuid8|RSP-n>.md   # persona-interviewee --save 트랜스크립트 (참가자가 생성, 이 폴더로 이동)
└── candidates.md  # W5
```

인터뷰가 사람 주도이므로 `ct`의 manifest·UUID 불변식·batch draw 스크립트를 승계하지 않는다.

---

## STEP 0 — 인테이크 (계약 §2-3 · W0 6행)

6개 필드를 확보한다: WD run ID(제안만, 확정은 사람) · HYP ID·EXP ID · 축(A/B) · **실측 결과**(무엇이
어떻게 나왔나) · **노출 세그먼트 조건** · **시나리오 검토 완료 기록** — `{이름} / {역할(상담사·해당
축 PM 중)} / {검토 날짜}`.

- 실측 결과가 없으면(런칭 전이거나 진행 중) **여기서 멈추고 되돌린다** — 그 경우는
  `synthetic-concept-test`(런칭 전) 소관이다.
- 시나리오 검토가 아직 완료되지 않았으면 이 필드에 `검토 대기 — {담당}`을 넣는다. **이름만 있고
  역할·날짜가 없는 것은 완료 기록이 아니다** — GATE 통과 조건이라는 것을 이 시점에 참가자에게 미리
  알린다(아래 "참가자에게 실제로 말할 대사" 참고).

`intake.md`에 W0 6행을 기록한다.

**다음**: STEP 1

---

## STEP 1 — 경계 선언 체크 (계약 §3-2 · W1)

킷 §6-④ 경계 선언 4항을 이 세션에 대고 하나씩 확인한다.

| # | 경계 항목 | 이 세션에서의 확인 | 판정 |
|---|---|---|---|
| 1 | 합성으로 실험 결과를 재현하지 않는다 | | |
| 2 | 합성으로 A/B를 시뮬레이션하지 않는다 | | |
| 3 | 오직 '왜' 가설을 만들기 위한 것 — 결과를 해석시키지 않는다 | | |
| 4 | 실측 숫자는 시나리오의 재료로만 쓴다 | | |

**하드 규칙(계약 §3-2)**: 4항 중 하나라도 `위반 우려`면 **STEP 2로 넘어가지 않는다** — 문구를 고쳐
재확인한다. `intake.md`에 표를 이어서 기록한다.

**다음**: STEP 2

---

## STEP 2 — 시나리오 + 표집 조건 + laddering 스크립트 조립 (계약 §3-3~§3-5 · 하드 §7-1·§7-2·§7-3)

### 2-1. W2 시나리오 문장 조립

*"당신은 [화면/단계]에서 [실제로 관찰된 행동]을 했습니다."* 형태로 쓴다 — 관찰된 행동만.

**판정 질문(필수 출력)** — *"W2 시나리오 문장에 실측된 행동 외의 추측·이유가 섞여 있는가?"* (계약
§7-2)
- **"아니다"(=섞여 있다)일 때**: 문장을 관찰된 행동만 남기고 다시 쓴다. **STEP 2를 통과시키지
  않는다.**

### 2-2. W3 표집 조건

행 5개: `ICP 카드`(킷 §3 번호·이름 그대로) · `노출 세그먼트와 동일 조건` · `N`(2~3) · `표집 경로`
(데이터셋 UUID / 인구통계 호출) · `시드`(데이터셋 경로면 값, 아니면 `해당 없음 — 인구통계 호출
경로`).

- 행동 경험 조건은 **"관심 있는 사람"이 아니라 "그 실험에 실제로 노출된 사람"**으로 좁힌다.
- 시드를 남겨도 신뢰등급을 올리지 않는다 — STEP 4에서 항상 `C`로 고정한다(계약 §3-7).

### 2-3. W4 laddering 스크립트 조립

5단(행동·장면 → 감정 → 가치(한 번 더 왜) → 대체 행동 → 반사실)을 킷 §6-④ 5문항 그대로 또는 이
맥락에 맞춘 변형으로 채운다. **한 번에 한 질문** — 스크립트 전체를 한 번에 던지지 않는다.

**판정 질문(필수 출력)** — *"인터뷰 스크립트(W4) 어디에도 페르소나에게 결과를 해석시키는 질문이
없는가?"* (계약 §7-1)
- **"아니다"일 때**: 해당 질문을 삭제하고 laddering 5단 중 하나로 재구성한다.

### 2-4. 금지 어휘 검사 (W2·W4 공통)

**판정 질문(필수 출력)** — *"W2·W4 문안에 정규식 `\d` 매치가 하나도 없고, `실험`·`A/B`·`전환율`도
없는가?"* (계약 §7-3)

- 검사 대상은 리터럴 문자열(`실험`·`A/B`·`전환율`)뿐 아니라 **숫자를 포함한 모든 표현(정규식
  `\d`)**이다. `몇 %`만 보면 `23%`·`0.7%p`·`3명 중 2명` 같은 표현을 놓친다.
- **"아니다"일 때**: 발견된 표현을 지우고 재조립한다. 참가자에게 이미 넘겼다면 회수하고 정정본을
  다시 넘긴다.

`scenario.md`에 W2·W3·W4를 함께 기록한다. **GATE 통과 후 임의로 고치지 않는다.**

**다음**: 🚦 GATE

---

## 🚦 GATE — announce, then stop (계약 §1 · 하드 §7-11)

STEP 2 끝, 시나리오·스크립트를 참가자에게 넘기기 전에 한 번 선다.

**판정 질문(필수 출력)** — *"시나리오를 누가 언제 검토했고, 그 기록이 W0에 남아 있는가?"* (계약
§7-11 — 이 규칙만 우회를 두지 않는다. **합성 응답자는 거짓 전제를 반박하지 않는다**(킷 §6-③) —
W2 2·3열 자체 검사만으로는 시나리오가 실측 사실과 다르게 왜곡됐는지 잡지 못하고, 다른 결함은 사후에
잡을 수 있지만 이것은 사전 검토밖에 방법이 없다. `synthetic-concept-test` §7-8과 같은 이유다.)
- **"아니다"일 때**: **GATE를 통과시키지 않는다.** 실무자 부재로 지연되면 W0 6행에 `검토 대기 —
  {담당}`으로 두고 세션을 멈춘다. **등급을 낮춰 진행하는 우회는 두지 않는다.**

확인 사항을 모두 나열해 보고하고 **여기서 멈춘다**:

> "**🚦 GATE — 참가자에게 스크립트를 넘기기 전 확인입니다. 여기서 멈추고 확인을 받겠습니다.**
> - W1 경계 선언 체크: {4항 모두 통과 / 위반 우려 목록}
> - W2 시나리오: {관찰된 행동만 — 통과 / 혼입 발견}
> - 금지 어휘 검사(정규식 `\d` 포함): {통과 / 걸림 — 발견된 표현}
> - W3 표집 조건: {노출 세그먼트와 일치 / 불일치 사유}
> - **시나리오 검토 완료 기록(§7-11)**: {완료 — 이름/역할/검토 날짜 / 미완 — 검토 대기}
>
> 마지막 항목은 정본 계약 §7-11 「시나리오 사전 검토 게이트」입니다 — **합성 응답자는 거짓 전제를
> 반박하지 않습니다.** 위 자체 검사만으로는 시나리오가 실측 사실과 다르게 왜곡됐는지 잡지 못하기
> 때문에, 실무자 확인 없이는 다음 단계로 넘어가지 않습니다. 이 항목만은 등급을 낮춰 우회하는 길이
> 없습니다.
>
> 이대로 진행할까요, 고칠 부분이 있을까요?"

**어느 하나라도 미충족이면 진행을 거부한다**:

> "**GATE를 통과시킬 수 없습니다.** {W1 위반 우려 항목 / 시나리오에 남은 추측 / 금지 어휘 / 시나리오
> 검토 완료 기록 미비 — 이름만 있고 역할·날짜가 없음} 때문입니다. 이 부분을 먼저 고치겠습니다."

시나리오 검토가 아직 완료 기록(이름/역할/검토 날짜)으로 남지 않았다면, **검토 회신이 올 때까지
STEP 3로 넘어가지 않는다** — 등급을 낮춰 우회하는 길은 두지 않는다(§7-11).

**다음**: 사람의 확인(+ 실무자 검토)을 받은 뒤에만 — **W4 스크립트를 참가자에게 넘긴다.** 인터뷰는
**참가자가 직접** `/nemotron-personas-korea:persona-interviewee`로 진행한다. 스킬이 N명을 자동
디스패치하지 않는다 — §6-④ 인터뷰는 2~3명 심층이고, 사람이 흐름을 보며 파고드는 게 낫다. laddering
craft(one question at a time, funnel broad→deep)는 sibling skill
`synthetic-icp-interview/references/interview-craft.md`를 참고한다.

---

## STEP 3 — 후처리: 트랜스크립트 → W5 '왜' 후보 (계약 §3-6 · 하드 §7-4·§7-5·§7-6·§7-7)

참가자가 트랜스크립트를 가져오면 다음을 수행한다.

1. `[누가] [어떤 상황에서] [무엇 때문에] [어떤 행동을 한다]` 형태로 후보 문장을 뽑는다.
2. 각 후보에 **원문 인용**을 붙인다.
3. **확인할 실제 데이터**(앰플리튜드 이벤트 / 실제 UT / 상담사 인터뷰 중)를 붙인다.

**판정 질문(필수 출력)** — *"W5 행이 3개를 넘는가?"* (계약 §7-4)
- **"아니다"(=넘는다)일 때**: 셋으로 추리거나 laddering 3번(가치) 질문으로 더 파고들어 후보를
  좁힌다. 추리지 못하면 가장 근거가 약한 행부터 제외하고 사유를 `candidates.md`에 남긴다.

**판정 질문 ①(필수 출력 · 기계적)** — *"이 후보를 뒷받침하는 응답자가 2명 이상인가?"* (계약 §7-5)
- **"아니다"(=1명뿐)일 때**: 후보를 삭제하지 않는다. **4열에 `[단일 응답 근거 — 추가 확인 필요]`를
  병기**하고 W6a에도 그대로 옮긴다.

**판정 질문 ②(필수 출력 · 판단)** — *"응답자별 인용이 서로 다른 장면에서 나왔는가?"* (계약 §7-5)
- 명확히 같은 장면(같은 화면·같은 문구를 그대로 재인용)이면 후보에서 내린다.
- 판단이 불가하면 **`Warning`으로 표기**하고 후보는 유지하되 `장면 중복 여부 미확정`을 병기한다 —
  삭제하지 않는다.

**판정 질문(필수 출력)** — *"W5 1열(가설 문장)에 반사실 질문의 답이 그대로 원인으로 옮겨진 행이
있는가?"* (계약 §7-6)
- **"아니다"(=있다)일 때**: 그 행을 삭제하거나 "이건 솔루션 제안이지 원인이 아닙니다"로 재분류해
  후보에서 제외한다.

**판정 질문(필수 출력)** — *"트랜스크립트의 답변이 앞뒤가 지나치게 딱 맞는가? 서로 다른 응답자의
표현까지 똑같은가?"* (계약 §7-7)
- **"아니다"(=그렇다·매끄럽다)일 때**: 그 응답을 근거로 단독 채택하지 않고, 추가 교차 확인 없이는
  후보에 올리지 않는다.

`candidates.md`에 W5를 출력한다.

**다음**: STEP 4

---

## STEP 4 — 노션 4장 착지 블록 (계약 §3-7 · 하드 §7-8·§7-9·§7-10)

W6a 코드블록을 4부 구성으로 출력한다.

**1부 — 경고문 (하드 §7-10 — 문구를 고치거나 줄이지 않는다)**

> ⚠️ 아래는 합성 인터뷰 결과로, 가설이지 근거가 아닙니다. 실제 고객 UT·상담사 인터뷰로 검증 전까지
> 확정된 문제로 취급하지 마세요.

**판정 질문(필수 출력)** — *"산출물 최상단에 이 경고문이 문구 그대로 있는가?"* (계약 §7-10)
- **"아니다"일 때**: 넣고 다시 출력한다. **경고문이 없는 산출물은 착지시키지 않는다.**

**2부** — `⚠️ 이건 가설입니다` 배너.

**3부** — W5 전문(최대 3행): 가설 문장 · 원문 인용 · 확인할 실제 데이터 · 교차 확인(`[단일 응답 근거
— 추가 확인 필요]` 또는 `장면 중복 여부 미확정` 표기 포함).

**4부** — 근거 지위 + 다음 단계 안내:

```
근거유형 합성 · Confidence 상한 1~3
신뢰등급 C — 단일 run·대조군 없음 (킷 §9-3)
백로그 등재는 사람이 판단합니다 — 이 블록은 등재가 아닙니다
```

**판정 질문(필수 출력)** — *"W6a에 근거유형 `합성`과 Confidence 상한 1~3이 적혀 있는가?"* (계약
§7-8 — 정본은 `hb-output-contract.md` §2-6·§7-4, 이 스킬은 인용만 한다)
- **"아니다"일 때**: 4부에 추가한다. 이미 착지했으면 정정한다.

**판정 질문(필수 출력)** — *"이 산출물 어디에도 「백로그에 등재했다/한다」는 확정 문장이 없는가?
W6a에 등재 여부를 사람에게 넘긴다는 안내가 있는가?"* (계약 §7-9)
- **"아니다"일 때**: 등재 관련 확정 문장을 삭제하고 `백로그 등재는 사람이 판단합니다`로 대체한다.

- **신뢰등급은 항상 `C`로 고정한다** — 등급 산출 절차를 두지 않는다. W3에 시드를 남겨도 이 계약은
  등급을 올리지 않는다(대조군 arm·사전등록이 애초에 없는 설계라서다).

착지 위치는 노션 **4장** 「'왜' 후보」 소절 하나다. **4장의 결과·배움·후속 액션 칸은 건드리지
않는다** — 범위 밖. 백로그 링크나 ICE 값을 이 블록에 넣지 않는다.

**세션 종료**: 노션 기입은 참가자가 한다. run 디렉토리 파일은 착지물이 아니라 재현성 증빙이다.

---

## Lines to actually say to the participant

When capturing W0 and the review owner isn't confirmed yet:

> "실무자(상담사 또는 해당 축 PM)가 시나리오를 검토해야 GATE를 통과할 수 있어요. 지금 담당자
> 이름만 정해도 괜찮지만, GATE를 통과하려면 '누가 검토했다'는 이름뿐 아니라 **역할과 검토 날짜까지
> 기록**돼야 해요 — 이름만 있으면 아직 '검토 대기' 상태로 봐요."

When they try to drop a real number into the scenario:

> "이 문장에 숫자나 '실험'이라는 말이 들어가면 페르소나가 결과를 보고 이유를 지어내기 시작해요.
> '%'나 '몇 %' 형태가 아니어도 숫자 자체가 걸려요 — 시나리오에는 '무엇을 했다'만 남기고, 숫자는
> 인테이크에만 남겨둘게요."

When they try to confirm a cause mid-interview ("이게 원인이네요"):

> "잠깐만요 — 그건 아직 가설이에요. 페르소나 한 명이 그렇게 말했다고 확정할 수는 없고, 최소 2~3명이
> 서로 다른 장면에서 같은 방향을 말해야 근거가 튼튼한 후보가 돼요. 지금은 일단 왜 그렇게 느꼈는지
> 한 단계만 더 물어봐 주시겠어요?"

When the interview surfaces 5+ candidates:

> "후보가 다섯 개가 넘게 나왔는데, 이건 좋은 신호가 아니라 인터뷰가 아직 얕았다는 신호예요. 깊게 판
> 인터뷰는 후보가 적고 뾰족하게 나와요. 가장 강하게 반복된 것부터 세 개만 추리거나, 남은 시간에
> '가치' 질문(3번)을 한 번 더 파고들어 볼까요?"

When only one respondent supports a candidate:

> "이 후보는 지금 한 명 응답만 근거예요. 지우지는 않고 '단일 응답 근거 — 추가 확인 필요'로 표시해서
> 남겨둘게요. 다음에 한 명 더 확인되면 그때 정식 후보로 올리면 돼요."

When they hand over a counterfactual answer as if it were the cause:

> "5번 질문 답변은 '이랬으면 좋았겠다'는 개선안에 가까워요. 그건 원인이 아니라 솔루션 제안이라서,
> 가설 문장 칸이 아니라 참고로만 남겨둘게요."

When they ask to enter a candidate straight into the hypothesis backlog:

> "이 스킬은 '왜' 후보까지예요. 백로그에 정식으로 올릴지는 그루밍/백로그 세션에서 사람이 판단하는
> 부분이라, 여기서는 후보와 근거만 정리해서 노션 4장에 남겨드릴게요."

When they ask why the reliability grade is stuck at C even with a dataset seed:

> "시드를 남기면 재현성은 확인할 수 있지만, 이 절차는 원래 단일 run·대조군 없음으로 설계돼 있어서
> 등급은 항상 C예요. B로 올리려면 대조군 arm과 사전등록이 있어야 하는데, 이 스킬은 그 설계 자체를
> 하지 않아요."

## Reference files

- `references/output-contract.md` — synced copy of the v0.1 contract (repo copy at
  `MFL-experimentation/habitfactory/prep-week/_specs/wd-output-contract.md` is SSOT).
- Sibling skill `synthetic-icp-interview/references/interview-craft.md` — laddering technique,
  live-probe convention, and the bracket convention for `persona-interviewee` mode. Read before
  handing off the script.
