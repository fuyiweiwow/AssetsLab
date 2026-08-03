"""Bind an FBX armature action to the project's prepared actor.

The actor blend remains untouched. The motion FBX is imported only as a
temporary source; matching pose-bone F-curves are copied to the actor's
armature and the temporary imported objects are removed before saving.

This is intentionally name-based for the current AccuRIG test motion. A
future Mixamo file can use the same entry point after its bones are mapped to
the project's CC_Base names.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor", required=True, type=Path)
    parser.add_argument("--motion-fbx", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target-armature", default="Armature")
    return parser.parse_args(argv)


def action_bone_name(data_path: str) -> str | None:
    marker = 'pose.bones["'
    if marker not in data_path:
        return None
    return data_path.split(marker, 1)[1].split('"]', 1)[0]


def find_motion_armature(before: set[str]) -> bpy.types.Object:
    candidates = [
        obj for obj in bpy.data.objects
        if obj.type == "ARMATURE" and obj.name not in before
    ]
    if len(candidates) != 1:
        raise RuntimeError(f"expected one imported motion armature, found {[obj.name for obj in candidates]}")
    return candidates[0]


def copy_action(source_action: bpy.types.Action, target: bpy.types.Object) -> tuple[bpy.types.Action, int, set[str]]:
    target_action = bpy.data.actions.new(f"{source_action.name}_on_{target.name}")
    copied_curves = 0
    copied_bones: set[str] = set()
    quaternion_bones: set[str] = set()
    euler_bones: set[str] = set()
    for curve in source_action.fcurves:
        bone_name = action_bone_name(curve.data_path)
        if bone_name is None or target.pose.bones.get(bone_name) is None:
            continue
        if curve.data_path.endswith("rotation_quaternion"):
            quaternion_bones.add(bone_name)
        elif curve.data_path.endswith("rotation_euler"):
            euler_bones.add(bone_name)
        group = target_action.groups.get(bone_name) or target_action.groups.new(bone_name)
        copied = target_action.fcurves.new(
            curve.data_path,
            index=curve.array_index,
            action_group=group.name,
        )
        for key in curve.keyframe_points:
            point = copied.keyframe_points.insert(key.co.x, key.co.y, options={"FAST"})
            point.interpolation = key.interpolation
            point.handle_left_type = key.handle_left_type
            point.handle_right_type = key.handle_right_type
        copied.update()
        copied_curves += 1
        copied_bones.add(bone_name)
    if copied_curves == 0:
        bpy.data.actions.remove(target_action)
        raise RuntimeError("motion action has no pose-bone curves matching the target armature")
    # Blender evaluates quaternion F-curves only when the target pose bone is
    # in quaternion rotation mode. The imported AccuRIG/Mixamo-style FBX
    # actions commonly use quaternions while the prepared actor defaults to
    # XYZ Euler, which otherwise produces a silent 'copied but not moving'
    # failure.
    for bone_name in quaternion_bones:
        target.pose.bones[bone_name].rotation_mode = "QUATERNION"
    for bone_name in euler_bones - quaternion_bones:
        target.pose.bones[bone_name].rotation_mode = "XYZ"
    target_action.use_fake_user = True
    return target_action, copied_curves, copied_bones


def main() -> int:
    options = cli_args()
    actor_path = options.actor.resolve()
    motion_path = options.motion_fbx.resolve()
    output_path = options.output.resolve()
    bpy.ops.wm.open_mainfile(filepath=str(actor_path))
    target = bpy.data.objects.get(options.target_armature)
    if target is None or target.type != "ARMATURE":
        raise RuntimeError(f"target armature not found: {options.target_armature}")

    before_objects = set(obj.name for obj in bpy.data.objects)
    before_actions = set(action.name for action in bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=str(motion_path), use_anim=True)
    source = find_motion_armature(before_objects)
    source_action = source.animation_data.action if source.animation_data else None
    if source_action is None:
        imported_actions = [action for action in bpy.data.actions if action.name not in before_actions]
        source_action = next((action for action in imported_actions if action.frame_range[1] > action.frame_range[0]), None)
    if source_action is None:
        raise RuntimeError("imported motion FBX has no usable action")

    target_action, copied_curves, copied_bones = copy_action(source_action, target)
    target.animation_data_clear()
    target.animation_data_create()
    target.animation_data.action = target_action
    target.data.pose_position = "POSE"
    scene = bpy.context.scene
    scene.frame_start = int(source_action.frame_range[0])
    scene.frame_end = int(source_action.frame_range[1])

    imported_objects = [obj for obj in bpy.data.objects if obj.name not in before_objects]
    for obj in imported_objects:
        bpy.data.objects.remove(obj, do_unlink=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "assetslab_motion_binding_test_v1",
        "actor_source": str(actor_path),
        "motion_source": str(motion_path),
        "target_armature": target.name,
        "source_action": source_action.name,
        "target_action": target_action.name,
        "frame_range": [scene.frame_start, scene.frame_end],
        "copied_fcurves": copied_curves,
        "copied_bones": sorted(copied_bones),
        "feature_policy": "existing eye, brow and ear objects remain attached to the actor head hierarchy",
    }
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path))
    manifest_path = output_path.with_suffix(".json")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        "MOTION_BINDING_PASS "
        f"action={source_action.name} frames={scene.frame_start}-{scene.frame_end} "
        f"curves={copied_curves} bones={len(copied_bones)} output={output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
