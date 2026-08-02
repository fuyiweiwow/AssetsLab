"""Make nearest-neighbor pixel previews for an EyePackage render folder."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, default=64)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for source in sorted(args.input.glob("*.png")):
        image = Image.open(source).convert("RGBA")
        small = image.resize((args.size, args.size), Image.Resampling.NEAREST)
        small.save(args.output / source.name)
        enlarged = small.resize(image.size, Image.Resampling.NEAREST)
        enlarged.save(args.output / f"{source.stem}_nearest_view.png")
    print(f"Pixel previews written to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
