"""Validate the reproducible A/B pixelization package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


DIRECTIONS = ("front", "right", "back", "left")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def check_frame(path: Path, size: int, allowed_colors: set[tuple[int, int, int]] | None) -> dict[str, object]:
    with Image.open(path).convert("RGBA") as image:
        if image.size != (size, size):
            raise RuntimeError(f"unexpected size {image.size}: {path}")
        colors = image.getcolors(maxcolors=1_000_000) or []
        rgb_colors = {color[:3] for _, color in colors}
        alpha_values = {color[3] for _, color in colors}
        if alpha_values - {0, 255}:
            raise RuntimeError(f"semi-transparent edge pixels found: {path}")
        if allowed_colors is not None and not rgb_colors.issubset(allowed_colors):
            raise RuntimeError(f"palette fidelity failed: {path}")
        return {"color_count": len(rgb_colors), "alpha_values": sorted(alpha_values)}


def main() -> int:
    options = parse_args()
    output_dir = options.output_dir.resolve()
    root = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    if root.get("schema") != "assetslab_pixelization_ab_v1":
        raise RuntimeError("unexpected pixelization manifest schema")
    if root.get("canvas_px") != [64, 64] or root.get("frame_count") != 8:
        raise RuntimeError("pixelization output contract changed")
    if root.get("shared_body_and_eye_sampling") is not True:
        raise RuntimeError("A/B candidates do not share the source sampling")

    reports = {}
    for candidate_name in ("nearest", "palette32"):
        candidate = root["candidates"][candidate_name]
        candidate_dir = output_dir / candidate_name
        palette = candidate.get("palette")
        allowed = None
        if palette:
            allowed = {tuple(int(value[index : index + 2], 16) for index in (1, 3, 5)) for value in palette}
        checked = 0
        for direction in DIRECTIONS:
            sheet = candidate_dir / candidate["sheets"][direction]
            with Image.open(sheet) as image:
                if image.size != (512, 64):
                    raise RuntimeError(f"unexpected sheet size {image.size}: {sheet}")
            for frame in range(8):
                path = candidate_dir / direction / f"frame_{frame:02d}" / "pixel.png"
                check_frame(path, 64, allowed)
                checked += 1
        reports[candidate_name] = {"frames": checked, "palette_fidelity": allowed is not None}
    print("PIXELIZATION_AB_VALIDATION_PASS candidates=2 directions=4 frames=8 alpha=crisp palette=global")
    print(json.dumps(reports, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
