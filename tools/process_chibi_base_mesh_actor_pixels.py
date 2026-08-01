"""Convert the downloaded chibi actor review renders to a 4x8 pixel sheet."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image

DIRECTIONS = ("front", "right", "back", "left")
FRAME_COUNT = 8
CELL = 64


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--actor-blend", required=True, type=Path)
    parser.add_argument("--source-archive", required=True)
    args = parser.parse_args()
    if args.output_dir.resolve() == args.actor_blend.resolve().parent:
        raise SystemExit("CHIBI_BASE_MESH_PIXEL_FAIL: output-dir must be separate from actor blend directory")
    if args.output_dir.exists():
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGBA", (CELL * FRAME_COUNT, CELL * len(DIRECTIONS)), (0, 0, 0, 0))
    frames = []
    for row, direction in enumerate(DIRECTIONS):
        for frame in range(FRAME_COUNT):
            source = args.render_dir / direction / f"frame_{frame:02d}" / "beauty.png"
            if not source.is_file():
                raise RuntimeError(f"missing render: {source}")
            full = Image.open(source).convert("RGBA")
            if full.size != (256, 256):
                raise RuntimeError(f"unexpected render size: {full.size}")
            cell = full.resize((CELL, CELL), Image.Resampling.NEAREST)
            target_dir = args.output_dir / direction / f"frame_{frame:02d}"
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / "pixel.png"
            cell.save(target)
            sheet.paste(cell, (frame * CELL, row * CELL))
            bbox = cell.getchannel("A").getbbox()
            frames.append({"direction": direction, "frame": frame, "path": str(target.relative_to(args.output_dir)), "alpha_bbox": list(bbox) if bbox else None})
    sheet_path = args.output_dir / "chibi_base_mesh_pixel_sheet.png"
    sheet.save(sheet_path)
    manifest = {
        "schema": "assetslab_chibi_base_mesh_pixel_review_v1",
        "stage": "downloaded_chibi_base_mesh_four_direction_pixel_review",
        "source_archive": args.source_archive,
        "actor_blend": str(args.actor_blend),
        "render_dir": str(args.render_dir),
        "canvas_px": [CELL, CELL],
        "render_canvas_px": [256, 256],
        "downscale": 4,
        "directions": list(DIRECTIONS),
        "frame_count": FRAME_COUNT,
        "sheet": sheet_path.name,
        "frames": frames,
        "runtime_ready": False,
        "manual_pixel_cleanup_required": True,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("CHIBI_BASE_MESH_PIXEL_PASS cells=32 sheet=%s" % sheet_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
