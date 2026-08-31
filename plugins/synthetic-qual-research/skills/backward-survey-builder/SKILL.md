---
name: backward-survey-builder
description: >-
  Designs backward-design survey instruments for SYNTHETIC-user qualitative research —
  where LLM personas (nemotron-personas-korea) answer the survey, not real humans.
  Use this whenever the user wants to build a survey, questionnaire, poll, or interview
  guide to run against synthetic/AI personas, OR wants a survey designed "backward" from a
  business goal or decision (not from a list of questions). Trigger on Korean phrases like
  "설문 만들어줘", "합성사용자 조사", "페르소나한테 물어볼 설문", "backward design 설문",
  "정성조사 설계", "타겟한테 뭘 물어볼지" and English "design a survey", "questionnaire for
  personas", "synthetic user research". Also trigger when the user states a goal (e.g. "설명회
  신청을 늘리고 싶어") and asks what to ask the target audience. Produces a research matrix
  (goal → evidence → research questions → items), a synthetic-respondent-ready survey with
  every item tagged to a research question, and an analysis-to-decision plan — then hands off
  to nemotron-personas-korea:dispatch-strategy for actually collecting responses.
---

# Backward Survey Builder (for synthetic-user qualitative research)

## What this skill is for

Most surveys are built forward: someone lists questions they're curious about, and hopes
the answers add up to something useful. They rarely do. **Backward design inverts this**:
start from the decision you need to make, work back to the evidence that would settle it,
and only then write questions. Every item earns its place by feeding a specific decision.

This skill is specialized for one context: **the respondents are synthetic** — LLM personas
(here, the `nemotron-personas-korea` Korean-adult personas) role-play the target audience and
answer. That changes how items must be written (see Phase 3). The skill's job ends at a
finished, analysis-ready survey plus a dispatch handoff; it does **not** run the personas
itself — that's `nemotron-personas-korea:dispatch-strategy`.

## The core principle

> A question that cannot change a decision does not belong in the survey.

Hold every candidate item against this. If you can't name the decision an item informs, cut it.
This is the single most important discipline the skill enforces — it's what makes a 20-item
survey worth more than a 60-item one.

## Workflow overview

Four phases, in order. Phase 1 (backward-design matrix) is the required backbone — never skip
it, even when the user hands you a goal and expects questions immediately. The matrix is what
prevents a forward-built survey from sneaking back in.

```
Phase 0  Capture the goal        → decision + knowledge sought + audience
Phase 1  Backward-design matrix  → goal → evidence → RQs → question areas   [REQUIRED]
Phase 2  Generate the survey     → items, each tagged →RQ#, sections
Phase 3  Make it synthetic-ready → closed-form reliability + debias
Phase 4  Analysis-to-decision    → how findings become the decision + handoff
```

---

## Phase 0 — Capture the goal (before anything else)

You need three things. If the user gave a rich brief (like a goal + what they want to learn +
who the audience is), extract these from it and confirm. If any is missing or vague, ask —
briefly, one round, then proceed. Do not start designing without them.

1. **Decision / goal** — what real-world action does this research serve? ("9월 설명회 신청을
   최대화", "가격을 올릴지 결정", "온보딩 이탈을 줄일 기능 선택"). A goal framed as an action
   is what makes backward design possible. If the user only gives a topic ("공동육아 조사"),
   push once for the decision behind it.
2. **Knowledge sought** — what must you learn to serve that decision? ("어떤 매력 포인트가
   신청으로 이어지는가"). This is narrower than the topic and closer to the research questions.
3. **Target audience** — who is the (synthetic) respondent? ("만 1~2세 자녀를 둔 부모"). This
   later becomes the persona-filter for nemotron dispatch, so capture it in filterable terms
   (age, life-stage, role, region if relevant).

Reflect these back in one or two lines and continue. Don't over-interview — the point of
synthetic research is fast iteration.

---

## Phase 1 — Backward-design matrix (the backbone) [REQUIRED]

Build the chain from goal to question areas explicitly. Present it as a table so the logic is
auditable — the user should be able to see why each research question exists.

**Step 1: State the goal chain.** Four rungs, top-down:

```
[Goal]      the decision/action
   ↑
[Evidence]  what data would let you make that decision confidently
   ↑
[Knowledge] what you must learn (from Phase 0)
   ↑
[Survey]    the survey's job in one line
```

**Step 2: Derive Research Questions (RQs).** Decompose the knowledge into 3–5 RQs. Good RQs are
distinct, each answerable by evidence, and collectively sufficient for the decision. A useful
decomposition heuristic — cover **motivation** (what pulls them in), **barriers** (what stops
them), and **decision context** (how/where/with whom they decide). Surveys that ask only about
appeal but never about barriers can't explain "why do they like it but not sign up?"

**Step 3: Build the matrix.** One row per RQ:

| # | Research Question (알고 싶은 것) | Evidence needed (이게 나와야 답이 됨) | Question areas |
|---|---|---|---|
| RQ1 | … | the specific data that answers RQ1 | which item types will produce it |
| … | … | … | … |

The middle column is the discipline: if you can't say what evidence answers an RQ, the RQ is
too vague to survey. Fix it before writing items.

If the user's goal is **conversion** (sign-ups, purchases, retention), add a line noting that
the survey should also measure *intent* and *what drives intent*, so the analysis can connect
"which appeal → which action." See the conversion note in `references/analysis-patterns.md`.

---

## Phase 2 — Generate the survey

Now, and only now, write items. Work RQ by RQ so coverage is guaranteed. Rules that matter:

- **Tag every item** with the RQ it serves, e.g. `→RQ2`. An untagged item is a forward-built
  item that snuck in — cut it or find its RQ. The tags also drive Phase 4 analysis.
- **Mix closed and open, on purpose.** Closed-form items (Likert scales, ranking, single/multi
  choice) give you countable patterns — *what* and *how much*. Open-ended items give texture and
  language — *why*, in the respondent's own words. The standard move: closed-form to find the
  pattern, one open-ended nearby to explain it.
- **Sequence for the respondent, not the analyst.** Put an unaided open-ended impression *before*
  the item that lists options, so you capture raw associations before you prime them. Group by
  theme; don't ping-pong between topics.
- **Screening first, sensitive/commitment last.** Demographics and qualifiers up front (they
  also become persona filters); intent and any commitment ask at the end.
- **Keep choice sets tight.** ~6 options per closed item where you can; when a construct genuinely
  needs more (e.g. selection criteria), cap the respondent's job instead ("rank your top 3").

Use `assets/survey-template.md` as the output skeleton. It already encodes section order,
the tagging convention, and inline designer notes (`ⓘ`) explaining *why* each item is shaped
that way — keep those notes in the deliverable; they teach the user and justify the design.

**Optional — psychology frameworks.** If the user wants richer motivational/experience design
(or their environment already leans on it — e.g. product-psychology conventions), pull item
patterns from `references/psychology-frameworks.md` (BMAP, B.I.A.S, Peak-End, 6P storyboard,
loss aversion). These are *optional enhancers*, not required — backward design stands on its own.
Reach for them when the goal is behavioral (conversion, habit, motivation) rather than purely
informational.

---

## Phase 3 — Make it synthetic-respondent-ready

This is what separates this skill from a generic survey builder. The respondents are LLM
personas, which have distinct strengths and failure modes. Design to their grain.

Read `references/synthetic-respondent-design.md` before finalizing items — it's short and
specific. The essentials:

- **Closed-form is where synthetic respondents are most trustworthy.** Likert, binary, and
  multiple-choice answers from personas reproduce population patterns far better than free text
  does. Lean on them for your load-bearing measurements (the ones a decision hinges on).
- **Write Likert anchors explicitly and symmetrically.** "1 = 전혀 그렇지 않다 … 5 = 매우 그렇다",
  with a genuine neutral midpoint. Vague or lopsided anchors make persona responses cluster and
  destroy the signal. This matters more for synthetic respondents than human ones.
- **Debias the wording.** Avoid leading stems, balance positively- and negatively-keyed items
  (mix "이것이 매력적이다" with "이것이 망설여진다"), and don't telegraph the "right" answer —
  personas are eager to please and will drift toward whatever the question implies.
- **Open-ended items are for texture, not counts.** Treat free-text persona answers as plausible
  voice-of-customer language to mine for phrasing and themes, not as statistically reliable
  distributions.

---

## Phase 4 — Analysis-to-decision plan (+ handoff)

A survey isn't done when the questions are written — it's done when you can say how the answers
become the decision. Produce two things:

1. **Analysis plan** — a short table mapping each RQ to its load-bearing items and the analysis
   move (e.g. "RQ1: top-box % on B1 scale → rank appeal points → headline"). This is where you
   name which closed-form item settles which RQ, and which open-ended item explains it. Patterns
   and the conversion-specific cross-tabs live in `references/analysis-patterns.md`.
2. **Decision bridge** — for goal-driven work, a table that turns findings into actions
   (e.g. "appeal point X ranks #1 → lead the campaign with X"). This is the payoff of backward
   design: the survey was built to fill exactly this table.

**Handoff to actually collect responses.** This skill designs; it does not dispatch. Close by
telling the user that to run the survey against synthetic Korean personas, the next step is the
`nemotron-personas-korea:dispatch-strategy` skill (which sizes the fan-out and drives the
`persona-respondent` subagent), and that the Phase 0 audience definition is the persona filter.
Offer to hand the finished survey to that skill if the user wants to proceed.

---

## Output shape

Deliver, in this order:
1. The backward-design matrix (Phase 1) — shown first, because it justifies everything after.
2. The survey itself (Phases 2–3), from `assets/survey-template.md`, items tagged to RQs.
3. The analysis-to-decision plan (Phase 4).
4. A one-line handoff to `nemotron-personas-korea:dispatch-strategy`.

Keep designer notes (`ⓘ`) inline in the survey — they explain the *why* and make the artifact
teachable and defensible, not just a list of questions.

## Reference files

- `references/synthetic-respondent-design.md` — how LLM personas answer, and how to design items
  they answer validly (Likert anchors, debias, closed-vs-open). Read in Phase 3, always.
- `references/psychology-frameworks.md` — BMAP, B.I.A.S, Peak-End, 6P, loss aversion item
  patterns. Optional, for behavioral/conversion goals (Phase 2).
- `references/analysis-patterns.md` — analysis moves, conversion cross-tabs, decision-bridge
  patterns. Read in Phase 4.
- `assets/survey-template.md` — the output skeleton with section order and tagging convention.
