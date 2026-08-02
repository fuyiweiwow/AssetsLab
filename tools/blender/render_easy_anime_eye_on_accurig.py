"""Attach the downloaded Easy Anime Eye geometry to the AccuRIG actor."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


SOURCE_URL = "https://kingmusa.gumroad.com/l/jjbrz"
FEATURE_NAMES = (
    "anime eye.L",
    "anime eye.R",
    "eye.under.shadow",
    "eyeball.L",
    "eyeball.R",
    "eyebrows",
    "eyelashes.body",
    "eyelashes.sharp",
    "highlight.L",
    "highlight.R",
)
LASH_FEATURE_NAMES = (
    "eyelashes.body",
    "eyelashes.sharp",
)


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--fbx", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scale-factor", type=float, default=4.4)
    parser.add_argument("--eye-spacing", type=float, default=0.28)
    parser.add_argument("--eye-z-ratio", type=float, default=0.82)
    parser.add_argument("--face-front-bias", type=float, default=-0.08)
    parser.add_argument("--freestyle", action="store_true")
    parser.add_argument("--parent-head", action="store_true")
    parser.add_argument("--debug-flat-eye", action="store_true")
    parser.add_argument("--adapt-source-materials", action="store_true")
    parser.add_argument("--hide-highlights", action="store_true")
    parser.add_argument("--lashes-only", action="store_true", help="Only attach the independent eyelash meshes")
    parser.add_argument("--save-blend", action="store_true", help="Save the generated Blender scene next to the renders")
    return parser.parse_args(argv)


def bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector((min(point[i] for point in points) for i in range(3))),
        Vector((max(point[i] for point in points) for i in range(3))),
    )


def configure_freestyle(scene: bpy.types.Scene) -> None:
    scene.render.use_freestyle = True
    settings = scene.view_layers[0].freestyle_settings
    line_set = settings.linesets[0]
    line_style = line_set.linestyle or bpy.data.linestyles.new("EasyAnimeEyeOutline")
    line_set.linestyle = line_style
    line_style.color = (0.04, 0.025, 0.05)
    line_style.thickness = 1.5


def parent_to_head_bone(obj: bpy.types.Object, armature: bpy.types.Object) -> None:
    matrix = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = "CC_Base_Head"
    obj.matrix_world = matrix


def append_features(source: Path, feature_names: tuple[str, ...]) -> list[bpy.types.Object]:
    with bpy.data.libraries.load(str(source.resolve()), link=False) as (data_from, data_to):
        data_to.objects = [name for name in feature_names if name in data_from.objects]
    loaded: list[bpy.types.Object] = []
    for obj in data_to.objects:
        if obj is None:
            continue
        bpy.context.collection.objects.link(obj)
        loaded.append(obj)
    bpy.context.view_layer.update()
    if len(loaded) < len(feature_names):
        names = {obj.name for obj in loaded}
        raise RuntimeError(f"source is missing feature objects: {sorted(set(feature_names) - names)}")
    return loaded


def world_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    return (
        Vector((min(point[i] for point in points) for i in range(3))),
        Vector((max(point[i] for point in points) for i in range(3))),
    )


def transform_feature_group(
    objects: list[bpy.types.Object],
    target_center: Vector,
    scale_factor: float,
    eye_spacing: float,
) -> None:
    """Preserve the source eye assembly, then place and scale it as one unit."""
    # Resolve the source hierarchy before detaching.  The eye balls and
    # highlights are children of the eyelid objects in the source file.
    bpy.context.view_layer.update()
    original_matrices = {obj: obj.matrix_world.copy() for obj in objects}
    for obj in objects:
        world_matrix = original_matrices[obj]
        obj.parent = None
        obj.matrix_world = world_matrix
    low, high = world_bounds(objects)
    source_center = (low + high) * 0.5
    source_l = next(obj for obj in objects if obj.name == "eyeball.L")
    source_l_center = (world_bounds([source_l])[0] + world_bounds([source_l])[1]) * 0.5
    source_eye_offset = max(abs(source_l_center.x - source_center.x), 1e-6)
    desired_x_scale = eye_spacing / (source_eye_offset * scale_factor)
    group_transform = (
        Matrix.Translation(target_center)
        @ Matrix.Scale(scale_factor, 4)
        @ Matrix.Scale(desired_x_scale, 4, (1.0, 0.0, 0.0))
        @ Matrix.Translation(-source_center)
    )
    for obj in objects:
        original_world = original_matrices[obj]
        obj.matrix_world = group_transform @ original_world


def make_camera(scene: bpy.types.Scene, target: Vector, name: str, location: tuple[float, float, float], scale: float) -> bpy.types.Object:
    data = bpy.data.cameras.new(name + "Data")
    data.type = "ORTHO"
    data.ortho_scale = scale
    camera = bpy.data.objects.new(name, data)
    scene.collection.objects.link(camera)
    camera.location = location
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    return camera


def flat_material(name: str, color: tuple[float, float, float, float], roughness: float = 0.7) -> bpy.types.Material:
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = 0.0
    return material


def adapt_source_materials(features: list[bpy.types.Object]) -> None:
    materials = {
        "white": flat_material("EasyAnimeEyeAdaptedWhite", (0.98, 0.98, 1.0, 1.0)),
        "black": flat_material("EasyAnimeEyeAdaptedBlack", (0.01, 0.008, 0.012, 1.0), 0.5),
        "brown": flat_material("EasyAnimeEyeAdaptedBrown", (0.28, 0.07, 0.025, 1.0), 0.8),
        "shadow": flat_material("EasyAnimeEyeAdaptedShadow", (0.52, 0.36, 0.42, 0.65), 1.0),
    }
    for feature in features:
        if feature.name.startswith(("anime eye", "highlight")):
            material = materials["white"]
        elif feature.name.startswith("eyeball"):
            material = materials["black"]
        elif feature.name.startswith(("eyebrows", "eyelashes")):
            material = materials["brown"]
        else:
            material = materials["shadow"]
        feature.data.materials.clear()
        feature.data.materials.append(material)


def main() -> int:
    options = cli_args()
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(options.fbx.resolve()), use_anim=True)
    mesh = next(obj for obj in bpy.data.objects if obj.type == "MESH")
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    low, high = bounds(mesh)
    overall_center = Vector(((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, (low.z + high.z) * 0.5))
    eye_z = low.z + (high.z - low.z) * options.eye_z_ratio
    target_center = Vector((overall_center.x, low.y + options.face_front_bias, eye_z))

    selected_names = LASH_FEATURE_NAMES if options.lashes_only else FEATURE_NAMES
    # Keep one left eyeball as a placement helper for lash-only mode. The helper
    # is removed after the shared source-group transform and is never rendered.
    append_names = selected_names + (("eyeball.L",) if options.lashes_only else ())
    loaded_features = append_features(options.source, append_names)
    features = [obj for obj in loaded_features if obj.name in selected_names]
    transform_feature_group(loaded_features, target_center, options.scale_factor, options.eye_spacing)
    for helper in [obj for obj in loaded_features if obj.name not in selected_names]:
        bpy.data.objects.remove(helper, do_unlink=True)
    if options.debug_flat_eye:
        debug_material = bpy.data.materials.new("EasyAnimeEyeDebugFlat")
        debug_material.diffuse_color = (0.8, 0.02, 0.02, 1.0)
        debug_material.use_nodes = True
        debug_material.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (0.8, 0.02, 0.02, 1.0)
        for feature in features:
            if feature.name.startswith("eyeball"):
                feature.data.materials.clear()
                feature.data.materials.append(debug_material)
    elif options.adapt_source_materials:
        adapt_source_materials(features)
    if options.hide_highlights:
        for feature in features:
            if feature.name.startswith("highlight"):
                feature.hide_render = True
    for feature in features:
        feature["source_model"] = "Easy Anime Eye free package"
        feature["source_license_note"] = "Commercial use allowed; do not redistribute standalone product"
        if options.parent_head:
            parent_to_head_bone(feature, armature)
    feature_low, feature_high = world_bounds(features)
    print("FEATURE_DEBUG", tuple(round(v, 3) for v in feature_low), tuple(round(v, 3) for v in feature_high), [(o.name, tuple(round(v, 3) for v in world_bounds([o])[0]), tuple(round(v, 3) for v in world_bounds([o])[1]), [(s.material.name if s.material else None, tuple(round(v, 3) for v in s.material.node_tree.nodes.get('プリンシプルBSDF').inputs['Base Color'].default_value[:3]) if s.material and s.material.use_nodes and s.material.node_tree.nodes.get('プリンシプルBSDF') else None) for s in o.material_slots]) for o in features])

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = scene.render.resolution_y = 256
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("EasyAnimeEyeWorld")
    scene.world.color = (0.06, 0.06, 0.08)
    for location, energy, size in (
        ((0.0, -4.0, 5.0), 1000.0, 4.0),
        ((-3.0, -2.0, 2.0), 450.0, 3.0),
    ):
        light_data = bpy.data.lights.new("EasyAnimeEyeArea", "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new("EasyAnimeEyeArea", light_data)
        scene.collection.objects.link(light)
        light.location = location
        light.rotation_euler = (overall_center - light.location).to_track_quat("-Z", "Y").to_euler()
    if options.freestyle:
        configure_freestyle(scene)

    camera_specs = {
        "front": (0.0, -12.0, overall_center.z),
        "right": (12.0, 0.0, overall_center.z),
        "back": (0.0, 12.0, overall_center.z),
        "left": (-12.0, 0.0, overall_center.z),
    }
    for direction, location in camera_specs.items():
        camera = make_camera(scene, overall_center, direction, location, max(4.0, high.z - low.z + 0.6))
        scene.camera = camera
        scene.render.filepath = str(output / f"{direction}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)

    (output / "feature_manifest.json").write_text(
        json.dumps(
            {
                "schema": "assetslab_easy_anime_eye_on_accurig_v1",
                "source_fbx": str(options.fbx.resolve()),
                "source_blend": str(options.source.resolve()),
                "source_url": SOURCE_URL,
        "features": list(selected_names),
        "lashes_only": options.lashes_only,
                "parent_bone": "CC_Base_Head",
                "placement": {
                    "scale_factor": options.scale_factor,
                    "eye_spacing": options.eye_spacing,
                    "eye_z_ratio": options.eye_z_ratio,
                    "face_front_bias": options.face_front_bias,
                },
                "directions": list(camera_specs),
                "status": "static_four_direction_review_only",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    if options.save_blend:
        blend_path = output / "easy_anime_eye_on_accurig.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
        print(f"BLEND_SAVED {blend_path}")
    print(f"EASY_ANIME_EYE_ON_ACCURIG_PASS output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
