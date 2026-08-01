"""Validate the G1 pose/pass renders against g1_pose_3d.json and compose a contact sheet.

Run with the project Python (Pillow required).  For every direction/frame cell:

- beauty.png must exist, be 256x256, and contain opaque mannequin pixels.
- For each of the seven parts, the pixel at its rounded centroid (depth_px)
  must carry the ID color of the geometry-visible part, and the depth.png
  value there must match the geometry-visible camera depth through the locked
  linear map (7.5..12.5 -> 0..1, Raw output, 16-bit PNG).
- The depth/ID expectations are computed in the Blender build from ray casts
  against the posed geometry, so occlusion is handled exactly.

A 4x8 contact sheet (directions x frames) is composed from the beauty renders.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

EXPECTED_DIRECTIONS = ("front", "right", "back", "left")
EXPECTED_PARTS = ["head", "torso", "pelvis", "arm_L", "arm_R", "leg_L", "leg_R"]
FRAME_COUNT = 8
DEPTH_TOL = 0.05          # world units, compared through the linear map
ID_TOL = 64               # 8-bit channel tolerance (absorbs MSAA edge tint)
# How many parts must have their own centroid pixel visible.  The side views
# are structurally limited: the far arm/leg are occluded by the near arm and
# the torso, and the pelvis centroid is covered by the swinging near arm, so
# only head/torso/near-arm/near-leg can be self-visible there.
MIN_SELF_VISIBLE = {"front": 6, "right": 4, "back": 6, "left": 4}


def depth_to_16bit(depth: float, depth_from: float, depth_to: float) -> int:
    value = max(0.0, min(1.0, (depth - depth_from) / (depth_to - depth_from)))
    return int(round(value * 65535))


def read_depth_pixel(image: Image.Image, x: int, y: int) -> int:
    pixel = image.getpixel((x, y))
    if isinstance(pixel, tuple):
        pixel = pixel[0]
    if image.mode == "L":
        return pixel * 257
    return int(pixel)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and compose G1 Blender guide renders.")
    parser.add_argument("--pose-3d", required=True, type=Path)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--render-dir", required=True, type=Path)
    parser.add_argument("--contact-sheet", required=True, type=Path)
    args = parser.parse_args()

    pose3d = json.loads(args.pose_3d.read_text(encoding="utf-8"))
    errors: list[str] = []
    if pose3d.get("schema") != "assetslab_3d_guide_v1_pose_3d":
        errors.append("unexpected pose3d schema")
    if pose3d.get("guide_canvas_px") != [256, 256]:
        errors.append("guide canvas must be 256x256")
    if tuple(pose3d.get("directions", [])) != EXPECTED_DIRECTIONS:
        errors.append("directions must be ordered front/right/back/left")
    parts = pose3d.get("parts", [])
    if [p["id"] for p in parts] != EXPECTED_PARTS:
        errors.append("part ids must be head/torso/pelvis/arm_L/arm_R/leg_L/leg_R")
    depth_map = pose3d.get("depth_map", {})
    depth_from, depth_to = depth_map.get("from"), depth_map.get("to")
    if depth_from is None or depth_to is None:
        errors.append("depth_map must define from/to")
    frames = pose3d.get("frames", [])
    if len(frames) != 4 * FRAME_COUNT:
        errors.append("pose3d must contain 32 frames")
    if not args.blend.is_file() or args.blend.stat().st_size == 0:
        errors.append("missing Blender source scene")
    if errors:
        raise SystemExit("G1_GUIDE_FAIL: " + "; ".join(errors))

    id_colors = {p["id"]: tuple(p["color"]) for p in parts}
    depth_tol_16bit = int(round(DEPTH_TOL / (depth_to - depth_from) * 65535))

    sheet = Image.new("RGBA", (FRAME_COUNT * 256, len(EXPECTED_DIRECTIONS) * 256), (15, 23, 42, 255))
    draw = ImageDraw.Draw(sheet)
    drawn_cells = 0
    for direction_index, direction in enumerate(EXPECTED_DIRECTIONS):
        for frame_index in range(FRAME_COUNT):
            cell_dir = args.render_dir / direction / ("frame_%02d" % frame_index)
            cell_label = "%s f%d" % (direction, frame_index)
            beauty_path = cell_dir / "beauty.png"
            depth_path = cell_dir / "depth.png"
            id_path = cell_dir / "id.png"
            if not (beauty_path.is_file() and depth_path.is_file() and id_path.is_file()):
                errors.append("%s: missing beauty/depth/id outputs" % cell_label)
                continue
            beauty = Image.open(beauty_path)
            depth = Image.open(depth_path)
            id_image = Image.open(id_path)
            if beauty.size != (256, 256) or depth.size != (256, 256) or id_image.size != (256, 256):
                errors.append("%s: renders must be 256x256" % cell_label)
                beauty.close(); depth.close(); id_image.close()
                continue
            if beauty.getchannel("A").getbbox() is None:
                errors.append("%s: beauty has no opaque mannequin pixels" % cell_label)

            frame_data = next(f for f in frames if f["direction"] == direction and f["frame"] == frame_index)
            self_visible = 0
            for entry in frame_data["expected"]:
                part = entry["part"]
                col, row = entry["depth_px"]
                visible_part = entry["visible_part"]
                visible_depth = entry["visible_depth"]
                if visible_part is None or visible_depth is None:
                    errors.append("%s: no geometry visible at %s centroid (%d,%d)" % (cell_label, part, col, row))
                    continue
                if visible_part == part:
                    self_visible += 1
                expected_color = id_colors[visible_part]
                actual_color = id_image.convert("RGB").getpixel((col, row))
                if any(abs(actual_color[c] - expected_color[c]) > ID_TOL for c in range(3)):
                    errors.append("%s: id pixel at %s centroid (%d,%d) is %s, expected %s (visible part %s)"
                                  % (cell_label, part, col, row, actual_color, expected_color, visible_part))
                expected16 = depth_to_16bit(visible_depth, depth_from, depth_to)
                actual16 = read_depth_pixel(depth, col, row)
                if abs(actual16 - expected16) > depth_tol_16bit:
                    errors.append("%s: depth pixel at %s centroid (%d,%d) is %d, expected %d (depth %.3f)"
                                  % (cell_label, part, col, row, actual16, expected16, visible_depth))
            if self_visible < MIN_SELF_VISIBLE[direction]:
                errors.append("%s: only %d of 7 parts have their own centroid visible (min %d for %s)"
                              % (cell_label, self_visible, MIN_SELF_VISIBLE[direction], direction))

            beauty_rgb = beauty.convert("RGBA")
            sheet.alpha_composite(beauty_rgb, (frame_index * 256, direction_index * 256))
            draw.text((frame_index * 256 + 10, direction_index * 256 + 10), cell_label, fill=(186, 230, 253, 255))
            draw.rectangle((frame_index * 256, direction_index * 256, frame_index * 256 + 255, direction_index * 256 + 255),
                           outline=(30, 58, 138, 255), width=2)
            drawn_cells += 1
            beauty.close(); depth.close(); id_image.close()

    if drawn_cells != 4 * FRAME_COUNT:
        errors.append("contact sheet is incomplete (%d/32 cells)" % drawn_cells)
    if errors:
        raise SystemExit("G1_GUIDE_FAIL: " + "; ".join(errors))

    args.contact_sheet.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.contact_sheet)
    print("G1_GUIDE_PASS directions=4 frames=%d parts=%d depth_tol=%.2f output=%s"
          % (FRAME_COUNT, len(EXPECTED_PARTS), DEPTH_TOL, args.contact_sheet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
