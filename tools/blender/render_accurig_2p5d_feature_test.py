"""Render shallow, head-bone-parented facial features on the real actor.

This is a static four-direction placement test. It intentionally creates only
eyes, irises, highlights, and small ears; nose and mouth stay out of scope.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


PROFILES = {
    "soft_anime_v1": {
        "eye_spacing": 0.22,
        "eye_z_ratio": 0.84,
        "face_y_offset": 0.08,
        "eye_outer_scale": [0.115, 0.028, 0.085],
        "iris_scale": [0.052, 0.016, 0.048],
        "highlight_radius": 0.018,
        "ear_x_ratio": 0.82,
        "ear_z_ratio": 0.82,
        "ear_scale": [0.14, 0.065, 0.20],
        "ear_inner_scale": [0.075, 0.018, 0.12],
    },
    "compact_v1": {
        "eye_spacing": 0.20,
        "eye_z_ratio": 0.83,
        "face_y_offset": 0.075,
        "eye_outer_scale": [0.10, 0.025, 0.072],
        "iris_scale": [0.045, 0.014, 0.040],
        "highlight_radius": 0.016,
        "ear_x_ratio": 0.80,
        "ear_z_ratio": 0.81,
        "ear_scale": [0.12, 0.055, 0.17],
        "ear_inner_scale": [0.064, 0.016, 0.10],
    },
}


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--fbx", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="soft_anime_v1")
    parser.add_argument("--freestyle", action="store_true")
    return parser.parse_args(argv)


def bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector((min(point[i] for point in points) for i in range(3))),
        Vector((max(point[i] for point in points) for i in range(3))),
    )


def make_material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    item = bpy.data.materials.new(name)
    item.diffuse_color = color
    return item


def configure_freestyle(scene: bpy.types.Scene) -> None:
    scene.render.use_freestyle = True
    settings = scene.view_layers[0].freestyle_settings
    line_set = settings.linesets[0]
    line_style = line_set.linestyle or bpy.data.linestyles.new("Pixel2P5DFeatureOutline")
    line_set.linestyle = line_style
    line_style.color = (0.04, 0.035, 0.08)
    line_style.thickness = 1.5
    for property_name in ("select_silhouette", "select_border", "select_crease"):
        if hasattr(line_set, property_name):
            setattr(line_set, property_name, True)


def parent_to_head_bone(obj: bpy.types.Object, armature: bpy.types.Object) -> None:
    world_matrix = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = "CC_Base_Head"
    obj.matrix_world = world_matrix


def add_shallow_sphere(
    name: str,
    location: Vector,
    scale: tuple[float, float, float],
    material: bpy.types.Material,
    armature: bpy.types.Object,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    parent_to_head_bone(obj, armature)
    return obj


def add_eye(
    armature: bpy.types.Object,
    side: float,
    location: Vector,
    profile: dict,
    eye_material: bpy.types.Material,
    iris_material: bpy.types.Material,
    highlight_material: bpy.types.Material,
) -> None:
    outer_scale = tuple(profile["eye_outer_scale"])
    iris_scale = tuple(profile["iris_scale"])
    side_name = "L" if side < 0 else "R"
    add_shallow_sphere(f"Face2P5D_Eye_{side_name}", location, outer_scale, eye_material, armature)

    iris_location = location + Vector((0.0, -(outer_scale[1] + iris_scale[1] * 0.8), 0.0))
    add_shallow_sphere(f"Face2P5D_Iris_{side_name}", iris_location, iris_scale, iris_material, armature)

    highlight_location = iris_location + Vector((-0.018 if side < 0 else 0.018, -0.018, 0.035))
    add_shallow_sphere(
        f"Face2P5D_Highlight_{side_name}",
        highlight_location,
        (profile["highlight_radius"], 0.010, profile["highlight_radius"]),
        highlight_material,
        armature,
    )


def add_ear(
    armature: bpy.types.Object,
    side: float,
    location: Vector,
    profile: dict,
    ear_material: bpy.types.Material,
    inner_material: bpy.types.Material,
) -> None:
    side_name = "L" if side < 0 else "R"
    outer_scale = tuple(profile["ear_scale"])
    inner_scale = tuple(profile["ear_inner_scale"])
    add_shallow_sphere(f"Face2P5D_Ear_{side_name}", location, outer_scale, ear_material, armature)
    inner_location = location + Vector((-side * outer_scale[0] * 0.35, -outer_scale[1] * 0.9, 0.0))
    add_shallow_sphere(f"Face2P5D_EarInner_{side_name}", inner_location, inner_scale, inner_material, armature)


def add_features(
    armature: bpy.types.Object,
    low: Vector,
    high: Vector,
    profile: dict,
) -> dict:
    height = high.z - low.z
    head_z = low.z + height * profile["eye_z_ratio"]
    face_y = low.y - profile["face_y_offset"]
    eye_spacing = profile["eye_spacing"]

    eye_material = make_material("Face2P5D_EyeOuter", (0.035, 0.045, 0.10, 1.0))
    iris_material = make_material("Face2P5D_Iris", (0.12, 0.34, 0.62, 1.0))
    highlight_material = make_material("Face2P5D_Highlight", (0.98, 0.99, 1.0, 1.0))
    ear_material = make_material("Face2P5D_EarOuter", (0.48, 0.31, 0.40, 1.0))
    inner_material = make_material("Face2P5D_EarInner", (0.72, 0.42, 0.50, 1.0))

    for side in (-1.0, 1.0):
        add_eye(
            armature,
            side,
            Vector((side * eye_spacing, face_y, head_z)),
            profile,
            eye_material,
            iris_material,
            highlight_material,
        )

    head_width = max(abs(low.x), abs(high.x))
    ear_x = head_width * profile["ear_x_ratio"]
    ear_z = low.z + height * profile["ear_z_ratio"]
    for side in (-1.0, 1.0):
        add_ear(
            armature,
            side,
            Vector((side * ear_x, 0.0, ear_z)),
            profile,
            ear_material,
            inner_material,
        )

    return {
        "eye_spacing": eye_spacing,
        "eye_z": head_z,
        "face_y": face_y,
        "ear_x": ear_x,
        "ear_z": ear_z,
        "eye_outer_scale": profile["eye_outer_scale"],
        "ear_scale": profile["ear_scale"],
    }


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
    profile = PROFILES[options.profile]
    placement = add_features(armature, low, high, profile)

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

    manifest = {
        "schema": "assetslab_accurig_2p5d_feature_test_v1",
        "source_fbx": str(options.fbx.resolve()),
        "profile": options.profile,
        "parent_bone": "CC_Base_Head",
        "directions": list(camera_specs),
        "features": ["shallow_eye_outer", "iris", "eye_highlight", "shallow_ears", "ear_inner"],
        "excluded": ["nose", "mouth"],
        "placement": placement,
        "status": "static_four_direction_review_only",
    }
    (output_dir / "feature_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"ACCURIG_2P5D_FEATURE_TEST_PASS profile={options.profile} output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
