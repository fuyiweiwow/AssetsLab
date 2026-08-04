"""Render the external unrigged chibi base through the accepted walk poses.

This is an offline experiment.  The source mesh is normalized, given a simple
automatic-weight armature, and rendered as a reference.  It is not a runtime
asset and is intentionally kept separate from the authored Q1 pixel base.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

FRAME_COUNT = 8
DIRECTIONS = ("front", "right", "back", "left")
PX_PER_UNIT = 256.0 / 6.98
K = 0.015


def args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--pose-contract", required=True, type=Path)
    parser.add_argument("--render-dir", required=True, type=Path)
    parser.add_argument("--blend", required=True, type=Path)
    return parser.parse_args(argv)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def load_source(path: Path) -> bpy.types.Object:
    bpy.ops.wm.open_mainfile(filepath=str(path))
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError("source must contain exactly one mesh")
    mesh = meshes[0]
    bpy.context.view_layer.objects.active = mesh
    mesh.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    min_z = min((mesh.matrix_world @ v.co).z for v in mesh.data.vertices)
    mesh.location.z -= min_z
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    height = max((mesh.matrix_world @ v.co).z for v in mesh.data.vertices)
    if height <= 0.01:
        raise RuntimeError("source mesh has no usable height")
    scale = 4.8 / height
    mesh.scale = (scale, scale, scale)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mesh.data.materials.clear()
    material = bpy.data.materials.new("ChibiBaseSkin")
    material.diffuse_color = (0.76, 0.56, 0.42, 1.0)
    mesh.data.materials.append(material)
    return mesh


def pose_joints(raw: dict, index: int) -> dict[str, Vector]:
    item = next(frame for frame in raw["frames"] if frame["frame"] == index)
    j = item["front"]["joints_2d"]
    def point(name: str, depth: float = 0.0) -> Vector:
        value = j[name]
        return Vector((K * (value[0] - 480.0), depth, K * (470.0 - value[1])))
    joints = {name: point(name) for name in ("head", "neck", "pelvis")}
    for side in ("left", "right"):
        near_leg = raw["depth_policy"]["near_leg"][index]
        near_arm = raw["depth_policy"]["near_arm"][index]
        leg_depth = -0.16 if side == near_leg else 0.16
        arm_depth = -0.10 if side == near_arm else 0.10
        joints[f"shoulder_{side}"] = point(f"shoulder_{side}")
        joints[f"elbow_{side}"] = point(f"elbow_{side}", arm_depth)
        joints[f"hand_{side}"] = point(f"hand_{side}", arm_depth)
        joints[f"hip_{side}"] = point(f"hip_{side}", leg_depth)
        joints[f"knee_{side}"] = point(f"knee_{side}", leg_depth)
        joints[f"foot_{side}"] = point(f"foot_{side}", leg_depth)
    return joints


def add_bone(edit_bones, name: str, head: Vector, tail: Vector, parent=None):
    bone = edit_bones.new(name)
    bone.head, bone.tail, bone.parent = head, tail, parent
    return bone


def build_rig(joints: dict[str, Vector]) -> bpy.types.Object:
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    rig = bpy.context.object
    rig.name = "ChibiBaseWalkRig"
    bones = rig.data.edit_bones
    bones.remove(bones[0])
    pelvis = add_bone(bones, "pelvis", joints["pelvis"], joints["pelvis"] + Vector((0, 0, .35)))
    spine = add_bone(bones, "spine", joints["pelvis"], joints["neck"], pelvis)
    neck = add_bone(bones, "neck", joints["neck"], joints["head"], spine)
    add_bone(bones, "head", joints["head"], joints["head"] + Vector((0, 0, .5)), neck)
    for side, short in (("left", "L"), ("right", "R")):
        upper = add_bone(bones, f"upper_arm.{short}", joints[f"shoulder_{side}"], joints[f"elbow_{side}"], spine)
        add_bone(bones, f"lower_arm.{short}", joints[f"elbow_{side}"], joints[f"hand_{side}"], upper)
        thigh = add_bone(bones, f"thigh.{short}", joints[f"hip_{side}"], joints[f"knee_{side}"], pelvis)
        add_bone(bones, f"shin.{short}", joints[f"knee_{side}"], joints[f"foot_{side}"], thigh)
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.show_in_front = False
    return rig


def parent_with_weights(mesh: bpy.types.Object, rig: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    try:
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    except RuntimeError as exc:
        raise RuntimeError("automatic weights failed for the source mesh") from exc


def pose_rig(rig: bpy.types.Object, joints: dict[str, Vector]) -> None:
    targets = {
        "pelvis": (joints["pelvis"], joints["pelvis"] + Vector((0, 0, .35))),
        "spine": (joints["pelvis"], joints["neck"]),
        "neck": (joints["neck"], joints["head"]),
        "head": (joints["head"], joints["head"] + Vector((0, 0, .5))),
    }
    for side, short in (("left", "L"), ("right", "R")):
        targets[f"upper_arm.{short}"] = (joints[f"shoulder_{side}"], joints[f"elbow_{side}"])
        targets[f"lower_arm.{short}"] = (joints[f"elbow_{side}"], joints[f"hand_{side}"])
        targets[f"thigh.{short}"] = (joints[f"hip_{side}"], joints[f"knee_{side}"])
        targets[f"shin.{short}"] = (joints[f"knee_{side}"], joints[f"foot_{side}"])
    matrices = {}
    for name, (head, tail) in targets.items():
        bone = rig.data.bones[name]
        direction = tail - head
        if direction.length < 1e-5:
            continue
        matrix = Matrix.Translation(head) @ Vector((0, 1, 0)).rotation_difference(direction.normalized()).to_matrix().to_4x4()
        matrix @= Matrix.Scale(direction.length / max(bone.length, 1e-5), 4)
        parent = bone.parent
        matrices[name] = matrix
        basis = bone.matrix_local.inverted() @ matrix
        if parent and parent.name in matrices:
            basis = bone.matrix_local.inverted() @ parent.matrix_local @ matrices[parent.name].inverted() @ matrix
        rig.pose.bones[name].matrix_basis = basis


def setup_render(scene: bpy.types.Scene) -> None:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = scene.render.resolution_y = 256
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = True
    scene.view_settings.look = "None"
    scene.render.image_settings.color_mode = "RGBA"
    scene.camera = None
    data = bpy.data.cameras.new("ChibiGuideCamera")
    camera = bpy.data.objects.new("ChibiGuideCamera", data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    data.type = "ORTHO"
    data.ortho_scale = 6.98
    scene.world.color = (0.02, 0.02, 0.02)
    light_data = bpy.data.lights.new("ChibiKey", "AREA")
    light_data.energy = 450
    light_data.shape = "DISK"
    light_data.size = 5
    light = bpy.data.objects.new("ChibiKey", light_data)
    light.location = (-4, -6, 8)
    scene.collection.objects.link(light)


def main() -> int:
    cli = args()
    raw = json.loads(cli.pose_contract.read_text(encoding="utf-8"))
    clear_scene()
    mesh = load_source(cli.source)
    rest = pose_joints(raw, 0)
    rig = build_rig(rest)
    parent_with_weights(mesh, rig)
    scene = bpy.context.scene
    setup_render(scene)
    camera = scene.camera
    target = Vector((0, 0, 3.05))
    camera_positions = {"front": (0, -10, 3.05), "right": (10, 0, 3.05), "back": (0, 10, 3.05), "left": (-10, 0, 3.05)}
    for direction in DIRECTIONS:
        position = Vector(camera_positions[direction])
        camera.location = position
        camera.rotation_euler = (target - position).to_track_quat("-Z", "Y").to_euler()
        for frame in range(FRAME_COUNT):
            pose_rig(rig, pose_joints(raw, frame))
            scene.render.filepath = str(cli.render_dir / direction / f"frame_{frame:02d}" / "beauty.png")
            Path(scene.render.filepath).parent.mkdir(parents=True, exist_ok=True)
            bpy.ops.render.render(write_still=True)
    cli.blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(cli.blend))
    print(f"CHIBI_BASE_WALK_RENDER_PASS frames={len(DIRECTIONS) * FRAME_COUNT} blend={cli.blend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
