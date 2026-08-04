"""Retarget arm swing trajectories without Blender IK constraints.

It scales the baked wrist trajectory in world X/Y around its temporal mean,
then analytically rebuilds the upperarm/forearm directions while retaining the
source elbow-bend side.  This keeps the original CC arm chain and avoids the
constraint-bake artefacts seen in prior experimental candidates.
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
    "L": ("CC_Base_L_Upperarm", "CC_Base_L_Forearm", "CC_Base_L_Hand"),
    "R": ("CC_Base_R_Upperarm", "CC_Base_R_Forearm", "CC_Base_R_Hand"),
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--lateral-scale", type=float, default=0.58, help="world X swing scale")
    parser.add_argument("--longitudinal-scale", type=float, default=1.30, help="world Y swing scale")
    parser.add_argument("--left-lateral-scale", type=float)
    parser.add_argument("--right-lateral-scale", type=float)
    parser.add_argument("--left-longitudinal-scale", type=float)
    parser.add_argument("--right-longitudinal-scale", type=float)
    return parser.parse_args(argv)


def world_point(armature: bpy.types.Object, point: Vector) -> Vector:
    return armature.matrix_world @ point


def average(points: list[Vector]) -> Vector:
    return sum(points, Vector((0.0, 0.0, 0.0))) / len(points)


def solve_elbow(shoulder: Vector, original_elbow: Vector, wrist: Vector, upper_length: float, forearm_length: float) -> Vector:
    line = wrist - shoulder
    distance = max(line.length, 1e-6)
    direction = line / distance
    reach_min = abs(upper_length - forearm_length) + 1e-5
    reach_max = upper_length + forearm_length - 1e-5
    clamped_distance = max(reach_min, min(reach_max, distance))
    if clamped_distance != distance:
        wrist = shoulder + direction * clamped_distance
        line = wrist - shoulder
        distance = clamped_distance
    along = (upper_length * upper_length - forearm_length * forearm_length + distance * distance) / (2.0 * distance)
    height = math.sqrt(max(upper_length * upper_length - along * along, 0.0))
    projected = shoulder + direction * along
    bend = original_elbow - projected
    bend -= direction * bend.dot(direction)
    if bend.length < 1e-6:
        bend = Vector((0.0, 0.0, 1.0)).cross(direction)
    return projected + bend.normalized() * height


def corrected_world_matrix(original: Matrix, original_head: Vector, original_tail: Vector, new_head: Vector, new_tail: Vector) -> Matrix:
    source_vector = original_tail - original_head
    target_vector = new_tail - new_head
    rotation = source_vector.rotation_difference(target_vector).to_matrix().to_4x4()
    corrected = rotation @ original
    corrected.translation = new_head
    return corrected


def main() -> int:
    options = parse_args()
    if options.lateral_scale <= 0 or options.longitudinal_scale <= 0:
        raise ValueError("trajectory scales must be positive")
    bpy.ops.wm.open_mainfile(filepath=str(options.blend.resolve()))
    armature = bpy.data.objects.get("Armature")
    if armature is None or armature.type != "ARMATURE" or not armature.animation_data or not armature.animation_data.action:
        raise RuntimeError("animated actor Armature not found")
    action = armature.animation_data.action
    start, end = (int(action.frame_range[0]), int(action.frame_range[1]))
    scene = bpy.context.scene
    samples: dict[str, list[dict[str, object]]] = {side: [] for side in SIDES}
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for side, (upper_name, fore_name, hand_name) in SIDES.items():
            upper = armature.pose.bones[upper_name]
            fore = armature.pose.bones[fore_name]
            hand = armature.pose.bones[hand_name]
            shoulder = world_point(armature, upper.head)
            elbow = world_point(armature, fore.head)
            wrist = world_point(armature, hand.head)
            samples[side].append(
                {
                    "frame": frame,
                    "shoulder": shoulder.copy(),
                    "elbow": elbow.copy(),
                    "wrist": wrist.copy(),
                    "upper_matrix": armature.matrix_world @ upper.matrix.copy(),
                    "fore_matrix": armature.matrix_world @ fore.matrix.copy(),
                    "upper_tail": world_point(armature, upper.tail),
                    "fore_tail": world_point(armature, fore.tail),
                }
            )
    centers = {side: average([item["wrist"] for item in values]) for side, values in samples.items()}
    for side, (upper_name, fore_name, _hand_name) in SIDES.items():
        values = samples[side]
        upper_length = (values[0]["elbow"] - values[0]["shoulder"]).length
        forearm_length = (values[0]["wrist"] - values[0]["elbow"]).length
        lateral_scale = options.left_lateral_scale if side == "L" and options.left_lateral_scale is not None else options.right_lateral_scale if side == "R" and options.right_lateral_scale is not None else options.lateral_scale
        longitudinal_scale = options.left_longitudinal_scale if side == "L" and options.left_longitudinal_scale is not None else options.right_longitudinal_scale if side == "R" and options.right_longitudinal_scale is not None else options.longitudinal_scale
        for item in values:
            frame = item["frame"]
            center = centers[side]
            original_wrist = item["wrist"]
            target_wrist = center + Vector(
                (
                    (original_wrist.x - center.x) * lateral_scale,
                    (original_wrist.y - center.y) * longitudinal_scale,
                    original_wrist.z - center.z,
                )
            )
            shoulder = item["shoulder"]
            elbow = solve_elbow(shoulder, item["elbow"], target_wrist, upper_length, forearm_length)
            # If reach was clamped, keep the same final line direction at valid length.
            actual_wrist_direction = (target_wrist - shoulder).normalized()
            actual_distance = min(max((target_wrist - shoulder).length, abs(upper_length - forearm_length) + 1e-5), upper_length + forearm_length - 1e-5)
            wrist = shoulder + actual_wrist_direction * actual_distance
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            upper = armature.pose.bones[upper_name]
            fore = armature.pose.bones[fore_name]
            upper_world = corrected_world_matrix(item["upper_matrix"], shoulder, item["upper_tail"], shoulder, elbow)
            upper.matrix = armature.matrix_world.inverted() @ upper_world
            upper.rotation_mode = "QUATERNION"
            upper.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=upper_name)
            fore_world = corrected_world_matrix(item["fore_matrix"], item["elbow"], item["fore_tail"], elbow, wrist)
            fore.matrix = armature.matrix_world.inverted() @ fore_world
            fore.rotation_mode = "QUATERNION"
            fore.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=fore_name)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.output.resolve()))
    manifest = {
        "schema": "assetslab_analytic_arm_trajectory_candidate_v1",
        "source_blend": str(options.blend.resolve()),
        "frame_range": [start, end],
        "lateral_scale": options.lateral_scale,
        "longitudinal_scale": options.longitudinal_scale,
        "left_lateral_scale": options.left_lateral_scale,
        "right_lateral_scale": options.right_lateral_scale,
        "left_longitudinal_scale": options.left_longitudinal_scale,
        "right_longitudinal_scale": options.right_longitudinal_scale,
        "method": "two-bone analytic wrist trajectory retiming; no IK constraints or arm mirroring",
        "status": "WIP_candidate_for_visual_comparison",
    }
    options.output.with_suffix(".json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ANALYTIC_ARM_TRAJECTORY_PASS frames={start}-{end} output={options.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
