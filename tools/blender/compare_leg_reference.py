"""Compare normalized leg-joint placement between two humanoid FBX files."""
from __future__ import annotations

import argparse
import sys

import bpy
from mathutils import Vector


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-fbx", required=True)
    parser.add_argument("--reference-fbx", required=True)
    return parser.parse_args(argv)


def distance_ratio(points: tuple[Vector, Vector, Vector]) -> tuple[float, float, float]:
    hip, knee, ankle = points
    upper = (knee - hip).length
    lower = (ankle - knee).length
    total = upper + lower
    return upper, lower, upper / total if total else 0.0


def import_one(path: str):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path, use_anim=False)
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    return armature


def main() -> int:
    options = cli_args()

    target = import_one(options.target_fbx)
    target_points = (
        target.data.bones["CC_Base_L_Thigh"].head_local,
        target.data.bones["CC_Base_L_Calf"].head_local,
        target.data.bones["CC_Base_L_Foot"].head_local,
    )
    target_result = distance_ratio(target_points)

    reference = import_one(options.reference_fbx)
    reference_points = (
        reference.data.bones["Leg.L"].head_local,
        reference.data.bones["Leg.L"].tail_local,
        reference.data.bones["Leg.L_end"].tail_local,
    )
    reference_result = distance_ratio(reference_points)

    print("LEG_REFERENCE_COMPARISON_BEGIN")
    print(f"target={options.target_fbx}")
    print(f"target_hip_to_knee={target_result[0]:.4f}")
    print(f"target_knee_to_ankle={target_result[1]:.4f}")
    print(f"target_knee_ratio_from_hip={target_result[2]:.4f}")
    print(f"reference={options.reference_fbx}")
    print(f"reference_hip_to_knee={reference_result[0]:.4f}")
    print(f"reference_knee_to_ankle={reference_result[1]:.4f}")
    print(f"reference_knee_ratio_from_hip={reference_result[2]:.4f}")
    print("LEG_REFERENCE_COMPARISON_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
