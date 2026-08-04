"""Render a procedural four-direction walk test from the downloaded Koban actor."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--amplitude", type=float, default=1.3)
    parser.add_argument("--freestyle", action="store_true")
    return parser.parse_args(argv)


def bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector((min(point[i] for point in points) for i in range(3))),
        Vector((max(point[i] for point in points) for i in range(3))),
    )


def reset_pose(armature: bpy.types.Object) -> None:
    armature.animation_data_clear()
    for bone in armature.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.location = (0.0, 0.0, 0.0)
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)


def rotate(armature: bpy.types.Object, name: str, axis: int, degrees: float) -> None:
    bone = armature.pose.bones.get(name)
    if bone is None:
        raise RuntimeError(f"missing Koban bone: {name}")
    bone.rotation_euler[axis] = math.radians(degrees)


def apply_walk_pose(armature: bpy.types.Object, phase: float, amplitude: float) -> None:
    swing = math.sin(phase)
    left_forward = swing
    right_forward = -swing

    rotate(armature, "thigh_stretch.l", 0, amplitude * 24.0 * left_forward)
    rotate(armature, "thigh_stretch.r", 0, amplitude * 24.0 * right_forward)
    rotate(armature, "leg_stretch.l", 0, amplitude * (8.0 + 26.0 * max(0.0, -left_forward)))
    rotate(armature, "leg_stretch.r", 0, amplitude * (8.0 + 26.0 * max(0.0, -right_forward)))
    rotate(armature, "foot.l", 0, amplitude * -10.0 * left_forward)
    rotate(armature, "foot.r", 0, amplitude * -10.0 * right_forward)

    rotate(armature, "arm_stretch.l", 0, amplitude * -18.0 * left_forward)
    rotate(armature, "arm_stretch.r", 0, amplitude * -18.0 * right_forward)
    rotate(armature, "forearm_stretch.l", 0, amplitude * -6.0 * left_forward)
    rotate(armature, "forearm_stretch.r", 0, amplitude * -6.0 * right_forward)


def make_camera(
    scene: bpy.types.Scene,
    target: Vector,
    low: Vector,
    high: Vector,
    name: str,
    location: tuple[float, float, float],
) -> bpy.types.Object:
    camera_data = bpy.data.cameras.new(name + "Data")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = max(4.8, (high.z - low.z) * 1.25)
    camera = bpy.data.objects.new(name, camera_data)
    scene.collection.objects.link(camera)
    camera.location = location
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    return camera


def configure_freestyle(scene: bpy.types.Scene) -> None:
    scene.render.use_freestyle = True
    settings = scene.view_layers[0].freestyle_settings
    line_set = settings.linesets[0]
    line_style = line_set.linestyle or bpy.data.linestyles.new("KobanWalkOutline")
    line_set.linestyle = line_style
    line_style.color = (0.04, 0.03, 0.05)
    line_style.thickness = 1.6
    for property_name in ("select_silhouette", "select_border", "select_crease"):
        if hasattr(line_set, property_name):
            setattr(line_set, property_name, True)


def main() -> int:
    options = cli_args()
    project_root = Path(__file__).resolve().parents[2]
    output_dir = options.output if options.output.is_absolute() else project_root / options.output
    output_dir = output_dir.resolve()

    bpy.ops.wm.open_mainfile(filepath=str(options.blend.resolve()))
    mesh = next((obj for obj in bpy.data.objects if obj.type == "MESH"), None)
    armature = next((obj for obj in bpy.data.objects if obj.type == "ARMATURE"), None)
    if mesh is None or armature is None:
        raise RuntimeError("expected one Koban mesh and one armature")

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
    if options.freestyle:
        configure_freestyle(scene)
    output_dir.mkdir(parents=True, exist_ok=True)

    camera_specs = {
        "front": (0.0, -12.0, target.z),
        "right": (12.0, 0.0, target.z),
        "back": (0.0, 12.0, target.z),
        "left": (-12.0, 0.0, target.z),
    }
    for direction, location in camera_specs.items():
        scene.camera = make_camera(scene, target, low, high, direction, location)
        for frame in range(8):
            reset_pose(armature)
            apply_walk_pose(armature, 2.0 * math.pi * frame / 8.0, options.amplitude)
            scene.render.filepath = str(output_dir / f"{direction}_{frame:02d}.png")
            bpy.ops.render.render(write_still=True)

    manifest = {
        "schema": "assetslab_koban_walk_test_v1",
        "source_blend": str(options.blend.resolve()),
        "character": "Koban Chibi Base Mesh VRM export",
        "motion": "procedural_walk_diagnostic",
        "amplitude": options.amplitude,
        "directions": list(camera_specs),
        "frame_count": 8,
        "bones": [
            "thigh_stretch.l",
            "thigh_stretch.r",
            "leg_stretch.l",
            "leg_stretch.r",
            "foot.l",
            "foot.r",
            "arm_stretch.l",
            "arm_stretch.r",
        ],
        "status": "binding_and_motion_diagnostic_only",
    }
    (output_dir / "walk_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"KOBAN_WALK_TEST_PASS amplitude={options.amplitude} output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
