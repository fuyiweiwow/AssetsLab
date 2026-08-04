"""Render neutral and isolated knee tests from an AccuRIG FBX."""
from __future__ import annotations

import argparse
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
        Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points))),
        Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points))),
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
    bpy.ops.import_scene.fbx(filepath=str(options.fbx), use_anim=True)
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    if len(meshes) != 1 or len(armatures) != 1:
        raise RuntimeError("expected exactly one mesh and one armature")
    mesh = meshes[0]
    armature = armatures[0]
    low, high = bounds(mesh)
    target = Vector(((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, (low.z + high.z) * 0.5))

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    options.output.mkdir(parents=True, exist_ok=True)

    camera_data = bpy.data.cameras.new("AccuRIGTestCameraData")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = max(4.0, (high.z - low.z) * 1.25)
    camera = bpy.data.objects.new("AccuRIGTestCamera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -12.0, target.z)
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera

    tests = [("neutral", None), ("left_knee_axis0", 0), ("left_knee_axis1", 1), ("left_knee_axis2", 2)]
    for name, axis in tests:
        reset_pose(armature)
        if axis is not None:
            pose_bone = armature.pose.bones["CC_Base_L_Calf"]
            pose_bone.rotation_euler[axis] = 0.261799  # 15 degrees
        scene.render.filepath = str(options.output / f"{name}.png")
        bpy.ops.render.render(write_still=True)

    print(f"ACCURIG_RIGGED_TEST_RENDER_PASS output={options.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
