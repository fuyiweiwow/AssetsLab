"""Attach the CC0 OpenGameArt anime eye geometry to the original actor."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


SOURCE_FACE_WIDTH = 0.273
SOURCE_URL = "https://opengameart.org/content/generic-anime-face"


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--fbx", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scale-factor", type=float, default=0.82)
    parser.add_argument("--eye-z-ratio", type=float, default=0.51)
    parser.add_argument("--front-surface-bias", type=float, default=-0.01)
    parser.add_argument("--depth-scale", type=float, default=0.35)
    parser.add_argument("--freestyle", action="store_true")
    return parser.parse_args(argv)


def bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector((min(point[i] for point in points) for i in range(3))),
        Vector((max(point[i] for point in points) for i in range(3))),
    )


def actor_head_points(mesh: bpy.types.Object) -> list[Vector]:
    group = mesh.vertex_groups.get("CC_Base_Head")
    if group is None:
        raise RuntimeError("original actor has no CC_Base_Head vertex group")
    points = []
    for vertex in mesh.data.vertices:
        if any(item.group == group.index and item.weight > 0.05 for item in vertex.groups):
            points.append(mesh.matrix_world @ vertex.co)
    if not points:
        raise RuntimeError("CC_Base_Head vertex group has no weighted vertices")
    return points


def preview_material(source: bpy.types.Material | None, role: str) -> bpy.types.Material:
    name = source.name if source is not None else role
    material = source.copy() if source is not None else bpy.data.materials.new(name)
    material.name = "AnimeEyePreview_" + name
    if role == "eyelash":
        material.diffuse_color = (0.015, 0.008, 0.012, 1.0)
    elif role == "eyes":
        material.diffuse_color = (0.015, 0.28, 0.12, 1.0)
    else:
        material.diffuse_color = (0.92, 0.92, 0.92, 1.0)
    return material


def solid_material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    return material


def ellipse_points(center_x: float, center_z: float, radius_x: float, radius_z: float, samples: int = 24) -> list[tuple[float, float]]:
    import math

    return [
        (
            center_x + radius_x * math.cos(2.0 * math.pi * index / samples),
            center_z + radius_z * math.sin(2.0 * math.pi * index / samples),
        )
        for index in range(samples)
    ]


def extruded_polygon(
    name: str,
    points_xz: list[tuple[float, float]],
    y_front: float,
    thickness: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
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


def add_pupil_and_highlight(iris: bpy.types.Object, side: str) -> list[bpy.types.Object]:
    points = [iris.matrix_world @ Vector(vertex.co) for vertex in iris.data.vertices]
    low = Vector((min(point[i] for point in points) for i in range(3)))
    high = Vector((max(point[i] for point in points) for i in range(3)))
    center = (low + high) * 0.5
    width = high.x - low.x
    height = high.z - low.z
    pupil_material = solid_material("AnimeEyePreview_Pupil", (0.005, 0.002, 0.008, 1.0))
    highlight_material = solid_material("AnimeEyePreview_Highlight", (1.0, 1.0, 1.0, 1.0))
    pupil = extruded_polygon(
        f"OpenGameArtEye_Pupil_{side}",
        ellipse_points(center.x, center.z - height * 0.015, width * 0.20, height * 0.31),
        low.y - 0.018,
        0.014,
        pupil_material,
    )
    sign = -1.0 if side == "L" else 1.0
    highlight = extruded_polygon(
        f"OpenGameArtEye_Highlight_{side}",
        ellipse_points(center.x - sign * width * 0.20, center.z + height * 0.20, width * 0.065, height * 0.11, 16),
        low.y - 0.035,
        0.010,
        highlight_material,
    )
    return [pupil, highlight]


def evaluated_mesh(obj: bpy.types.Object) -> tuple[bpy.types.Object, bpy.types.Mesh]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    return evaluated, evaluated.to_mesh()


def build_feature(
    source: bpy.types.Object,
    name: str,
    transform_point,
    material_filter: str | None = None,
) -> tuple[bpy.types.Object, list[Vector]]:
    evaluated, source_mesh = evaluated_mesh(source)
    used_vertices: dict[int, int] = {}
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    material_roles: list[str] = []
    source_points: list[Vector] = []
    try:
        for polygon in source_mesh.polygons:
            source_material = source.data.materials[polygon.material_index] if polygon.material_index < len(source.data.materials) else None
            role = source_material.name if source_material is not None else "default"
            if material_filter is not None and role != material_filter:
                continue
            local_face: list[int] = []
            for vertex_index in polygon.vertices:
                if vertex_index not in used_vertices:
                    point = evaluated.matrix_world @ source_mesh.vertices[vertex_index].co
                    source_points.append(point)
                    used_vertices[vertex_index] = len(vertices)
                    vertices.append(tuple(transform_point(point)))
                local_face.append(used_vertices[vertex_index])
            faces.append(tuple(local_face))
            material_roles.append(role)
    finally:
        evaluated.to_mesh_clear()
    if not faces:
        raise RuntimeError(f"source feature is empty: {source.name} filter={material_filter}")
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    roles = sorted(set(material_roles))
    role_to_index: dict[str, int] = {}
    for role in roles:
        role_to_index[role] = len(mesh.materials)
        source_material = source.data.materials[next((index for index, item in enumerate(source.data.materials) if item is not None and item.name == role), 0)] if source.data.materials else None
        mesh.materials.append(preview_material(source_material, role))
    for polygon, role in zip(mesh.polygons, material_roles):
        polygon.material_index = role_to_index[role]
        polygon.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj["source_model"] = "OpenGameArt Generic Anime Face"
    obj["source_license"] = "CC0"
    return obj, source_points


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
    line_style = line_set.linestyle or bpy.data.linestyles.new("OpenGameArtAnimeEyeOutline")
    line_set.linestyle = line_style
    line_style.color = (0.04, 0.03, 0.07)
    line_style.thickness = 1.7


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
    head_points = actor_head_points(actor_mesh)
    head_low = Vector((min(point[i] for point in head_points) for i in range(3)))
    head_high = Vector((max(point[i] for point in head_points) for i in range(3)))
    head_width = head_high.x - head_low.x
    target_center = Vector((0.0, head_low.y + options.front_surface_bias, head_low.z + (head_high.z - head_low.z) * options.eye_z_ratio))

    with bpy.data.libraries.load(str(options.source.resolve()), link=False) as (data_from, data_to):
        data_to.objects = list(data_from.objects)
    for loaded in data_to.objects:
        if loaded is not None and loaded.name not in bpy.context.collection.objects:
            bpy.context.collection.objects.link(loaded)
    cornea = bpy.data.objects.get("H.cornea")
    left_iris = bpy.data.objects.get("H.face.l.iris")
    right_iris = bpy.data.objects.get("H.face.r.iris")
    face = bpy.data.objects.get("H.face")
    if not all((cornea, left_iris, right_iris, face)):
        raise RuntimeError("OpenGameArt source is missing expected eye objects")

    source_world_points: list[Vector] = []
    for source in (cornea, left_iris, right_iris):
        evaluated, source_mesh = evaluated_mesh(source)
        try:
            source_world_points.extend(evaluated.matrix_world @ vertex.co for vertex in source_mesh.vertices)
        finally:
            evaluated.to_mesh_clear()
    eye_low = Vector((min(point[i] for point in source_world_points) for i in range(3)))
    eye_high = Vector((max(point[i] for point in source_world_points) for i in range(3)))
    source_center = Vector(((eye_low.x + eye_high.x) * 0.5, 0.0, (eye_low.z + eye_high.z) * 0.5))
    source_front_y = eye_low.y
    target_pair_width = head_width * 0.71 * options.scale_factor
    source_pair_width = eye_high.x - eye_low.x
    target_scale = target_pair_width / source_pair_width

    def transform_point(point: Vector) -> Vector:
        return Vector(
            (
                target_center.x + (point.x - source_center.x) * target_scale,
                target_center.y + (point.y - source_front_y) * target_scale * options.depth_scale,
                target_center.z + (point.z - source_center.z) * target_scale,
            )
        )

    generated: list[bpy.types.Object] = []
    for source, name, side in (
        (cornea, "OpenGameArtEye_Cornea", None),
        (left_iris, "OpenGameArtEye_Iris_L", "L"),
        (right_iris, "OpenGameArtEye_Iris_R", "R"),
    ):
        feature, _ = build_feature(source, name, transform_point)
        generated.append(feature)
        if side is not None:
            generated.extend(add_pupil_and_highlight(feature, side))
    lashes, _ = build_feature(face, "OpenGameArtEye_Eyelash", transform_point, material_filter="eyelash")
    generated.append(lashes)

    for source in (cornea, left_iris, right_iris, face):
        source.hide_render = True
    actor_low, actor_high = bounds(actor_mesh)
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
        "schema": "assetslab_opengameart_anime_eyes_on_accurig_v1",
        "source_url": SOURCE_URL,
        "source_blend": str(options.source.resolve()),
        "source_license": "CC0",
        "target_fbx": str(options.fbx.resolve()),
        "target_bone": "CC_Base_Head",
        "eye_z_ratio": options.eye_z_ratio,
        "front_surface_bias": options.front_surface_bias,
        "depth_scale": options.depth_scale,
        "scale_factor": options.scale_factor,
        "source_pair_width": source_pair_width,
        "target_pair_width": target_pair_width,
        "target_scale": target_scale,
        "features": [obj.name for obj in generated],
        "directions": list(camera_specs),
        "status": "external_candidate_static_review_only",
    }
    (output_dir / "attachment_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"OPENGAMEART_ANIME_EYES_ON_ACCURIG_PASS scale={target_scale:.4f} output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
