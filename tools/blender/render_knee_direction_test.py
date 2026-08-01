"""Render both signs of the current calf rotation to diagnose knee direction."""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--fbx", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points))),
        Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points))),
    )


def reset_pose(armature: bpy.types.Object) -> None:
    armature.animation_data_clear()
    for bone in armature.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.location = (0.0, 0.0, 0.0)
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)


def main() -> int:
    options = cli_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(options.fbx), use_anim=False)
    mesh = next(obj for obj in bpy.data.objects if obj.type == "MESH")
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    low, high = bounds(mesh)
    target = Vector(((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, (low.z + high.z) * 0.5))

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = True
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = True
    options.output.mkdir(parents=True, exist_ok=True)

    camera_data = bpy.data.cameras.new("KneeDirectionCameraData")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = max(4.0, (high.z - low.z) * 1.25)
    camera = bpy.data.objects.new("KneeDirectionCamera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (12.0, 0.0, target.z)
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera

    tests = (
        ("neutral", None, 0.0),
        ("calf_axis0_positive", "CC_Base_L_Calf", 25.0),
        ("calf_axis0_negative", "CC_Base_L_Calf", -25.0),
        ("thigh_axis0_positive", "CC_Base_L_Thigh", 25.0),
        ("thigh_axis0_negative", "CC_Base_L_Thigh", -25.0),
    )
    for name, bone_name, degrees in tests:
        reset_pose(armature)
        if bone_name:
            armature.pose.bones[bone_name].rotation_euler[0] = math.radians(degrees)
        scene.render.filepath = str(options.output / f"{name}.png")
        bpy.ops.render.render(write_still=True)

    print(f"KNEE_DIRECTION_TEST_PASS output={options.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
