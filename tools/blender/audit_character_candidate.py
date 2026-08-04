"""Audit and render a complete 3D character candidate for the current anchor."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


SUPPORTED_EXTENSIONS = {".blend", ".fbx", ".glb", ".gltf", ".obj"}


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--resolution", type=int, default=256)
    return parser.parse_args(argv)


def load_source(source: Path) -> None:
    source = source.resolve()
    if not source.is_file():
        raise SystemExit(f"CHARACTER_CANDIDATE_AUDIT_FAIL: source not found: {source}")
    if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise SystemExit(f"CHARACTER_CANDIDATE_AUDIT_FAIL: unsupported source: {source.suffix}")
    if source.suffix.lower() == ".blend":
        bpy.ops.wm.open_mainfile(filepath=str(source))
        return
    if source.suffix.lower() == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(source), automatic_bone_orientation=False)
        return
    if source.suffix.lower() in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(source))
        return
    bpy.ops.wm.obj_import(filepath=str(source))


def world_bounds(meshes: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    low = Vector((float("inf"), float("inf"), float("inf")))
    high = Vector((float("-inf"), float("-inf"), float("-inf")))
    for obj in meshes:
        for corner in obj.bound_box:
            point = obj.matrix_world @ Vector(corner)
            low.x, low.y, low.z = min(low.x, point.x), min(low.y, point.y), min(low.z, point.z)
            high.x, high.y, high.z = max(high.x, point.x), max(high.y, point.y), max(high.z, point.z)
    if not meshes:
        raise SystemExit("CHARACTER_CANDIDATE_AUDIT_FAIL: no mesh object")
    return low, high


def object_record(obj: bpy.types.Object) -> dict:
    return {
        "name": obj.name,
        "type": obj.type,
        "vertices": len(obj.data.vertices) if obj.type == "MESH" else None,
        "polygons": len(obj.data.polygons) if obj.type == "MESH" else None,
        "materials": [slot.material.name for slot in obj.material_slots if slot.material],
        "vertex_groups": len(obj.vertex_groups) if obj.type == "MESH" else None,
        "modifiers": [modifier.type for modifier in obj.modifiers],
        "dimensions": [round(value, 4) for value in obj.dimensions],
        "location": [round(value, 4) for value in obj.matrix_world.translation],
    }


def render_static(output: Path, low: Vector, high: Vector, direction: str, resolution: int) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"

    target = (low + high) * 0.5
    height = max(high.z - low.z, 0.1)
    camera_data = bpy.data.cameras.new(f"CharacterCandidateAuditCamera_{direction}")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = height * 1.25
    camera_data.clip_start = 0.01
    camera_data.clip_end = max(1000.0, height * 20.0)
    camera = bpy.data.objects.new(f"CharacterCandidateAuditCamera_{direction}", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    distance = max(height * 4.0, 12.0)
    if direction == "front":
        camera.location = target + Vector((0.0, -distance, 0.0))
    elif direction == "back":
        camera.location = target + Vector((0.0, distance, 0.0))
    elif direction == "left":
        camera.location = target + Vector((-distance, 0.0, 0.0))
    else:
        camera.location = target + Vector((distance, 0.0, 0.0))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    output.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)


def main() -> int:
    options = parse_args()
    source = options.source.resolve()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    load_source(source)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    low, high = world_bounds(meshes)
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    report = {
        "schema": "assetslab_character_candidate_audit_v1",
        "source": str(source),
        "objects": [object_record(obj) for obj in bpy.context.scene.objects if obj.type in {"MESH", "ARMATURE"}],
        "mesh_count": len(meshes),
        "armature_count": sum(obj.type == "ARMATURE" for obj in bpy.context.scene.objects),
        "action_count": len(bpy.data.actions),
        "bounds_min": [round(value, 4) for value in low],
        "bounds_max": [round(value, 4) for value in high],
        "dimensions": [round(value, 4) for value in (high - low)],
        "production_ready": False,
        "decision": "front_anchor_review_required",
    }
    (output / "candidate_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for direction in ("front", "right", "back", "left"):
        render_static(output / f"candidate_static_{direction}.png", low, high, direction, options.resolution)
    print(
        "CHARACTER_CANDIDATE_AUDIT_PASS meshes=%d armatures=%d actions=%d output=%s"
        % (report["mesh_count"], report["armature_count"], report["action_count"], output)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

