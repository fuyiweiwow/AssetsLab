"""Repair missing main AccuRIG deformation weights on the prepared actor.

The source actor contains useful weights on several ``*Twist`` groups but
omits the main upper-arm, forearm, thigh, calf, foot, and toe groups. This
tool preserves the actor as a new file, transfers arm twist weights to the
corresponding main arm bones, and redistributes each leg's calf-twist weight
to the nearest thigh/calf/foot/toe bone segment.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--armature", default="Armature")
    parser.add_argument("--mesh", default="ChibiBaseMesh_AccuRIG_InputMesh")
    return parser.parse_args(argv)


def ensure_group(mesh: bpy.types.Object, name: str) -> bpy.types.VertexGroup:
    return mesh.vertex_groups.get(name) or mesh.vertex_groups.new(name=name)


def vertex_weight(vertex: bpy.types.MeshVertex, group_index: int) -> float:
    return sum(weight.weight for weight in vertex.groups if weight.group == group_index)


def point_segment_distance(point: Vector, head: Vector, tail: Vector) -> float:
    segment = tail - head
    length_sq = segment.length_squared
    if length_sq <= 1e-12:
        return (point - head).length
    factor = max(0.0, min(1.0, (point - head).dot(segment) / length_sq))
    return (point - (head + factor * segment)).length


def leg_segment_name(point: Vector, armature: bpy.types.Object, side: str) -> str:
    names = [
        f"CC_Base_{side}_Thigh",
        f"CC_Base_{side}_Calf",
        f"CC_Base_{side}_Foot",
        f"CC_Base_{side}_ToeBase",
    ]
    distances = []
    for name in names:
        bone = armature.data.bones.get(name)
        if bone is None:
            continue
        distances.append(
            (point_segment_distance(point, bone.head_local, bone.tail_local), name)
        )
    if not distances:
        raise RuntimeError(f"missing leg bones for side {side}")
    return min(distances)[1]


def transfer_arm_twist_weights(mesh: bpy.types.Object) -> dict[str, int]:
    transfers = {
        "L_Upperarm": ["L_UpperarmTwist01", "L_UpperarmTwist02"],
        "R_Upperarm": ["R_UpperarmTwist01", "R_UpperarmTwist02"],
        "L_Forearm": ["L_ForearmTwist01", "L_ForearmTwist02"],
        "R_Forearm": ["R_ForearmTwist01", "R_ForearmTwist02"],
    }
    result: dict[str, int] = {}
    for suffix, source_suffixes in transfers.items():
        destination = ensure_group(mesh, f"CC_Base_{suffix}")
        sources = [mesh.vertex_groups.get(f"CC_Base_{name}") for name in source_suffixes]
        sources = [group for group in sources if group is not None]
        affected = 0
        for vertex in mesh.data.vertices:
            total = sum(vertex_weight(vertex, group.index) for group in sources)
            if total <= 1e-6:
                continue
            for group in sources:
                group.remove([vertex.index])
            destination.add([vertex.index], total, "REPLACE")
            affected += 1
        result[f"CC_Base_{suffix}"] = affected
    return result


def redistribute_leg_weights(mesh: bpy.types.Object, armature: bpy.types.Object) -> dict[str, int]:
    inverse = armature.matrix_world.inverted() @ mesh.matrix_world
    hip = mesh.vertex_groups.get("CC_Base_Hip")
    result: dict[str, int] = {}
    for side in ("L", "R"):
        source = mesh.vertex_groups.get(f"CC_Base_{side}_CalfTwist02")
        if source is None:
            result[f"CC_Base_{side}_CalfTwist02"] = 0
            continue
        destinations = {
            name: ensure_group(mesh, f"CC_Base_{side}_{name}")
            for name in ("Thigh", "Calf", "Foot", "ToeBase")
        }
        affected = 0
        for vertex in mesh.data.vertices:
            source_weight = vertex_weight(vertex, source.index)
            hip_weight = vertex_weight(vertex, hip.index) if hip is not None else 0.0
            weight = source_weight + hip_weight
            if source_weight <= 1e-6:
                continue
            point = inverse @ vertex.co
            destination_name = leg_segment_name(point, armature, side)
            source.remove([vertex.index])
            if hip is not None and hip_weight > 1e-6:
                hip.remove([vertex.index])
            destinations[destination_name.removeprefix(f"CC_Base_{side}_")].add(
                [vertex.index], weight, "REPLACE"
            )
            affected += 1
        result[f"CC_Base_{side}_CalfTwist02"] = affected
    return result


def main() -> int:
    options = cli_args()
    input_path = options.input.resolve()
    output_path = options.output.resolve()
    bpy.ops.wm.open_mainfile(filepath=str(input_path))
    armature = bpy.data.objects.get(options.armature)
    mesh = bpy.data.objects.get(options.mesh)
    if armature is None or armature.type != "ARMATURE":
        raise RuntimeError(f"armature not found: {options.armature}")
    if mesh is None or mesh.type != "MESH":
        raise RuntimeError(f"mesh not found: {options.mesh}")
    before = {group.name for group in mesh.vertex_groups}
    arm_result = transfer_arm_twist_weights(mesh)
    leg_result = redistribute_leg_weights(mesh, armature)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path))
    report = {
        "schema": "assetslab_accurig_weight_repair_v1",
        "input": str(input_path),
        "output": str(output_path),
        "armature": armature.name,
        "mesh": mesh.name,
        "groups_before": sorted(before),
        "groups_after": sorted(group.name for group in mesh.vertex_groups),
        "arm_twist_transfers": arm_result,
        "leg_twist_redistributions": leg_result,
        "method": "twist_to_main_arm_transfer_and_nearest_leg_bone_segment",
    }
    output_path.with_suffix(".json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        "ACCURIG_WEIGHT_REPAIR_PASS "
        f"mesh={mesh.name} groups={len(mesh.vertex_groups)} "
        f"arm={arm_result} legs={leg_result} output={output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
