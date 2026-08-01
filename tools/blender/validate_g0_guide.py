from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


EXPECTED_DIRECTIONS = ("front", "right", "back", "left")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and compose G0 Blender guide renders.")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--render-dir", required=True, type=Path)
    parser.add_argument("--contact-sheet", required=True, type=Path)
    args = parser.parse_args()

    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    errors: list[str] = []
    if contract.get("guide_canvas_px") != [256, 256]:
        errors.append("guide canvas must be 256x256")
    if contract.get("runtime_canvas_px") != [64, 64] or contract.get("integer_downscale") != 4:
        errors.append("runtime must be 64x64 with exact 4x downscale")
    anchors = contract.get("runtime_anchors_px", {})
    if anchors != {"head_center": [32, 16], "neck": [32, 25], "foot_baseline_y": 60}:
        errors.append("runtime anchors differ from the locked G0 values")
    if tuple(contract.get("directions", {}).keys()) != EXPECTED_DIRECTIONS:
        errors.append("directions must be ordered front/right/back/left")
    if not args.blend.is_file() or args.blend.stat().st_size == 0:
        errors.append("missing Blender source scene")

    frames: list[Image.Image] = []
    for direction in EXPECTED_DIRECTIONS:
        path = args.render_dir / (direction + ".png")
        if not path.is_file():
            errors.append("missing %s render" % direction)
            continue
        image = Image.open(path).convert("RGBA")
        if image.size != (256, 256):
            errors.append("%s render is not 256x256" % direction)
        if image.getchannel("A").getbbox() is None:
            errors.append("%s render has no opaque mannequin pixels" % direction)
        frames.append(image)
    if errors:
        raise SystemExit("G0_GUIDE_FAIL: " + "; ".join(errors))

    sheet = Image.new("RGBA", (512, 512), (15, 23, 42, 255))
    labels = (("front", 0, 0), ("right", 256, 0), ("back", 0, 256), ("left", 256, 256))
    for (direction, x, y), image in zip(labels, frames, strict=True):
        tile = Image.new("RGBA", (256, 256), (15, 23, 42, 255))
        tile.alpha_composite(image)
        draw = ImageDraw.Draw(tile)
        draw.rectangle((0, 0, 255, 255), outline=(30, 58, 138, 255), width=2)
        draw.text((12, 12), direction.upper(), fill=(186, 230, 253, 255))
        sheet.alpha_composite(tile, (x, y))
        image.close()
    args.contact_sheet.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.contact_sheet)
    print("G0_GUIDE_PASS directions=4 guide=256x256 runtime=64x64 anchors=head32_16_neck32_25_floor60 output=%s" % args.contact_sheet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
