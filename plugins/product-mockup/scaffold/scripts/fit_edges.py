#!/usr/bin/env python3
"""Sub-pixel edge fitting for the product face in a generated scene.

Scans 1-D gradient profiles across each edge, fits a line by least squares with
one outlier-rejection pass, and prints the four corner intersections. Used to
turn eyeballed quads into measured ones.

Usage:
    python fit_edges.py <scene> <edge spec> ... [--scenes-dir DIR]
      edge spec: bottom=x0,x1,y0,y1  left=y0,y1,x0,x1  right=y0,y1,x0,x1  top=x0,x1,y0,y1

<scene> is either a path to a scene image (e.g. scenes/study_a.png,
/abs/path/study_a.png) or a bare scene id (e.g. study_a), which is resolved
as <scenes-dir>/<id>.png. --scenes-dir defaults to ./scenes (relative to the
current working directory).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def edge_points(gray, spec, kind):
    """Walk the scan range, return (pos_along, pos_across) of the strongest step."""
    a0, a1, b0, b1 = spec
    pts = []
    for a in range(a0, a1, 6):
        if kind in ("bottom", "top"):
            prof = gray[b0:b1, a - 2:a + 3].mean(1)
        else:
            prof = gray[a - 2:a + 3, b0:b1].mean(0)
        d = np.diff(cv2.GaussianBlur(prof.reshape(-1, 1), (1, 7), 1.6).ravel())
        if d.size == 0:
            continue
        # paper is bright: bottom/right edges are falling steps, top/left rising
        idx = int(np.argmin(d)) if kind in ("bottom", "right") else int(np.argmax(d))
        if abs(d[idx]) < 6:
            continue
        pts.append((a, b0 + idx + 0.5))
    return np.array(pts, float)


def fit(pts):
    for _ in range(2):
        if len(pts) < 4:
            break
        k, c = np.polyfit(pts[:, 0], pts[:, 1], 1)
        res = np.abs(np.polyval([k, c], pts[:, 0]) - pts[:, 1])
        pts = pts[res < max(3.0, 2.0 * res.std())]
    k, c = np.polyfit(pts[:, 0], pts[:, 1], 1)
    return k, c, len(pts)


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


def main():
    parser = argparse.ArgumentParser(
        description="Fit sub-pixel paper edges in a scene and print corner intersections."
    )
    parser.add_argument(
        "scene",
        help="Path to a scene image, or a bare scene id resolved under --scenes-dir.",
    )
    parser.add_argument(
        "edges",
        nargs="+",
        metavar="EDGE_SPEC",
        help="bottom=x0,x1,y0,y1  left=y0,y1,x0,x1  right=y0,y1,x0,x1  top=x0,x1,y0,y1",
    )
    parser.add_argument(
        "--scenes-dir",
        type=Path,
        default=Path("scenes"),
        help="Directory to resolve a bare scene id against (default: ./scenes).",
    )
    args = parser.parse_args()

    path = resolve_scene_path(args.scene, args.scenes_dir)
    img = cv2.imread(str(path))
    if img is None:
        raise SystemExit(f"Could not read scene image: {path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)

    lines = {}
    for arg in args.edges:
        kind, nums = arg.split("=")
        spec = [int(v) for v in nums.split(",")]
        pts = edge_points(gray, spec, kind)
        k, c, n = fit(pts)
        lines[kind] = (k, c)
        print(f"{kind}: slope={k:+.5f} intercept={c:.1f} n={n}")

    def cross(h, v):
        """h: across = k*a + c with a = x ; v: across = k*a + c with a = y."""
        kh, ch = lines[h]
        kv, cv_ = lines[v]
        # y = kh*x + ch ; x = kv*y + cv_
        y = (kh * cv_ + ch) / (1 - kh * kv)
        x = kv * y + cv_
        return round(x), round(y)

    for name, (h, v) in {"TL": ("top", "left"), "TR": ("top", "right"),
                         "BR": ("bottom", "right"), "BL": ("bottom", "left")}.items():
        if h in lines and v in lines:
            print(name, cross(h, v))


if __name__ == "__main__":
    main()
