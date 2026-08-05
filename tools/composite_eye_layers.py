"""Composite independently rendered eye RGBA layers over body frames."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


DIRECTIONS = ("front", "right", "back", "left")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--body-dir", type=Path, required=True)
    parser.add_argument("--eyes-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frame-count", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    options = parse_args()
    options.output_dir.mkdir(parents=True, exist_ok=True)
    for direction in DIRECTIONS:
        for index in range(options.frame_count):
            body_path = options.body_dir / f"{direction}_{index:02d}.png"
            eyes_path = options.eyes_dir / f"{direction}_{index:02d}.png"
            output_path = options.output_dir / f"{direction}_{index:02d}.png"
            if not body_path.is_file() or not eyes_path.is_file():
                raise FileNotFoundError(f"missing independent layer: {body_path} / {eyes_path}")
            body = Image.open(body_path).convert("RGBA")
            eyes = Image.open(eyes_path).convert("RGBA")
            if body.size != eyes.size:
                raise ValueError(f"layer size mismatch: {body_path} / {eyes_path}")
            body.alpha_composite(eyes)
            body.save(output_path)
    print(f"EYE_LAYER_COMPOSITE_PASS output={options.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
