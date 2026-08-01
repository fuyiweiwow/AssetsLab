"""Create a non-destructive variant with both knees moved to leg midpoints."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-fbx", required=True, type=Path)
    parser.add_argument("--output-blend", required=True, type=Path)
    return parser.parse_args(argv)


def move_bone(bone, delta: Vector) -> None:
    bone.head += delta
    bone.tail += delta


def reposition_leg(armature: bpy.types.Object, side: str) -> dict[str, tuple[float, float, float]]:
    bones = armature.data.edit_bones
    thigh = bones[f"CC_Base_{side}_Thigh"]
    calf = bones[f"CC_Base_{side}_Calf"]
    foot = bones[f"CC_Base_{side}_Foot"]
    old_knee = calf.head.copy()
    target_knee = thigh.head.lerp(foot.head, 0.5)
    delta = target_knee - old_knee

    # Move the primary calf and its auxiliary bones with the new knee.
    move_bone(calf, delta)
    for name in (
        f"CC_Base_{side}_CalfTwist01",
        f"CC_Base_{side}_CalfTwist02",
        f"CC_Base_{side}_KneeShareBone",
    ):
        bone = bones.get(name)
        if bone is not None:
            move_bone(bone, delta)

    # Keep the thigh twist chain ending at the new knee.
    thigh_twist02 = bones.get(f"CC_Base_{side}_ThighTwist02")
    if thigh_twist02 is not None:
        thigh_twist02.tail = target_knee.copy()

    # Keep the lower-leg auxiliary chain ending at the ankle.
    calf_twist01 = bones.get(f"CC_Base_{side}_CalfTwist01")
    calf_twist02 = bones.get(f"CC_Base_{side}_CalfTwist02")
    if calf_twist01 is not None and calf_twist02 is not None:
        midpoint = target_knee.lerp(foot.head, 0.5)
        calf_twist01.head = target_knee.copy()
        calf_twist01.tail = midpoint.copy()
        calf_twist02.head = midpoint.copy()
        calf_twist02.tail = foot.head.copy()

    knee_share = bones.get(f"CC_Base_{side}_KneeShareBone")
    if knee_share is not None:
        knee_share.head = target_knee.copy()
        knee_share.tail = target_knee.lerp(foot.head, 0.25)

    return {
        "old_knee": tuple(round(value, 4) for value in old_knee),
        "new_knee": tuple(round(value, 4) for value in target_knee),
        "hip": tuple(round(value, 4) for value in thigh.head),
        "ankle": tuple(round(value, 4) for value in foot.head),
    }


def main() -> int:
    options = cli_args()
    options.output_fbx.parent.mkdir(parents=True, exist_ok=True)
    options.output_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(options.source), use_anim=False)
    mesh = next(obj for obj in bpy.data.objects if obj.type == "MESH")
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    armature.animation_data_clear()

    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    results = {side: reposition_leg(armature, side) for side in ("L", "R")}
    bpy.ops.object.mode_set(mode="OBJECT")
    mesh.data.update()
    bpy.context.view_layer.update()

    bpy.ops.wm.save_as_mainfile(filepath=str(options.output_blend))
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.fbx(
        filepath=str(options.output_fbx),
        use_selection=True,
        add_leaf_bones=False,
        bake_anim=False,
        object_types={"ARMATURE", "MESH"},
        armature_nodetype="NULL",
        mesh_smooth_type="FACE",
        use_mesh_modifiers=True,
    )
    print("MID_KNEE_VARIANT_PASS")
    print(f"source={options.source}")
    print(f"output_fbx={options.output_fbx}")
    print(f"output_blend={options.output_blend}")
    print(f"leg_results={results}")
    print("MID_KNEE_VARIANT_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
