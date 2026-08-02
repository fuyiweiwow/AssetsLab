"""Split a two-eye RGBA sheet into left/right transparent eye assets."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def crop_half(image: Image.Image, x0: int, x1: int, padding: int) -> Image.Image:
    alpha = image.getchannel("A")
    bbox = alpha.crop((x0, 0, x1, image.height)).getbbox()
    if bbox is None:
        raise RuntimeError(f"no visible eye in half {x0}:{x1}")
    left, top, right, bottom = bbox
    box = (
        max(x0, x0 + left - padding),
        max(0, top - padding),
        min(x1, x0 + right + padding),
        min(image.height, bottom + padding),
    )
    result = image.crop(box)
    rgba = np.array(result)
    mask = (rgba[:, :, 3] > 20).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if count > 1:
        largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        main_area = stats[largest, cv2.CC_STAT_AREA]
        keep = np.zeros_like(mask, dtype=bool)
        for label in range(1, count):
            area = stats[label, cv2.CC_STAT_AREA]
            # Keep the main eye and intentional secondary features such as a
            # detached eyebrow; discard tiny generation artifacts.
            if label == largest or area >= max(64, int(main_area * 0.02)):
                keep |= labels == label
        rgba[~keep, 3] = 0
        result = Image.fromarray(rgba, mode="RGBA")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--padding", type=int, default=12)
    args = parser.parse_args()
    image = Image.open(args.input).convert("RGBA")
    midpoint = image.width // 2
    args.output.mkdir(parents=True, exist_ok=True)
    left = crop_half(image, 0, midpoint, args.padding)
    right = crop_half(image, midpoint, image.width, args.padding)
    left.save(args.output / "imagegen_eye_L.png")
    right.save(args.output / "imagegen_eye_R.png")
    print(f"ImageGen eye crops written to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
