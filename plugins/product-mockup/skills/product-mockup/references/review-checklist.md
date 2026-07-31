# Review checklist — judging generated scenes (stage 04 of the pipeline)

Judge every scene against these five categories, then assign one verdict.
Do this as a **separate agent/pass** from whoever wrote the prompt (see
`orchestration.md`) — self-grading is unreliable.

## The five checks

1. **텍스트 충실도 / Text fidelity** — is every piece of printed text
   (headers, numbers, captions, fine print) legible and correct? This check
   almost always fails at native render size for small text — that's
   expected (see `prompt-patterns.md`, "What did not work"). Crop and zoom
   before judging; don't pass or fail this on a thumbnail glance.
   **Any phone number, address, URL, or email that the generator invented is
   a hard stop** — those strings may belong to a real, uninvolved third
   party, and they must never reach a published listing.
2. **아트 충실도 / Art fidelity** — does the large-scale artwork (illustration,
   photo, layout, color palette) match the source reference in *content*, not
   just style? A plausible-looking but different illustration is a fail here
   even if it "looks nice."
3. **제품 구조 / Product structure** — is the product's physical form correct?
   Right proportions, right binding/mount/stand mechanism, right number of
   structural repeats (columns, panels, folds, pages visible), flat/rigid
   where it should be (not curled, unless the source product legitimately
   curls).
4. **연출 리얼리즘 / Staging realism** — does the scene read as a real photo?
   Consistent lighting direction and color temperature, plausible shadow,
   no obviously AI-artifact geometry in the surrounding room, no orphaned
   props floating or clipping through surfaces.
5. **이커머스 적합성 / E-commerce suitability** — is the product the clear
   visual hero (not competing with background clutter), is the framing usable
   for the intended placement (hero image vs. detail/lifestyle thumbnail),
   and is there enough of the product visible to be recognizable at
   thumbnail size?

## Verdicts

- **PASS** — all five checks are clean at native resolution, including text.
  Use the generated image as-is (still worth confirming composite isn't
  needed for consistency with other scenes in the same set — see COMPOSITE).
- **COMPOSITE** — checks 2-5 are clean; only check 1 (text fidelity) fails, or
  the product face needs the source's exact pixels for consistency even if
  the AI's version looks close. This is the *default expected* verdict for
  most scenes given the hybrid strategy — it means the composite stage will
  fix it, not that anything needs to be regenerated.
- **REGEN** — a *fixable* defect outside text: wrong art content, wrong
  binding/mount rendering, unrealistic lighting/shadow, clutter competing
  with the product, structural count errors (e.g. wrong number of columns).
  Revise the prompt using the reinforcement catalogue in
  `prompt-patterns.md` and rerun generation for just this scene id.
- **FAIL** — a *structural* defect that survived 2 REGEN rounds (see SKILL.md
  cutoff rule): wrong product shape/proportions, a required element entirely
  missing, an unusable pose/crop. Discard the scene; do not attempt a third
  round. Substitute a different scene or angle instead.

## What to record for a COMPOSITE verdict

The compositing stage (`scripts/composite.py`) needs precise inputs that only
exist once you've looked closely at the generated scene — record these while
you're already zoomed in for the text-fidelity check, don't make the
compositor re-derive them from scratch:

- **4-point quad** (or a frontal rect) in scene-image pixel coordinates: the
  four corners of the product face as the AI actually drew it, in TL, TR, BR,
  BL order. Use `scripts/fit_edges.py` to fit these sub-pixel from gradient
  profiles, or eyeball them from `scripts/zoom_corners.py`'s labelled
  montage and refine.
- **Whether the full source or a sub-rect needs warping** — if the AI's own
  art panel is usable (passes check 2) and only e.g. a date grid or fine-print
  block needs replacing, record that sub-rect instead of the full page (see
  `src_rect` in `composite.py`'s docstring) — this preserves more of the
  AI-generated realism (shadow, lighting drawn on the art panel itself).
- **Occlusion locations** — anything in the generated scene that sits in
  front of the product (a lamp, a book, reading glasses, a plant) and must
  stay on top of the composite. Note a rough polygon around it and whether
  its edge is hard (opaque object) or soft (defocused/out-of-focus) — this
  picks the `occluders[].mode` in `composite.py`'s config (see below).

## Choosing an occluder `mode`

`composite.py` offers three ways to build the occluder mask. They differ only
in how the mask's *edge* is decided; all three re-paste the scene's own pixels
on top of the composite.

| `mode` | How the mask is built | Needs a threshold? | Use when |
|---|---|---|---|
| `"auto"` | Grey threshold (`thresh`) inside the polygon, then morphological cleanup + largest connected component | yes, but just one number (`thresh`), and it's forgiving | The occluder is **opaque and in focus**, clearly darker than the product face — a lamp base, a book spine, a solid object with a crisp edge. |
| `"soft"` | Alpha *ramp* on a discriminator (`metric`: `lum` or `warm`) from `t0` to `t0 + softness` | yes — two coupled numbers, the fiddly case | The occluder is **out of focus** and its blurred edge must survive — a shelf edge, a defocused plant, anything the lens smeared. A hard mask here reads as a cutout. |
| `"poly"` | The polygon itself, feathered by `feather` | **no** | You can't find a threshold that separates cleanly, or the occluder has no usable discriminator (same brightness *and* same colour as the product face). |

**`"poly"` is the escape hatch — use it.** If `probe_occluder.py`'s two
histograms overlap, or the suggested ramp leaves the product face above alpha
0, stop tuning and set `"mode": "poly"` with a `feather` of 4–8. You lose the
lens blur at the boundary and the edge follows your polygon rather than the
object, so draw the polygon carefully — but it *always* works, needs no
threshold, and a slightly coarse edge is a far smaller defect than the
product's type ghosting through the occluder. Ship `poly`, then refine to
`soft` later if it's worth it.

### Finding `t0` / `softness` for `"soft"`

Don't guess these — run `scripts/probe_occluder.py`:

```bash
# 1. grid overlay, to read polygon vertices off the scene by eye
python scripts/probe_occluder.py scenes/<id>.png --overlay

# 2. probe: prints the occluder vs. product-face distributions and a suggestion
python scripts/probe_occluder.py scenes/<id>.png \
    --metric warm --quad <TL> <TR> <BR> <BL> --poly <x,y> <x,y> ...
```

Read the output like this:

- **Always pass `--quad`.** Without it the product-face sample runs off the
  product onto the background, which inflates `t0` and produces exactly the
  ramp that never reaches alpha 1.
- Pick `--metric` by what actually separates the two: `lum` for a dark object
  on bright paper, `warm` (R−B) for warm wood/leather against neutral print.
  If one metric's histograms overlap, try the other before giving up.
- `t0` should sit **just above the product face's upper tail** — every paper
  pixel must land on alpha 0, or printed glyphs bleed into the occluder.
- `t0 + softness` should sit **at or below the occluder's lower tail**,
  including its brightest specular rim. This is the one that bites: set it too
  high and the occluder's rim stalls around alpha 0.6, and the product's type
  shows through the object.
- The printed `mean alpha` line is the check — face near 0.00, occluder near
  1.00. If it isn't, take the `"poly"` escape hatch above.

## How to zoom for inspection

Native-resolution thumbnails hide exactly the defects that matter for an
e-commerce image. Before recording any verdict:

1. Run `scripts/zoom_corners.py <scene> x0,y0 x1,y1 x2,y2 x3,y3` with four
   rough (x, y) points around the product's corners — `<scene>` can be a bare
   scene id (resolved as `<--scenes-dir, default ./scenes>/<id>.png`) or a
   direct path to a scene image. It writes a labelled 2x2 montage (default:
   `<scene's dir>/_inspect/zoom_<scene_id>.png`, override with `--out`) with a
   pixel-coordinate grid overlaid, useful both for judging *and* for reading
   off quad corners for the composite stage.
2. Look at the montage at full resolution (not scaled down in a viewer) —
   text-fidelity defects are often invisible until you're at 100% crop zoom.
3. If judging an occluder, crop tightly around just that object at full
   resolution to decide hard vs. soft edge mode.
