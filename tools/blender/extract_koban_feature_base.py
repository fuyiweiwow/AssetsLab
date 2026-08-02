"""Extract a first Koban eye/brow/ear feature pack from its single mesh."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


EYE_MATERIALS = {"Material.010", "Material.012", "Material.014"}
BROW_MATERIAL = "Material.012"
SKIN_MATERIAL = "Material.015"


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    return parser.parse_args(argv)


def world_center(obj: bpy.types.Object, polygon: bpy.types.MeshPolygon) -> Vector:
    return obj.matrix_world @ polygon.center


def side_name(center_x: float) -> str:
    return "L" if center_x < 0.0 else "R"


def build_submesh(source: bpy.types.Object, name: str, face_indices: list[int]) -> bpy.types.Object:
    source_mesh = source.data
    used_vertices: dict[int, int] = {}
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    face_materials: list[int] = []
    face_smooth: list[bool] = []

    for face_index in face_indices:
        polygon = source_mesh.polygons[face_index]
        local_face: list[int] = []
        for vertex_index in polygon.vertices:
            if vertex_index not in used_vertices:
                used_vertices[vertex_index] = len(vertices)
                vertices.append(tuple(source_mesh.vertices[vertex_index].co))
            local_face.append(used_vertices[vertex_index])
        faces.append(tuple(local_face))
        face_materials.append(polygon.material_index)
        face_smooth.append(polygon.use_smooth)

    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    material_map: dict[int, int] = {}
    for material_index in sorted(set(face_materials)):
        material_map[material_index] = len(mesh.materials)
        mesh.materials.append(source_mesh.materials[material_index])
    for polygon, source_material_index, smooth in zip(mesh.polygons, face_materials, face_smooth):
        polygon.material_index = material_map[source_material_index]
        polygon.use_smooth = smooth

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.matrix_world = source.matrix_world.copy()
    obj["source_model"] = "Koban Chibi Base Mesh VRM export"
    obj["feature_pack_status"] = "base_extraction_review_only"
    return obj


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.blend.resolve()))
    source = next((obj for obj in bpy.data.objects if obj.type == "MESH"), None)
    armature = next((obj for obj in bpy.data.objects if obj.type == "ARMATURE"), None)
    if source is None or armature is None:
        raise RuntimeError("expected one Koban mesh and armature")
    mesh = source.data

    groups: dict[str, list[int]] = {
        "eye_L": [],
        "eye_R": [],
        "brow_L": [],
        "brow_R": [],
        "ear_L": [],
        "ear_R": [],
    }
    for polygon in mesh.polygons:
        center = world_center(source, polygon)
        absolute_x = abs(center.x)
        material_name = mesh.materials[polygon.material_index].name
        side = side_name(center.x)

        if material_name in EYE_MATERIALS and 0.25 < absolute_x < 0.60 and 3.12 < center.z < 3.62:
            groups[f"eye_{side}"] .append(polygon.index)
        elif material_name == BROW_MATERIAL and 0.25 < absolute_x < 0.65 and 3.64 < center.z < 3.83:
            groups[f"brow_{side}"] .append(polygon.index)
        elif material_name == SKIN_MATERIAL and 0.84 < absolute_x < 1.02 and 3.12 < center.z < 3.48:
            groups[f"ear_{side}"] .append(polygon.index)

    missing = [name for name, faces in groups.items() if not faces]
    if missing:
        raise RuntimeError(f"feature selection produced empty groups: {missing}")

    root = bpy.data.objects.new("KobanFeatureRoot_Base", None)
    root.empty_display_type = "CUBE"
    root.empty_display_size = 0.12
    bpy.context.collection.objects.link(root)
    root["source_mesh_matrix_world"] = [list(row) for row in source.matrix_world]
    head_bone = armature.data.bones.get("head.x")
    if head_bone is None:
        raise RuntimeError("Koban head.x bone not found")
    root.matrix_world.translation = armature.matrix_world @ head_bone.head_local
    root["feature_root_translation"] = list(root.matrix_world.translation)

    objects: dict[str, bpy.types.Object] = {}
    for group_name, face_indices in groups.items():
        obj = build_submesh(source, "KobanFeature_" + group_name, face_indices)
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix
        objects[group_name] = obj

    # Save only the extracted feature pack, not the external source character.
    for obj in list(bpy.data.objects):
        if obj == source or obj == armature:
            bpy.data.objects.remove(obj, do_unlink=True)

    output = options.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    manifest = {
        "schema": "assetslab_koban_feature_base_v1",
        "source_blend": str(options.blend.resolve()),
        "output_blend": str(output),
        "root": "KobanFeatureRoot_Base",
        "groups": {name: len(faces) for name, faces in groups.items()},
        "source_head_bone": "head.x",
        "intended_target_bone": "CC_Base_Head",
        "features": ["eye_L", "eye_R", "brow_L", "brow_R", "ear_L", "ear_R"],
        "status": "base_extraction_review_only",
    }
    manifest_path = options.manifest.resolve()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"KOBAN_FEATURE_BASE_EXTRACT_PASS groups={len(groups)} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
