# Orchestration — the seam contract

This is the connective tissue the orchestrator owns. The sub-skills own their craft; this file
owns **what gets written to disk at each seam, what gets validated, and how a run resumes.**

## Run directory

```
${SQR_RUNS_DIR:-research/runs}/<YYYY-MM-DD>-<goal-slug>/
├── manifest.json         # single source of truth for the run (schema below)
├── drawn_personas.jsonl  # Phase 2: the N real rows actually sampled (uuid spine origin)
├── survey.md             # Phase 1: backward-survey-builder output, RQ tags kept
├── results.json          # Phase 2: { "<uuid>": {answers...}, ... }  (welded)
├── icp.json              # Phase 3: {primary_uuid, contrast_uuid, evidence:[...]}
├── <ts>-<uuid8>.md       # Phase 4: persona-interviewee --save transcripts (one per interview)
└── synthesis.md          # Phase 5: decision bridge + validity caveat section
```

`<goal-slug>` is a short kebab-case slug from the goal (e.g. "9월 설명회 신청 최대화" →
`sept-briefing`). Keep it stable for a run so resume can find the directory.

## manifest.json schema

```json
{
  "slug": "sept-briefing",
  "created": "2026-07-13",
  "goal": "9월 설명회 신청을 최대화",
  "audience_filter": "sex=여자,age>=28,age<=42,province=서울",
  "icp_hypothesis": "만 1~2세 자녀를 둔 서울 거주 워킹맘",
  "N": 15,
  "random_state": 42,
  "model": "claude-opus-4-8",
  "phase_status": {
    "0_init": "done",
    "1_survey": "todo",
    "2_field": "todo",
    "3_icp": "todo",
    "4_interview": "todo",
    "5_synthesis": "todo"
  },
  "artifacts": {
    "survey": "survey.md",
    "drawn": "drawn_personas.jsonl",
    "results": "results.json",
    "icp": "icp.json",
    "synthesis": "synthesis.md"
  }
}
```

`phase_status` values: `todo` (not started), `pending` (started, awaiting a human gate or
sub-skill result), `done`. Update the relevant key at the END of each phase — write it before
moving on, so an interrupted run resumes cleanly.

`audience_filter` uses `load_persona.py` filter syntax: comma-separated `col=val`, `col>=n`,
`col<=n`, and `xsubstr=<text>` (substring across descriptive fields). Remember the field quirks:
`province` is abbreviated (`서울`, `경기`, `전북` doubly-shortened vs `전라남` singly), and
`district` already carries the province prefix — never combine `province` + `district` in one
injected location string.

## The UUID invariant (the load-bearing check)

> `icp.json.uuid ∈ results.json.keys ⊆ drawn_personas.jsonl.uuids`

Three checkpoints; each is a **hard stop** on failure (report which inclusion broke and which UUID):

1. **After Phase 2 draw** — `drawn_personas.jsonl` has exactly N rows, each with a real `uuid`
   pulled by `scripts/draw_personas.py` (not written by hand). If you find yourself *typing* a UUID
   rather than *reading* one out of the draw output, stop — the spine is already broken.
2. **After Phase 2 field** — run `scripts/validate_results.py`. Exit 2 means a `results.json` key
   isn't in the drawn set (fabricated/blended) → hard stop. Exit 3 lists slots that are missing or
   fail the response schema (e.g. a dispatch returned `"OK"` not the answer JSON) → re-field only
   those and re-validate. Exit 0 = every slot valid.
3. **Before Phase 4 interview** — `icp.json.primary_uuid` and `contrast_uuid` both exist in
   `results.json`. Pass the confirmed UUID to persona-interviewee **verbatim**
   (`uuid:<REAL_UUID>`), never a lookalike.

Why this matters: the value of synthetic research is that personas are calibrated to real Korean
population marginals. A fabricated persona is talking to yourself with extra steps, and the survey
numbers become fiction. Files are the enforcement mechanism — memory is not trustworthy across a
multi-phase run.

## Seam-by-seam: invoke → persist → validate

| Phase | Invoke | Persist | Validate |
|---|---|---|---|
| 1 | `backward-survey-builder` | `survey.md` (RQ tags + `ⓘ` notes kept) | survey items all tagged `→RQ#` |
| 2 | `scripts/draw_personas.py --filter --n --seed --out`; then `synthetic-icp-interview`(P1) + `dispatch-strategy`; then `scripts/validate_results.py` | `drawn_personas.jsonl`, then `results.json` (uuid→answers) | invariant checks 1 & 2 via validator (exit 2 hard stop, 3 re-dispatch, 0 pass) |
| 3 | `synthetic-icp-interview`(P2) | `icp.json` (draft) | ranked shortlist shows evidence per UUID |
| 4 | `/nemotron-personas-korea:persona-interviewee uuid:<real> --save` ×2 | `<ts>-<uuid8>.md` ×2 | invariant check 3 |
| 5 | `synthetic-icp-interview`(P4) + `synthetic-population-validity` | `synthesis.md` (+ caveat section) | every implication traces to a quote + ties to goal |

## Human gates (do not auto-advance past these)

- **Gate 1 (end of Phase 0):** confirm goal + audience + N before any design work. Cheapest fix point.
- **Gate 2 (end of Phase 3):** confirm the ICP pick (primary + contrast) before interviewing. The
  human owns who gets interviewed — it steers everything after.

Announce, then stop. Do not design a survey, field, or interview past an unconfirmed gate.

## Resume protocol

On re-entry with an existing run directory:

1. Read `manifest.json`. If absent, this is a fresh run → Phase 0.
2. Walk `phase_status` in order; skip every `done` phase, reusing its artifact from disk.
3. Resume at the first non-`done` phase. If it is `pending`, it was interrupted at a gate or
   mid-dispatch — re-present the gate (Gate 1/2) or re-run only the incomplete dispatch, don't
   redo completed work.
4. Never re-draw personas or re-field a phase already `done` unless the user explicitly asks
   (re-drawing changes the sample and invalidates downstream artifacts).

## Dispatch announce (Phase 2, from dispatch-strategy)

Always announce before launch so the user can adjust N or the filter, e.g.:

> N=15, file-read batch, 2 dispatches × ~8 personas, launched at once (closed-form; bottleneck is
> the ~1.8 s/dispatch launch emit, no hard cap ≤24).

Batch-of-10 is the validated closed-form size. Interview-depth / opinion-projection → one-per
dispatch. Re-measure concurrency; never quote a remembered cap.

## Bundled scripts

- `scripts/draw_personas.py --filter "<clauses>" --n <N> --seed <s> --out <path>` — draws N real
  rows in one dataset load (same filter grammar and `random_state` semantics as the dataset skill's
  `load_persona.py`, which only draws one). Reproducible: same filter+seed → same rows. Prints the
  drawn uuids for verification.
- `scripts/validate_results.py --drawn <jsonl> --results <json> [--require <keys>]` — the Phase 2
  gate. Exit **0** = invariant holds and every drawn uuid has a schema-valid response; exit **2** =
  a results uuid is not in the drawn set (fabricated/blended → hard stop); exit **3** = some slots
  are missing or fail the response schema (their uuids print to stdout → re-dispatch only those).

## Changelog

- **v2** — Found in the first live smoke test: (1) `load_persona.py` draws only one row, so
  `scripts/draw_personas.py` now owns the batch draw; (2) a dispatch can silently return junk (`"OK"`)
  instead of the answer JSON, so `scripts/validate_results.py` adds a per-response schema check and a
  re-dispatch loop on top of the UUID invariant; (3) Phase 4 now names an explicit interactive vs
  auto-conduct interview mode (persona-interviewee assumes the user is the interviewer).
