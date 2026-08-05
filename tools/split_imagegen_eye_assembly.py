"""Split an imagegen front eye assembly into left/right RGBA reference crops.

This performs only chroma/alpha-aware cropping and resizing. It does not draw,
trace, or synthesize any eye pixels locally.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def crop_side(image: Image.Image, side: str, padding: int) -> tuple[Image.Image, tuple[int, int, int, int]]:
    half = image.width // 2
    if side == "L":
        region = image.crop((0, 0, half, image.height))
        offset_x = 0
    else:
        region = image.crop((half, 0, image.width, image.height))
        offset_x = half
    bbox = region.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError(f"{side} side has no alpha content")
    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - padding)
    y0 = max(0, y0 - padding)
    x1 = min(region.width, x1 + padding)
    y1 = min(region.height, y1 + padding)
    return region.crop((x0, y0, x1, y1)), (offset_x + x0, y0, offset_x + x1, y1)


def fit_canvas(source: Image.Image, size: tuple[int, int]) -> Image.Image:
    scale = min((size[0] * 0.92) / source.width, (size[1] * 0.92) / source.height)
    resized = source.resize(
        (max(1, round(source.width * scale)), max(1, round(source.height * scale))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(resized, ((size[0] - resized.width) // 2, (size[1] - resized.height) // 2))
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--width", type=int, default=496)
    parser.add_argument("--height", type=int, default=609)
    parser.add_argument("--padding", type=int, default=18)
    options = parser.parse_args()

    output_dir = options.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    image = Image.open(options.source.resolve()).convert("RGBA")
    metadata: dict[str, object] = {
        "schema": "assetslab_imagegen_eye_assembly_crops_v1",
        "source": str(options.source.resolve()),
        "canvas": [options.width, options.height],
        "sides": {},
    }
    for side in ("L", "R"):
        crop, bbox = crop_side(image, side, options.padding)
        output = output_dir / f"imagegen_eye_assembly_{side}.png"
        fit_canvas(crop, (options.width, options.height)).save(output)
        metadata["sides"][side] = {"source_alpha_bbox": list(bbox), "output": str(output)}
    (output_dir / "manifest.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"IMAGEGEN_EYE_ASSEMBLY_SPLIT_PASS output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
