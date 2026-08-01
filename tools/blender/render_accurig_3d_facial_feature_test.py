"""Render 3D facial feature variants on the actual AccuRIG chibi actor."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--fbx", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--variant", type=int, default=0)
    parser.add_argument("--freestyle", action="store_true")
    return parser.parse_args(argv)


def bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector((min(point[i] for point in points) for i in range(3))),
        Vector((max(point[i] for point in points) for i in range(3))),
    )


def material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    item = bpy.data.materials.new(name)
    item.diffuse_color = color
    return item


def configure_freestyle(scene: bpy.types.Scene) -> None:
    scene.render.use_freestyle = True
    settings = scene.view_layers[0].freestyle_settings
    line_set = settings.linesets[0]
    line_style = line_set.linestyle or bpy.data.linestyles.new("PixelFacialFeatureOutline")
    line_set.linestyle = line_style
    line_style.color = (0.06, 0.05, 0.10)
    line_style.thickness = 1.6
    for property_name in ("select_silhouette", "select_border", "select_crease"):
        if hasattr(line_set, property_name):
            setattr(line_set, property_name, True)


def parent_to_head_bone(obj: bpy.types.Object, armature: bpy.types.Object, world_matrix) -> None:
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = "CC_Base_Head"
    obj.matrix_world = world_matrix


def add_eye(
    armature: bpy.types.Object,
    location: Vector,
    scale: tuple[float, float, float],
    dark: bpy.types.Material,
    highlight: bpy.types.Material,
    side: float,
) -> None:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, location=location)
    eye = bpy.context.object
    eye.name = f"Face3D_Eye_{'L' if side < 0 else 'R'}"
    eye.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    eye.data.materials.append(dark)
    matrix = eye.matrix_world.copy()
    parent_to_head_bone(eye, armature, matrix)

    highlight_location = location + Vector((-0.045 if side < 0 else 0.045, -0.075, 0.055))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=4, radius=0.035, location=highlight_location)
    shine = bpy.context.object
    shine.name = f"Face3D_EyeHighlight_{'L' if side < 0 else 'R'}"
    shine.data.materials.append(highlight)
    parent_to_head_bone(shine, armature, shine.matrix_world.copy())


def add_ear(armature: bpy.types.Object, location: Vector, side: float, pointed: bool, ear_material: bpy.types.Material) -> None:
    if pointed:
        bpy.ops.mesh.primitive_cone_add(
            vertices=8,
            radius1=0.18,
            radius2=0.0,
            depth=0.46,
            location=location,
            rotation=(0.0, math.radians(90.0 if side < 0 else -90.0), 0.0),
        )
    else:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=5, location=location)
        bpy.context.object.scale = (0.20, 0.12, 0.28)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ear = bpy.context.object
    ear.name = f"Face3D_Ear_{'L' if side < 0 else 'R'}"
    ear.data.materials.append(ear_material)
    parent_to_head_bone(ear, armature, ear.matrix_world.copy())


def add_facial_features(armature: bpy.types.Object, low: Vector, high: Vector, variant: int) -> dict:
    variant %= 4
    head_center_z = low.z + (high.z - low.z) * 0.82
    face_y = low.y - 0.08
    eye_shapes = [
        (0.15, 0.07, 0.16),
        (0.11, 0.07, 0.18),
        (0.16, 0.07, 0.095),
        (0.09, 0.06, 0.09),
    ]
    eye_scale = eye_shapes[variant]
    eye_z = head_center_z + 0.02
    eye_spacing = 0.28
    dark = material("Face3D_EyeDark", (0.035, 0.045, 0.085, 1.0))
    highlight = material("Face3D_EyeHighlight", (0.95, 0.98, 1.0, 1.0))
    ear_material = material("Face3D_Ear", (0.44, 0.50, 0.66, 1.0))
    add_eye(armature, Vector((-eye_spacing, face_y, eye_z)), eye_scale, dark, highlight, -1.0)
    add_eye(armature, Vector((eye_spacing, face_y, eye_z)), eye_scale, dark, highlight, 1.0)
    ear_z = head_center_z - 0.02
    ear_x = max(abs(low.x), abs(high.x)) * 0.88
    add_ear(armature, Vector((-ear_x, 0.0, ear_z)), -1.0, variant in (1, 3), ear_material)
    add_ear(armature, Vector((ear_x, 0.0, ear_z)), 1.0, variant in (1, 3), ear_material)
    return {
        "variant": variant,
        "eye_spacing": eye_spacing,
        "eye_scale": eye_scale,
        "eye_z": eye_z,
        "ear_x": ear_x,
        "ear_z": ear_z,
        "face_y": face_y,
    }


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
    project_root = Path(__file__).resolve().parents[2]
    output_dir = options.output if options.output.is_absolute() else project_root / options.output
    output_dir = output_dir.resolve()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(options.fbx), use_anim=True)
    mesh = next((obj for obj in bpy.data.objects if obj.type == "MESH"), None)
    armature = next((obj for obj in bpy.data.objects if obj.type == "ARMATURE"), None)
    if mesh is None or armature is None:
        raise RuntimeError("expected one mesh and one armature")
    low, high = bounds(mesh)
    target = Vector(((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, (low.z + high.z) * 0.5))
    feature_manifest = add_facial_features(armature, low, high, options.variant)

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
        scene.render.filepath = str(output_dir / f"{direction}.png")
        bpy.ops.render.render(write_still=True)

    import json

    (output_dir / "feature_manifest.json").write_text(
        json.dumps(
            {
                "schema": "assetslab_accurig_3d_facial_feature_test_v1",
                "source_fbx": str(options.fbx.resolve()),
                "variant": options.variant % 4,
                "parent_bone": "CC_Base_Head",
                "directions": list(camera_specs),
                "features": ["eyes", "eye_highlights", "ears"],
                "excluded": ["nose", "mouth"],
                "placement": feature_manifest,
                "status": "static_four_direction_review_only",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"ACCURIG_3D_FACE_TEST_PASS variant={options.variant % 4} output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

