---
name: product-mockup
description: Use when the user needs realistic lifestyle/staging photos of a flat product design (packaging, print product, poster, book cover, label, calendar, card, box art, ...) placed in a real-world scene — e.g. "상세페이지 연출 사진 만들어줘", "상세페이지용 제품 사진", "라이프스타일 목업 이미지 생성", "제품 목업 만들어줘", "인테리어에 걸린/놓인 제품 이미지", "이 디자인을 방 안에 걸려있는 것처럼 보여줘", "제품 연출컷", "product mockup", "lifestyle shot", "product lifestyle mockup", "staged product photo", "hang this design on a wall and photograph it", "put this design in a room shot", "generate lifestyle scenes for this design". Do NOT use for pure AI image generation with no existing source design to preserve (no reference artwork), or for simple background removal/photo editing.
---

# Product Mockup (hybrid AI scene + composite)

## Why this exists: AI alone cannot do this job

A single generative image call cannot both (a) invent a convincing real-world
scene around a product and (b) preserve that product's fine print pixel-exact.

This was proven empirically on the reference project this skill was extracted
from — a spiral-bound wall calendar. Round 1 generated **8 scenes** with
`gemini-3-pro-image`: the small text on the product (weekday header letters)
came out hallucinated or garbled in **all 8**. Round 2 added four separate
reinforcement instructions and regenerated the **3** scenes whose *other*
defects made them worth another pass — and the weekday header text was still
wrong in **all 3 of those**. Everything else about the generations was
usable — lighting, room detail, product placement, even the overall art
layout. Only the small text failed, and prompting could not fix it.

See `references/prompt-patterns.md` for exactly which reinforcement sentences
worked (art content, grid structure, flatness, binding — real, measurable
fixes) and which one didn't (text accuracy — no fix found in two rounds).

**The fix is architectural, not a better prompt**: let the AI model do only
what it's good at — scene, lighting, materials, camera — and composite the
*original, pixel-exact source design* onto the product face it drew, warped
through a 4-point perspective transform to match the angle it chose. This is
the hybrid strategy. Do not attempt a third prompt round chasing text fidelity
before reading `references/prompt-patterns.md` — it will not converge.

## How to run this: read the orchestration doc

`references/orchestration.md` is the authority on **who runs which stage and
why**. Read it before dispatching anything. In short:

| Stage | Agent | Model |
|---|---|---|
| 01 Extract source | *(inline / general-purpose)* | sonnet |
| 02 Scene prompts | `mockup-scene-designer` | sonnet |
| 03 Generate | *(general-purpose, one per scene)* | sonnet |
| 04 Review | `mockup-verifier` | **opus** |
| 05 Composite | `mockup-compositor` | **opus** |
| 06 Ship | *(inline)* | haiku |
| Final pass | `mockup-reviewer` | **opus** |

Three rules from that doc are load-bearing enough to restate here:

- **Authoring and review are separate passes, always.** `mockup-verifier` and
  `mockup-reviewer` are declared read-only for exactly this reason. When
  dispatching generation work, say explicitly in the prompt: *"Do not assess
  image quality. A separate review stage handles that."* Without it,
  generators volunteer favourable self-assessments and the operator anchors
  on them.
- **Hand off through files, never through conversation.** Each stage writes to
  a fixed directory and the next stage receives only a path. Passing images or
  long results through agent messages poisons context, inflates cost, and
  destroys crash recovery — and long runs *will* lose an agent to a network
  error. When that happens, inspect the directories to see how far it got and
  restart only the remainder.
- **Fan out generation, batch review.** Scene generation is embarrassingly
  parallel — dispatch every scene at once. Review is the opposite: collect all
  candidates and review them together in one agent, because "is this one worse
  than the others?" is only answerable with all of them in hand.

## Prerequisites

Before starting, confirm all of these exist or get them from the user:

- `GEMINI_API_KEY` in a `.env` file (`GEMINI_API_KEY=...`, see `.env.example`
  in the starter kit). Never print or log this value.
- The **original source design** at full resolution (e.g. a print-ready PDF
  exported to PNG at print DPI). This is what gets warped onto every scene —
  its quality is a hard ceiling on every final image's quality.
- A **second reference photo** of one physical detail the AI can't infer from
  the flat design alone: how it's bound, mounted, framed, or held (spiral
  binding, stitching, a stand hinge, a frame, packaging tape, ...). Skipping
  this reference is the single most common cause of a wrong-looking product
  structure in round 1.
- A rough list of scenes wanted (e.g. "living room, study, kitchen, office" x
  "straight-on and angled" = 8 scenes) — confirm with the user if not given.

## The 6-stage pipeline

### 01. Extract and clean the source design
Goal: one high-resolution PNG/JPEG of the full product face, with accurate
page bounds (crop out scanner margin / matte). Also identify and note any
fixed structural landmarks you'll need later for compositing sub-regions
(e.g. "the date grid starts at row 1296px") — record these now, while you're
looking closely at the source, not later while debugging a warp.
Output: `source/design_full.png` (or similar) + a note of its page bounds.
Gate: the image opens cleanly, is the full intended resolution, and you can
point to its four true corners in pixel coordinates.
**Dispatch:** inline or a general-purpose agent, sonnet. Mechanical scripting.

### 02. Design scene prompts
Goal: one prompt per scene, following the six-part structure in
`references/prompt-patterns.md` (placement → scene description → **explicit
preservation instruction** → product structure → camera/lighting → output
resolution). Every prompt must name the exact preservation clause — "keep the
exact design ... from the first reference image unchanged" — even though you
already know small text won't survive; this clause is what keeps the
*large-scale* art, layout, and colors faithful, which the composite stage
depends on for realistic relighting. Every scene must target a *different*
buying motive.
Output: `prompts.json` (`{"scenes": [{"id", "scene", "variant", "motive", "prompt"}]}`).
**Dispatch:** `mockup-scene-designer` (sonnet).

### 03. Generate scenes
Goal: call `scripts/generate_scenes.py --config <project.json>` (optionally
`--only <ids>` to target specific scenes) to produce one PNG per scene via
`gemini-3-pro-image`.
Output: `scenes/<id>.png` + `scenes/metadata.json` (resolution, model,
timing — the script merges this on reruns so `--only` doesn't wipe earlier
entries).
**Dispatch:** general-purpose agents, sonnet, one per scene in parallel. This
stage is mechanical (run a script, check exit code) — do not spend a
reasoning-heavy agent on it, and tell each generator not to assess quality.

### 04. Inspect and judge
Goal: for every scene, render a verdict using the checklist and PASS /
COMPOSITE / REGEN / FAIL scale in `references/review-checklist.md`. Crop and
zoom the product face and any occluding foreground objects before judging —
defects that are invisible at thumbnail size are exactly the ones that ruin a
final e-commerce image. `scripts/zoom_corners.py` renders a labelled 2x2
montage of four regions for this.
Output: a verdict + notes per scene id, and for any COMPOSITE verdict, the
**exact data stage 05 needs**: the 4-point quad (or a frontal rect) in
scene-image pixel coordinates, which sub-region of the source needs warping
(full page, or a smaller rect), and any occluder polygons.
**Dispatch:** `mockup-verifier` (opus), on the whole batch at once. Must be a
different agent/pass than whoever wrote the prompts in stage 02.

Do not economize on this stage. A cheap reviewer that misses one hallucinated
phone number costs more than every token it saved — that number is probably
someone's real number.

Expect **zero PASS verdicts on the first round**. On the reference project all
eight first-round scenes needed compositing. That is the normal shape of this
workflow, not a sign that something went wrong.

### 05. Regenerate or composite
For scenes marked REGEN: revise the prompt (see the reinforcement catalogue in
`references/prompt-patterns.md`) via `mockup-scene-designer`, rerun stage 03
with `--only` for just those ids, then re-judge with a **fresh** verifier
pass — same rule as above, no self-grading. Apply the cutoff rule (below)
before starting a regen round.

For scenes marked PASS or COMPOSITE: run `scripts/composite.py --config
<scenes.json> [scene_id ...]` to warp the source design onto the product face
and blend it in (illumination transfer, edge-band detail, grain matching,
optional drop-shadow repair, optional occluder re-paste — see the docstring
in `scripts/composite.py` for what each `scenes.json` key controls, and
`scripts/fit_edges.py` / `scripts/zoom_corners.py` to *measure* quad corners
rather than estimate them).
Output: `final/<id>_final.png` + `final/_evidence/<id>_grid_crop.png` (a
zoomed crop proving the fine print survived undistorted) +
`final/_evidence/composite_report.json`.
**Dispatch:** `mockup-compositor` (opus). Getting the quad/band/light
parameters right from a description of the defect — not just running the
script — is a judgment task, not a mechanical one.

### 06. Organize deliverables and write a placement guide
Goal: a short doc mapping each final image to its intended use (hero shot,
detail shot, lifestyle variant N) plus any known caveats per image (e.g. "a
small mid-frame text region is still slightly soft — acceptable at this
crop"). Reuse the evidence crops from stage 05 as the fidelity proof.
**Dispatch:** inline, haiku. Writing up a finished result.

### Final pass
Before declaring the deliverable set done, `mockup-reviewer` (opus, **never**
the same agent instance that ran stages 02-05) reviews the full `final/`
folder against the original request from a commerce standpoint: which cut is
the hero, what order the detail page runs them in, which buying question no
cut answers. This is the one pass allowed to send scenes all the way back to
stage 02 if the verifier was too lenient.

## Cutoff rule (don't burn budget chasing a bad generation)

- Regeneration budget per scene: **2 rounds maximum**.
- After round 2, if the defect is **structural** (product shape/proportions
  wrong, a required element entirely missing, the wrong number of
  rows/columns, an unusable pose or crop) — **discard the scene** and
  substitute a different scene/angle rather than a third prompt round. Fixing
  text on a product that is structurally wrong yields a picture of a different
  product.
- If the *only* remaining defect is **text distortion** on the product face —
  don't regenerate at all. Route it straight to the composite stage. Composite
  is the designed fix for this failure mode, not a fallback of last resort.
- **Record what was dropped.** When a scene is cut, write down which and why.
  A silent drop reads as "all scenes succeeded" to whoever reads the output
  later.

## Prerequisites checklist (recap)
- [ ] `GEMINI_API_KEY` set in `.env`, never logged
- [ ] Full-resolution original source design available
- [ ] Physical-detail reference photo available (binding/mount/stand/etc.)
- [ ] Scene list confirmed with the user
