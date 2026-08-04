"""Copy an imported same-name FBX action onto a target armature.

The KIIRA FBX and the project source rig share 19 deform-bone names. FBX leaf
bones are intentionally ignored. This creates a new action datablock on the
target rig without modifying the source FBX action.
"""

from __future__ import annotations

import argparse
import bpy
import sys


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--action", default="")
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def find_armature(name: str):
    object = bpy.data.objects.get(name)
    if object is None or object.type != "ARMATURE":
        raise RuntimeError(f"armature not found: {name}")
    return object


def main() -> int:
    options = parse_args()
    target = find_armature(options.target)
    source = find_armature(options.source)
    source_action = bpy.data.actions.get(options.action) if options.action else None
    if source_action is None:
        source_action = source.animation_data.action if source.animation_data else None
    if source_action is None:
        raise RuntimeError("source armature has no action")

    target_action = bpy.data.actions.new(f"{source_action.name}_on_{target.name}")
    for curve in source_action.fcurves:
        if 'pose.bones["' not in curve.data_path:
            continue
        bone_name = curve.data_path.split('pose.bones["', 1)[1].split('"]', 1)[0]
        if target.pose.bones.get(bone_name) is None:
            continue
        copied = target_action.fcurves.new(curve.data_path, index=curve.array_index, action_group=bone_name)
        for key in curve.keyframe_points:
            point = copied.keyframe_points.insert(key.co.x, key.co.y, options={"FAST"})
            point.interpolation = key.interpolation

    target.animation_data_create()
    target.animation_data.action = target_action
    target_action.use_fake_user = True
    bpy.ops.wm.save_as_mainfile(filepath=options.output)
    print(f"ACTION_TRANSFER_PASS source={source.name} target={target.name} action={target_action.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
