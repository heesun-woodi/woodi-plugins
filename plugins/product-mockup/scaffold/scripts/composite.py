"""Composite the original product artwork onto AI-generated scene images.

Product-agnostic compositor, generalized from the reference project (a printed
wall calendar) this kit was extracted from. Every scene gets the
full source design (or a sub-rect of it) warped through a 4-point perspective
transform onto the product face that the generator produced, so small text /
fine print stays pixel-exact (AI image models cannot reliably preserve small
text, so this hybrid step is load-bearing, not cosmetic).

Realism passes, in order:
  1. perspective warp (pre-downsampled with INTER_AREA -> no moire)
  2. low-frequency illumination transfer from the scene's own product pixels
  3. binding/edge-band detail multiply (keeps the scene's own fine detail on top)
  4. film grain matched to the scene's noise floor
  5. feathered alpha composite
  6. optional: old drop-shadow erase + synthetic drop shadow for scenes whose
     generated product was smaller/shorter than the real design
  7. optional: occluder re-paste (something in the scene sits in front of the
     product and must stay on top of the composite)

Run:
    .venv/bin/python composite.py --config scenes.json [scene_id ...]

All product-specific data (source scan path, page landmarks, and the per-scene
warp/lighting recipe) lives in the --config JSON so this script is reusable
across products. See scenes.example.json in this folder for the schema and
per-key documentation.

--- scenes.json key reference (per scene, under "scenes": {"<scene_id>": {...}}) ---
  quad            REQUIRED unless quad_rect is given. 4 [x, y] points in the
                  scene image, in TL, TR, BR, BL order — the corners the
                  source design gets warped onto. Use fit_edges.py /
                  zoom_corners.py to measure these from the generated scene.
  quad_rect       Shortcut for a frontal (non-skewed) placement: [left, top,
                  right] in scene-image px. The bottom edge is derived from
                  the source rect's aspect ratio so nothing stretches.
                  Mutually exclusive with quad.
  src_rect        Optional [x, y, w, h] sub-rect of the source scan to use
                  instead of the full landmarks.page (e.g. when only the date
                  face needs replacing because the generator's own artwork
                  panel is being kept). Defaults to landmarks.page.
  band            [top, bottom] in source-space rows (relative to the warped
                  region), kept as "binding/edge detail": the scene's own
                  pixels are multiplied back in here so printed hardware
                  (spiral wire, stitching, stand hinge, ...) stays on top of
                  the flat warped artwork instead of being replaced by it.
  light_sigma_frac  Fraction of the warped region's height used as the blur
                  radius for illumination transfer. Larger = softer, more
                  global relighting; smaller = tracks local shadows more.
  light_clip      [lo, hi] clamp on the per-pixel relighting gain, so the
                  transfer can't blow out highlights or crush shadows.
  grain           Multiplier on the measured scene grain (film-noise) applied
                  to the composited region. 1.0 = match the scene exactly.
  orig_bottom     Bottom y (scene-image px) of the AI-generated product face,
                  when it's shorter than the real design. Triggers old
                  drop-shadow erasure + (if drop_shadow is set) a new one.
  drop_shadow     Optional dict: strength, sigma, dy, dx for a synthetic
                  contact shadow under the part of the design the generator
                  never drew (used together with orig_bottom).
  occluders       Optional list of dicts describing things in the scene that
                  sit in front of the product and must be re-pasted on top of
                  the composite. Each has a "poly" (rough ROI polygon) and a
                  "mode": "auto" (threshold-based silhouette on a dark
                  object), "soft" (soft alpha ramp on a "lum" or "warm"
                  discriminator, for out-of-focus occluders), or "poly" (use
                  the polygon itself as a hard/feathered mask). May also carry
                  a "shadow" dict (strength, sigma, dy, dx) for a contact
                  shadow cast by the occluder onto the composited product.

--- scenes.json "landmarks" section ---
  page            [x, y, w, h] tight bounds of the printed page/panel inside
                  the source scan (outside this is scanner margin/matte).
  content_bottom  Last printed row of the source scan; used to sample a
                  "paper" background color when src_rect runs past the scan.
  Any additional landmark keys your evidence_crop customization needs (e.g.
  date_face_top, grid_top, grid_bottom for the calendar's date grid) can be
  added here and read via LANDMARKS[...] — see evidence_crop() below.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

# Populated from --config at startup; see load_config().
PATHS: dict = {}
LANDMARKS: dict = {}
CONFIG: dict = {}


def rect_quad(left, top, right, aspect):
    """Frontal placement: derive the bottom from the source aspect so nothing stretches."""
    h = (right - left) / aspect
    return [[left, top], [right, top], [right, top + h], [left, top + h]]


def load_config(config_path: Path) -> None:
    """Populate the module-level PATHS / LANDMARKS / CONFIG from a scenes.json file.

    Relative paths are resolved against the config file's own directory.
    """
    global PATHS, LANDMARKS, CONFIG
    data = json.loads(config_path.read_text(encoding="utf-8"))
    base_dir = config_path.parent

    def resolve(rel_path: str) -> str:
        p = Path(rel_path)
        return str(p if p.is_absolute() else (base_dir / p).resolve())

    raw_paths = data["paths"]
    PATHS = {
        "src_path": resolve(raw_paths["src_path"]),
        "scene_dir": resolve(raw_paths.get("scene_dir", "scenes")),
        "out_dir": resolve(raw_paths.get("out_dir", "final")),
        "evidence_dir": resolve(raw_paths.get("evidence_dir", "final/_evidence")),
    }
    LANDMARKS = dict(data["landmarks"])

    page = LANDMARKS["page"]
    aspect = page[2] / page[3]

    scenes_cfg = {}
    for scene_id, raw in data["scenes"].items():
        cfg = dict(raw)
        if "quad" not in cfg:
            if "quad_rect" not in cfg:
                raise SystemExit(
                    f"scene '{scene_id}' needs either 'quad' or 'quad_rect'"
                )
            left, top, right = cfg.pop("quad_rect")
            cfg["quad"] = rect_quad(left, top, right, aspect)
        scenes_cfg[scene_id] = cfg
    CONFIG = scenes_cfg


# --------------------------------------------------------------------------- utils
def gblur(img, sigma):
    k = int(sigma * 6) | 1
    return cv2.GaussianBlur(img, (k, k), sigma, borderType=cv2.BORDER_REPLICATE)


def norm_blur(img, weight, sigma):
    """Normalised convolution: blur `img` using only pixels where weight>0."""
    w = gblur(weight, sigma)
    if img.ndim == 3:
        w = w[..., None]
        num = gblur(img * weight[..., None], sigma)
    else:
        num = gblur(img * weight, sigma)
    return num / np.maximum(w, 1e-6)


def build_source(full, rect):
    """Crop `rect` (full-image coords) out of the scan, padding with paper white.

    Scenes whose generated product only needs a sub-region replaced map a
    sub-rect; the rect may also run past the scan's bottom, in which case the
    missing rows are the page's own blank margin and are filled with paper white.
    """
    page = LANDMARKS["page"]
    content_bottom = LANDMARKS["content_bottom"]
    x, y, w, h = rect
    paper = np.median(
        full[content_bottom + 12:page[1] + page[3], page[0] + 200:page[0] + 1200]
        .reshape(-1, 3), axis=0)
    canvas = np.tile(paper.astype(np.float32), (h, w, 1))
    sx0, sy0 = max(x, 0), max(y, 0)
    sx1, sy1 = min(x + w, full.shape[1]), min(y + h, full.shape[0])
    if sx1 > sx0 and sy1 > sy0:
        canvas[sy0 - y:sy1 - y, sx0 - x:sx1 - x] = full[sy0:sy1, sx0:sx1]
    return canvas


def poly_mask(shape, poly, feather=0.0):
    m = np.zeros(shape[:2], np.float32)
    cv2.fillPoly(m, [np.round(np.asarray(poly)).astype(np.int32)], 1.0, cv2.LINE_AA)
    if feather > 0:
        m = gblur(m, feather)
    return m


def measure_grain(scene_gray, quad):
    """Noise floor of the flat wall/surface next to the product (robust to clutter)."""
    h, w = scene_gray.shape
    q = np.asarray(quad)
    x0, x1 = int(q[:, 0].min()), int(q[:, 0].max())
    y0, y1 = int(q[:, 1].min()), int(q[:, 1].max())
    hp = scene_gray - gblur(scene_gray, 1.6)
    stds = []
    for cx in (x0 - 120, x0 - 55, x1 + 55, x1 + 120):
        for cy in np.linspace(y0 + 40, y1 - 40, 6):
            px, py = int(cx), int(cy)
            if px - 32 < 0 or py - 32 < 0 or px + 32 >= w or py + 32 >= h:
                continue
            patch = hp[py - 32:py + 32, px - 32:px + 32]
            stds.append(float(np.std(patch)))
    if not stds:
        return 0.8
    return float(min(np.percentile(stds, 30), 3.2))


# --------------------------------------------------------------------------- core
def composite(scene_id, cfg, full_scan):
    scene_path = f"{PATHS['scene_dir']}/{scene_id}.png"
    scene = cv2.imread(scene_path).astype(np.float32)
    H_img, W_img = scene.shape[:2]
    quad = np.asarray(cfg["quad"], np.float32)

    rect = cfg.get("src_rect", LANDMARKS["page"])
    src_page = build_source(full_scan, rect)
    sw, sh = rect[2], rect[3]
    src_corners = np.float32([[0, 0], [sw, 0], [sw, sh], [0, sh]])
    Hm = cv2.getPerspectiveTransform(src_corners, quad)
    Hinv = np.linalg.inv(Hm)

    # ---- inverse maps over the quad's bounding box (+ margin)
    pad = 90
    bx0 = max(0, int(quad[:, 0].min()) - pad)
    bx1 = min(W_img, int(quad[:, 0].max()) + pad)
    by0 = max(0, int(quad[:, 1].min()) - pad)
    by1 = min(H_img, int(quad[:, 1].max()) + pad)
    xs, ys = np.meshgrid(np.arange(bx0, bx1, dtype=np.float32),
                         np.arange(by0, by1, dtype=np.float32))
    ones = np.ones_like(xs)
    stack = np.stack([xs, ys, ones], -1)[..., None]
    uvw = (Hinv[None, None] @ stack)[..., 0]
    u = uvw[..., 0] / uvw[..., 2]
    v = uvw[..., 1] / uvw[..., 2]

    # ---- pre-downsample the source to roughly the on-screen size (INTER_AREA)
    dst_h = 0.5 * (np.linalg.norm(quad[3] - quad[0]) + np.linalg.norm(quad[2] - quad[1]))
    dst_w = 0.5 * (np.linalg.norm(quad[1] - quad[0]) + np.linalg.norm(quad[2] - quad[3]))
    fx = min(1.0, float(dst_w) / sw * 1.08)
    fy = min(1.0, float(dst_h) / sh * 1.08)
    small = cv2.resize(src_page, (max(2, int(sw * fx)), max(2, int(sh * fy))),
                       interpolation=cv2.INTER_AREA).astype(np.float32)
    sh_s, sw_s = small.shape[:2]
    map_x = (u * (sw_s / sw)).astype(np.float32)
    map_y = (v * (sh_s / sh)).astype(np.float32)
    warped = cv2.remap(small, map_x, map_y, cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_REPLICATE)

    # ---- masks (in bbox space)
    inside = ((u >= 0) & (u <= sw) & (v >= 0) & (v <= sh)).astype(np.float32)
    alpha = gblur(inside, 1.2)
    alpha = np.clip((alpha - 0.12) / 0.76, 0, 1)

    roi = scene[by0:by1, bx0:bx1]

    # ---- illumination: only sample where the generator actually drew product
    light_src = inside.copy()
    if cfg.get("orig_bottom"):
        light_src[ys > cfg["orig_bottom"] - 6] = 0.0
    light_src = cv2.erode(light_src, np.ones((7, 7), np.uint8))
    if light_src.sum() < 500:
        light_src = inside.copy()

    sigma = max(6.0, cfg["light_sigma_frac"] * dst_h)
    roi_lum = roi @ np.float32([0.114, 0.587, 0.299])
    warp_lum = warped @ np.float32([0.114, 0.587, 0.299])
    wsum = max(float(light_src.sum()), 1.0)

    def avg(a):
        if a.ndim == 3:
            return np.array([(a[..., c] * light_src).sum() / wsum for c in range(3)], np.float32)
        return float((a * light_src).sum() / wsum)

    scene_mean, scene_lm = avg(roi), avg(roi_lum)
    src_mean, src_lm = avg(warped), avg(warp_lum)

    # brightness varies at the sigma scale; colour temperature only at 3x sigma,
    # so the printed pixels of the generated product cannot tint the surface.
    lum = norm_blur(roi_lum, light_src, sigma)
    col = norm_blur(roi, light_src, sigma * 3.0)
    col_l = norm_blur(roi_lum, light_src, sigma * 3.0)
    chroma = (col / np.maximum(col_l, 1e-3)[..., None]) / \
        np.maximum(scene_mean / max(scene_lm, 1e-3), 1e-3)[None, None, :]
    chroma = 1.0 + (chroma - 1.0) * cfg.get("chroma_strength", 0.7)

    base = (scene_mean * src_lm) / np.maximum(src_mean * max(scene_lm, 1e-3), 1e-3)
    gain = (lum / max(src_lm, 1e-3))[..., None] * base[None, None, :] * chroma
    lo, hi = cfg["light_clip"]
    gain = np.clip(gain, lo, hi)
    out = warped * gain

    soften = cfg.get("soften", 0.35)
    if soften > 0:
        out = out * (1 - soften) + gblur(out, 0.9) * soften

    # ---- binding/edge band: re-imprint the scene's own fine detail (high-freq darkening)
    b0, b1 = cfg["band"]
    band = ((v >= b0) & (v <= b1)).astype(np.float32)
    band = gblur(band, 3.0)
    roi_g = cv2.cvtColor(roi.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
    detail = np.clip(roi_g / np.maximum(gblur(roi_g, 9.0), 1e-3), 0.18, 1.0)
    out *= (1.0 - band[..., None] * (1.0 - detail[..., None]))

    # ---- grain matched to the scene's noise floor
    g_sigma = measure_grain(cv2.cvtColor(scene.astype(np.uint8), cv2.COLOR_BGR2GRAY)
                            .astype(np.float32), quad) * cfg["grain"]
    rng = np.random.default_rng(7)
    out += rng.normal(0.0, max(g_sigma, 0.4), out.shape[:2])[..., None]

    result = scene.copy()

    # ---- erase the generated product's old drop shadow in the extension band
    if cfg.get("orig_bottom"):
        _erase_old_shadow(result, cfg, quad, inside, (bx0, by0, bx1, by1))

    # ---- synthetic drop shadow under the new (lower) bottom edge
    if cfg.get("drop_shadow"):
        nb = float(np.asarray(quad)[2:, 1].max())
        ramp = float(cfg["orig_bottom"] - 30) if cfg.get("orig_bottom") else nb - 45
        _drop_shadow(result, cfg["drop_shadow"], inside, (bx0, by0, bx1, by1), quad, ramp)

    # ---- composite
    a = alpha[..., None]
    result[by0:by1, bx0:bx1] = result[by0:by1, bx0:bx1] * (1 - a) + out * a

    # ---- occluders back on top
    for occ in cfg.get("occluders", []):
        _repaste_occluder(result, scene, occ)

    return np.clip(result, 0, 255).astype(np.uint8), Hm, rect


def _erase_old_shadow(result, cfg, quad, inside, box):
    """Wipe the leftover drop shadow that hugged the shorter generated product.

    Only the thin side strips need it: everything directly under the old bottom
    edge is repainted by the taller design. Donor rows come from higher up the
    same strip, which carries the product's vertical side shading.
    """
    bx0, by0, bx1, by1 = box
    ob = int(cfg["orig_bottom"])
    pad = cfg.get("erase_pad", 55)
    y0, y1 = max(0, ob - 14), min(result.shape[0], ob + 52)
    x0 = max(0, int(np.asarray(quad)[:, 0].min()) - pad)
    x1 = min(result.shape[1], int(np.asarray(quad)[:, 0].max()) + pad)
    if y1 <= y0:
        return
    page = np.zeros(result.shape[:2], np.float32)
    page[by0:by1, bx0:bx1] = inside
    page = cv2.dilate(page, np.ones((7, 7), np.uint8))
    m = np.zeros(result.shape[:2], np.uint8)
    m[y0:y1, x0:x1] = 1
    m[page > 0.02] = 0
    if m.sum() == 0:
        return
    fixed = cv2.inpaint(np.clip(result, 0, 255).astype(np.uint8), m, 9, cv2.INPAINT_TELEA)
    a = gblur(m.astype(np.float32), 1.5)[..., None]
    result[:] = result * (1 - a) + fixed.astype(np.float32) * a


def _drop_shadow(result, ds, inside, box, quad, ramp_from):
    """Soft contact shadow for the part of the page that the generator never drew."""
    bx0, by0, bx1, by1 = box
    shifted = np.zeros_like(inside)
    dy, dx = int(ds["dy"]), int(ds.get("dx", 0))
    ys0, xs0 = max(0, dy), max(0, dx)
    shifted[ys0:, xs0:] = inside[:inside.shape[0] - ys0, :inside.shape[1] - xs0]
    sh = gblur(shifted, ds["sigma"])
    sh *= np.clip(1.0 - cv2.dilate(inside, np.ones((5, 5), np.uint8)), 0, 1)
    yy = np.arange(by0, by1, dtype=np.float32)[:, None]
    sh *= np.clip((yy - ramp_from) / 55.0, 0, 1)
    region = result[by0:by1, bx0:bx1]
    region *= (1.0 - ds["strength"] * sh)[..., None]


def _occluder_mask(scene, occ):
    """Hug the occluder's real silhouette: threshold inside a generous ROI polygon."""
    roi = poly_mask(scene.shape, occ["poly"], 0.0)
    roi = cv2.dilate(roi, np.ones((13, 13), np.uint8))
    gray = cv2.cvtColor(np.clip(scene, 0, 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
    raw = ((gray < occ.get("thresh", 165)) & (roi > 0)).astype(np.uint8)
    # open first: kills thin printed strokes that would otherwise bridge to the body
    raw = cv2.morphologyEx(raw, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    raw = cv2.morphologyEx(raw, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(raw, 8)
    if n > 1:
        k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        raw = (lab == k).astype(np.uint8)
    return raw.astype(np.float32)


def _soft_occluder_mask(scene, occ):
    """Soft alpha for defocused occluders: ramp on a discriminator, blur preserved.

    `metric` picks what separates foreground from paper - "lum" for a dark
    object on a bright surface, "warm" (R-B) for out-of-focus wood/warm
    material against a neutral print. A ramp instead of a hard threshold keeps
    the lens blur at the boundary, and the core cleanup drops isolated printed
    glyphs without hardening the edge.
    """
    img = np.clip(scene, 0, 255)
    if occ.get("metric", "lum") == "warm":
        score = img[..., 2] - img[..., 0]
    else:
        score = -cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
    t0, width = occ["t0"], occ.get("softness", 25.0)
    alpha = np.clip((score - t0) / width, 0, 1)
    alpha *= poly_mask(scene.shape, occ["poly"], occ.get("roi_feather", 3.0))
    core = (alpha > 0.6).astype(np.uint8)
    core = cv2.morphologyEx(core, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(core, 8)
    if n > 1:
        k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        core = (lab == k).astype(np.uint8)
    keep = gblur(cv2.dilate(core, np.ones((25, 25), np.uint8)).astype(np.float32), 6.0)
    return alpha * np.clip(keep, 0, 1)


def _repaste_occluder(result, scene, occ):
    mode = occ.get("mode", "auto")
    if mode == "soft":
        hard = _soft_occluder_mask(scene, occ)
        m = hard[..., None]
        occ = dict(occ, _hard=(hard > 0.5).astype(np.float32))
    elif mode == "poly":
        hard = poly_mask(result.shape, occ["poly"], occ.get("feather", 6.0))
        m = hard[..., None]
        occ = dict(occ, _hard=(hard > 0.5).astype(np.float32))
    else:
        hard = _occluder_mask(scene, occ)
        m = gblur(hard, occ.get("feather", 1.3))[..., None]
        occ = dict(occ, _hard=hard)
    if occ.get("shadow"):
        s = occ["shadow"]
        hard = occ.get("_hard")
        if hard is None:
            hard = poly_mask(result.shape, occ["poly"], 0.0)
        M = np.float32([[1, 0, s.get("dx", 0)], [0, 1, s["dy"]]])
        moved = cv2.warpAffine(hard, M, (result.shape[1], result.shape[0]))
        sh = gblur(moved, s["sigma"]) * np.clip(1 - hard, 0, 1)
        result *= (1.0 - s["strength"] * sh)[..., None]
    result[:] = result * (1 - m) + scene * m


def evidence_crop(final, Hm, rect, scene_id):
    """Zoomed crop of the fine-print region, to prove the type/detail is undistorted.

    Uses landmarks.grid_top / grid_bottom if present (as in the calendar date
    grid); falls back to the full src_rect height if this project didn't
    define those landmarks.
    """
    ry, rh = rect[1], rect[3]
    grid_top = LANDMARKS.get("grid_top", rect[1])
    grid_bottom = LANDMARKS.get("grid_bottom", rect[1] + rect[3])
    top = float(np.clip(grid_top - ry, 0, rh))
    bot = float(np.clip(grid_bottom - ry, 0, rh))
    pts = np.float32([[[30, top], [rect[2] - 30, top],
                       [rect[2] - 30, bot], [30, bot]]])
    d = cv2.perspectiveTransform(pts, Hm)[0]
    x0, y0 = int(d[:, 0].min()), int(d[:, 1].min())
    x1, y1 = int(np.ceil(d[:, 0].max())), int(np.ceil(d[:, 1].max()))
    x0, y0 = max(0, x0 - 6), max(0, y0 - 6)
    x1, y1 = min(final.shape[1], x1 + 6), min(final.shape[0], y1 + 6)
    crop = final[y0:y1, x0:x1]
    scale = min(3.0, max(1.6, 1500.0 / max(crop.shape[1], 1)))
    crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    os.makedirs(PATHS["evidence_dir"], exist_ok=True)
    cv2.imwrite(f"{PATHS['evidence_dir']}/{scene_id}_grid_crop.png", crop)
    return crop.shape


def load_report(path: str) -> dict:
    """Previous run's report, so a partial re-run doesn't wipe the other scenes."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def main():
    parser = argparse.ArgumentParser(
        description="Composite the source design onto AI-generated scenes."
    )
    parser.add_argument(
        "--config", required=True, type=Path, help="Path to scenes.json (see scenes.example.json)."
    )
    parser.add_argument(
        "scene_ids", nargs="*", help="Scene ids to composite (default: all in config)."
    )
    args = parser.parse_args()

    load_config(args.config.resolve())

    full = cv2.imread(PATHS["src_path"]).astype(np.float32)
    os.makedirs(PATHS["out_dir"], exist_ok=True)
    os.makedirs(PATHS["evidence_dir"], exist_ok=True)
    ids = args.scene_ids or list(CONFIG)

    # Merge into the existing report so compositing a subset (the normal case
    # during the review loop) doesn't wipe the entries for scenes that weren't
    # rerun. Same read-merge-write pattern as generate_scenes.py's metadata.json.
    report_path = f"{PATHS['evidence_dir']}/composite_report.json"
    report = load_report(report_path)
    for sid in ids:
        if sid not in CONFIG:
            raise SystemExit(f"Unknown scene id: {sid}")
        final, Hm, rect = composite(sid, CONFIG[sid], full)
        cv2.imwrite(f"{PATHS['out_dir']}/{sid}_final.png", final)
        shape = evidence_crop(final, Hm, rect, sid)
        report[sid] = dict(size=[final.shape[1], final.shape[0]],
                           evidence=[shape[1], shape[0]],
                           src_rect=list(rect))
        print(f"{sid}: {final.shape[1]}x{final.shape[0]}  evidence {shape[1]}x{shape[0]}")
    # keep the config's scene order, and drop stale ids no longer in the config
    merged = {sid: report[sid] for sid in CONFIG if sid in report}
    with open(report_path, "w") as f:
        json.dump(merged, f, indent=2)


if __name__ == "__main__":
    main()
