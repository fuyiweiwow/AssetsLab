"""Audit and render the downloaded chibi-base-mesh Blender candidate."""

from __future__ import annotations

import argparse
import io
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


def args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def resolve_blend(source: Path) -> tuple[Path, Path | None]:
    source = source.resolve()
    if source.suffix.lower() == ".blend":
        return source, None
    temp_root = Path(tempfile.mkdtemp(prefix="assetslab-chibi-audit-"))
    try:
        with zipfile.ZipFile(source) as outer:
            nested = next(
                (name for name in outer.namelist()
                 if name.lower().endswith("chibi base mesh_blender.zip")),
                None,
            )
            if nested is None:
                raise RuntimeError("outer archive has no nested chibi base mesh archive")
            inner_bytes = outer.read(nested)
        with zipfile.ZipFile(io.BytesIO(inner_bytes)) as inner:
            blend_name = next(
                (name for name in inner.namelist()
                 if name.lower().endswith("chibi base mesh.blend")),
                None,
            )
            if blend_name is None:
                raise RuntimeError("nested archive has no chibi base mesh.blend")
            blend_path = temp_root / "chibi base mesh.blend"
            blend_path.write_bytes(inner.read(blend_name))
        return blend_path, temp_root
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise


def components(mesh: bpy.types.Mesh) -> list[dict]:
    adjacency = [set() for _ in mesh.vertices]
    for edge in mesh.edges:
        left, right = edge.vertices
        adjacency[left].add(right)
        adjacency[right].add(left)
    unseen = set(range(len(adjacency)))
    result = []
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        group = [seed]
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
                    group.append(neighbor)
        points = [mesh.vertices[index].co for index in group]
        result.append({
            "vertices": len(group),
            "min": [round(min(point[i] for point in points), 4) for i in range(3)],
            "max": [round(max(point[i] for point in points), 4) for i in range(3)],
        })
    return sorted(result, key=lambda item: item["vertices"], reverse=True)


def load_source(source: Path) -> list[bpy.types.Object]:
    blend_path, temp_root = resolve_blend(source)
    try:
        with bpy.data.libraries.load(str(blend_path), link=False) as (from_data, to_data):
            to_data.objects = list(from_data.objects)
        loaded = []
        for obj in to_data.objects:
            if obj is None:
                continue
            bpy.context.collection.objects.link(obj)
            loaded.append(obj)
        return loaded
    finally:
        if temp_root is not None:
            shutil.rmtree(temp_root, ignore_errors=True)


def render_static(mesh: bpy.types.Object, output: Path, low: Vector, high: Vector, position: tuple[float, float, float]) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 256
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    camera_data = bpy.data.cameras.new("ChibiCandidateAuditCamera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = max(4.0, (high.z - low.z) * 1.25)
    camera = bpy.data.objects.new("ChibiCandidateAuditCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = position
    target = Vector((0.0, 0.0, (low.z + high.z) * 0.5))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    output.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)


def main() -> int:
    options = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    loaded = load_source(options.source)
    meshes = [obj for obj in loaded if obj.type == "MESH"]
    if not meshes:
        raise SystemExit("CHIBI_CANDIDATE_AUDIT_FAIL: no mesh object")
    primary = max(meshes, key=lambda obj: len(obj.data.vertices))
    bpy.context.view_layer.objects.active = primary
    primary.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    source_low = Vector((float("inf"), float("inf"), float("inf")))
    source_high = Vector((float("-inf"), float("-inf"), float("-inf")))
    for vertex in primary.data.vertices:
        source_low.x, source_low.y, source_low.z = min(source_low.x, vertex.co.x), min(source_low.y, vertex.co.y), min(source_low.z, vertex.co.z)
        source_high.x, source_high.y, source_high.z = max(source_high.x, vertex.co.x), max(source_high.y, vertex.co.y), max(source_high.z, vertex.co.z)
    center = Vector(((source_low.x + source_high.x) * 0.5, (source_low.y + source_high.y) * 0.5, source_low.z))
    primary.data.transform(Matrix.Translation(-center))
    primary.data.update()
    low = Vector((float("inf"), float("inf"), float("inf")))
    high = Vector((float("-inf"), float("-inf"), float("-inf")))
    for vertex in primary.data.vertices:
        low.x, low.y, low.z = min(low.x, vertex.co.x), min(low.y, vertex.co.y), min(low.z, vertex.co.z)
        high.x, high.y, high.z = max(high.x, vertex.co.x), max(high.y, vertex.co.y), max(high.z, vertex.co.z)
    report = {
        "schema": "assetslab_chibi_candidate_audit_v1",
        "source": str(options.source.resolve()),
        "objects": [
            {
                "name": obj.name,
                "type": obj.type,
                "location": [round(value, 4) for value in obj.location],
                "rotation_euler": [round(value, 4) for value in obj.rotation_euler],
                "scale": [round(value, 4) for value in obj.scale],
                "vertices": len(obj.data.vertices) if obj.type == "MESH" else None,
                "polygons": len(obj.data.polygons) if obj.type == "MESH" else None,
                "materials": [slot.material.name for slot in obj.material_slots if slot.material],
                "vertex_groups": len(obj.vertex_groups) if obj.type == "MESH" else None,
                "modifiers": [modifier.type for modifier in obj.modifiers],
                "dimensions": [round(value, 4) for value in obj.dimensions],
            }
            for obj in loaded
        ],
        "primary_mesh": {
            "name": primary.name,
            "bounds_min": [round(value, 4) for value in low],
            "bounds_max": [round(value, 4) for value in high],
            "dimensions": [round(value, 4) for value in (high - low)],
            "connected_components": components(primary.data),
        },
        "armature_count": sum(obj.type == "ARMATURE" for obj in loaded),
        "action_count": len(bpy.data.actions),
        "production_ready": False,
        "decision": "static_style_candidate_requires_project_specific_rig_or_pose_transfer",
    }
    options.output.mkdir(parents=True, exist_ok=True)
    (options.output / "candidate_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    target_z = (low.z + high.z) * 0.5
    render_static(primary, options.output / "candidate_static_y_negative.png", low, high, (0.0, -12.0, target_z))
    render_static(primary, options.output / "candidate_static_x_negative.png", low, high, (-12.0, 0.0, target_z))
    render_static(primary, options.output / "candidate_static_source_camera_axis.png", low, high, (9.9052, -8.2506, 5.7946))
    print("CHIBI_CANDIDATE_AUDIT_PASS mesh=%s vertices=%d polygons=%d armatures=%d actions=%d output=%s" % (
        primary.name, len(primary.data.vertices), len(primary.data.polygons), report["armature_count"], report["action_count"], options.output
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
