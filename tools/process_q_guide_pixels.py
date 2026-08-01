"""Post-process Q1 256px renders into the 64x64 pixel base.

Reads the Q1 render tree (render_dir/<direction>/frame_XX/beauty.png),
downsamples each frame 4x with nearest-neighbor, writes 64x64 transparent
PNGs, assembles the four-direction x eight-frame sheet, and writes a
manifest. The 256->64 mapping keeps the G1 registration: foot baseline at
y=60, head center around y=18 in the runtime canvas.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image

CELL = 64
DOWNSCALE = 4
DIRECTIONS = ("front", "right", "back", "left")
FRAME_COUNT = 8


def cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--pose-3d", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = cli_args()
    out_root = args.output_dir
    source_parent = args.blend.resolve().parent
    if out_root.resolve() == source_parent:
        raise SystemExit(
            "Q1_PIXEL_BASE_FAIL: output-dir must not be the parent directory "
            "of the source blend/pose files; use a separate pixel output directory"
        )
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    sheet = Image.new("RGBA", (CELL * FRAME_COUNT, CELL * len(DIRECTIONS)), (0, 0, 0, 0))
    frames = []
    for row, direction in enumerate(DIRECTIONS):
        for frame_index in range(FRAME_COUNT):
            source = args.render_dir / direction / ("frame_%02d" % frame_index) / "beauty.png"
            if not source.is_file():
                raise RuntimeError("missing render %s" % source)
            full = Image.open(source).convert("RGBA")
            if full.size != (256, 256):
                raise RuntimeError("unexpected render size %s" % (full.size,))
            cell = full.resize((CELL, CELL), Image.NEAREST)
            cell_dir = out_root / direction / ("frame_%02d" % frame_index)
            cell_dir.mkdir(parents=True, exist_ok=True)
            target = cell_dir / "pixel.png"
            cell.save(target)
            sheet.paste(cell, (frame_index * CELL, row * CELL))
            frames.append({"direction": direction, "frame": frame_index, "path": str(target.relative_to(out_root))})

    sheet_path = out_root / "q_base_sheet.png"
    sheet.save(sheet_path)

    pose3d = json.loads(args.pose_3d.read_text(encoding="utf-8"))
    manifest = {
        "schema": "assetslab_2d_pixel_base_v1",
        "stage": "Q1_four_direction_eight_frame_pixel_base",
        "canvas_px": [CELL, CELL],
        "downscale": DOWNSCALE,
        "render_canvas_px": [256, 256],
        "anchors": {"head_center": [32, 18], "neck": [32, 31], "foot_baseline_y": 60},
        "directions": list(DIRECTIONS),
        "frame_count": FRAME_COUNT,
        "sheet": str(sheet_path.relative_to(out_root)),
        "source_pose_3d": str(args.pose_3d),
        "source_blend": str(args.blend),
        "frames": frames,
    }
    manifest_path = out_root / "q_base_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Q1_PIXEL_BASE_PASS cells=%d sheet=%s manifest=%s" % (len(frames), sheet_path, manifest_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
