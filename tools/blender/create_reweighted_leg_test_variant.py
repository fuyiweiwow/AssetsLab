"""Create a diagnostic variant with explicit thigh/calf/foot vertex weights."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-fbx", required=True, type=Path)
    parser.add_argument("--output-blend", required=True, type=Path)
    return parser.parse_args(argv)


def remove_vertex_groups(mesh: bpy.types.Object, vertex_index: int) -> None:
    vertex = mesh.data.vertices[vertex_index]
    for assignment in list(vertex.groups):
        mesh.vertex_groups[assignment.group].remove([vertex_index])


def add_weight(group: bpy.types.VertexGroup, vertex_index: int, weight: float) -> None:
    if weight > 0.0001:
        group.add([vertex_index], weight, "REPLACE")


def main() -> int:
    options = cli_args()
    options.output_fbx.parent.mkdir(parents=True, exist_ok=True)
    options.output_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(options.source), use_anim=False)
    mesh = next(obj for obj in bpy.data.objects if obj.type == "MESH")
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    armature.animation_data_clear()

    # Use the current rig's hip, midpoint knee, and ankle as geometric anchors.
    anchors = {}
    for side in ("L", "R"):
        hip = armature.data.bones[f"CC_Base_{side}_Thigh"].head_local
        ankle = armature.data.bones[f"CC_Base_{side}_Foot"].head_local
        knee = hip.lerp(ankle, 0.5)
        anchors[side] = (hip.z, knee.z, ankle.z)

    groups = {
        name: mesh.vertex_groups.get(name) or mesh.vertex_groups.new(name=name)
        for side in ("L", "R")
        for name in (
            f"CC_Base_{side}_Thigh",
            f"CC_Base_{side}_Calf",
            f"CC_Base_{side}_Foot",
        )
    }

    assigned = {"L": 0, "R": 0}
    for vertex in mesh.data.vertices:
        point = vertex.co
        # Leg geometry is below the hips and away from the center line.
        if point.z > 62.0 or abs(point.x) < 8.0:
            continue
        side = "L" if point.x > 0.0 else "R"
        hip_z, knee_z, ankle_z = anchors[side]
        remove_vertex_groups(mesh, vertex.index)
        thigh_group = groups[f"CC_Base_{side}_Thigh"]
        calf_group = groups[f"CC_Base_{side}_Calf"]
        foot_group = groups[f"CC_Base_{side}_Foot"]

        if point.z >= knee_z + 4.0:
            add_weight(thigh_group, vertex.index, 1.0)
        elif point.z >= knee_z - 4.0:
            factor = (point.z - (knee_z - 4.0)) / 8.0
            add_weight(thigh_group, vertex.index, factor)
            add_weight(calf_group, vertex.index, 1.0 - factor)
        elif point.z >= ankle_z + 4.0:
            add_weight(calf_group, vertex.index, 1.0)
        elif point.z >= ankle_z - 3.0:
            factor = (point.z - (ankle_z - 3.0)) / 7.0
            add_weight(calf_group, vertex.index, max(0.0, factor))
            add_weight(foot_group, vertex.index, 1.0 - max(0.0, factor))
        else:
            add_weight(foot_group, vertex.index, 1.0)
        assigned[side] += 1

    mesh.data.update()
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(options.output_blend))
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.fbx(
        filepath=str(options.output_fbx),
        use_selection=True,
        add_leaf_bones=False,
        bake_anim=False,
        object_types={"ARMATURE", "MESH"},
        armature_nodetype="NULL",
        mesh_smooth_type="FACE",
        use_mesh_modifiers=True,
    )
    print("REWEIGHTED_LEG_VARIANT_PASS")
    print(f"source={options.source}")
    print(f"output_fbx={options.output_fbx}")
    print(f"output_blend={options.output_blend}")
    print(f"assigned_vertices={assigned}")
    print(f"anchors={anchors}")
    print("REWEIGHTED_LEG_VARIANT_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
