"""Create a flatter rounded-rectangle upper eyelid from the concept style."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = Image.open(args.source).convert("RGB")
    args.output.mkdir(parents=True, exist_ok=True)
    regions = {"L": (365, 460, 505, 560), "R": (550, 460, 695, 560)}
    manifest = {
        "schema": "assetslab_concept_eye_frame_v2",
        "source": str(args.source.resolve()),
        "method": "rounded_rectangle_landmark_trace",
        "regions": {},
    }
    for label, box in regions.items():
        width, height = 160, 100
        image = Image.new("RGBA", (width, height), (28, 20, 34, 0))
        draw = ImageDraw.Draw(image)
        # Short rounded corners + long flatter top/side segments.  The prior
        # trace used a large continuous arc at both the inner and outer upper
        # corners, which made the eye read as a half-circle instead of a
        # rounded rectangle.
        upper = [
            # L is written from the outer corner to the inner corner.  The
            # inner end stops after the small corner radius instead of
            # dropping down as a second vertical eyelid.
            (10, 58), (10, 34), (12, 26), (16, 19), (22, 14), (30, 11),
            (42, 9), (115, 9), (127, 11), (135, 14), (142, 19),
            (148, 26), (150, 34), (150, 44),
        ]
        lower = [(12, 60), (22, 70), (37, 77), (52, 78)]
        # The outer wing and lash cluster are on the left for L, then mirrored
        # for R.  Keep the inner corner clean and readable at pixel scale.
        wing = [(11, 48), (4, 55)]
        lash_polygons = [
            # Longest at the outer/lower corner, then shorter toward the top.
            [(14, 50), (10, 45), (1, 41)],
            [(14, 43), (10, 39), (3, 31)],
            [(14, 36), (10, 33), (7, 24)],
        ]
        if label == "R":
            upper = [(width - x, y) for x, y in upper[::-1]]
            lower = [(width - x, y) for x, y in lower[::-1]]
            wing = [(width - x, y) for x, y in wing[::-1]]
            lash_polygons = [[(width - x, y) for x, y in polygon] for polygon in lash_polygons]
        draw.line(upper, fill=(28, 20, 34, 255), width=9, joint="curve")
        draw.line(wing, fill=(28, 20, 34, 255), width=6, joint="curve")
        for polygon in lash_polygons:
            draw.polygon(polygon, fill=(28, 20, 34, 245))
        draw.line(lower, fill=(42, 30, 48, 185), width=3, joint="curve")
        output_path = args.output / f"concept_eye_frame_v2_{label}.png"
        image.save(output_path)
        source.crop(box).save(args.output / f"concept_eye_reference_v2_{label}.png")
        manifest["regions"][label] = {"box_xyxy": list(box), "output": str(output_path.resolve())}
    (args.output / "concept_eye_frame_v2_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Rounded-rectangle concept eye frames written to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
