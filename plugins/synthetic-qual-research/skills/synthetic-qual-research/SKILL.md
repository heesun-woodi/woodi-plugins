---
name: synthetic-qual-research
description: >-
  End-to-end orchestrator for SYNTHETIC-user qualitative research on nemotron-personas-korea
  personas — conducts the whole arc from a business goal to a decision: design survey → field →
  find ICP → deep interview → synthesize. It does NOT reimplement the steps; it conducts the two
  existing skills (backward-survey-builder, synthetic-icp-interview) plus dispatch-strategy and
  the persona-interviewee command, and owns the seam between them: a run directory, a
  reproducibility manifest, file-welded UUIDs, two human gates, and a validity caveat pass.
  Trigger when the user wants the WHOLE arc from a goal (no survey yet) through to a decision.
  Korean triggers: "정성조사 처음부터 끝까지", "설문부터 인터뷰까지 다 해줘", "합성사용자 조사 통째로",
  "목표부터 의사결정까지 조사해줘", "설문 설계하고 필드하고 인터뷰까지". English: "end-to-end
  synthetic qual research", "goal to decision synthetic study", "run the whole synthetic user
  study". Do NOT trigger this (use the narrower skill) when the user only wants a survey DESIGNED
  (→ backward-survey-builder) or already HAS a survey and only wants it fielded+interviewed
  (→ synthetic-icp-interview). CRITICAL: real dataset UUIDs flow end-to-end through files;
  fabricating a UUID breaks the pipeline — this skill enforces that with a file invariant.
---

# Synthetic Qual Research (orchestrator)

## What this skill is — and is NOT

This is a **thin conductor**. It drives the full arc **goal → survey → field → ICP → interview →
synthesis → decision** by invoking existing pieces in order and owning only the *seam* between
them. It does not design questions, score ICPs, size dispatch fan-out, or play personas — those
belong to the skills below and must not be reimplemented here.

```
goal → [backward-survey-builder] → [synthetic-icp-interview] → [persona-interviewee] → decision
           design survey             field · select ICP           deep interview
        ↑─────────────── THIS SKILL conducts + owns the seam ───────────────↑
```

Pieces it conducts (never duplicate their internals):
- `backward-survey-builder` — designs the survey backward from the goal (Phase 1).
- `synthetic-icp-interview` — fields the survey and selects the ICP with evidence (Phases 2–3, 5 synthesis).
- `nemotron-personas-korea:dataset` — persona field semantics + `scripts/load_persona.py`.
- `nemotron-personas-korea:dispatch-strategy` — persona-respondent fan-out sizing (Phase 2).
- `/nemotron-personas-korea:persona-interviewee` — in-character interview command (Phase 4).
- `nemotron-personas-korea:synthetic-population-validity` — the validity caveat pass (Phase 5).

## Trigger boundary (avoid stealing narrower work)

Only conduct the **whole** arc. If the user just wants a survey designed → hand to
`backward-survey-builder`. If they already have a survey and want it fielded/interviewed → hand
to `synthetic-icp-interview`. This skill is for "do the whole thing from the goal."

## The one rule that breaks everything

> Every persona surveyed and interviewed must be a **real row**, carried by its real `uuid`.
> Never invent a UUID; never interview a persona you didn't actually draw.

This skill enforces the rule structurally with a **file invariant** (see Phase 2 / Phase 4):
`icp.json.uuid ∈ results.json.keys ⊆ drawn_personas.jsonl.uuids`. If any inclusion breaks, **hard
stop** — a fabricated UUID cannot pass silently. Read `references/orchestration.md` for the exact
checks and the resume protocol before running.

---

## Phase 0 — Initialize the run (state on disk from the first move)

1. **Capture three things** (extract from the user's brief; ask one short round only if missing):
   **goal** (the decision, framed as an action), **audience** (in filterable terms — age band,
   life-stage, region, family type), and an optional **ICP hypothesis**. Settle **N** (10–20 is
   plenty for find-the-ICP) and a fixed **random_state** (default 42) for reproducibility.
2. **Create the run directory** at `${SQR_RUNS_DIR:-research/runs}/<YYYY-MM-DD>-<goal-slug>/` and
   write `manifest.json` from `assets/manifest.template.json` (schema in `references/orchestration.md`).
   Record goal, audience_filter, icp_hypothesis, N, random_state, model, created date, and
   `phase_status` (all `todo` except `0_init: done`).
3. **🚦 GATE 1 — confirm goal + audience.** Reflect the captured goal/audience/N/hypothesis back in
   one or two lines and the run-dir path, and **stop for confirmation** before designing anything.
   This is the cheapest place to fix a wrong target.

## Phase 1 — Design the survey (invoke, then persist)

Invoke `backward-survey-builder` with the confirmed goal + audience. Let it run its full backward
design (matrix → RQs → tagged items → synthetic-ready → analysis plan). **Persist its output** to
`<run>/survey.md`, keeping every `→RQ#` tag and the inline designer notes. Update
`phase_status.1_survey = done`. The tags are load-bearing downstream (Phase 3 aggregates by RQ).

## Phase 2 — Field the survey (draw real rows FIRST, then weld)

1. **Draw real rows first.** Run the bundled batch-draw helper (NOT `load_persona.py` — that
   draws only ONE row):
   `python <skill>/scripts/draw_personas.py --filter "<audience_filter>" --n <N> --seed
   <random_state> --out <run>/drawn_personas.jsonl`. It samples N real rows in one dataset load
   and writes them; every row has a real `uuid` — this file is the spine's origin. (Respect field
   quirks from the `dataset` skill: `province` is abbreviated; `district` already includes the
   province prefix — never inject both.)
2. **Field it.** Hand mechanics to `synthetic-icp-interview` (Phase 1) + `dispatch-strategy`: pick
   dispatch mode + concurrency and **announce before launch** (dispatch-strategy's format), driving
   `persona-respondent` over the drawn rows. Closed-form → trust the numbers; open-ended → harvest
   language, don't count it.
3. **Weld UUIDs to answers, then validate.** Record responses as `<run>/results.json` =
   `{ "<uuid>": {answers}, … }`, never an anonymous list. **Then run the validator**
   (encodes the invariant AND a per-response schema check — a dispatch can silently return junk
   like `"OK"` instead of the answer JSON, as the smoke test found):
   `python <skill>/scripts/validate_results.py --drawn <run>/drawn_personas.jsonl --results
   <run>/results.json`. Act on the exit code:
   - **exit 2** — a results uuid isn't in the drawn set (fabricated/blended). **Hard stop**; discard.
   - **exit 3** — some slots are missing or fail schema; stdout lists their uuids. **Re-dispatch
     only those slots** (resend the survey to those personas), merge, and re-validate. Loop until 0.
   - **exit 0** — invariant holds and every slot is valid. Update `phase_status.2_field = done`.

## Phase 3 — Analyze → infer ICP  [🚦 GATE 2]

Invoke `synthetic-icp-interview` (Phase 2): aggregate closed-form by RQ, skim open-ends for
*tension* (high pull + real hesitation — the best interviewee, not the most enthusiastic), score
and rank respondents, and draft the ICP profile. Write the draft to `<run>/icp.json` as
`{primary_uuid, contrast_uuid, evidence:[{uuid, scores, quoted_line}]}`. Present the ranked
shortlist **with evidence** (UUID + key scores + a quoted open-end) and recommend a primary + a
contrast pick from a different segment. **🚦 Stop and let the user confirm or swap.** Carry the
confirmed **real UUIDs** verbatim. Update `phase_status.3_icp = done`.

## Phase 4 — Deep interview (1 primary + 1 contrast)

**First, pick the interview mode** (persona-interviewee assumes the *user* is the interviewer, so
be explicit about who drives — the smoke test surfaced this ambiguity):
- **Interactive (default when a human is present)** — hand control to the user as interviewer.
  You load the persona and play them in character; the user asks; you append probe blocks after
  each answer for their next move. Wait for the user turn by turn.
- **Auto-conduct (default for autonomous/smoke runs)** — you play BOTH the interviewer (applying
  the craft below) and the persona, in clearly-labeled channels (`**Interviewer:**` / `**Persona:**`),
  writing the full transcript yourself. Use when no human will drive the turns. Announce which mode
  you're in before starting.

For each confirmed UUID, verify it is present in `results.json` (invariant), then enter interview
mode: `/nemotron-personas-korea:persona-interviewee uuid:<REAL_UUID> --save`, with the run
directory as the transcript home (`NEMOTRON_INTERVIEWS_DIR=<run>` so transcripts land as
`<run>/…-<uuid8>.md`, or move them in after). Layer `synthetic-icp-interview`'s interview craft:
one question at a time, funnel broad→deep, ladder behavior→feeling→value, and **after every
in-character answer append a bracketed `> [추천 질문 N개]` probe block** — 2–3 next questions, each
with one line on the insight it unlocks and how it serves the goal. Keep probes in the meta-channel,
never in the persona's mouth. Steer for one peak moment; close by letting the persona reflect.
Run the primary deep, then the contrast interview shorter (why does the other segment diverge?).
Update `phase_status.4_interview = done`.

## Phase 5 — Synthesize to a decision + validity caveat

Invoke `synthetic-icp-interview` (Phase 4) to write `<run>/synthesis.md`: the **real need** (often
different from the survey headline), the **decisive tension/barrier** explained, **3–5 decision
implications** each traceable to something a persona said and tied to the Phase 0 goal, and **what
to validate next**. Then run the `synthetic-population-validity` caveat pass and **append a
"신뢰 구간 · 검증 다음 단계" section** stating plainly that synthetic personas are a fast, cheap
*first* read — where the numbers are trustworthy (closed-form, calibrated marginals) and where a
real interview must still check the finding. Update `phase_status.5_synthesis = done`.

---

## Resume (state is on disk)

On re-entry into an existing run, read `manifest.json.phase_status`, skip `done` phases, and
continue from the first non-done phase using the artifacts already written. Never re-field or
re-draw a phase already marked done unless the user asks. See `references/orchestration.md`.

## Output shape (what the user receives, in order)

1. Phase 0 one-liner (goal · audience · N · hypothesis) + run-dir path. [Gate 1]
2. `survey.md` (link) with RQ tags.
3. Fielded results table with **real UUIDs attached** — compact, not prose.
4. ICP draft + ranked shortlist with evidence + confirmed pick. [Gate 2]
5. Interview transcripts with probe blocks after each answer (×2).
6. Synthesis → decision + the validity caveat section.

## Reference files & scripts

- `references/orchestration.md` — the seam contract: manifest schema, what to persist/validate at
  each phase, the UUID invariant checks, and the resume protocol. Read before running.
- `assets/manifest.template.json` — run manifest skeleton.
- `scripts/draw_personas.py` — batch-draw N real personas (Phase 2 step 1). load_persona.py draws
  only one; this draws N reproducibly.
- `scripts/validate_results.py` — invariant + per-response schema check (Phase 2 step 3). Exit 2 =
  fabricated uuid (hard stop), 3 = slots to re-dispatch, 0 = valid.
