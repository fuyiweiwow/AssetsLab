"""Report connected vertex components in the source chibi mesh."""

from __future__ import annotations

import bpy


def main() -> int:
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    if not meshes:
        raise SystemExit("no mesh objects")
    for mesh in meshes:
        adjacency = [set() for _ in mesh.data.vertices]
        for edge in mesh.data.edges:
            left, right = edge.vertices
            adjacency[left].add(right)
            adjacency[right].add(left)
        unseen = set(range(len(adjacency)))
        components = []
        while unseen:
            seed = unseen.pop()
            stack = [seed]
            component = [seed]
            while stack:
                current = stack.pop()
                for neighbor in adjacency[current]:
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        stack.append(neighbor)
                        component.append(neighbor)
            points = [mesh.data.vertices[index].co for index in component]
            components.append({
                "vertices": len(component),
                "min": [round(min(point[i] for point in points), 4) for i in range(3)],
                "max": [round(max(point[i] for point in points), 4) for i in range(3)],
                "center": [round(sum(point[i] for point in points) / len(points), 4) for i in range(3)],
            })
        components.sort(key=lambda item: item["vertices"], reverse=True)
        print("MESH_COMPONENT_AUDIT_BEGIN")
        print("mesh=%s vertices=%d polygons=%d components=%d" % (mesh.name, len(mesh.data.vertices), len(mesh.data.polygons), len(components)))
        for index, component in enumerate(components):
            print("component_%02d=%s" % (index, component))
        print("MESH_COMPONENT_AUDIT_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
