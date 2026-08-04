"""Make already-retargeted finger motion visible on a small chibi hand."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion


FINGER_NAMES = [
    f"CC_Base_{side}_{part}{index}"
    for side in ("L", "R")
    for part in ("Thumb", "Index", "Ring", "Pinky")
    for index in (1, 2, 3)
]


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--amplitude", type=float, default=3.0)
    return parser.parse_args(argv)


def main() -> int:
    options = parse_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.blend.resolve()))
    armature = bpy.data.objects.get("Armature")
    if armature is None or armature.type != "ARMATURE":
        raise RuntimeError("target Armature not found")
    if not armature.animation_data or not armature.animation_data.action:
        raise RuntimeError("target actor has no active action")
    action = armature.animation_data.action
    scene = bpy.context.scene
    start, end = int(action.frame_range[0]), int(action.frame_range[1])
    names = [name for name in FINGER_NAMES if armature.pose.bones.get(name)]
    if len(names) < 20:
        raise RuntimeError(f"expected at least 20 finger bones, found {len(names)}")
    scene.frame_set(start)
    bpy.context.view_layer.update()
    bases = {name: armature.pose.bones[name].rotation_quaternion.copy() for name in names}
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for name in names:
            pose_bone = armature.pose.bones[name]
            delta = bases[name].rotation_difference(pose_bone.rotation_quaternion)
            axis, angle = delta.to_axis_angle()
            scaled = Quaternion(axis, angle * options.amplitude) if angle > 1e-7 else Quaternion((1, 0, 0, 0))
            pose_bone.rotation_mode = "QUATERNION"
            pose_bone.rotation_quaternion = bases[name] @ scaled
            pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=name)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.output.resolve()))
    manifest = {
        "schema": "assetslab_finger_amplitude_tune_v1",
        "source_blend": str(options.blend.resolve()),
        "frame_range": [start, end],
        "mapped_bones": names,
        "amplitude": options.amplitude,
        "status": "WIP_candidate_for_visual_comparison",
    }
    options.output.with_suffix(".json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"FINGER_AMPLITUDE_PASS bones={len(names)} amplitude={options.amplitude} output={options.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
