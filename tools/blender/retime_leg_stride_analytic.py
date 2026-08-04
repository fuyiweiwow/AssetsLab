"""Reduce a baked walk's sagittal foot stride without changing foot height.

The tool retargets each ankle trajectory around its temporal mean in world Y,
then solves the thigh/calf chain analytically.  Foot orientation is restored
from the source frame after the new ankle position is applied, so this is a
stride/overlap experiment rather than another ankle-rotation tweak.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


SIDES = {
    "L": ("CC_Base_L_Thigh", "CC_Base_L_Calf", "CC_Base_L_Foot"),
    "R": ("CC_Base_R_Thigh", "CC_Base_R_Calf", "CC_Base_R_Foot"),
}


def args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--stride-scale", type=float, default=0.90, help="world-Y ankle stride scale around each foot mean")
    parser.add_argument("--rear-scale", type=float, help="optional scale only for the negative-Y rear half of the stride")
    return parser.parse_args(values)


def world(armature: bpy.types.Object, point: Vector) -> Vector:
    return armature.matrix_world @ point


def average(points: list[Vector]) -> Vector:
    return sum(points, Vector()) / len(points)


def solve_knee(hip: Vector, original_knee: Vector, ankle: Vector, thigh_len: float, calf_len: float) -> tuple[Vector, Vector]:
    line = ankle - hip
    distance = max(line.length, 1e-6)
    direction = line / distance
    minimum = abs(thigh_len - calf_len) + 1e-5
    maximum = thigh_len + calf_len - 1e-5
    distance = min(max(distance, minimum), maximum)
    ankle = hip + direction * distance
    along = (thigh_len * thigh_len - calf_len * calf_len + distance * distance) / (2.0 * distance)
    height = math.sqrt(max(thigh_len * thigh_len - along * along, 0.0))
    projected = hip + direction * along
    bend = original_knee - projected
    bend -= direction * bend.dot(direction)
    if bend.length < 1e-6:
        bend = Vector((1.0, 0.0, 0.0)).cross(direction)
    return projected + bend.normalized() * height, ankle


def reoriented_matrix(original: Matrix, old_head: Vector, old_tail: Vector, new_head: Vector, new_tail: Vector) -> Matrix:
    old_direction = old_tail - old_head
    new_direction = new_tail - new_head
    rotated = old_direction.rotation_difference(new_direction).to_matrix().to_4x4() @ original
    rotated.translation = new_head
    return rotated


def main() -> int:
    options = args()
    if not 0.65 <= options.stride_scale <= 1.0:
        raise ValueError("stride-scale must be within 0.65..1.0 for this conservative repair")
    if options.rear_scale is not None and not 0.50 <= options.rear_scale <= 1.0:
        raise ValueError("rear-scale must be within 0.50..1.0")
    bpy.ops.wm.open_mainfile(filepath=str(options.blend.resolve()))
    armature = bpy.data.objects.get("Armature")
    if armature is None or not armature.animation_data or not armature.animation_data.action:
        raise RuntimeError("animated actor Armature not found")
    scene = bpy.context.scene
    action = armature.animation_data.action
    start, end = int(action.frame_range[0]), int(action.frame_range[1])
    samples: dict[str, list[dict[str, object]]] = {side: [] for side in SIDES}
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for side, (thigh_name, calf_name, foot_name) in SIDES.items():
            thigh, calf, foot = (armature.pose.bones[name] for name in (thigh_name, calf_name, foot_name))
            samples[side].append(
                {
                    "frame": frame,
                    "hip": world(armature, thigh.head).copy(),
                    "knee": world(armature, calf.head).copy(),
                    "ankle": world(armature, foot.head).copy(),
                    "thigh_matrix": armature.matrix_world @ thigh.matrix.copy(),
                    "calf_matrix": armature.matrix_world @ calf.matrix.copy(),
                    "foot_matrix": armature.matrix_world @ foot.matrix.copy(),
                    "thigh_tail": world(armature, thigh.tail).copy(),
                    "calf_tail": world(armature, calf.tail).copy(),
                    "foot_tail": world(armature, foot.tail).copy(),
                }
            )
    means = {side: average([item["ankle"] for item in values]) for side, values in samples.items()}
    for side, (thigh_name, calf_name, foot_name) in SIDES.items():
        values = samples[side]
        thigh_len = (values[0]["knee"] - values[0]["hip"]).length
        calf_len = (values[0]["ankle"] - values[0]["knee"]).length
        for item in values:
            frame = item["frame"]
            original_ankle = item["ankle"]
            mean = means[side]
            y_delta = original_ankle.y - mean.y
            scale = options.rear_scale if options.rear_scale is not None and y_delta < 0.0 else options.stride_scale
            target_ankle = Vector((original_ankle.x, mean.y + y_delta * scale, original_ankle.z))
            knee, target_ankle = solve_knee(item["hip"], item["knee"], target_ankle, thigh_len, calf_len)
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            thigh = armature.pose.bones[thigh_name]
            calf = armature.pose.bones[calf_name]
            foot = armature.pose.bones[foot_name]
            thigh_world = reoriented_matrix(item["thigh_matrix"], item["hip"], item["thigh_tail"], item["hip"], knee)
            thigh.matrix = armature.matrix_world.inverted() @ thigh_world
            thigh.rotation_mode = "QUATERNION"
            thigh.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=thigh_name)
            calf_world = reoriented_matrix(item["calf_matrix"], item["knee"], item["calf_tail"], knee, target_ankle)
            calf.matrix = armature.matrix_world.inverted() @ calf_world
            calf.rotation_mode = "QUATERNION"
            calf.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=calf_name)
            old_foot_vector = item["foot_tail"] - item["ankle"]
            foot_world = reoriented_matrix(item["foot_matrix"], item["ankle"], item["foot_tail"], target_ankle, target_ankle + old_foot_vector)
            foot.matrix = armature.matrix_world.inverted() @ foot_world
            foot.rotation_mode = "QUATERNION"
            foot.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=foot_name)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.output.resolve()))
    options.output.with_suffix(".json").write_text(json.dumps({
        "schema": "assetslab_analytic_leg_stride_retime_v1",
        "source_blend": str(options.blend.resolve()),
        "frame_range": [start, end],
        "stride_scale": options.stride_scale,
        "rear_scale": options.rear_scale,
        "policy": "world-Y ankle stride scaled; hip and ankle height preserved; source foot orientation restored",
        "status": "WIP_candidate_for_side_view_comparison",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"LEG_STRIDE_RETIME_PASS frames={start}-{end} output={options.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
