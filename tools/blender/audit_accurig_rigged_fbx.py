"""Audit an AccuRIG-exported FBX and run isolated calf-bone deformation tests.

Usage:
    blender --background --python audit_accurig_rigged_fbx.py -- character.fbx
"""
from __future__ import annotations

import math
import sys

import bpy


def args() -> list[str]:
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def evaluated_points(mesh_obj: bpy.types.Object, depsgraph):
    evaluated = mesh_obj.evaluated_get(depsgraph)
    temp_mesh = evaluated.to_mesh()
    try:
        return [mesh_obj.matrix_world @ vertex.co for vertex in temp_mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def clear_pose(armature: bpy.types.Object) -> None:
    armature.animation_data_clear()
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "XYZ"
        pose_bone.location = (0.0, 0.0, 0.0)
        pose_bone.rotation_euler = (0.0, 0.0, 0.0)
        pose_bone.scale = (1.0, 1.0, 1.0)


def main() -> int:
    file_args = args()
    if not file_args:
        raise SystemExit("usage: audit_accurig_rigged_fbx.py -- character.fbx")

    filepath = file_args[0]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=filepath, use_anim=True)

    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    actions = list(bpy.data.actions)

    print("ACCURIG_FBX_AUDIT_BEGIN")
    print(f"source={filepath}")
    print(f"meshes={[(obj.name, len(obj.data.vertices), len(obj.vertex_groups)) for obj in meshes]}")
    print(f"armatures={[(obj.name, len(obj.data.bones)) for obj in armatures]}")
    print(f"actions={[(action.name, tuple(action.frame_range), len(action.fcurves)) for action in actions]}")

    if len(meshes) != 1 or len(armatures) != 1:
        print("status=FAIL expected_one_mesh_and_one_armature")
        print("ACCURIG_FBX_AUDIT_END")
        return 2

    mesh_obj = meshes[0]
    armature = armatures[0]
    required_bones = [
        "CC_Base_L_Thigh",
        "CC_Base_L_Calf",
        "CC_Base_L_Foot",
        "CC_Base_R_Thigh",
        "CC_Base_R_Calf",
        "CC_Base_R_Foot",
    ]
    missing = [name for name in required_bones if name not in armature.data.bones]
    print(f"required_leg_bones_missing={missing}")
    if missing:
        print("status=FAIL_missing_leg_chain")
        print("ACCURIG_FBX_AUDIT_END")
        return 3

    for side in ("L", "R"):
        thigh = armature.data.bones[f"CC_Base_{side}_Thigh"]
        calf = armature.data.bones[f"CC_Base_{side}_Calf"]
        foot = armature.data.bones[f"CC_Base_{side}_Foot"]
        print(
            f"leg_chain_{side}="
            f"thigh_head={tuple(round(value, 3) for value in thigh.head_local)} "
            f"calf_head={tuple(round(value, 3) for value in calf.head_local)} "
            f"foot_head={tuple(round(value, 3) for value in foot.head_local)}"
        )

    depsgraph = bpy.context.evaluated_depsgraph_get()
    clear_pose(armature)
    depsgraph.update()
    base_points = evaluated_points(mesh_obj, depsgraph)

    for side in ("L", "R"):
        bone_name = f"CC_Base_{side}_Calf"
        pose_bone = armature.pose.bones[bone_name]
        for axis in range(3):
            pose_bone.rotation_euler = (0.0, 0.0, 0.0)
            pose_bone.rotation_euler[axis] = math.radians(15.0)
            depsgraph.update()
            current_points = evaluated_points(mesh_obj, depsgraph)
            displacements = [
                (current - original).length
                for current, original in zip(current_points, base_points)
            ]
            print(
                f"isolated_test bone={bone_name} axis={axis} angle_deg=15 "
                f"moved_vertices={sum(value > 0.001 for value in displacements)} "
                f"max_displacement={max(displacements):.3f} "
                f"mean_displacement={sum(displacements) / len(displacements):.3f}"
            )
        pose_bone.rotation_euler = (0.0, 0.0, 0.0)
        depsgraph.update()

    print("status=PASS_structure_and_isolated_leg_test")
    print("ACCURIG_FBX_AUDIT_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
