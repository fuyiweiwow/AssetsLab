"""Create a zoomed face crop from a 256px front render for review."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--box", nargs=4, type=int, default=[45, 20, 210, 155])
    parser.add_argument("--size", type=int, default=660)
    options = parser.parse_args()
    image = Image.open(options.input).convert("RGBA")
    crop = image.crop(tuple(options.box))
    crop.resize((options.size, options.size), Image.Resampling.NEAREST).save(options.output)
    print(f"FACE_CROP_PASS output={options.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
