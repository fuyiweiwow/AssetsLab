"""Prepare Miku-inspired iris bases and elongated anime pupil decals."""

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
    args.output.mkdir(parents=True, exist_ok=True)

    iris_regions = {
        "L": (32, 32, 96, 96),
        "R": (160, 32, 224, 96),
    }
    for label, box in iris_regions.items():
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
        # Remove the source's round pupil so a separate elongated pupil can
        # be placed and randomized without inheriting a circular silhouette.
        draw = ImageDraw.Draw(mask)
        draw.ellipse((23, 13, 41, 53), fill=0)
        mask = mask.filter(ImageFilter.MaxFilter(5))
        crop.putalpha(mask)
        crop.save(args.output / f"miku_iris_base_{label}.png")

        pupil = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        pupil_draw = ImageDraw.Draw(pupil)
        pupil_draw.rounded_rectangle((24, 9, 40, 55), radius=7, fill=(5, 10, 35, 245))
        pupil.save(args.output / f"anime_pupil_vertical_{label}.png")

    print(f"Miku-inspired eye layers written to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
