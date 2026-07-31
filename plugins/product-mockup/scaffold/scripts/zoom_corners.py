#!/usr/bin/env python3
"""Zoom montage helper: crop 4 regions of a scene, upscale, overlay a labelled grid.

Usage:
    python zoom_corners.py <scene> x0,y0 x1,y1 x2,y2 x3,y3 [--half N] [--zoom Z]
        [--scenes-dir DIR] [--out PATH]

<scene> is either a path to a scene image (e.g. scenes/study_a.png,
/abs/path/study_a.png) or a bare scene id (e.g. study_a), which is resolved
as <scenes-dir>/<id>.png. --scenes-dir defaults to ./scenes (relative to the
current working directory).

Writes a 2x2 montage (order TL TR BR BL) to --out, or by default to
<scene's own dir>/_inspect/zoom_<scene_id>.png.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def tile(img, cx, cy, half, zoom, label):
    h, w = img.shape[:2]
    x0, y0 = cx - half, cy - half
    canvas = np.full((half * 2, half * 2, 3), 40, np.uint8)
    sx0, sy0 = max(0, x0), max(0, y0)
    sx1, sy1 = min(w, x0 + half * 2), min(h, y0 + half * 2)
    if sx1 > sx0 and sy1 > sy0:
        canvas[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = img[sy0:sy1, sx0:sx1]
    big = cv2.resize(canvas, None, fx=zoom, fy=zoom, interpolation=cv2.INTER_NEAREST)
    step = 20  # source px between grid lines
    for gx in range(x0 - x0 % step, x0 + half * 2, step):
        px = int((gx - x0) * zoom)
        if 0 <= px < big.shape[1]:
            major = gx % 100 == 0
            cv2.line(big, (px, 0), (px, big.shape[0]), (255, 0, 255) if major else (255, 200, 255), 2 if major else 1)
            if major:
                cv2.putText(big, str(gx), (px + 3, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 255), 2)
    for gy in range(y0 - y0 % step, y0 + half * 2, step):
        py = int((gy - y0) * zoom)
        if 0 <= py < big.shape[0]:
            major = gy % 100 == 0
            cv2.line(big, (0, py), (big.shape[1], py), (255, 255, 0) if major else (200, 255, 255), 2 if major else 1)
            if major:
                cv2.putText(big, str(gy), (3, py - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 128, 0), 2)
    cv2.putText(big, label, (10, big.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)
    return big


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


def main():
    parser = argparse.ArgumentParser(
        description="Crop 4 regions of a scene into a labelled zoom montage."
    )
    parser.add_argument(
        "scene",
        help="Path to a scene image, or a bare scene id resolved under --scenes-dir.",
    )
    parser.add_argument(
        "points",
        nargs=4,
        type=parse_point,
        metavar="x,y",
        help="4 center points, in TL, TR, BR, BL order.",
    )
    parser.add_argument("--half", type=int, default=130, help="Half-width of each crop in source px (default: 130).")
    parser.add_argument("--zoom", type=int, default=3, help="Upscale factor (default: 3).")
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
        help="Output path (default: <scene's dir>/_inspect/zoom_<scene id>.png).",
    )
    args = parser.parse_args()

    path = resolve_scene_path(args.scene, args.scenes_dir)
    img = cv2.imread(str(path))
    if img is None:
        raise SystemExit(f"Could not read scene image: {path}")

    labels = ["TL", "TR", "BR", "BL"]
    tiles = [tile(img, x, y, args.half, args.zoom, labels[k]) for k, (x, y) in enumerate(args.points)]
    top = np.hstack([tiles[0], tiles[1]])
    bot = np.hstack([tiles[3], tiles[2]])
    out = np.vstack([top, bot])

    dst = args.out or (path.parent / "_inspect" / f"zoom_{path.stem}.png")
    dst.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dst), out)
    print(dst, out.shape)


if __name__ == "__main__":
    main()
