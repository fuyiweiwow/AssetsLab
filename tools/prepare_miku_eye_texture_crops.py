"""Create reusable left/right eye texture crops from the Miku chibi atlas."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source = Image.open(args.source).convert("RGBA")
    if source.size != (256, 128):
        raise RuntimeError(f"expected the known Miku atlas size 256x128, got {source.size}")

    args.output.mkdir(parents=True, exist_ok=True)
    # The atlas contains two complete eye islands. The ellipse trims the atlas
    # background while retaining the white lower eye area and the colored iris.
    crops = {
        "miku_eye_left.png": (18, 18, 114, 114, (48, 22, 88, 92)),
        "miku_eye_right.png": (142, 18, 238, 114, (48, 22, 88, 92)),
    }
    for filename, (x0, y0, x1, y1, ellipse) in crops.items():
        crop = source.crop((x0, y0, x1, y1))
        alpha = Image.new("L", crop.size, 0)
        draw = ImageDraw.Draw(alpha)
        draw.ellipse(ellipse, fill=255)
        crop.putalpha(alpha)
        crop.save(args.output / filename)

    # Separate iris/highlight decals. Keeping the white eye area as geometry
    # avoids blending into a light-colored actor face.
    iris_regions = {
        "miku_iris_left.png": (32, 32, 96, 96),
        "miku_iris_right.png": (160, 32, 224, 96),
    }
    for filename, box in iris_regions.items():
        crop = source.crop(box)
        mask = Image.new("L", crop.size, 0)
        pixels = crop.load()
        mask_pixels = mask.load()
        for y in range(crop.height):
            for x in range(crop.width):
                r, g, b, _ = pixels[x, y]
                teal = r < 175 and g > r + 5 and b > r + 8
                dark = max(r, g, b) < 110
                mask_pixels[x, y] = 255 if teal or dark else 0
        mask = mask.filter(ImageFilter.MaxFilter(9))
        crop.putalpha(mask)
        crop.save(args.output / filename)

    print(f"Miku eye texture crops written to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
