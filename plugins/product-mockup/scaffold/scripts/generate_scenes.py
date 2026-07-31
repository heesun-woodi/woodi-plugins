#!/usr/bin/env python3
"""Generate lifestyle scene images for a product mockup, via Gemini 3 Pro Image.

Product-agnostic generator, generalized from the reference project (a printed
wall calendar) this kit was extracted from. Uses Gemini 3
Pro Image (Nano Banana Pro) via the google-genai Interactions API
(client.interactions.create) to compose a product design (reference image 1)
placed in a real-world scene, using a second reference photo (reference image
2) so a hard-to-describe physical detail (binding, hardware, texture, stand
mechanism, ...) is rendered accurately.

Usage:
    .venv/bin/python generate_scenes.py --config project.json
    .venv/bin/python generate_scenes.py --config project.json --only living_room_a study_b
    .venv/bin/python generate_scenes.py --config project.json --env /path/to/.env

Everything project-specific (reference image paths, output folder, prompts
file, model, API key location) lives in the --config JSON so this script can
be reused across products without editing code. See config.example.json in
this same folder for the schema.
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import io
import json
import sys
import time
from pathlib import Path

from google import genai
from google.genai import errors as genai_errors
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent

DEFAULT_MODEL = "gemini-3-pro-image"
DEFAULT_REF_IMAGE_2_MAX_SIDE = 1536
MAX_CONCURRENCY = 3
MAX_RETRIES = 3
RETRY_STATUS_CODES = {429, 503}
BASE_BACKOFF_SECONDS = 2.0


class ProjectConfig:
    """Resolved paths and settings for one product-mockup project.

    All relative paths in the config JSON are resolved against the config
    file's own directory, so a project config can live anywhere (e.g. at the
    root of your working folder) and doesn't need to know where this script
    lives.
    """

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.base_dir = config_path.parent
        data = json.loads(config_path.read_text(encoding="utf-8"))

        self.ref_image_1 = self._resolve(data["ref_image_1"])
        self.ref_image_2 = self._resolve(data["ref_image_2"])
        self.ref_image_2_max_side = int(
            data.get("ref_image_2_max_side", DEFAULT_REF_IMAGE_2_MAX_SIDE)
        )
        self.scenes_dir = self._resolve(data.get("scenes_dir", "scenes"))
        self.prompts_file = self._resolve(data.get("prompts_file", "prompts.json"))
        self.model = data.get("model", DEFAULT_MODEL)
        # Where to cache the resized copy of ref_image_2 (avoids re-resizing
        # on every --only rerun during the review loop).
        self.ref_image_2_resized = self.ref_image_2.with_name(
            self.ref_image_2.stem + "_resized.jpg"
        )

    def _resolve(self, rel_path: str) -> Path:
        p = Path(rel_path)
        return p if p.is_absolute() else (self.base_dir / p).resolve()


def find_env_file(explicit: Path | None, config: ProjectConfig) -> Path:
    """Locate the .env file holding GEMINI_API_KEY.

    Search order: --env if given, then <config dir>/.env, then <cwd>/.env.
    """
    candidates = []
    if explicit is not None:
        candidates.append(explicit)
    candidates.append(config.base_dir / ".env")
    candidates.append(Path.cwd() / ".env")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise SystemExit(
        "No .env file found. Looked in: "
        + ", ".join(str(c) for c in candidates)
        + ". Pass --env <path> or create one (see .env.example)."
    )


def load_api_key(env_path: Path) -> str:
    """Read GEMINI_API_KEY from an .env file without ever printing it."""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == "GEMINI_API_KEY":
            value = value.strip().strip('"').strip("'")
            if not value:
                raise SystemExit(f"GEMINI_API_KEY is empty in {env_path}")
            return value
    raise SystemExit(f"GEMINI_API_KEY not found in {env_path}")


def get_or_create_resized_reference(config: ProjectConfig) -> Path:
    """Resize ref_image_2 so its longest side is ref_image_2_max_side.

    Caches the resized copy on disk so repeated runs (e.g. --only reruns
    during the review loop) don't redo the work.
    """
    if config.ref_image_2_resized.exists():
        return config.ref_image_2_resized
    with Image.open(config.ref_image_2) as im:
        im = im.convert("RGB")
        width, height = im.size
        scale = config.ref_image_2_max_side / max(width, height)
        if scale < 1:
            im = im.resize(
                (round(width * scale), round(height * scale)), Image.LANCZOS
            )
        im.save(config.ref_image_2_resized, "JPEG", quality=92)
    return config.ref_image_2_resized


def encode_image_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def mime_for(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".png":
        return "image/png"
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    raise SystemExit(f"Unsupported reference image type: {path}")


def build_input_blocks(
    prompt_text: str, ref1_b64: str, ref1_mime: str, ref2_b64: str, ref2_mime: str
) -> list:
    # Order matters: first reference image, second reference image, then the
    # text prompt (the prompts refer to "first/second reference image").
    return [
        {"type": "image", "mime_type": ref1_mime, "data": ref1_b64},
        {"type": "image", "mime_type": ref2_mime, "data": ref2_b64},
        {"type": "text", "text": prompt_text},
    ]


def generate_one(
    client: "genai.Client",
    scene: dict,
    input_blocks: list,
    model: str,
    scenes_dir: Path,
    project_root: Path,
) -> dict:
    scene_id = scene["id"]
    input_blocks = [dict(b) for b in input_blocks[:-1]] + [
        {"type": "text", "text": scene["prompt"]}
    ]

    last_error = None
    elapsed = 0.0
    attempt = 0
    for attempt in range(1, MAX_RETRIES + 1):
        start = time.monotonic()
        try:
            interaction = client.interactions.create(
                model=model,
                input=input_blocks,
                response_format={"type": "image", "image_size": "2K"},
            )
            elapsed = time.monotonic() - start
            output_image = interaction.output_image
            if output_image is None or not output_image.data:
                raise RuntimeError("No image returned in interaction.output_image")

            image_bytes = base64.b64decode(output_image.data)
            with Image.open(io.BytesIO(image_bytes)) as img:
                img.load()
                width, height = img.size
                out_path = scenes_dir / f"{scene_id}.png"
                img.convert("RGB").save(out_path, "PNG")

            return {
                "id": scene_id,
                "status": "success",
                "path": str(_relative_or_absolute(out_path, project_root)),
                "model": model,
                "elapsed_seconds": round(elapsed, 2),
                "resolution": f"{width}x{height}",
                "attempts": attempt,
            }
        except genai_errors.APIError as e:
            elapsed = time.monotonic() - start
            status_code = getattr(e, "code", None)
            last_error = f"APIError {status_code}: {getattr(e, 'message', str(e))}"
            if status_code in RETRY_STATUS_CODES and attempt < MAX_RETRIES:
                time.sleep(BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)))
                continue
            break
        except Exception as e:  # noqa: BLE001 - report and move on, don't crash the batch
            elapsed = time.monotonic() - start
            last_error = f"{type(e).__name__}: {e}"
            break

    return {
        "id": scene_id,
        "status": "failed",
        "error": last_error,
        "model": model,
        "elapsed_seconds": round(elapsed, 2),
        "attempts": attempt,
    }


def _relative_or_absolute(path: Path, project_root: Path) -> Path:
    try:
        return path.relative_to(project_root)
    except ValueError:
        return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate product lifestyle scene images via Gemini 3 Pro Image."
    )
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to a project config JSON (see config.example.json).",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="SCENE_ID",
        help="Only (re)generate these scene ids, e.g. --only living_room_a study_b",
    )
    parser.add_argument(
        "--env",
        type=Path,
        default=None,
        help="Explicit path to the .env file holding GEMINI_API_KEY.",
    )
    args = parser.parse_args()

    config = ProjectConfig(args.config.resolve())
    env_path = find_env_file(args.env, config)
    api_key = load_api_key(env_path)

    prompts_data = json.loads(config.prompts_file.read_text(encoding="utf-8"))
    all_scenes = prompts_data["scenes"]

    scenes = all_scenes
    if args.only:
        wanted = set(args.only)
        scenes = [s for s in all_scenes if s["id"] in wanted]
        missing = wanted - {s["id"] for s in scenes}
        if missing:
            raise SystemExit(f"Unknown scene id(s): {', '.join(sorted(missing))}")

    if not scenes:
        raise SystemExit("No scenes to generate.")

    config.scenes_dir.mkdir(parents=True, exist_ok=True)
    resized_ref2_path = get_or_create_resized_reference(config)

    ref1_b64 = encode_image_b64(config.ref_image_1)
    ref2_b64 = encode_image_b64(resized_ref2_path)
    ref1_mime = mime_for(config.ref_image_1)
    ref2_mime = mime_for(resized_ref2_path)
    template_blocks = build_input_blocks("", ref1_b64, ref1_mime, ref2_b64, ref2_mime)

    client = genai.Client(api_key=api_key)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as pool:
        futures = {
            pool.submit(
                generate_one,
                client,
                scene,
                template_blocks,
                config.model,
                config.scenes_dir,
                config.base_dir,
            ): scene["id"]
            for scene in scenes
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            label = "OK" if result["status"] == "success" else "FAIL"
            print(f"[{label}] {result['id']}")

    # Merge into existing metadata.json so a --only rerun doesn't wipe out
    # the metadata for scenes that weren't regenerated this run.
    metadata_path = config.scenes_dir / "metadata.json"
    existing_by_id = {}
    if metadata_path.exists():
        try:
            existing_data = json.loads(metadata_path.read_text(encoding="utf-8"))
            existing_by_id = {e["id"]: e for e in existing_data.get("scenes", [])}
        except (json.JSONDecodeError, KeyError):
            existing_by_id = {}

    for result in results:
        existing_by_id[result["id"]] = result

    ordered_ids = [s["id"] for s in all_scenes]
    merged_scenes = [existing_by_id[i] for i in ordered_ids if i in existing_by_id]

    metadata_path.write_text(
        json.dumps(
            {
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "model": config.model,
                "scenes": merged_scenes,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    failures = [r for r in results if r["status"] != "success"]
    if failures:
        print(
            f"\n{len(failures)} scene(s) failed. See {metadata_path} for details.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
