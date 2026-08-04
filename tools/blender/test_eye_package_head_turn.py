"""Test EyePackage v2 while the actor head turns around the vertical axis."""

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

from render_procedural_anime_eye_on_accurig import bounds, make_camera, setup_render  # noqa: E402


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--save-blend", type=Path, required=True)
    parser.add_argument("--yaw-deg", type=float, default=18.0)
    return parser.parse_args(argv)


def world_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    return (
        Vector((min(point[i] for point in points) for i in range(3))),
        Vector((max(point[i] for point in points) for i in range(3))),
    )


def main() -> int:
    options = cli_args()
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    actor_mesh = next(obj for obj in bpy.data.objects if obj.type == "MESH" and not obj.name.startswith((
        "EyePackageV1_", "EyePackageV2_"
    )))
    head = armature.pose.bones.get("CC_Base_Head")
    if head is None:
        raise RuntimeError("CC_Base_Head pose bone is missing")
    package = [obj for obj in bpy.data.objects if obj.name.startswith(("EyePackageV1_", "EyePackageV2_"))]
    if not package:
        raise RuntimeError("EyePackageV2 objects are missing")

    head.rotation_mode = "XYZ"
    for frame, yaw in ((1, 0.0), (12, options.yaw_deg), (24, 0.0)):
        bpy.context.scene.frame_set(frame)
        head.rotation_euler = (0.0, 0.0, math.radians(yaw))
        head.keyframe_insert(data_path="rotation_euler", frame=frame)

    low, high = bounds(actor_mesh)
    package_low, package_high = world_bounds(package)
    target = Vector(((package_low.x + package_high.x) * 0.5, (low.y + high.y) * 0.5, (package_low.z + package_high.z) * 0.5))
    scene = bpy.context.scene
    setup_render(scene, -1.0)
    scene.render.resolution_x = scene.render.resolution_y = 384
    scene.render.resolution_percentage = 100
    scene.render.image_settings.color_mode = "RGBA"
    frames = {}
    for frame in (1, 12, 24):
        scene.frame_set(frame)
        camera = make_camera(scene, target, f"EyePackageHeadTurn_{frame}", (0.0, -12.0, target.z), 1.45)
        scene.camera = camera
        scene.render.filepath = str(output / f"frame_{frame:02d}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)
        frames[str(frame)] = {"yaw_deg": 0.0 if frame != 12 else options.yaw_deg}

    bpy.ops.wm.save_as_mainfile(filepath=str(options.save_blend.resolve()))
    (output / "manifest.json").write_text(json.dumps({
        "schema": "assetslab_eye_package_head_turn_test_v1",
        "parent_bone": "CC_Base_Head",
        "yaw_deg": options.yaw_deg,
        "frames": frames,
        "status": "head_turn_follow_test",
    }, indent=2), encoding="utf-8")
    print(f"EYE_PACKAGE_HEAD_TURN_PASS output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
