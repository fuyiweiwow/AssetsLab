"""Convert the chibi-base Blender walk renders into a review-only pixel sheet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

DIRECTIONS = ("front", "right", "back", "left")
FRAME_COUNT = 8
CELL = 64


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--source-archive", required=True)
    parser.add_argument("--source-blend", required=True)
    args = parser.parse_args()
    sheet = Image.new("RGBA", (CELL * FRAME_COUNT, CELL * len(DIRECTIONS)), (0, 0, 0, 0))
    frames = []
    for row, direction in enumerate(DIRECTIONS):
        for frame in range(FRAME_COUNT):
            source = args.render_dir / direction / f"frame_{frame:02d}" / "beauty.png"
            if not source.is_file():
                raise RuntimeError(f"missing render: {source}")
            image = Image.open(source).convert("RGBA")
            if image.size != (256, 256):
                raise RuntimeError(f"unexpected render size: {image.size}")
            pixel = image.resize((CELL, CELL), Image.Resampling.NEAREST)
            target_dir = args.output_dir / direction / f"frame_{frame:02d}"
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / "pixel.png"
            pixel.save(target)
            sheet.alpha_composite(pixel, (frame * CELL, row * CELL))
            frames.append({"direction": direction, "frame": frame, "path": str(target.relative_to(args.output_dir))})
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sheet_path = args.output_dir / "chibi_base_walk_sheet.png"
    sheet.save(sheet_path)
    manifest = {
        "schema": "assetslab_2d_pixel_experiment_v1",
        "stage": "chibi_base_mesh_four_direction_eight_frame_review",
        "purpose": "Review-only pixels generated from the external unrigged chibi base mesh.",
        "canvas_px": [CELL, CELL],
        "render_canvas_px": [256, 256],
        "downscale": 4,
        "directions": list(DIRECTIONS),
        "frame_count": FRAME_COUNT,
        "anchors": {"head_center": [32, 16], "neck": [32, 25], "foot_baseline_y": 60},
        "source_archive": args.source_archive,
        "source_blend": args.source_blend,
        "source_render_dir": str(args.render_dir),
        "sheet": sheet_path.name,
        "frames": frames,
        "runtime_ready": False,
        "manual_pixel_cleanup_required": True,
    }
    (args.output_dir / "chibi_base_walk_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"CHIBI_BASE_PIXEL_PASS cells={len(frames)} sheet={sheet_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
