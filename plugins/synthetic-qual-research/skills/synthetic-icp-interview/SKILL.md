---
name: synthetic-icp-interview
description: >-
  Runs a survey against synthetic Korean personas, analyzes the responses to find the
  ICP (ideal customer / ideal interviewee), and conducts a deep in-character interview with
  that persona — the connective spine between a finished survey and real qualitative insight.
  Use this whenever the user HAS a survey (from backward-survey-builder or their own) and wants
  to actually field it on nemotron-personas-korea personas, then pick who to interview and dig
  deeper. Trigger on Korean phrases like "설문 돌려줘", "페르소나한테 설문하고 인터뷰",
  "합성사용자 조사하고 심층인터뷰", "ICP 찾아서 인터뷰", "설문 결과에서 인터뷰 대상 골라줘",
  "타겟 심층인터뷰", and English "run this survey on personas then interview", "find the ICP and
  interview them", "survey-to-interview", "synthetic user deep dive". Also trigger right after a
  survey is designed and the user says "이제 이걸로 조사해보자" / "let's field it". This skill
  does NOT design surveys (that is backward-survey-builder) — it fields, selects, and interviews.
  CRITICAL: it carries REAL dataset UUIDs end-to-end; fabricating a UUID breaks the whole pipeline.
---

# Synthetic ICP Interview (field → select → interview → synthesize)

## What this skill is for

A survey tells you *what* and *how much*. It rarely tells you *why*. The move that turns survey
data into a decision is: field the survey, read the pattern, find the one respondent whose answers
sit on the decision's fault line, and interview them until the *why* comes out. This skill owns
that spine.

It sits **downstream** of survey design and **upstream** of the decision:

```
backward-survey-builder        →  THIS SKILL  →  the decision
(designs the survey)              field · select · interview · synthesize
```

The four existing pieces it orchestrates:
- `nemotron-personas-korea:dataset` — how to filter personas and the field-semantics quirks.
- `nemotron-personas-korea:dispatch-strategy` — how to fan out the `persona-respondent` subagent.
- `nemotron-personas-korea:persona-interviewee` — the in-character interview mode.

This skill's contribution is the connective tissue none of those own: **selecting the ICP from
survey results with evidence**, **orchestrating so the real UUID flows through**, and the
**interview craft** (funnel, laddering, live probe recommendations, peak-end synthesis).

## The one rule that breaks everything if ignored

> Every persona you survey and interview must be a **real row** from the dataset, carried by its
> real `uuid`. Never invent a UUID, and never interview a persona you didn't actually draw.

This is not pedantry. The value of synthetic research is that the personas are calibrated to real
Korean population marginals — a fabricated persona is just you talking to yourself with extra
steps, and the survey numbers become fiction. In practice the failure looks like this: the survey
"respondents" get plausible-looking UUIDs that don't exist in the dataset, and when you try to
interview one, the loader returns nothing. If you ever find yourself writing a UUID rather than
reading one out of a dispatch result, stop — you've lost the thread. Load real rows (Phase 1),
keep their UUIDs attached to their answers, and hand the *same* UUID to the interview (Phase 3).

## Workflow overview

```
Phase 0  Confirm the survey + goal + ICP hypothesis + audience filter
Phase 1  Field the survey        → real personas answer, UUIDs attached to answers   [REAL UUIDs]
Phase 2  Analyze → infer ICP      → draft an ICP profile, score respondents, user CONFIRMS
Phase 3  Deep interview           → persona-interviewee with the confirmed real UUID + live probes
Phase 4  Synthesize → decision    → what the interview revealed, tied back to the goal
```

Don't collapse phases. In particular, Phase 2's user-confirmation gate matters: the skill *drafts*
the ICP, but the human owns the call on who gets interviewed, because that choice steers everything
after it.

---

## Phase 0 — Confirm what you're fielding

You need four things before dispatching. Usually three come straight from an upstream
backward-survey-builder run or the user's brief — extract and reflect them back, don't re-interview:

1. **The survey** — the actual items. If items aren't in hand, ask for them or offer to design
   them with `backward-survey-builder` first. This skill fields; it doesn't invent questions.
2. **The goal** — the decision the research serves (e.g. "설명회 신청을 최대화"). This is the
   yardstick for both ICP selection and the final synthesis, so state it in one line.
3. **The audience filter** — who the respondents are, in *filterable* terms (age band, life-stage,
   region, family type). This becomes the persona query. See `nemotron-personas-korea:dataset` for
   the exact column names and the naming quirks (`province` is abbreviated; `district` already
   includes the province prefix — don't double it).
4. **The ICP hypothesis** — an early guess at who the *most decision-relevant* respondent looks
   like. It's fine for this to be rough; Phase 2 refines it against real answers. If the user has
   none, say so and let the data suggest it in Phase 2.

Also settle **N** — how many personas to survey. For a find-the-ICP interview, N=10–20 is usually
plenty: enough to see a pattern and a spread, small enough to read every open-ended answer. Bigger
N is for stable distributions, not for picking one person to talk to.

---

## Phase 1 — Field the survey (real personas only)

Hand the mechanics to `nemotron-personas-korea:dispatch-strategy` — it picks the dispatch mode and
concurrency and drives the `persona-respondent` subagent. Your job here is **integrity of the
sample**, three things it's easy to get wrong:

- **Draw real rows first.** Filter the dataset to the audience and sample N real rows (with a fixed
  `random_state` for reproducibility). Every sampled row has a real `uuid` — that column is the
  spine of everything downstream. The `dataset` skill's `scripts/load_persona.py` loads a row by
  `--uuid` or `--filter`; use it to pull the actual rows, don't imagine them.
- **Keep the UUID welded to the answer.** When responses come back, each respondent's answers must
  stay attached to the UUID that produced them. Record them as `uuid → {answers}`, not as an
  anonymous list. Phase 3 needs to interview a specific real row, and the only bridge is the UUID.
- **For closed-form items, trust the numbers; for open-ended, harvest the language.** Personas
  answer Likert/binary/multi-choice in ways that track real population patterns; free-text is
  voice-of-customer texture, not a reliable count. This shapes Phase 2: score the ICP mostly on
  closed-form signal, and use open-ends to spot who is *articulate and torn* (great interviewee).

If the survey came from `backward-survey-builder`, each item is tagged to a research question
(`→RQ2`). Keep those tags — they make Phase 2's analysis fall out cleanly (aggregate by RQ).

Announce the dispatch before launching (per dispatch-strategy's announce format) so the user can
adjust N or the filter.

---

## Phase 2 — Analyze results and infer the ICP  [user confirms]

This is the skill's core. Read `references/icp-selection.md` before finalizing the pick — it has the
scoring rubric, a worked example, and how to handle ties and thin cells. The essentials:

**Step 1 — Read the pattern.** Aggregate the closed-form answers (by RQ if tagged): what ranks
highest, where's the spread, which items split the sample. Skim every open-ended answer for
recurring language and, crucially, for *tension* — respondents who want the thing but name a
blocker in the same breath.

**Step 2 — Draft the ICP profile.** Turn the goal + pattern into a short profile of the person most
worth interviewing. Two ingredients:
- **Fit** — are they squarely in the target? (life-stage, region, role — from the persona row.)
- **Signal** — are they the *right* one to talk to? The best interviewee is usually **not** the
  most enthusiastic respondent but the one whose answers reveal a **productive tension**: high pull
  *and* real hesitation. That gap is exactly what an interview exists to explain. A respondent who
  answered "5, definitely attending, no concerns" gives you nothing to dig into; one who answered
  "4, very interested" but flagged a barrier is a goldmine.

**Step 3 — Score and rank.** Apply the rubric in the reference to every respondent, producing a
ranked shortlist. For the top 2–3, show the **evidence**: their UUID, key closed-form scores, and a
quoted open-ended line that shows the tension. Evidence-first is what keeps selection honest — the
user should see *why* this UUID, grounded in its actual answers.

**Step 4 — Present and get confirmation.** Show the draft ICP profile and the ranked shortlist with
evidence, and recommend one primary interviewee (optionally a contrast pick from a different
segment). Then **stop and let the user confirm or swap.** The user owns this call. Carry the
confirmed **real UUID** into Phase 3 verbatim.

---

## Phase 3 — Deep interview (with live probe recommendations)

Enter interview mode via `nemotron-personas-korea:persona-interviewee` with the confirmed real UUID:
`uuid:<REAL_UUID_FROM_PHASE_2>`. That skill loads the full narrative row and plays the persona in
character. Layer this skill's interview craft on top — read `references/interview-craft.md` for the
full technique. The three things that make these interviews land:

- **One question at a time, funnel from broad to deep.** Open easy (a self-intro, a recent
  episode), then follow the *emotion*, not your question list. Ladder down: from behavior → to the
  feeling under it → to the value under that. The richest material in a good interview is usually
  three "why"s below the opening answer.
- **After every in-character answer, recommend follow-up probes.** This is the practice the user
  asked for and it's built into this skill: once the persona has answered, append a clearly-marked
  block (e.g. `> [추천 질문 N개]`) suggesting 2–3 next questions — and for each, one line on *what
  insight it would unlock and how it serves the goal*. This turns the interview into a guided
  instrument: the user always has a sharp next move and understands why it's sharp. Keep these
  recommendations in the meta-channel (brackets/blockquote), never in the persona's mouth.
- **Design for peak-end.** People remember the emotional peak and the ending. Steer toward at least
  one genuine peak moment (the question no one has asked them — in our reference case, "is this good
  for *you*, not just your kid?"), and close by letting the persona reflect on the conversation.

Interview one persona deeply by default. If the goal needs contrast (why do segment A and segment B
diverge?), run a second short interview with a contrasting UUID rather than padding the first.

---

## Phase 4 — Synthesize to a decision

An interview isn't done at "goodbye" — it's done when the *why* is on paper and pointed at the goal.
Produce a tight synthesis (template in `assets/synthesis-template.md`):

- **The real need** — often different from the survey's headline. (Survey said "안전·위생"; the
  interview revealed the need was *emotional permission to stop worrying*.) Name the latent need the
  numbers only hinted at.
- **The decisive tension / barrier** — the productive tension you selected for, now explained.
- **Decision implications** — 3–5 concrete moves for the goal, each traceable to something the
  persona said. This is the payoff: the pipeline existed to fill this table.
- **What to validate next** — where the synthetic interview is a hypothesis a real interview should
  check. Be honest that synthetic personas are a fast, cheap *first* read, not the last word.

Tie every implication back to the Phase 0 goal. If an insight doesn't touch the decision, it's
color, not a finding.

---

## Output shape

Deliver, in order:
1. A one-line reflection of the survey + goal + audience + N (Phase 0).
2. The fielded results with **real UUIDs attached** (Phase 1) — a compact table, not prose.
3. The ICP draft + ranked shortlist with evidence, and the confirmed pick (Phase 2).
4. The interview transcript with live probe blocks after each answer (Phase 3).
5. The synthesis-to-decision (Phase 4).

## Reference files

- `references/icp-selection.md` — the ICP scoring rubric, a worked example, tension-over-enthusiasm
  reasoning, tie-breaking, thin-cell handling. Read in Phase 2, always.
- `references/interview-craft.md` — funnel structure, laddering, the live-probe-recommendation
  format, peak-end steering, and how the interview meta-channel interacts with persona-interviewee's
  bracket convention. Read in Phase 3, always.
- `assets/synthesis-template.md` — the Phase 4 synthesis skeleton.
