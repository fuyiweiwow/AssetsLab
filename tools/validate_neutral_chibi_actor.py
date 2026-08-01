"""Validate the neutral chibi actor's 3D renders and 64x64 pixel handoff."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

DIRECTIONS = ("front", "right", "back", "left")
FRAME_COUNT = 8


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-dir", required=True, type=Path)
    parser.add_argument("--pixel-dir", required=True, type=Path)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--pose-3d", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--strict", action="store_true", help="fail on any one-pixel baseline tolerance")
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    stats = {"renders": [], "pixels": []}
    if not args.blend.is_file() or args.blend.stat().st_size == 0:
        errors.append("missing or empty actor blend")

    if not args.pose_3d.is_file():
        errors.append("missing pose-3d manifest")
        pose = {}
    else:
        pose = json.loads(args.pose_3d.read_text(encoding="utf-8"))
        if pose.get("stage") != "Q1_q_style_base_render":
            errors.append("pose-3d manifest is not Q1_q_style_base_render")
        if len(pose.get("frames", [])) != 32:
            errors.append("pose-3d manifest must contain 32 frames")

    for direction in DIRECTIONS:
        for frame in range(FRAME_COUNT):
            label = f"{direction}/frame_{frame:02d}"
            render = args.render_dir / direction / f"frame_{frame:02d}" / "beauty.png"
            pixel = args.pixel_dir / direction / f"frame_{frame:02d}" / "pixel.png"
            if not render.is_file():
                errors.append(f"{label}: missing 256px beauty render")
            else:
                image = Image.open(render).convert("RGBA")
                bbox = image.getchannel("A").getbbox()
                if image.size != (256, 256):
                    errors.append(f"{label}: render size is {image.size}, expected (256, 256)")
                if bbox is None:
                    errors.append(f"{label}: render has no visible actor")
                else:
                    stats["renders"].append({"direction": direction, "frame": frame, "alpha_bbox": list(bbox)})
                image.close()
            if not pixel.is_file():
                errors.append(f"{label}: missing 64px pixel output")
            else:
                image = Image.open(pixel).convert("RGBA")
                bbox = image.getchannel("A").getbbox()
                if image.size != (64, 64):
                    errors.append(f"{label}: pixel size is {image.size}, expected (64, 64)")
                if bbox is None:
                    errors.append(f"{label}: pixel has no visible actor")
                elif bbox[3] not in (59, 60):
                    errors.append(f"{label}: foot baseline is {bbox[3]}, expected 60 (+/-1)")
                elif bbox[3] != 60:
                    message = f"{label}: foot baseline is {bbox[3]}, target bbox end is 60"
                    if args.strict:
                        errors.append(message)
                    else:
                        warnings.append(message)
                if bbox is not None and bbox[3] in (59, 60):
                    stats["pixels"].append({"direction": direction, "frame": frame, "alpha_bbox": list(bbox)})
                image.close()

    if len(stats["renders"]) != 32:
        errors.append("not all 32 render cells passed")
    if len(stats["pixels"]) != 32:
        errors.append("not all 32 pixel cells passed")

    report = {
        "schema": "assetslab_neutral_chibi_actor_validation_v1",
        "status": "pass" if not errors else "fail",
        "directions": list(DIRECTIONS),
        "frame_count": FRAME_COUNT,
        "blend": str(args.blend),
        "pose_3d": str(args.pose_3d),
        "render_dir": str(args.render_dir),
        "pixel_dir": str(args.pixel_dir),
        "errors": errors,
        "warnings": warnings,
        "stats": stats,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if errors:
        raise SystemExit("NEUTRAL_CHIBI_ACTOR_FAIL: " + "; ".join(errors))
    print("NEUTRAL_CHIBI_ACTOR_PASS directions=4 frames=8 renders=32 pixels=32 warnings=%d report=%s" % (len(warnings), args.report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
