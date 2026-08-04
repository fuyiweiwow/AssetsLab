"""Rebuild the primary leg weights for an attached chibi AccuRIG actor.

The source asset can retain only twist-bone assignments after the chibi mesh
conversion.  That makes thigh rotations visually inert in side-view walks.
This diagnostic tool preserves all non-leg bindings and attachments while
assigning lower-body vertices to the thigh, calf, and foot chains.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-blend", required=True, type=Path)
    parser.add_argument("--output-blend", required=True, type=Path)
    parser.add_argument("--leg-z-max", type=float, default=62.0)
    parser.add_argument("--center-exclusion", type=float, default=8.0)
    parser.add_argument("--knee-blend", type=float, default=4.0)
    parser.add_argument("--ankle-blend", type=float, default=3.0)
    return parser.parse_args(argv)


def remove_vertex_groups(mesh: bpy.types.Object, vertex_index: int) -> None:
    for assignment in list(mesh.data.vertices[vertex_index].groups):
        mesh.vertex_groups[assignment.group].remove([vertex_index])


def add_weight(group: bpy.types.VertexGroup, vertex_index: int, weight: float) -> None:
    if weight > 0.0001:
        group.add([vertex_index], weight, "REPLACE")


def main() -> int:
    options = cli_args()
    if options.knee_blend <= 0.0 or options.ankle_blend <= 0.0:
        raise RuntimeError("blend widths must be positive")
    bpy.ops.wm.open_mainfile(filepath=str(options.input_blend.resolve()))
    mesh = next(obj for obj in bpy.data.objects if obj.type == "MESH" and obj.name.startswith("ChibiBase"))
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")

    anchors: dict[str, tuple[float, float, float]] = {}
    groups: dict[str, bpy.types.VertexGroup] = {}
    for side in ("L", "R"):
        thigh = armature.data.bones[f"CC_Base_{side}_Thigh"]
        foot = armature.data.bones[f"CC_Base_{side}_Foot"]
        hip_z = thigh.head_local.z
        knee_z = thigh.head_local.lerp(foot.head_local, 0.5).z
        ankle_z = foot.head_local.z
        anchors[side] = (hip_z, knee_z, ankle_z)
        for part in ("Thigh", "Calf", "Foot"):
            name = f"CC_Base_{side}_{part}"
            groups[name] = mesh.vertex_groups.get(name) or mesh.vertex_groups.new(name=name)

    assigned = {"L": 0, "R": 0}
    for vertex in mesh.data.vertices:
        point = vertex.co
        if point.z > options.leg_z_max or abs(point.x) < options.center_exclusion:
            continue
        side = "L" if point.x > 0.0 else "R"
        _, knee_z, ankle_z = anchors[side]
        remove_vertex_groups(mesh, vertex.index)
        thigh_group = groups[f"CC_Base_{side}_Thigh"]
        calf_group = groups[f"CC_Base_{side}_Calf"]
        foot_group = groups[f"CC_Base_{side}_Foot"]

        if point.z >= knee_z + options.knee_blend:
            add_weight(thigh_group, vertex.index, 1.0)
        elif point.z >= knee_z - options.knee_blend:
            thigh_weight = (point.z - (knee_z - options.knee_blend)) / (2.0 * options.knee_blend)
            add_weight(thigh_group, vertex.index, thigh_weight)
            add_weight(calf_group, vertex.index, 1.0 - thigh_weight)
        elif point.z >= ankle_z + options.ankle_blend:
            add_weight(calf_group, vertex.index, 1.0)
        elif point.z >= ankle_z - options.ankle_blend:
            calf_weight = (point.z - (ankle_z - options.ankle_blend)) / (2.0 * options.ankle_blend)
            add_weight(calf_group, vertex.index, calf_weight)
            add_weight(foot_group, vertex.index, 1.0 - calf_weight)
        else:
            add_weight(foot_group, vertex.index, 1.0)
        assigned[side] += 1

    mesh.data.update()
    bpy.context.view_layer.update()
    options.output_blend.resolve().parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.output_blend.resolve()))
    print(f"CHIBI_LEG_REWEIGHT_PASS assigned={assigned} anchors={anchors} output={options.output_blend.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
