#!/usr/bin/env python3
"""Pick occluder thresholds (`t0` / `softness`) by looking at the actual pixels.

`composite.py`'s `"mode": "soft"` occluder turns a per-pixel discriminator into
an alpha ramp:

    alpha = clip((score - t0) / softness, 0, 1)

`score` is either `lum` (negated grey — bright paper is very negative, a dark
object is closer to 0) or `warm` (R - B — warm wood/leather is positive,
neutral print is near 0). Guessing `t0` and `softness` blind does not work: too
low and printed glyphs get pulled into the occluder, too high and the occluder
never reaches alpha 1 and the product's type ghosts through it.

This script shows the two populations the ramp has to separate:

  * **occluder pixels** — the pixels inside your ROI polygon that belong to the
    object, split off from the paper underneath it by an Otsu threshold on the
    polygon's own (bimodal) histogram.
  * **product-face pixels** — a band of the product face outside the polygon,
    held back from the polygon edge by `--standoff` so the lens-blur transition
    doesn't pollute it, and (with `--quad`) clipped to the product face so
    background/desk pixels don't either.

It prints both distributions as quantiles and side-by-side histograms so you
can see where the valley is, then proposes `t0` / `softness` from the tails:
`t0` at the product face's upper tail (still alpha 0) and `t0 + softness` at
the occluder's lower tail (already alpha 1).

Two ways to run it:

  1. `--overlay` (no polygon needed): writes a copy of the scene with a
     labelled pixel-coordinate grid on top, so you can read polygon vertices
     off it by eye. Do this first.
  2. `--poly x0,y0 x1,y1 ...`: the actual probe.

Usage:
    python probe_occluder.py <scene> --overlay [--grid 100] [--out PATH]
    python probe_occluder.py <scene> --poly x0,y0 x1,y1 ... [--metric lum|warm]
        [--quad x0,y0 x1,y1 x2,y2 x3,y3] [--standoff 40] [--band 80]
        [--bins 24] [--scenes-dir DIR]

<scene> is either a path to a scene image (e.g. scenes/study_b.png,
/abs/path/study_b.png) or a bare scene id (e.g. study_b), which is resolved as
<scenes-dir>/<id>.png. --scenes-dir defaults to ./scenes (relative to the
current working directory).

The suggested numbers are a starting point, not an answer — look at the two
histograms and move `t0` yourself if the valley sits elsewhere. If the two
populations overlap so much that no split is clean, the script says so: that
is your signal to use `"mode": "poly"` instead, which uses the polygon itself
as the mask and needs no threshold at all.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

# Tail percentiles used for the suggestion. t0 sits at the product face's upper
# tail (those pixels must still land on alpha 0) and t0+softness at the
# occluder's lower tail (those must already be alpha 1).
FACE_TAIL_PCT = 98.0
OCCLUDER_TAIL_PCT = 2.0
MIN_SOFTNESS = 4.0


def parse_point(s: str) -> tuple[int, int]:
    x, y = s.split(",")
    return int(x), int(y)


def resolve_scene_path(scene: str, scenes_dir: Path) -> Path:
    """Resolve `scene` to an image path.

    If `scene` already has a file extension (a path to an image, relative or
    absolute), it is used as-is. Otherwise it is treated as a bare scene id
    and resolved as `<scenes_dir>/<id>.png`.
    """
    p = Path(scene)
    if p.suffix:
        return p
    return scenes_dir / f"{scene}.png"


def score_map(img, metric):
    """The same discriminator composite.py's _soft_occluder_mask() uses."""
    img = np.clip(img.astype(np.float32), 0, 255)
    if metric == "warm":
        return img[..., 2] - img[..., 0]        # R - B (OpenCV loads BGR)
    return -cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)


def poly_mask(shape, poly):
    m = np.zeros(shape[:2], np.uint8)
    cv2.fillPoly(m, [np.asarray(poly, np.int32)], 1)
    return m


def dilate(mask, radius):
    return cv2.dilate(mask, np.ones((radius * 2 + 1,) * 2, np.uint8))


def otsu_split(values, bins=128):
    """Threshold between the two modes of a bimodal 1-D distribution."""
    lo, hi = float(values.min()), float(values.max())
    counts, edges = np.histogram(values, bins=bins, range=(lo, hi))
    mids = 0.5 * (edges[:-1] + edges[1:])
    p = counts / max(counts.sum(), 1)
    w = np.cumsum(p)
    mu = np.cumsum(p * mids)
    between = (mu[-1] * w - mu) ** 2 / np.maximum(w * (1 - w), 1e-9)
    return float(mids[int(np.argmax(between))])


def write_overlay(img, path, step):
    """Save the scene with a labelled coordinate grid, for eyeballing polygons.

    Labels repeat every `step * 5` px *along* each line, not just once at the
    image edge, so a 100% zoom on any crop still shows its own coordinates.
    """
    out = img.copy()
    h, w = out.shape[:2]
    label_every = step * 5
    for x in range(0, w, step):
        major = x % label_every == 0
        cv2.line(out, (x, 0), (x, h), (255, 0, 255) if major else (255, 200, 255),
                 2 if major else 1)
        if major:
            for y in range(24, h, label_every):
                cv2.putText(out, str(x), (x + 5, y), cv2.FONT_HERSHEY_SIMPLEX,
                            0.7, (255, 0, 255), 2)
    for y in range(0, h, step):
        major = y % label_every == 0
        cv2.line(out, (0, y), (w, y), (255, 255, 0) if major else (200, 255, 255),
                 2 if major else 1)
        if major:
            for x in range(6, w, label_every):
                cv2.putText(out, str(y), (x, y - 7), cv2.FONT_HERSHEY_SIMPLEX,
                            0.7, (255, 128, 0), 2)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), out)
    return path


def histogram_rows(values, lo, hi, bins, peak, width=40):
    counts, edges = np.histogram(values, bins=bins, range=(lo, hi))
    rows = []
    for k, c in enumerate(counts):
        rows.append((f"{edges[k]:8.1f}..{edges[k + 1]:7.1f}",
                     "#" * int(round(width * c / max(peak, 1)))))
    return rows, counts


def main():
    parser = argparse.ArgumentParser(
        description="Probe an occluder ROI and suggest composite.py t0 / softness."
    )
    parser.add_argument(
        "scene",
        help="Path to a scene image, or a bare scene id resolved under --scenes-dir.",
    )
    parser.add_argument(
        "--poly",
        nargs="+",
        type=parse_point,
        metavar="x,y",
        default=None,
        help="ROI polygon around the occluder (same polygon you'd put in scenes.json), "
             "e.g. --poly 742,2100 770,2028 800,1962 ...",
    )
    parser.add_argument(
        "--metric",
        choices=("lum", "warm"),
        default="lum",
        help="Discriminator: 'lum' for a dark object on bright paper, 'warm' (R-B) for "
             "out-of-focus wood/leather against neutral print (default: lum).",
    )
    parser.add_argument(
        "--quad",
        nargs=4,
        type=parse_point,
        metavar="x,y",
        default=None,
        help="The scene's product-face quad (TL TR BR BL), so the product-face sample "
             "is clipped to the product instead of spilling onto the background.",
    )
    parser.add_argument(
        "--standoff",
        type=int,
        default=40,
        help="Gap in px between the polygon and the product-face sample band, so the "
             "lens-blur transition is excluded (default: 40).",
    )
    parser.add_argument(
        "--band",
        type=int,
        default=80,
        help="Width in px of the product-face sample band (default: 80).",
    )
    parser.add_argument("--bins", type=int, default=24, help="Histogram bins (default: 24).")
    parser.add_argument(
        "--overlay",
        action="store_true",
        help="Also write a coordinate-grid overlay of the scene, for reading off "
             "polygon vertices by eye.",
    )
    parser.add_argument("--grid", type=int, default=100, help="Overlay grid step in px (default: 100).")
    parser.add_argument(
        "--scenes-dir",
        type=Path,
        default=Path("scenes"),
        help="Directory to resolve a bare scene id against (default: ./scenes).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Overlay output path (default: <scene's dir>/_inspect/grid_<scene id>.png).",
    )
    args = parser.parse_args()

    path = resolve_scene_path(args.scene, args.scenes_dir)
    img = cv2.imread(str(path))
    if img is None:
        raise SystemExit(f"Could not read scene image: {path}")

    if args.overlay:
        dst = args.out or (path.parent / "_inspect" / f"grid_{path.stem}.png")
        print(f"overlay: {write_overlay(img, dst, args.grid)}  {img.shape[1]}x{img.shape[0]}")
        if args.poly is None:
            print("Read the polygon vertices off the overlay, then rerun with "
                  "--poly x,y x,y ...")
            return

    if args.poly is None:
        raise SystemExit("Nothing to do: pass --poly x,y x,y ... (and/or --overlay).")
    if len(args.poly) < 3:
        raise SystemExit("--poly needs at least 3 vertices.")

    score = score_map(img, args.metric)
    roi = poly_mask(img.shape, args.poly)

    band = dilate(roi, args.standoff + args.band) - dilate(roi, args.standoff)
    if args.quad is not None:
        band = band & poly_mask(img.shape, args.quad)

    inside = score[roi > 0]
    band_vals = score[band > 0]
    if inside.size < 200:
        raise SystemExit("ROI polygon covers too few pixels; check the coordinates.")
    if band_vals.size < 200:
        raise SystemExit(
            "Product-face sample is too small; lower --standoff, raise --band, "
            "or check --quad."
        )

    # Split the ROI's own bimodal histogram into "occluder" and "paper under it",
    # then keep only the below-split part of the outside band as product face
    # (in scenes where the occluder extends past the polygon, the band would
    # otherwise be half occluder).
    split = otsu_split(inside)
    occ_vals = inside[inside > split]
    face_vals = band_vals[band_vals <= split]
    if occ_vals.size < 100 or face_vals.size < 100:
        raise SystemExit(
            f"The ROI does not look bimodal on '{args.metric}' (split={split:.1f}, "
            f"occluder {occ_vals.size} px, face {face_vals.size} px). Try the other "
            '--metric, or use "mode": "poly" and skip thresholds entirely.'
        )

    print(f"scene    : {path}  ({img.shape[1]}x{img.shape[0]})")
    print(f"metric   : {args.metric}  "
          f"({'R - B' if args.metric == 'warm' else '-grey; bright paper is very negative'})")
    print(f"occluder : {occ_vals.size} px  (inside the polygon, above the Otsu split {split:.1f})")
    print(f"face     : {face_vals.size} px  (band outside the polygon, standoff "
          f"{args.standoff} px, width {args.band} px"
          f"{', clipped to --quad' if args.quad is not None else ''})")
    if args.quad is None:
        print("           WARNING: no --quad given, so this band runs off the product "
              "onto the")
        print("           background. That inflates t0 and is how you end up with a "
              "ramp that")
        print("           never reaches alpha 1. Pass the product quad.")

    qs = (1, 5, 25, 50, 75, 95, 99)
    print("\nquantiles")
    print("            " + " ".join(f"{q:>7}%" for q in qs))
    for name, vals in (("occluder", occ_vals), ("face    ", face_vals)):
        print(f"  {name}  " + " ".join(f"{np.percentile(vals, q):8.1f}" for q in qs))

    lo = float(min(occ_vals.min(), face_vals.min()))
    hi = float(max(occ_vals.max(), face_vals.max()))
    peak = max(np.histogram(occ_vals, bins=args.bins, range=(lo, hi))[0].max(),
               np.histogram(face_vals, bins=args.bins, range=(lo, hi))[0].max())
    occ_rows, _ = histogram_rows(occ_vals, lo, hi, args.bins, peak)
    face_rows, _ = histogram_rows(face_vals, lo, hi, args.bins, peak)

    print(f"\n{'score range':>24} | {'face (want alpha 0)':<42}| occluder (want alpha 1)")
    for (label, fbar), (_, obar) in zip(face_rows, occ_rows):
        print(f"{label:>24} | {fbar:<42}| {obar}")

    t0 = float(np.percentile(face_vals, FACE_TAIL_PCT))
    end = float(np.percentile(occ_vals, OCCLUDER_TAIL_PCT))
    softness = max(end - t0, MIN_SOFTNESS)

    face_alpha = float(np.clip((face_vals - t0) / softness, 0, 1).mean())
    occ_alpha = float(np.clip((occ_vals - t0) / softness, 0, 1).mean())

    print(f"\nsuggested (t0 = face p{FACE_TAIL_PCT:g}, t0+softness = occluder "
          f"p{OCCLUDER_TAIL_PCT:g}):")
    print(f'  "mode": "soft", "metric": "{args.metric}", '
          f'"t0": {t0:.1f}, "softness": {softness:.1f}')
    print(f"  ramp spans {t0:.1f} .. {t0 + softness:.1f}")
    print(f"  mean alpha -> face {face_alpha:.2f} (want ~0), "
          f"occluder {occ_alpha:.2f} (want ~1)")
    print("  Starting point only: read the two histograms above and move t0 to the "
          "valley yourself if it sits elsewhere.")

    if face_alpha > 0.10 or occ_alpha < 0.85:
        print("\n  WARNING: this ramp does not separate the two cleanly.")
        print("  Tighten the polygon, try the other --metric, or use")
        print('  "mode": "poly" — it masks with the polygon itself, so no threshold')
        print("  is needed. A slightly coarse edge beats type ghosting through the")
        print("  occluder. See the product-mockup skill's review-checklist")
        print("  reference, \"Choosing an occluder mode\".")


if __name__ == "__main__":
    main()
