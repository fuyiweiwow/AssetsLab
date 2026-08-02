"""Create a small head-turn animation test for the Boolean eye socket candidate."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy


def cli() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--armature", default="Armature")
    return parser.parse_args(argv)


def main() -> None:
    options = cli()
    armature = bpy.data.objects.get(options.armature)
    if armature is None:
        raise RuntimeError("Armature is missing")
    bone = armature.pose.bones.get("CC_Base_Head")
    if bone is None:
        raise RuntimeError("CC_Base_Head is missing")
    armature.animation_data_clear()
    action = bpy.data.actions.new("TEST_BooleanSocket_HeadTurn")
    armature.animation_data_create()
    armature.animation_data.action = action
    bone.rotation_mode = "XYZ"
    for frame, yaw in ((1, 0.0), (12, math.radians(22.0)), (24, math.radians(-22.0)), (36, 0.0)):
        bone.rotation_euler = (0.0, 0.0, yaw)
        bone.keyframe_insert(data_path="rotation_euler", frame=frame, group="CC_Base_Head")
    action.frame_range = (1, 36)
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 36
    options.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.output.resolve()), compress=True)
    print({"output": str(options.output), "action": action.name, "frames": [1, 12, 24, 36], "bone": bone.name})


if __name__ == "__main__":
    main()
