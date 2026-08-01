"""Inspect source mesh connectivity and symmetry for the chibi archive."""

from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_original_chibi_actor_test as binding  # noqa: E402


def main() -> int:
    args = sys.argv[sys.argv.index("--") + 1:]
    source = Path(args[0])
    center_source = "--raw" not in args
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh = binding.load_source_mesh(source, center_source=center_source)
    print("CENTER_SOURCE", center_source)
    print("OBJECT_TRANSFORM", tuple(mesh.location), tuple(mesh.matrix_world.translation))
    adjacency = [set() for _ in mesh.data.vertices]
    for polygon in mesh.data.polygons:
        for index in polygon.vertices:
            adjacency[index].update(other for other in polygon.vertices if other != index)
    seen: set[int] = set()
    components = []
    for index in range(len(adjacency)):
        if index in seen:
            continue
        queue = deque([index])
        seen.add(index)
        component = []
        while queue:
            current = queue.popleft()
            component.append(current)
            for other in adjacency[current]:
                if other not in seen:
                    seen.add(other)
                    queue.append(other)
        components.append(component)
    summary = []
    for component in sorted(components, key=len, reverse=True):
        xs = [mesh.data.vertices[index].co.x for index in component]
        zs = [mesh.data.vertices[index].co.z for index in component]
        summary.append({
            "vertices": len(component),
            "min_x": round(min(xs), 4),
            "max_x": round(max(xs), 4),
            "min_z": round(min(zs), 4),
            "max_z": round(max(zs), 4),
        })
    print("SOURCE_VERTEX_COUNT", len(mesh.data.vertices))
    print("SOURCE_POLYGON_COUNT", len(mesh.data.polygons))
    print("SOURCE_COMPONENT_COUNT", len(summary))
    print("SOURCE_COMPONENTS", summary)
    print("SOURCE_MODIFIERS", [(modifier.name, modifier.type) for modifier in mesh.modifiers])
    for low_z, high_z in ((0.0, 0.5), (0.5, 1.2), (1.2, 2.0), (2.0, 2.6), (2.6, 3.2)):
        vertices = [vertex.co for vertex in mesh.data.vertices if low_z <= vertex.co.z < high_z]
        print("SOURCE_Z_BAND", low_z, high_z, {
            "count": len(vertices),
            "min_x": round(min((vertex.x for vertex in vertices), default=0.0), 4),
            "max_x": round(max((vertex.x for vertex in vertices), default=0.0), 4),
            "positive": sum(vertex.x > 0.001 for vertex in vertices),
            "negative": sum(vertex.x < -0.001 for vertex in vertices),
        })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
