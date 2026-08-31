# ICP selection from survey results

The goal of this phase is to pick the one (occasionally two or three) real persona whose interview
will most move the decision. This is a judgment call, but a *disciplined* one — grounded in the
actual answers, not vibes. This file gives you the rubric and the reasoning behind it.

## The counterintuitive core: select for tension, not enthusiasm

The instinct is to interview your happiest respondent — the "5, definitely, love it" persona. Resist
it. That interview goes nowhere: there's no gap to explain, so you get a wall of agreement and no
mechanism. The decision-relevant persona is the one sitting **on the fault line** of the decision:

> High pull **and** real hesitation, in the same respondent.

They want the thing (so the demand is real and worth serving) but something holds them back (so
there's a *why* to excavate — and that why is usually the exact lever the decision needs). In the
reference case, the selected persona rated attendance intent 4/5 (high) *but* flagged the
parent-participation-vs-dual-income barrier — and the interview's entire payoff was explaining that
tension. A 5/5-no-concerns respondent would have taught nothing.

Enthusiasm is a data point. **Tension is an interview.**

## The scoring rubric

Score every real respondent on three axes. Keep it lightweight — a 1–3 per axis is enough to rank.

### Axis 1 — Fit (are they the target?)
From the persona row + screening answers. Are they squarely in the audience the decision is about
(life-stage, region, role, family type)? A respondent who slipped through the filter but isn't
really the target scores low here regardless of how interesting they are. Non-negotiable floor: an
interviewee must actually be in-target.

### Axis 2 — Decision-relevant tension (are they on the fault line?)
The heart of the rubric. Look for the co-occurrence of **pull** and **friction** in their answers:
- High intent/appeal on the load-bearing closed-form items, **combined with**
- A named barrier, a hesitation, a low sub-score, or an open-ended line that hedges.

A respondent who is uniformly high or uniformly low scores *lower* here than one who is split. The
split is the signal.

### Axis 3 — Texture (will they give a rich interview?)
From the open-ended answers. Did they write in specifics — an anecdote, a concrete worry, their own
phrasing — or a flat "좋아요"? Articulate, detail-giving respondents yield deeper interviews. This is
also where the persona's narrative fields matter: richer `family_persona` / `professional_persona`
text predicts a more textured interview.

### Combining
Rank by tension (Axis 2) first among respondents who clear the fit floor (Axis 1), then use texture
(Axis 3) as the tie-breaker. You're not computing a precise total — you're finding the one or two
who are clearly in-target, clearly torn, and clearly articulate.

## Presenting the shortlist (evidence-first)

For the top 2–3, show — for each — enough that the user can audit the pick:

```
#1 (recommended)  uuid: ee94d5d00d224bd68aaeb105093927d7
   40세 여자 · 서울-서대문구 · 교육·훈련 사무원 · 맞벌이
   Fit 3 / Tension 3 / Texture 3
   Signal: 참석의향 4/5 (pull) BUT 최우선 '안전·위생' + open-end named 부모 참여 의무 as the blocker (friction)
   Why interview: high demand held back by a concrete, fixable barrier — the interview can explain
   whether the barrier is dealbreaker or negotiable, which directly informs the 설명회 messaging.
```

Then recommend one primary. Optionally add a **contrast pick** from a different segment if the goal
hinges on a divergence (e.g. why fathers and mothers answered differently) — a second short
interview is worth more than a longer single one in that case.

**Stop here and let the user confirm or swap.** The user owns the selection; the skill only drafts
it. Carry the confirmed **real UUID** forward verbatim — this is the same UUID you loaded in Phase 1,
never a new one.

## Edge cases

- **No respondent shows tension** (everyone's uniformly high or low). Two moves: (a) interview the
  most *articulate* in-target respondent anyway, to understand the uniformity itself — is the appeal
  really that clean, or is the survey not surfacing the friction? (b) Consider that the survey may
  need a negatively-keyed item; note it for a future `backward-survey-builder` pass.
- **Thin target cell** (the filter left very few real in-target respondents). Widen the audience
  filter slightly and re-field rather than interviewing an off-target persona — an out-of-ICP
  interview is worse than a slightly-broader sample. Never invent a persona to fill the gap.
- **Two respondents tie.** Prefer the one whose tension maps most directly onto the *decision* (not
  just the most dramatic personal story). The interview serves the goal, not narrative interest.
- **The most interesting respondent is off-target.** Note them as color, but interview an in-target
  persona. Fit is a floor, not a trade-off.
