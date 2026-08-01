"""Audit leg vertex groups and isolated deformation for an AccuRIG FBX."""
from __future__ import annotations

import argparse
import math
import sys

import bpy


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--fbx", required=True)
    return parser.parse_args(argv)


def evaluated_points(mesh_obj: bpy.types.Object, depsgraph):
    evaluated = mesh_obj.evaluated_get(depsgraph)
    temp_mesh = evaluated.to_mesh()
    try:
        return [mesh_obj.matrix_world @ vertex.co for vertex in temp_mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def reset_pose(armature: bpy.types.Object) -> None:
    armature.animation_data_clear()
    for bone in armature.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.location = (0.0, 0.0, 0.0)
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)


def group_stats(mesh: bpy.types.Object, name: str) -> tuple[int, float]:
    group = mesh.vertex_groups.get(name)
    if group is None:
        return 0, 0.0
    total = 0.0
    count = 0
    for vertex in mesh.data.vertices:
        for assignment in vertex.groups:
            if assignment.group == group.index and assignment.weight > 0.001:
                count += 1
                total += assignment.weight
    return count, total


def main() -> int:
    options = cli_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=options.fbx, use_anim=False)
    mesh = next(obj for obj in bpy.data.objects if obj.type == "MESH")
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    depsgraph = bpy.context.evaluated_depsgraph_get()
    reset_pose(armature)
    depsgraph.update()
    base = evaluated_points(mesh, depsgraph)

    print("LEG_WEIGHT_AUDIT_BEGIN")
    print(f"source={options.fbx}")
    for side in ("L", "R"):
        for part in ("Thigh", "Calf", "Foot"):
            name = f"CC_Base_{side}_{part}"
            count, total = group_stats(mesh, name)
            print(f"weights bone={name} vertices={count} weight_sum={total:.3f}")

    for side in ("L", "R"):
        for part in ("Thigh", "Calf", "Foot"):
            name = f"CC_Base_{side}_{part}"
            if name not in armature.pose.bones:
                continue
            reset_pose(armature)
            armature.pose.bones[name].rotation_euler[0] = math.radians(15.0)
            depsgraph.update()
            current = evaluated_points(mesh, depsgraph)
            displacements = [(a - b).length for a, b in zip(current, base)]
            moved = [value for value in displacements if value > 0.001]
            print(
                f"deform bone={name} moved_vertices={len(moved)} "
                f"max_displacement={max(moved) if moved else 0.0:.4f} "
                f"mean_displacement={sum(moved) / len(moved) if moved else 0.0:.4f}"
            )

    print("LEG_WEIGHT_AUDIT_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
