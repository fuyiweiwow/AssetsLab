"""Find connected face components in a Blender mesh, grouped by material."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path

import bpy
from mathutils import Vector


def args() -> argparse.Namespace:
    argv = __import__("sys").argv
    argv = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def bounds(obj: bpy.types.Object, face_indices: list[int]) -> dict[str, object]:
    mesh = obj.data
    vertices = {v for face in face_indices for v in mesh.polygons[face].vertices}
    points = [obj.matrix_world @ mesh.vertices[index].co for index in vertices]
    low = Vector((min(p[i] for p in points) for i in range(3)))
    high = Vector((max(p[i] for p in points) for i in range(3)))
    return {
        "face_count": len(face_indices),
        "vertex_count": len(vertices),
        "bounds_min": list(low),
        "bounds_max": list(high),
        "center": list((low + high) * 0.5),
        "dimensions": list(high - low),
        "face_indices": face_indices,
    }


def main() -> int:
    options = args()
    bpy.ops.wm.open_mainfile(filepath=str(options.blend.resolve()))
    objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    if not objects:
        raise RuntimeError("No mesh object found")

    result: dict[str, object] = {
        "schema": "assetslab_mesh_components_v1",
        "source_blend": str(options.blend.resolve()),
        "objects": [],
    }
    for obj in objects:
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
            item = bounds(obj, faces)
            item["material_index"] = material_index
            item["material_name"] = (
                mesh.materials[material_index].name if material_index < len(mesh.materials) else str(material_index)
            )
            components.append(item)
        components.sort(key=lambda item: int(item["face_count"]), reverse=True)
        result["objects"].append({
            "object": obj.name,
            "vertex_count": len(mesh.vertices),
            "face_count": len(mesh.polygons),
            "components": components,
        })

    output = options.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"MESH_COMPONENT_ANALYSIS_PASS objects={len(objects)} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
