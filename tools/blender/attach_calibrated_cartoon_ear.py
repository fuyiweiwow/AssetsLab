"""Attach the downloaded ear using normalized front/right anchor annotations."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from attach_cartoon_ear_candidate import (  # noqa: E402
    HEAD_BONE,
    append_source_part,
    bounds,
    center_mesh,
    configure_render,
    duplicate_ear,
    make_skin_material,
)
from render_procedural_anime_eye_on_accurig import make_camera  # noqa: E402


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-blend", required=True, type=Path)
    parser.add_argument("--source-blend", required=True, type=Path)
    parser.add_argument("--calibration", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--save-blend", required=True, type=Path)
    parser.add_argument("--part", default="CartoonEarPart_01")
    return parser.parse_args(argv)


def image_point_to_world(point: dict, center: Vector, ortho_scale: float, side: str) -> Vector:
    screen_x = float(point["x"])
    screen_y = float(point["y"])
    world_x = center.x + (screen_x - 0.5) * ortho_scale if side == "front" else center.y + (screen_x - 0.5) * ortho_scale
    world_z = center.z + (0.5 - screen_y) * ortho_scale
    if side == "front":
        return Vector((world_x, center.y, world_z))
    return Vector((center.x, world_x, world_z))


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.input_blend.resolve()))
    output = options.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    actor = next(obj for obj in bpy.data.objects if obj.type == "MESH" and obj.name.startswith("ChibiBase"))
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    if HEAD_BONE not in armature.data.bones:
        raise RuntimeError(f"actor is missing {HEAD_BONE}")
    calibration = json.loads(options.calibration.resolve().read_text(encoding="utf-8"))
    if calibration.get("schema") != "assetslab_chibi_ear_anchor_calibration_v1":
        raise RuntimeError("unsupported ear calibration schema")

    low, high = bounds(actor)
    center = (low + high) * 0.5
    ortho_scale = max(4.0, high.z - low.z + 0.6)
    front = calibration["views"]["front"]
    side = calibration["views"]["side"]["R"]
    root_l = image_point_to_world(front["L"]["root"], center, ortho_scale, "front")
    root_r = image_point_to_world(front["R"]["root"], center, ortho_scale, "front")
    depth_r = image_point_to_world(side["root"], center, ortho_scale, "side")
    root_l.y = depth_r.y
    root_r.y = depth_r.y
    height_l = abs(float(front["L"]["bottom"]["y"]) - float(front["L"]["top"]["y"])) * ortho_scale
    height_r = abs(float(front["R"]["bottom"]["y"]) - float(front["R"]["top"]["y"])) * ortho_scale

    source = append_source_part(options.source_blend, options.part)
    center_mesh(source)
    source_width = source.dimensions.x
    source_height = source.dimensions.z
    scale = max(0.05, ((height_l + height_r) * 0.5) / source_height)
    half_width = source_width * scale * 0.5
    skin = make_skin_material()
    left = duplicate_ear(source, "L", root_l.x - half_width, root_l.y, root_l.z, scale, 0.0, 0.0, True, armature, skin)
    right = duplicate_ear(source, "R", root_r.x + half_width, root_r.y, root_r.z, scale, 0.0, 0.0, False, armature, skin)
    bpy.data.objects.remove(source, do_unlink=True)

    configure_render(bpy.context.scene)
    scene = bpy.context.scene
    specs = {
        "front": ((0.0, -12.0, center.z), ortho_scale),
        "right": ((12.0, 0.0, center.z), ortho_scale),
        "front_face_closeup": ((0.0, -12.0, (root_l.z + root_r.z) * 0.5), max(1.35, (high.z - low.z) * 0.38)),
        "right_face_closeup": ((12.0, 0.0, depth_r.z), max(1.35, (high.z - low.z) * 0.38)),
    }
    for name, (location, camera_scale) in specs.items():
        target = Vector((center.x, center.y, depth_r.z if "closeup" in name else center.z))
        camera = make_camera(scene, target, name, location, camera_scale)
        scene.camera = camera
        scene.render.filepath = str(output / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)

    options.save_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.save_blend.resolve()))
    manifest = {
        "schema": "assetslab_calibrated_cartoon_ear_attachment_v1",
        "calibration": str(options.calibration.resolve()),
        "source_part": options.part,
        "parent_bone": HEAD_BONE,
        "computed": {
            "left_root": list(root_l),
            "right_root": list(root_r),
            "right_side_depth": depth_r.y,
            "ortho_scale": ortho_scale,
            "scale": scale,
            "half_width_offset": half_width,
        },
        "renders": {name: str(output / f"{name}.png") for name in specs},
        "status": "calibrated_attachment_review_pending",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"CALIBRATED_CARTOON_EAR_PASS output={output} blend={options.save_blend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
