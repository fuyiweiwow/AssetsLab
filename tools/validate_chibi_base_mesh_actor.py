"""Validate the actual downloaded chibi-base-mesh actor review output."""

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
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--strict-registration", action="store_true")
    args = parser.parse_args()
    errors = []
    warnings = []
    renders = []
    pixels = []
    if not args.blend.is_file() or args.blend.stat().st_size == 0:
        errors.append("missing or empty actor blend")
    if not args.manifest.is_file():
        errors.append("missing render manifest")
        manifest = {}
    else:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        if manifest.get("model_is_downloaded_chibi_base_mesh") is not True:
            errors.append("manifest does not identify the downloaded chibi base mesh")
        if len(manifest.get("frames", [])) != 32:
            errors.append("render manifest must contain 32 frames")
    for direction in DIRECTIONS:
        for frame in range(FRAME_COUNT):
            label = f"{direction}/frame_{frame:02d}"
            render = args.render_dir / direction / f"frame_{frame:02d}" / "beauty.png"
            pixel = args.pixel_dir / direction / f"frame_{frame:02d}" / "pixel.png"
            if not render.is_file():
                errors.append(f"{label}: missing 256px render")
            else:
                image = Image.open(render).convert("RGBA")
                bbox = image.getchannel("A").getbbox()
                if image.size != (256, 256) or bbox is None:
                    errors.append(f"{label}: invalid render size or alpha")
                else:
                    renders.append({"direction": direction, "frame": frame, "alpha_bbox": list(bbox)})
                image.close()
            if not pixel.is_file():
                errors.append(f"{label}: missing 64px pixel")
            else:
                image = Image.open(pixel).convert("RGBA")
                bbox = image.getchannel("A").getbbox()
                if image.size != (64, 64) or bbox is None:
                    errors.append(f"{label}: invalid pixel size or alpha")
                else:
                    pixels.append({"direction": direction, "frame": frame, "alpha_bbox": list(bbox)})
                    if bbox[3] != 60:
                        message = f"{label}: bbox end y={bbox[3]}, project target is 60"
                        (errors if args.strict_registration else warnings).append(message)
                image.close()
    if len(renders) != 32 or len(pixels) != 32:
        errors.append(f"expected 32 renders and pixels, got {len(renders)} and {len(pixels)}")
    report = {
        "schema": "assetslab_chibi_base_mesh_actor_validation_v1",
        "status": "pass" if not errors else "fail",
        "model": "third_party/chibi-base-meshblender.zip",
        "blend": str(args.blend),
        "render_dir": str(args.render_dir),
        "pixel_dir": str(args.pixel_dir),
        "errors": errors,
        "warnings": warnings,
        "renders": renders,
        "pixels": pixels,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if errors:
        raise SystemExit("CHIBI_BASE_MESH_ACTOR_FAIL: " + "; ".join(errors))
    print("CHIBI_BASE_MESH_ACTOR_PASS directions=4 frames=8 renders=32 pixels=32 warnings=%d report=%s" % (len(warnings), args.report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
