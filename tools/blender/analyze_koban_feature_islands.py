"""Analyze connected face islands in the Koban single-mesh character."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from pathlib import Path

import bpy
from mathutils import Vector


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def component_bounds(obj: bpy.types.Object, face_indices: list[int]) -> dict[str, object]:
    mesh = obj.data
    vertex_indices = {vertex_index for face_index in face_indices for vertex_index in mesh.polygons[face_index].vertices}
    points = [obj.matrix_world @ mesh.vertices[index].co for index in vertex_indices]
    low = Vector((min(point[i] for point in points) for i in range(3)))
    high = Vector((max(point[i] for point in points) for i in range(3)))
    center = (low + high) * 0.5
    return {
        "face_count": len(face_indices),
        "vertex_count": len(vertex_indices),
        "bounds_min": list(low),
        "bounds_max": list(high),
        "center": list(center),
        "dimensions": list(high - low),
    }


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.blend.resolve()))
    obj = next((item for item in bpy.data.objects if item.type == "MESH"), None)
    if obj is None:
        raise RuntimeError("Koban mesh not found")
    mesh = obj.data

    vertex_to_faces: dict[int, list[int]] = defaultdict(list)
    for polygon in mesh.polygons:
        for vertex_index in polygon.vertices:
            vertex_to_faces[vertex_index].append(polygon.index)

    unvisited = {polygon.index for polygon in mesh.polygons}
    components: list[dict[str, object]] = []
    while unvisited:
        start = next(iter(unvisited))
        material_index = mesh.polygons[start].material_index
        queue = deque([start])
        unvisited.remove(start)
        faces: list[int] = []
        while queue:
            face_index = queue.popleft()
            faces.append(face_index)
            for vertex_index in mesh.polygons[face_index].vertices:
                for neighbor in vertex_to_faces[vertex_index]:
                    if neighbor in unvisited and mesh.polygons[neighbor].material_index == material_index:
                        unvisited.remove(neighbor)
                        queue.append(neighbor)
        item = component_bounds(obj, faces)
        item["material_index"] = material_index
        item["material_name"] = mesh.materials[material_index].name if material_index < len(mesh.materials) else str(material_index)
        item["face_indices"] = faces
        components.append(item)

    components.sort(key=lambda item: int(item["face_count"]), reverse=True)
    result = {
        "schema": "assetslab_koban_feature_islands_v1",
        "source_blend": str(options.blend.resolve()),
        "mesh": obj.name,
        "materials": [material.name for material in mesh.materials],
        "components": components,
    }
    output = options.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"KOBAN_FEATURE_ISLAND_ANALYSIS_PASS components={len(components)} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
