"""Attach the extracted Koban base features to the original AccuRIG actor."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


KOBAN_REFERENCE_HEAD_WIDTH = 1.836


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--fbx", required=True, type=Path)
    parser.add_argument("--features", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--front-offset", type=float, default=0.18)
    parser.add_argument("--ear-outward", type=float, default=0.10)
    parser.add_argument("--eye-style", choices=("source", "anime_plate_v2"), default="anime_plate_v2")
    parser.add_argument("--eye-inset", type=float, default=0.09)
    parser.add_argument("--freestyle", action="store_true")
    return parser.parse_args(argv)


def bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector((min(point[i] for point in points) for i in range(3))),
        Vector((max(point[i] for point in points) for i in range(3))),
    )


def actor_head_bounds(mesh: bpy.types.Object) -> tuple[Vector, Vector]:
    group = mesh.vertex_groups.get("CC_Base_Head")
    if group is None:
        raise RuntimeError("original actor has no CC_Base_Head vertex group")
    points = []
    for vertex in mesh.data.vertices:
        if any(item.group == group.index and item.weight > 0.05 for item in vertex.groups):
            points.append(mesh.matrix_world @ vertex.co)
    if not points:
        raise RuntimeError("CC_Base_Head vertex group has no weighted vertices")
    return (
        Vector((min(point[i] for point in points) for i in range(3))),
        Vector((max(point[i] for point in points) for i in range(3))),
    )


def load_feature_objects(path: Path) -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    with bpy.data.libraries.load(str(path.resolve()), link=False) as (data_from, data_to):
        data_to.objects = list(data_from.objects)
    loaded = [obj for obj in data_to.objects if obj is not None]
    for obj in loaded:
        if obj.name not in bpy.context.collection.objects:
            bpy.context.collection.objects.link(obj)
    root = next((obj for obj in loaded if obj.name == "KobanFeatureRoot_Base"), None)
    if root is None:
        raise RuntimeError("Koban feature root not found")
    features = [obj for obj in loaded if obj.type == "MESH"]
    if len(features) != 6:
        raise RuntimeError(f"expected 6 extracted feature meshes, found {len(features)}")
    return root, features


def parent_to_head_bone(obj: bpy.types.Object, armature: bpy.types.Object) -> None:
    world_matrix = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = "CC_Base_Head"
    obj.matrix_world = world_matrix


def material_by_name(materials: list[bpy.types.Material], name: str, fallback: str) -> bpy.types.Material:
    for material in materials:
        if material is not None and material.name == name:
            return material
    for material in materials:
        if material is not None and material.name == fallback:
            return material
    material = bpy.data.materials.new(name)
    material.diffuse_color = (0.8, 0.8, 0.8, 1.0)
    return material


def extruded_polygon(
    name: str,
    points_xz: list[tuple[float, float]],
    y_front: float,
    thickness: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    """Create a shallow closed polygon, facing the actor's front (-Y)."""
    vertices = [(x, y_front, z) for x, z in points_xz]
    vertices += [(x, y_front + thickness, z) for x, z in points_xz]
    count = len(points_xz)
    faces: list[tuple[int, ...]] = [tuple(range(count - 1, -1, -1)), tuple(range(count, count * 2))]
    for index in range(count):
        next_index = (index + 1) % count
        faces.append((index, next_index, count + next_index, count + index))
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(material)
    for polygon in mesh.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj["feature_role"] = "anime_eye_component"
    return obj


def almond_points(center_x: float, center_z: float, half_width: float, half_height: float, samples: int = 16) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for index in range(samples + 1):
        t = index / samples
        x = center_x - half_width + (2.0 * half_width * t)
        z = center_z + half_height * (math.sin(math.pi * t) ** 0.72)
        points.append((x, z))
    for index in range(samples, -1, -1):
        t = index / samples
        x = center_x - half_width + (2.0 * half_width * t)
        z = center_z - half_height * (math.sin(math.pi * t) ** 0.88)
        points.append((x, z))
    return points


def ellipse_points(center_x: float, center_z: float, radius_x: float, radius_z: float, samples: int = 24) -> list[tuple[float, float]]:
    return [
        (
            center_x + radius_x * math.cos(2.0 * math.pi * index / samples),
            center_z + radius_z * math.sin(2.0 * math.pi * index / samples),
        )
        for index in range(samples)
    ]


def create_anime_eye(
    side: str,
    center: Vector,
    width: float,
    height: float,
    front_y: float,
    source_materials: list[bpy.types.Material],
) -> list[bpy.types.Object]:
    """Build a thin, layered anime eye with a controlled side profile."""
    sign = -1.0 if side == "L" else 1.0
    black = material_by_name(source_materials, "Material.012", "Material.010")
    white = material_by_name(source_materials, "Material.010", "Material.015")
    iris_material = material_by_name(source_materials, "Material.014", "Material.010")
    parts: list[bpy.types.Object] = []
    outline = almond_points(center.x, center.z, width * 0.56, height * 0.57)
    parts.append(extruded_polygon(f"AnimeEye_{side}_Outline", outline, front_y + 0.045, 0.055, black))
    sclera = almond_points(center.x, center.z, width * 0.49, height * 0.44)
    parts.append(extruded_polygon(f"AnimeEye_{side}_Sclera", sclera, front_y + 0.010, 0.045, white))

    iris_x = center.x - sign * width * 0.035
    iris_z = center.z - height * 0.055
    iris_outline = ellipse_points(iris_x, iris_z, width * 0.245, height * 0.355)
    parts.append(extruded_polygon(f"AnimeEye_{side}_IrisOutline", iris_outline, front_y - 0.005, 0.040, black))
    iris = ellipse_points(iris_x, iris_z, width * 0.205, height * 0.315)
    parts.append(extruded_polygon(f"AnimeEye_{side}_Iris", iris, front_y - 0.018, 0.035, iris_material))
    pupil = ellipse_points(iris_x, iris_z - height * 0.005, width * 0.085, height * 0.190)
    parts.append(extruded_polygon(f"AnimeEye_{side}_Pupil", pupil, front_y - 0.030, 0.030, black))
    highlight = ellipse_points(iris_x - sign * width * 0.065, iris_z + height * 0.135, width * 0.042, height * 0.075, 16)
    parts.append(extruded_polygon(f"AnimeEye_{side}_Highlight", highlight, front_y - 0.043, 0.020, white))
    for part in parts:
        part["eye_side"] = side
        part["eye_style"] = "anime_plate_v2"
    return parts


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


def configure_freestyle(scene: bpy.types.Scene) -> None:
    scene.render.use_freestyle = True
    settings = scene.view_layers[0].freestyle_settings
    line_set = settings.linesets[0]
    line_style = line_set.linestyle or bpy.data.linestyles.new("KobanFeaturesOnActorOutline")
    line_set.linestyle = line_style
    line_style.color = (0.04, 0.03, 0.07)
    line_style.thickness = 1.7
    for property_name in ("select_silhouette", "select_border", "select_crease"):
        if hasattr(line_set, property_name):
            setattr(line_set, property_name, True)


def main() -> int:
    options = cli_args()
    project_root = Path(__file__).resolve().parents[2]
    output_dir = options.output if options.output.is_absolute() else project_root / options.output
    output_dir = output_dir.resolve()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(options.fbx.resolve()), use_anim=True)
    actor_mesh = next((obj for obj in bpy.data.objects if obj.type == "MESH"), None)
    armature = next((obj for obj in bpy.data.objects if obj.type == "ARMATURE"), None)
    if actor_mesh is None or armature is None:
        raise RuntimeError("expected one original actor mesh and armature")

    actor_low, actor_high = bounds(actor_mesh)
    head_low, head_high = actor_head_bounds(actor_mesh)
    actor_head_width = head_high.x - head_low.x
    scale = (actor_head_width / KOBAN_REFERENCE_HEAD_WIDTH) * options.scale
    root, features = load_feature_objects(options.features)
    source_materials = [material for feature in features for material in feature.data.materials if material is not None]
    root_translation_values = root.get("feature_root_translation")
    if root_translation_values is None:
        raise RuntimeError("feature pack is missing feature_root_translation")
    koban_root_translation = Vector(root_translation_values)
    source_matrix_values = root.get("source_mesh_matrix_world")
    if source_matrix_values is None:
        raise RuntimeError("feature pack is missing source_mesh_matrix_world")
    source_mesh_matrix = Matrix(source_matrix_values)
    actor_head_bone = armature.data.bones.get("CC_Base_Head")
    if actor_head_bone is None:
        raise RuntimeError("original actor has no CC_Base_Head bone")
    actor_head_anchor = armature.matrix_world @ actor_head_bone.head_local
    actor_feature_anchor = actor_head_anchor + Vector((0.0, -options.front_offset, 0.0))
    mapping = Matrix.Translation(actor_feature_anchor) @ Matrix.Diagonal((scale, scale, scale, 1.0)) @ Matrix.Translation(-koban_root_translation)

    eye_specs: list[dict[str, object]] = []
    retained_features: list[bpy.types.Object] = []
    for feature in features:
        source_world_matrix = source_mesh_matrix.copy()
        print(
            "FEATURE_SOURCE",
            feature.name,
            tuple(round(value, 4) for value in source_world_matrix.translation),
            tuple(round(value, 4) for value in source_world_matrix.to_scale()),
        )
        mapped_matrix = mapping @ source_world_matrix
        if "ear_L" in feature.name:
            mapped_matrix = Matrix.Translation(Vector((-options.ear_outward, 0.0, 0.0))) @ mapped_matrix
        elif "ear_R" in feature.name:
            mapped_matrix = Matrix.Translation(Vector((options.ear_outward, 0.0, 0.0))) @ mapped_matrix
        mapped_points = [mapped_matrix @ vertex.co for vertex in feature.data.vertices]
        if options.eye_style == "anime_plate_v2" and "eye_" in feature.name:
            low = Vector((min(point[i] for point in mapped_points) for i in range(3)))
            high = Vector((max(point[i] for point in mapped_points) for i in range(3)))
            side = "L" if "_L" in feature.name else "R"
            eye_specs.append(
                {
                    "side": side,
                    "center": (low + high) * 0.5,
                    "width": high.x - low.x,
                    "height": high.z - low.z,
                    "front_y": low.y,
                }
            )
            bpy.data.objects.remove(feature, do_unlink=True)
            continue
        for vertex, point in zip(feature.data.vertices, mapped_points):
            vertex.co = point
        feature.data.update()
        # Keep the first review render in world space. Bone parenting is tested
        # separately after the static transform is visually accepted; this
        # avoids importing the Koban source scale into the FBX bone space.
        feature.parent = None
        feature.matrix_world = Matrix.Identity(4)
        retained_features.append(feature)

    generated_eye_parts: list[bpy.types.Object] = []
    if options.eye_style == "anime_plate_v2":
        for spec in eye_specs:
            generated_eye_parts.extend(
                create_anime_eye(
                    str(spec["side"]),
                    spec["center"],
                    float(spec["width"]) * 1.15,
                    float(spec["height"]) * 0.88,
                    float(spec["front_y"]) + options.eye_inset,
                    source_materials,
                )
            )
    retained_features.extend(generated_eye_parts)
    bpy.data.objects.remove(root, do_unlink=True)

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
    target = Vector(((actor_low.x + actor_high.x) * 0.5, (actor_low.y + actor_high.y) * 0.5, (actor_low.z + actor_high.z) * 0.5))
    camera_specs = {
        "front": (0.0, -12.0, target.z),
        "right": (12.0, 0.0, target.z),
        "back": (0.0, 12.0, target.z),
        "left": (-12.0, 0.0, target.z),
    }
    for direction, location in camera_specs.items():
        scene.camera = make_camera(scene, target, actor_low, actor_high, direction, location)
        scene.render.filepath = str(output_dir / f"{direction}.png")
        bpy.ops.render.render(write_still=True)

    manifest = {
        "schema": "assetslab_koban_features_on_accurig_v1",
        "source_fbx": str(options.fbx.resolve()),
        "source_features": str(options.features.resolve()),
        "target_bone": "CC_Base_Head",
        "head_width": actor_head_width,
        "scale": scale,
        "front_offset": options.front_offset,
        "ear_outward": options.ear_outward,
        "directions": list(camera_specs),
        "eye_style": options.eye_style,
        "eye_inset": options.eye_inset,
        "features": [obj.name for obj in retained_features],
        "eye_source_specs": [
            {
                "side": spec["side"],
                "center": list(spec["center"]),
                "width": spec["width"],
                "height": spec["height"],
                "front_y": spec["front_y"],
            }
            for spec in eye_specs
        ],
        "feature_bounds": {
            obj.name: {
                "min": list(bounds(obj)[0]),
                "max": list(bounds(obj)[1]),
            }
            for obj in retained_features
        },
        "status": "static_attachment_review_only",
    }
    (output_dir / "attachment_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"KOBAN_FEATURES_ON_ACCURIG_PASS scale={scale:.4f} output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
