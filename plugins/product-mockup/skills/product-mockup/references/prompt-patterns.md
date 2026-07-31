# Prompt patterns for AI scene generation (gemini-3-pro-image)

Source: analysis of the scene prompt set from the reference project this skill
was extracted from — a spiral-bound wall calendar, 8 scenes, 2 generation
rounds.

## Validated prompt structure

Every working prompt in the reference project follows the same six-part order.
Order matters — later clauses get less "attention" from the model, so the
non-negotiable preservation and structure clauses go early/mid, not last.

1. **Placement** — where exactly the product sits in the scene, stated first,
   in one flowing sentence ("Hung on the wall directly above a low oak
   console table in a warm, sunlit apartment living room, the tall vertical
   wall calendar hangs at eye level between a beige linen sofa and a large
   window on the left...").
2. **Scene description** — the supporting environment: props, wall texture,
   light quality. Keep this short and say explicitly that the space stays
   uncluttered — the product must stay the visual hero.
3. **Preservation instruction** — an explicit, unambiguous "do not alter the
   design" clause naming the reference image. This is necessary but **not
   sufficient** for small text (see "What did not work" below) — it's what
   keeps large-scale art/layout/color faithful, which the later composite
   step depends on.
4. **Binding/structure description** — how the product is physically held,
   mounted, or displayed, referencing the *second* reference photo (the
   physical-detail shot) by name.
5. **Camera and lighting** — angle, lens/eye-level language, light direction,
   depth of field. This is what actually varies the most between "front" and
   "angle_close" scene variants.
6. **Output resolution** — a one-line resolution/quality instruction at the
   very end.

## Full example (`living_room_a`)

```
Hung on the wall directly above a low oak console table in a warm, sunlit
apartment living room, the tall vertical wall calendar hangs at eye level
between a beige linen sofa and a large window on the left that pours in soft
morning daylight. A small potted fiddle-leaf fig and a woven basket sit on
the console below, and the wall is painted a warm off-white with a faint
plaster texture. Keep the exact calendar design, watercolor artwork,
lettering, and all text and numbers from the first reference image
unchanged — do not redraw or alter the design. The calendar is spiral-bound
at the top with a white PVC holder rail, hanging from a small nail, as shown
in the second reference image. Shot straight-on at eye level with a standard
50mm lens, soft directional light falling from the left casts a gentle,
natural shadow of the calendar onto the wall to its right. The room is tidy
and uncluttered so the calendar remains the hero, no clutter. Output at 4K
resolution.
```

Swap the product noun, the binding clause, and the room for your own product —
the *ordering* is the transferable part, not the wording.

## Regeneration reinforcement catalogue

When a round-1 scene comes back with a defect, add the *specific* sentence
below that targets that defect — don't rewrite the whole prompt. All four
sentences were added to all three scenes that got a round 2 (`study_b`,
`kitchen_dining_b`, `church_office_b`), and each fixed a distinct, previously-seen
failure — the round-1 versions of exactly those three are what ends up in
`scenes/_rejected/`.

Note the yield: **three scenes went into round 2 and two came out.**
`study_b` and `church_office_b` cleared their defects and went on to the composite
step; `kitchen_dining_b` did not clear its, and under the cutoff rule
(SKILL.md — no third prompt round for a structural defect) it was discarded
rather than re-prompted, with `kitchen_dining_a` taking its slot in the final
set. Budget for that: a reinforcement round is not a guaranteed fix, and the
cutoff rule is what stops one stubborn scene from eating the schedule.

| # | Sentence added | Failure it fixed |
|---|---|---|
| 1 | "The product's upper artwork is a soft watercolor painting of a figure seen from behind carrying a woven basket of flowers through a green meadow with pink wildflowers, with brush lettering down the left side — reproduce this artwork exactly as in the first reference image." | Round 1 let the model reinterpret/generalize the illustration instead of reproducing it — naming the actual subject, setting, palette and lettering block anchored it back to the reference. |
| 2 | "The date grid has exactly 7 columns (Sunday through Saturday), as in the reference image — do not add or duplicate columns or numbers." | Round 1 occasionally hallucinated an extra or duplicated column/row in the grid structure — an explicit count fixed the *structural* grid, though not the header text (see below). |
| 3 | "The page is rigid and perfectly flat against the wall, no curling or bending." | Round 1 sometimes drew a curled/bent page, which breaks the flat 4-point perspective assumption the composite step needs — this is a compositing prerequisite, not just an aesthetic note. |
| 4 | "The product is spiral-bound at the top with a white PVC holder rail **and twin wire spiral binding**, hanging from a small nail, as shown in the second reference image." | Round 1's shorter binding description sometimes rendered simplified/wrong hardware (e.g. single wire, wrong clip style) — naming the specific mechanism fixed it. |

General pattern: **when a reinforcement sentence names the specific content,
count, or mechanism instead of restating "keep it accurate," it tends to
work.** Vague reinforcement ("try to keep the text more accurate") does not
reliably help — be as concrete as sentence #1 and #2 above.

## What did not work (stop trying this)

**Small text/glyph accuracy could not be fixed by prompting.** In the
reference project the weekday header letters came out hallucinated or garbled
in *all 8 scenes* in round 1. Three of those eight were sent to a round 2 with
the four reinforcement sentences above, and the header text was still wrong in
*all 3* — including under sentence #2, which explicitly named the correct
column count and still didn't fix the header text itself (it fixed the grid
*structure*, not the small *glyphs* inside it).

Note what that means: the reinforcement sentences have a demonstrated track
record on art, structure, flatness and binding, and a 0-for-3 record on small
text. Do not spend a third prompt round chasing this. Treat any defect that is
specifically about small/fine text as a signal to move straight to the
composite step, not to iterate the prompt further.
