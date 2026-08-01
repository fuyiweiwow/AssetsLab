"""Package a validated pixel test into a runtime-oriented asset directory."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--character-id", required=True)
    parser.add_argument("--motion", default="walk")
    parser.add_argument("--amplitude", type=float, default=1.3)
    return parser.parse_args()


def main() -> int:
    options = parse_args()
    source = options.source_dir.resolve()
    output = options.output_dir.resolve()
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    copied_frames: list[dict[str, object]] = []
    for frame in manifest["frames"]:
        relative = Path(frame["path"])
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)
        copied_frames.append({**frame, "path": relative.as_posix()})

    sheets: dict[str, str] = {}
    previews: dict[str, str] = {}
    for direction in manifest["directions"]:
        sheet_name = manifest["sheets"][direction]
        gif_name = f"{direction}.gif"
        shutil.copy2(source / sheet_name, output / sheet_name)
        shutil.copy2(source / gif_name, output / gif_name)
        sheets[direction] = sheet_name
        previews[direction] = gif_name

    runtime_manifest = {
        "schema": "assetslab_pixel_runtime_asset_v1",
        "character_id": options.character_id,
        "motion": options.motion,
        "motion_amplitude": options.amplitude,
        "canvas_px": manifest["canvas_px"],
        "directions": manifest["directions"],
        "frame_count": manifest["frame_count"],
        "filter": "nearest",
        "transparent": True,
        "sprite_sheets": sheets,
        "preview_gifs": previews,
        "frames": copied_frames,
        "runtime_ready": True,
        "godot_import_verified": False,
        "godot_runtime_file_load_verified": False,
        "godot_animatedsprite_verified": False,
        "source_package": str(source),
    }
    (output / "runtime_manifest.json").write_text(
        json.dumps(runtime_manifest, indent=2), encoding="utf-8"
    )
    print(f"PIXEL_RUNTIME_PACKAGE_PASS frames={len(copied_frames)} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
