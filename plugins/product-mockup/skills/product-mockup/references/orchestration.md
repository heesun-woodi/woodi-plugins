# Orchestration

How to run the six stages across sub-agents. The point of splitting the work is
**not speed** — it is bias isolation. An agent that just generated an image will
pass its own work. A separate reviewer will not.

## Roster

Four agents ship with this plugin. Stages without a dedicated agent run inline or
on a general-purpose agent.

| Stage | Agent | Model | Why this tier |
|---|---|---|---|
| 01 Extract source | *(inline / general-purpose)* | sonnet | Mechanical scripting |
| 02 Scene prompts | `mockup-scene-designer` | sonnet | Staging and lighting judgment |
| 03 Generate | *(general-purpose, one per scene)* | sonnet | API calls; fan out |
| 04 Review | `mockup-verifier` | **opus** | Spotting sub-pixel text corruption is the whole job |
| 05 Composite | `mockup-compositor` | **opus** | Hardest technical stage: homography, light transfer, occlusion |
| 06 Ship | *(inline)* | haiku | Writing up a finished result |
| Final pass | `mockup-reviewer` | **opus** | Independent commerce-side judgment |

Do not economize on stage 04. A cheap reviewer that misses one hallucinated phone
number costs more than every token it saved.

## Rules

### 1. Never let the same agent write and judge

`mockup-verifier` and `mockup-reviewer` are declared read-only for this reason.
When dispatching generation work, state explicitly in the prompt:

> Do not assess image quality. A separate review stage handles that.

Without this, generators volunteer favourable assessments and the operator
anchors on them.

### 2. Fan out generation, batch review

Scene generation is embarrassingly parallel — dispatch every scene at once.

Review is the opposite: **collect all candidates, then review them together in one
agent.** Splitting review across agents makes verdicts drift, and "is this one
worse than the others?" is a question a reviewer can only answer with all of them
in hand.

### 3. Hand off through files, never through conversation

Each stage writes to a fixed directory and the next stage receives only a path.
Passing images or long results through agent messages poisons context and inflates
cost.

```
source/    original design + real product reference
scenes/    generated candidates       + metadata.json
final/     composited output          + _evidence/ crops
```

This also buys crash recovery. Long runs *will* lose an agent to a network error;
when that happens, inspect the directories to see how far it got and restart only
the remainder. Design for that from the start.

### 4. Two rounds, then cut

Regeneration is capped at two rounds.

- **Structural defect survives round 2** (wrong product shape, missing required
  element) → drop the scene, replace it with another. Fixing text on a product
  that is structurally wrong yields a picture of a different product.
- **Only text is corrupt** → do not regenerate at all. Composite it. Prompt
  wording does not fix small type; this is the single most expensive lesson in
  this workflow and the reason the plugin exists.

### 5. Record what was dropped

When a scene is cut, write down which and why. A silent drop reads as "all scenes
succeeded" to whoever reads the output later.

## Dispatch sketch

```
01  extract source            →  source/
02  mockup-scene-designer     →  prompts.json
03  N generators in parallel  →  scenes/
04  mockup-verifier (batched) →  verdicts: PASS / COMPOSITE / REGEN / FAIL
      ├ REGEN  → back to 03 with reinforced prompt  (max 2 rounds)
      └ FAIL   → drop, note the reason
05  mockup-compositor         →  final/ + _evidence/
06  mockup-reviewer           →  placement guidance, ranked picks
```

Expect zero PASS verdicts on the first round. On the reference project all eight
first-round scenes needed compositing. That is the normal shape of this workflow,
not a sign that something went wrong.
