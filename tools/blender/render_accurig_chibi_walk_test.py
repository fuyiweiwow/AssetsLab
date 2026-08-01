"""Render a restrained 8-frame chibi walk test from an AccuRIG FBX.

This is a diagnostic motion, not a replacement for a production motion clip.
It is intentionally small so knee placement, foot behavior, and head stability
can be judged before retargeting a larger motion library.
"""
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
    parser.add_argument("--amplitude", type=float, default=1.0)
    parser.add_argument("--reverse-calf", action="store_true")
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


def rotate(armature: bpy.types.Object, name: str, axis: int, degrees: float) -> None:
    armature.pose.bones[name].rotation_euler[axis] = math.radians(degrees)


def apply_walk_pose(
    armature: bpy.types.Object,
    phase: float,
    amplitude: float = 1.0,
    reverse_calf: bool = False,
) -> None:
    """Apply a visible in-place walk cycle using the FBX local X swing axis."""
    swing = math.sin(phase)
    left_forward = swing
    right_forward = -swing

    # Legs: clear contact, passing, and swing phases for a short-legged actor.
    rotate(armature, "CC_Base_L_Thigh", 0, amplitude * 24.0 * left_forward)
    rotate(armature, "CC_Base_R_Thigh", 0, amplitude * 24.0 * right_forward)
    left_calf = amplitude * (8.0 + 26.0 * max(0.0, -left_forward))
    right_calf = amplitude * (8.0 + 26.0 * max(0.0, -right_forward))
    if reverse_calf:
        left_calf = -left_calf
        right_calf = -right_calf
    rotate(armature, "CC_Base_L_Calf", 0, left_calf)
    rotate(armature, "CC_Base_R_Calf", 0, right_calf)
    rotate(armature, "CC_Base_L_Foot", 0, amplitude * -10.0 * left_forward)
    rotate(armature, "CC_Base_R_Foot", 0, amplitude * -10.0 * right_forward)

    # Arms counter-swing; head and torso remain fixed for deformation inspection.
    rotate(armature, "CC_Base_L_Upperarm", 0, amplitude * -18.0 * left_forward)
    rotate(armature, "CC_Base_R_Upperarm", 0, amplitude * -18.0 * right_forward)
    rotate(armature, "CC_Base_L_Forearm", 0, amplitude * -6.0 * left_forward)
    rotate(armature, "CC_Base_R_Forearm", 0, amplitude * -6.0 * right_forward)


def make_camera(scene: bpy.types.Scene, target: Vector, low: Vector, high: Vector, name: str, location: tuple[float, float, float]):
    camera_data = bpy.data.cameras.new(name + "Data")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = max(4.0, (high.z - low.z) * 1.25)
    camera = bpy.data.objects.new(name, camera_data)
    scene.collection.objects.link(camera)
    camera.location = location
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    return camera


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
    scene.render.resolution_x = scene.render.resolution_y = 256
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = True
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    options.output.mkdir(parents=True, exist_ok=True)

    camera_specs = {
        "front": (0.0, -12.0, target.z),
        "right": (12.0, 0.0, target.z),
        "back": (0.0, 12.0, target.z),
        "left": (-12.0, 0.0, target.z),
    }
    cameras = {
        name: make_camera(scene, target, low, high, name, location)
        for name, location in camera_specs.items()
    }
    for direction, camera in cameras.items():
        scene.camera = camera
        for frame in range(8):
            reset_pose(armature)
            apply_walk_pose(
                armature,
                (2.0 * math.pi * frame) / 8.0,
                options.amplitude,
                options.reverse_calf,
            )
            scene.render.filepath = str(options.output / f"{direction}_{frame:02d}.png")
            bpy.ops.render.render(write_still=True)

    print(f"ACCURIG_CHIBI_WALK_TEST_PASS output={options.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
