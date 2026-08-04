"""Downsample a four-view render set to a nearest-neighbour pixel preview."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--size", type=int, default=64)
    parser.add_argument("--scale", type=int, default=4)
    options = parser.parse_args()

    options.output_dir.mkdir(parents=True, exist_ok=True)
    directions = ("front", "right", "back", "left")
    previews: list[Image.Image] = []
    for direction in directions:
        source = options.input_dir / f"{direction}.png"
        if not source.is_file():
            raise FileNotFoundError(source)
        image = Image.open(source).convert("RGBA")
        pixel = image.resize((options.size, options.size), Image.Resampling.NEAREST)
        pixel.save(options.output_dir / f"{direction}_pixel.png")
        previews.append(pixel.resize((options.size * options.scale, options.size * options.scale), Image.Resampling.NEAREST))

    sheet = Image.new("RGBA", (options.size * options.scale * len(directions), options.size * options.scale), (24, 24, 32, 255))
    for index, preview in enumerate(previews):
        sheet.alpha_composite(preview, (index * options.size * options.scale, 0))
    sheet.save(options.output_dir / "four_view_pixel_sheet.png")
    print(f"PIXEL_PREVIEW_PASS output={options.output_dir.resolve()} size={options.size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
