"""Validate a pixel asset test package produced by the local pixel processor."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pixel-dir", required=True, type=Path)
    parser.add_argument("--expected-size", type=int, default=128)
    parser.add_argument("--expected-frames", type=int, default=8)
    return parser.parse_args()


def fail(message: str) -> int:
    print(f"PIXEL_ASSET_TEST_FAIL {message}")
    return 1


def main() -> int:
    options = parse_args()
    root = options.pixel_dir.resolve()
    manifest_path = root / "manifest.json"
    if not root.is_dir():
        return fail(f"missing_dir={root}")
    if not manifest_path.is_file():
        return fail(f"missing_manifest={manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    directions = ["front", "right", "back", "left"]
    if manifest.get("canvas_px") != [options.expected_size, options.expected_size]:
        return fail(f"canvas_px={manifest.get('canvas_px')}")
    if manifest.get("directions") != directions:
        return fail(f"directions={manifest.get('directions')}")
    if manifest.get("frame_count") != options.expected_frames:
        return fail(f"frame_count={manifest.get('frame_count')}")

    frames = manifest.get("frames", [])
    expected_count = len(directions) * options.expected_frames
    if len(frames) != expected_count:
        return fail(f"manifest_frames={len(frames)} expected={expected_count}")

    for frame in frames:
        relative = Path(frame["path"])
        image_path = root / relative
        if not image_path.is_file():
            return fail(f"missing_frame={image_path}")
        with Image.open(image_path) as image:
            if image.size != (options.expected_size, options.expected_size):
                return fail(f"size={image_path}:{image.size}")
            if image.mode != "RGBA":
                return fail(f"mode={image_path}:{image.mode}")
            actual_bbox = image.getchannel("A").getbbox()
            if actual_bbox is None:
                return fail(f"empty_alpha={image_path}")
            if list(actual_bbox) != frame.get("alpha_bbox"):
                return fail(
                    f"manifest_bbox={image_path}:{frame.get('alpha_bbox')}"
                    f" actual={actual_bbox}"
                )

    canvas_center = (options.expected_size - 1) / 2.0
    centers: dict[str, list[float]] = {direction: [] for direction in directions}
    bottoms: dict[str, list[int]] = {direction: [] for direction in directions}
    heights: dict[str, list[int]] = {direction: [] for direction in directions}
    for frame in frames:
        direction = frame["direction"]
        left, top, right, bottom = frame["alpha_bbox"]
        centers[direction].append((left + right - 1) / 2.0)
        bottoms[direction].append(bottom)
        heights[direction].append(bottom - top)

    for direction in directions:
        center_delta = max(abs(value - canvas_center) for value in centers[direction])
        bottom_delta = max(bottoms[direction]) - min(bottoms[direction])
        height_delta = max(heights[direction]) - min(heights[direction])
        if center_delta > 2.0:
            return fail(f"off_center={direction}:{center_delta:.2f}px")
        if bottom_delta > 2:
            return fail(f"foot_baseline_drift={direction}:{bottom_delta}px")
        if height_delta > 3:
            return fail(f"height_drift={direction}:{height_delta}px")

    for direction in directions:
        sheet = root / manifest["sheets"][direction]
        if not sheet.is_file():
            return fail(f"missing_sheet={sheet}")
        gif = root / f"{direction}.gif"
        if not gif.is_file():
            return fail(f"missing_gif={gif}")

    print(
        "PIXEL_ASSET_TEST_PASS "
        f"directions={len(directions)} frames={expected_count} "
        f"size={options.expected_size} root={root} "
        "framing=centered baseline=stable"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
