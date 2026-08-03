"""Retarget a Mixamo-style FBX action to the prepared AccuRIG actor.

The source skeleton is imported temporarily. Copy Rotation constraints are
baked frame-by-frame onto the target actor, so the final blend contains only
the actor, its existing head features, and a regular action on ``Armature``.
The standard ``mixamorig:`` prefix is optional.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


MIXAMO_TO_CC_BASE = {
    "Hips": "CC_Base_Hip",
    "Spine": "CC_Base_Waist",
    "Spine1": "CC_Base_Spine01",
    "Spine2": "CC_Base_Spine02",
    "Neck": "CC_Base_NeckTwist01",
    "Head": "CC_Base_Head",
    "LeftShoulder": "CC_Base_L_Clavicle",
    "LeftArm": "CC_Base_L_Upperarm",
    "LeftForeArm": "CC_Base_L_Forearm",
    "LeftHand": "CC_Base_L_Hand",
    "RightShoulder": "CC_Base_R_Clavicle",
    "RightArm": "CC_Base_R_Upperarm",
    "RightForeArm": "CC_Base_R_Forearm",
    "RightHand": "CC_Base_R_Hand",
    "LeftUpLeg": "CC_Base_L_Thigh",
    "LeftLeg": "CC_Base_L_Calf",
    "LeftFoot": "CC_Base_L_Foot",
    "LeftToeBase": "CC_Base_L_ToeBase",
    "RightUpLeg": "CC_Base_R_Thigh",
    "RightLeg": "CC_Base_R_Calf",
    "RightFoot": "CC_Base_R_Foot",
    "RightToeBase": "CC_Base_R_ToeBase",
}


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor", required=True, type=Path)
    parser.add_argument("--mixamo-fbx", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target-armature", default="Armature")
    parser.add_argument("--fps", type=float, default=30.0)
    return parser.parse_args(argv)


def normalized(name: str) -> str:
    value = name.replace("mixamorig:", "").replace("mixamorig.", "")
    return value.split(".", 1)[0]


def find_imported_armature(before: set[str]) -> bpy.types.Object:
    found = [obj for obj in bpy.data.objects if obj.type == "ARMATURE" and obj.name not in before]
    if len(found) != 1:
        raise RuntimeError(f"expected one imported Mixamo armature, found {[obj.name for obj in found]}")
    return found[0]


def main() -> int:
    options = cli_args()
    actor_path = options.actor.resolve()
    source_path = options.mixamo_fbx.resolve()
    output_path = options.output.resolve()
    bpy.ops.wm.open_mainfile(filepath=str(actor_path))
    target = bpy.data.objects.get(options.target_armature)
    if target is None or target.type != "ARMATURE":
        raise RuntimeError(f"target armature not found: {options.target_armature}")

    before_objects = {obj.name for obj in bpy.data.objects}
    before_actions = {action.name for action in bpy.data.actions}
    bpy.ops.import_scene.fbx(filepath=str(source_path), use_anim=True)
    source = find_imported_armature(before_objects)
    source_action = source.animation_data.action if source.animation_data else None
    if source_action is None:
        imported = [action for action in bpy.data.actions if action.name not in before_actions]
        source_action = next((action for action in imported if action.frame_range[1] > action.frame_range[0]), None)
    if source_action is None:
        raise RuntimeError("Mixamo FBX has no usable animation action")

    source_bones = {normalized(bone.name): bone.name for bone in source.data.bones}
    mapping: dict[str, str] = {}
    for mixamo_name, target_name in MIXAMO_TO_CC_BASE.items():
        source_name = source_bones.get(mixamo_name)
        if source_name and target.pose.bones.get(target_name):
            mapping[target_name] = source_name
    if len(mapping) < 10:
        raise RuntimeError(f"only {len(mapping)} Mixamo bones mapped; expected at least 10")

    target.animation_data_clear()
    for target_name, source_name in mapping.items():
        target_bone = target.pose.bones[target_name]
        target_bone.rotation_mode = "QUATERNION"
        constraint = target_bone.constraints.new("COPY_ROTATION")
        constraint.name = "MixamoRetargetRotation"
        constraint.target = source
        constraint.subtarget = source_name
        constraint.target_space = "POSE"
        constraint.owner_space = "POSE"
        constraint.mix_mode = "REPLACE"
    hip_constraint = target.pose.bones["CC_Base_Hip"].constraints.new("COPY_LOCATION")
    hip_constraint.name = "MixamoRetargetHipLocation"
    hip_constraint.target = source
    hip_constraint.subtarget = source_bones.get("Hips", "")
    hip_constraint.target_space = "POSE"
    hip_constraint.owner_space = "POSE"

    start, end = (int(source_action.frame_range[0]), int(source_action.frame_range[1]))
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = start, end
    target_action = bpy.data.actions.new(f"Mixamo_{source_action.name}_on_{target.name}")
    target_action.use_fake_user = True
    target.animation_data_create()
    target.animation_data.action = target_action
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for target_name in mapping:
            bone = target.pose.bones[target_name]
            bone.keyframe_insert("rotation_quaternion", frame=frame, group=target_name)
        target.pose.bones["CC_Base_Hip"].keyframe_insert("location", frame=frame, group="CC_Base_Hip")

    for bone in target.pose.bones:
        for constraint in list(bone.constraints):
            if constraint.name.startswith("MixamoRetarget"):
                bone.constraints.remove(constraint)

    imported_objects = [obj for obj in bpy.data.objects if obj.name not in before_objects]
    for obj in imported_objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path))
    manifest = {
        "schema": "assetslab_mixamo_retarget_v1",
        "actor_source": str(actor_path),
        "mixamo_source": str(source_path),
        "source_action": source_action.name,
        "target_action": target_action.name,
        "frame_range": [start, end],
        "mapped_bones": mapping,
        "retarget_mode": "pose_space_copy_rotation_baked",
        "features": "existing eye, brow and ear head attachments preserved",
    }
    output_path.with_suffix(".json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        "MIXAMO_RETARGET_PASS "
        f"action={source_action.name} frames={start}-{end} mapped_bones={len(mapping)} output={output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
