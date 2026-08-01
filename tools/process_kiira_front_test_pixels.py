"""Convert the featureless KIIRA front test strip to 64x64 review frames."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for index in range(8):
        source = args.render_dir / f"frame_{index:02d}" / "beauty.png"
        image = Image.open(source).convert("RGBA")
        if image.size != (256, 256):
            raise RuntimeError(f"unexpected render size: {image.size}")
        pixel = image.resize((64, 64), Image.Resampling.NEAREST)
        target = args.output_dir / f"frame_{index:02d}.png"
        pixel.save(target)
        frames.append({"frame": index, "source": str(source), "path": target.name})
    sheet = Image.new("RGBA", (512, 64), (0, 0, 0, 0))
    for item in frames:
        sheet.alpha_composite(Image.open(args.output_dir / item["path"]).convert("RGBA"), (item["frame"] * 64, 0))
    sheet.save(args.output_dir / "front_sheet.png")
    manifest = {
        "schema": "assetslab_kiira_front_pixel_test_v1",
        "purpose": "Featureless KIIRA walk actor review before four-direction capture.",
        "canvas_px": [64, 64],
        "render_canvas_px": [256, 256],
        "downscale": 4,
        "face_hidden": True,
        "runtime_ready": False,
        "frames": frames,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"KIIRA_FRONT_PIXEL_TEST_PASS frames={len(frames)} output={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
