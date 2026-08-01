"""Downsample the front actor test to review-only 64x64 pixel references."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

FRAME_COUNT = 8
CELL = 64


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--source-archive", required=True)
    parser.add_argument("--source-blend", required=True)
    parser.add_argument("--actor-blend", required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGBA", (CELL * FRAME_COUNT, CELL), (0, 0, 0, 0))
    frames = []
    for frame in range(FRAME_COUNT):
        source = args.render_dir / f"frame_{frame:02d}" / "beauty.png"
        if not source.is_file():
            raise RuntimeError(f"missing render: {source}")
        image = Image.open(source).convert("RGBA")
        if image.size != (256, 256):
            raise RuntimeError(f"unexpected render size: {image.size}")
        pixel = image.resize((CELL, CELL), Image.Resampling.NEAREST)
        target_dir = args.output_dir / f"frame_{frame:02d}"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / "pixel.png"
        pixel.save(target)
        sheet.alpha_composite(pixel, (frame * CELL, 0))
        alpha = pixel.getchannel("A")
        frames.append({
            "frame": frame,
            "path": str(target.relative_to(args.output_dir)),
            "alpha_bbox": list(alpha.getbbox()) if alpha.getbbox() else None,
        })

    sheet_path = args.output_dir / "front_pixel_sheet.png"
    sheet.save(sheet_path)
    manifest = {
        "schema": "assetslab_original_chibi_actor_pixel_review_v1",
        "stage": "actor_v1_front_walk_8_frame_pixel_review",
        "purpose": "Review-only nearest-neighbor pixels from the bound 3D actor.",
        "canvas_px": [CELL, CELL],
        "render_canvas_px": [256, 256],
        "downscale": 4,
        "direction": "front",
        "frame_count": FRAME_COUNT,
        "anchors": {
            "target_head_center": [32, 16],
            "target_neck": [32, 25],
            "target_foot_baseline_y": 60,
            "camera_registration": "review_only_union_bounds_not_G0_locked",
        },
        "source_archive": args.source_archive,
        "source_blend": args.source_blend,
        "actor_blend": args.actor_blend,
        "source_render_dir": str(args.render_dir),
        "sheet": sheet_path.name,
        "frames": frames,
        "runtime_ready": False,
        "manual_pixel_cleanup_required": True,
        "reason_not_runtime_ready": "Actor camera and pixel silhouette still require G0 registration and manual cleanup.",
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"ORIGINAL_CHIBI_PIXEL_REVIEW_PASS frames={len(frames)} sheet={sheet_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
