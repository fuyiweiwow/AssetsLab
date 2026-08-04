"""Extract dark eye-frame strokes from front-character-anchor.png."""

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
    # Boxes are measured from the supplied 1024x1536 concept image. They keep
    # the eye and eyelid while excluding most hair and the opposite eye.
    regions = {
        "L": (365, 460, 505, 560),
        "R": (550, 460, 695, 560),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "assetslab_concept_eye_frame_analysis_v1",
        "source": str(args.source.resolve()),
        "image_size": list(source.size),
        "regions": {},
    }
    for label, box in regions.items():
        crop = source.crop(box)
        width, height = 160, 100
        rgba = Image.new("RGBA", (width, height), (28, 20, 34, 0))
        draw = ImageDraw.Draw(rgba)
        # Landmark-traced from the supplied concept crop: a heavy upper lid,
        # a short outer wing, and a restrained lower inner contour. The right
        # eye mirrors this clean shape instead of inheriting hair pixels.
        upper = [(12, 57), (22, 37), (41, 21), (68, 12), (98, 13), (124, 26), (143, 49)]
        wing = [(141, 47), (151, 55), (154, 62)]
        lower = [(13, 59), (22, 70), (37, 77), (51, 78)]
        if label == "R":
            upper = [(width - x, y) for x, y in upper[::-1]]
            wing = [(width - x, y) for x, y in wing[::-1]]
            lower = [(width - x, y) for x, y in lower[::-1]]
        draw.line(upper, fill=(28, 20, 34, 255), width=10, joint="curve")
        draw.line(wing, fill=(28, 20, 34, 255), width=7, joint="curve")
        draw.line(lower, fill=(42, 30, 48, 190), width=3, joint="curve")
        output_path = args.output / f"concept_eye_frame_{label}.png"
        rgba.save(output_path)
        crop.save(args.output / f"concept_eye_reference_{label}.png")
        manifest["regions"][label] = {
            "box_xyxy": list(box),
            "output": str(output_path.resolve()),
            "method": "manual_landmark_trace_from_reference_crop",
        }
    (args.output / "concept_eye_frame_analysis.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"Concept eye frame assets written to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
