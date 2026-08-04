"""Create a non-destructive no-knee test variant from an AccuRIG FBX."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-fbx", required=True, type=Path)
    parser.add_argument("--output-blend", required=True, type=Path)
    return parser.parse_args(argv)


def move_weights(mesh: bpy.types.Object, source_names: list[str], target_name: str) -> None:
    target = mesh.vertex_groups.get(target_name)
    if target is None:
        target = mesh.vertex_groups.new(name=target_name)
    source_indices = {
        group.index
        for name in source_names
        if (group := mesh.vertex_groups.get(name)) is not None
    }
    if not source_indices:
        return
    for vertex in mesh.data.vertices:
        amount = sum(item.weight for item in vertex.groups if item.group in source_indices)
        if amount > 0.0:
            target.add([vertex.index], amount, "ADD")
    for name in source_names:
        group = mesh.vertex_groups.get(name)
        if group is not None and group.name != target_name:
            mesh.vertex_groups.remove(group)


def remove_leg_middle(armature: bpy.types.Object, mesh: bpy.types.Object, side: str) -> None:
    thigh_name = f"CC_Base_{side}_Thigh"
    foot_name = f"CC_Base_{side}_Foot"
    deleted_names = [
        f"CC_Base_{side}_Calf",
        f"CC_Base_{side}_CalfTwist01",
        f"CC_Base_{side}_CalfTwist02",
        f"CC_Base_{side}_KneeShareBone",
        f"CC_Base_{side}_ThighTwist01",
        f"CC_Base_{side}_ThighTwist02",
    ]
    move_weights(mesh, deleted_names, thigh_name)

    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    bones = armature.data.edit_bones
    thigh = bones[thigh_name]
    foot = bones[foot_name]
    foot.parent = thigh
    foot.use_connect = False
    # Make one continuous rigid leg segment from hip to the foot joint.
    thigh.tail = foot.head.copy()
    for name in deleted_names:
        bone = bones.get(name)
        if bone is not None:
            bones.remove(bone)
    bpy.ops.object.mode_set(mode="OBJECT")


def main() -> int:
    options = cli_args()
    options.output_fbx.parent.mkdir(parents=True, exist_ok=True)
    options.output_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(options.source), use_anim=False)
    mesh = next(obj for obj in bpy.data.objects if obj.type == "MESH")
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    armature.animation_data_clear()

    remove_leg_middle(armature, mesh, "L")
    remove_leg_middle(armature, mesh, "R")
    mesh.data.update()

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
    print("NO_KNEE_VARIANT_PASS")
    print(f"source={options.source}")
    print(f"output_fbx={options.output_fbx}")
    print(f"output_blend={options.output_blend}")
    print(f"mesh_vertices={len(mesh.data.vertices)}")
    print(f"armature_bones={len(armature.data.bones)}")
    print("NO_KNEE_VARIANT_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
