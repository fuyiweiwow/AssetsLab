"""Q2: KIIRA chibi mesh skinned onto the accepted G1 walk skeleton.

Loads the KIIRA CC-BY-SA chibi model (third_party/kiira_chibi/Character Base.blend),
discards its own armature/demo textures, splits the ARMS/LEGS meshes at
elbow/knee, retargets the parts into the project Q proportions (head center
z=4.69, shoulder line 2.83, pelvis 1.41, foot baseline z=0 = runtime y=60),
and binds each part rigidly to GuideRigQ2. The walk joints come from the
verified G1 pose contract via q_map_joints, so the motion phase is identical
to the Q1 base render; only the skin differs.

Post-processing (tools/process_q_guide_pixels.py) downsamples to 64x64 PNGs
and assembles the pixel base sheet + manifest, same as Q1.

Run with the KIIRA blend loaded:
    blender --background third_party/kiira_chibi/Character\ Base.blend \
        --python tools/blender/create_q2_guide_scene.py -- --contract ... ...
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

PX_PER_UNIT = 256.0 / 6.98
DEPTH_FROM = 7.5
DEPTH_TO = 12.5
FRAME_COUNT = 8
DIRECTIONS = ("front", "right", "back", "left")

SKIN_COLOR = (0.93, 0.87, 0.82, 1.0)

# Q proportions matching the hand-authored pixel base (head 34px tall, body to
# y=60). Head center z=4.69 (y=17), radius 1.85 (17px); shoulder line 2.83.
Q_HEAD_Z = 4.69
Q_NECK_Z = 2.84
Q_SHOULDER_Z = 2.83
Q_SHOULDER_X = 0.55
Q_ELBOW_Z = 1.90
Q_HAND_Z_BASE = 1.45
Q_PELVIS_Z = 1.41
Q_HIP_Z = 1.35
Q_KNEE_Z_BASE = 0.70
Q_FOOT_Z_LAND = 0.26

# KIIRA mesh names.
KIIRA_HEAD = "HEAD"
KIIRA_TORSO = "TORSO"
KIIRA_ARMS = "ARMS"
KIIRA_HANDS = "HANDS"
KIIRA_LEGS = "LEGS"
KIIRA_FEET = "FEET"
KIIRA_FACE = "FACE"

# KIIRA rest-pose geometry (world units, from probe).
KIIRA_T_Z = 2.554              # feet baseline -> z=0
KIIRA_HEAD_CX = 0.0
KIIRA_HEAD_CY = 0.016
KIIRA_HEAD_CZ = 1.1005
KIIRA_HEAD_SCALE = 1.91        # radius 0.9685 -> 1.85 (34px head)
KIIRA_TORSO_TOP = 2.896        # shifted z: shoulder line
KIIRA_TORSO_BOTTOM = 1.609     # shifted z: hip line
KIIRA_TORSO_X = 0.644
KIIRA_ELBOW_Z = 2.094          # shifted z split line: upper arm / forearm
KIIRA_ARM_TOP = 2.540
KIIRA_ARM_ROOT_X = 0.642
KIIRA_ARM_END_X = 1.16
KIIRA_KNEE_Z = 1.204           # shifted z split line: thigh / shin
KIIRA_HIP_Z = 1.731
KIIRA_ANKLE_Z = 0.354
KIIRA_FOOT_ANKLE = 0.381

# Target rest chain (world units, standing pose like G1 frame 0).
REST_SHOULDER_X = 0.55
REST_ELBOW_X = 0.70
REST_HAND_X = 0.78
REST_HIP_X = 0.40
REST_KNEE_X = 0.30


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--pose-contract", required=True, type=Path)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--render-dir", required=True, type=Path)
    parser.add_argument("--pose-3d", required=True, type=Path)
    return parser.parse_args(argv)


def make_material(name: str, rgba: tuple[float, float, float, float]) -> bpy.types.Material:
    item = bpy.data.materials.new(name)
    item.use_nodes = True
    nodes = item.node_tree.nodes
    nodes.clear()
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = rgba
    shader.inputs["Roughness"].default_value = 0.82
    output = nodes.new("ShaderNodeOutputMaterial")
    item.node_tree.links.new(shader.outputs[0], output.inputs["Surface"])
    return item


def smooth_shade(obj: bpy.types.Object) -> None:
    for polygon in obj.data.polygons:
        polygon.use_smooth = True


def assign_material(obj: bpy.types.Object, item: bpy.types.Material) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(item)


def subsurf(obj: bpy.types.Object, level: int = 2) -> None:
    modifier = obj.modifiers.new("SubsurfSkin", "SUBSURF")
    modifier.levels = level
    modifier.render_levels = level


def bind_bone(obj: bpy.types.Object, bone_name: str, rig: bpy.types.Object) -> None:
    group = obj.vertex_groups.new(name=bone_name)
    group.add([v.index for v in obj.data.vertices], 1.0, "REPLACE")
    modifier = obj.modifiers.new("Armature", "ARMATURE")
    modifier.object = rig


def point_camera(camera: bpy.types.Object, location: Vector, target: Vector) -> None:
    camera.location = location
    camera.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()


class PoseContract:
    def __init__(self, path: Path) -> None:
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.policy = raw["depth_policy"]
        self.k = self.policy["constants_3d"]["k"]
        self.leg_depth = self.policy["constants_3d"]["leg_depth"]
        self.arm_depth = self.policy["constants_3d"]["arm_depth"]
        self.foot_advance = self.policy["constants_3d"]["foot_advance"]
        self.knee_advance_ratio = self.policy["constants_3d"]["knee_advance_ratio"]
        self.hand_advance = self.policy["constants_3d"]["hand_advance"]
        self.elbow_advance_ratio = self.policy["constants_3d"]["elbow_advance_ratio"]
        self.frames = raw["frames"]

    def frame(self, index: int) -> dict:
        return next(f for f in self.frames if f["frame"] == index)

    def joints_2d(self, index: int) -> dict:
        return self.frame(index)["front"]["joints_2d"]

    def depth_offset(self, index: int, side: str, kind: str) -> float:
        if kind == "center":
            return 0.0
        near = self.policy["near_leg"][index] if kind == "leg" else self.policy["near_arm"][index]
        offset = self.leg_depth if kind == "leg" else self.arm_depth
        return -offset if side == near else offset

    def lift_phase(self, index: int, side: str) -> float:
        phase = math.tau * index / FRAME_COUNT
        if side == "left":
            return max(0.0, math.sin(phase))
        return max(0.0, -math.sin(phase))

    def arm_swing_phase(self, index: int, side: str) -> float:
        phase = math.tau * index / FRAME_COUNT
        if side == "left":
            return max(0.0, -math.sin(phase))
        return max(0.0, math.sin(phase))


def to_world(joint_2d: list[float], depth: float, k: float) -> Vector:
    return Vector((k * (joint_2d[0] - 480.0), depth, k * (470.0 - joint_2d[1])))


def compute_joints(contract: PoseContract, index: int) -> dict[str, Vector]:
    j = contract.joints_2d(index)
    k = contract.k
    joints = {}
    joints["head"] = to_world(j["head"], 0.0, k)
    joints["neck"] = to_world(j["neck"], 0.0, k)
    joints["pelvis"] = to_world(j["pelvis"], 0.0, k)
    for side in ("left", "right"):
        base = {"left": "left", "right": "right"}
        joints["shoulder_" + side] = to_world(j["shoulder_" + base[side]], 0.0, k)
        elbow = Vector(j["elbow_" + base[side]])
        hand = Vector(j["hand_" + base[side]])
        depth_arm = contract.depth_offset(index, side, "arm")
        advance = contract.hand_advance * contract.arm_swing_phase(index, side)
        joints["elbow_" + side] = to_world(list(elbow) + [], depth_arm, k) + Vector((0.0, -advance * contract.elbow_advance_ratio, 0.0))
        joints["hand_" + side] = to_world(list(hand) + [], depth_arm, k) + Vector((0.0, -advance, 0.0))
        depth_leg = contract.depth_offset(index, side, "leg")
        lift = contract.lift_phase(index, side)
        joints["hip_" + side] = to_world(j["hip_" + base[side]], depth_leg, k)
        knee = Vector(j["knee_" + base[side]])
        joints["knee_" + side] = to_world(list(knee) + [], depth_leg, k) + Vector((0.0, -contract.foot_advance * contract.knee_advance_ratio * lift, 0.0))
        foot = Vector(j["foot_" + base[side]])
        joints["foot_" + side] = to_world(list(foot) + [], depth_leg, k) + Vector((0.0, -contract.foot_advance * lift, 0.0))
    return joints


def q_map_joints(joints: dict[str, Vector]) -> dict[str, Vector]:
    """Map accepted G1 walk joints onto Q proportions (identical to Q1)."""
    out: dict[str, Vector] = {}
    out["head"] = Vector((0.0, 0.0, Q_HEAD_Z))
    out["neck"] = Vector((0.0, 0.0, Q_NECK_Z))
    out["pelvis"] = Vector((0.0, 0.0, Q_PELVIS_Z))
    for side in ("left", "right"):
        sign = 1.0 if side == "right" else -1.0
        shoulder_x = joints["shoulder_" + side].x
        out["shoulder_" + side] = Vector((sign * Q_SHOULDER_X, joints["shoulder_" + side].y, Q_SHOULDER_Z))
        elbow_x = joints["elbow_" + side].x
        out["elbow_" + side] = Vector((shoulder_x + (elbow_x - shoulder_x) * 0.6, joints["elbow_" + side].y * 0.8, Q_ELBOW_Z))
        hand_x = joints["hand_" + side].x
        hand_z = Q_HAND_Z_BASE + (joints["hand_" + side].z - 1.32) * 0.4
        out["hand_" + side] = Vector((shoulder_x + (hand_x - shoulder_x) * 0.6, joints["hand_" + side].y * 0.8, hand_z))
        hip_x = joints["hip_" + side].x
        out["hip_" + side] = Vector((hip_x * 0.8, joints["hip_" + side].y, Q_HIP_Z))
        knee_x = joints["knee_" + side].x
        knee_z = Q_KNEE_Z_BASE + (joints["knee_" + side].z - 0.84) * 0.3
        out["knee_" + side] = Vector((knee_x * 0.8, joints["knee_" + side].y, knee_z))
        foot_x = joints["foot_" + side].x
        foot_z = Q_FOOT_Z_LAND + joints["foot_" + side].z * 0.6
        out["foot_" + side] = Vector((foot_x * 0.8, joints["foot_" + side].y, foot_z))
    return out


def build_armature(joints: dict[str, Vector]) -> bpy.types.Object:
    bpy.ops.object.armature_add(enter_editmode=True, location=(0.0, 0.0, 0.0))
    rig = bpy.context.object
    rig.name = "GuideRigQ2"
    rig.data.name = "GuideRigDataQ2"
    edit_bones = rig.data.edit_bones
    edit_bones.remove(edit_bones[0])

    def bone(name: str, head: Vector, tail: Vector, parent=None):
        item = edit_bones.new(name)
        item.head = head
        item.tail = tail
        item.parent = parent
        return item

    pelvis = bone("pelvis", joints["pelvis"], joints["pelvis"] + Vector((0.0, 0.0, 0.35)))
    spine = bone("spine", joints["pelvis"], joints["neck"], pelvis)
    neck = bone("neck", joints["neck"], joints["head"], spine)
    bone("head", joints["head"], joints["head"] + Vector((0.0, 0.0, 0.5)), neck)
    for side in ("L", "R"):
        base = "left" if side == "L" else "right"
        upper = bone("upper_arm." + side, joints["shoulder_" + base], joints["elbow_" + base], spine)
        bone("lower_arm." + side, joints["elbow_" + base], joints["hand_" + base], upper)
        thigh = bone("thigh." + side, joints["hip_" + base], joints["knee_" + base], pelvis)
        bone("shin." + side, joints["knee_" + base], joints["foot_" + base], thigh)
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.hide_render = False
    rig.show_in_front = True
    return rig


def pose_frame(rig: bpy.types.Object, joints: dict[str, Vector], frame: int, keyframe: bool) -> None:
    bones = {
        "pelvis": (joints["pelvis"], joints["pelvis"] + Vector((0.0, 0.0, 0.35))),
        "spine": (joints["pelvis"], joints["neck"]),
        "neck": (joints["neck"], joints["head"]),
        "head": (joints["head"], joints["head"] + Vector((0.0, 0.0, 0.5))),
    }
    for side, base in (("L", "left"), ("R", "right")):
        bones["upper_arm." + side] = (joints["shoulder_" + base], joints["elbow_" + base])
        bones["lower_arm." + side] = (joints["elbow_" + base], joints["hand_" + base])
        bones["thigh." + side] = (joints["hip_" + base], joints["knee_" + base])
        bones["shin." + side] = (joints["knee_" + base], joints["foot_" + base])

    pose_mats: dict[str, Matrix] = {}
    for bone_name, (head, tail) in bones.items():
        bone = rig.data.bones[bone_name]
        rest_length = (bone.head_local - bone.tail_local).length
        direction = tail - head
        length = direction.length
        if length < 1e-6 or rest_length < 1e-6:
            continue
        rotation = Vector((0.0, 1.0, 0.0)).rotation_difference(direction / length)
        scale = Matrix.Scale(length / rest_length, 4)
        matrix = Matrix.Translation(head) @ rotation.to_matrix().to_4x4() @ scale
        parent = bone.parent
        if parent is None:
            basis = bone.matrix_local.inverted() @ matrix
        else:
            basis = bone.matrix_local.inverted() @ parent.matrix_local @ pose_mats[parent.name].inverted() @ matrix
        pose_mats[bone_name] = matrix
        pose_bone = rig.pose.bones[bone_name]
        pose_bone.rotation_mode = "QUATERNION"
        pose_bone.matrix_basis = basis
        if keyframe:
            pose_bone.keyframe_insert(data_path="location", frame=frame)
            pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)
            pose_bone.keyframe_insert(data_path="scale", frame=frame)


def camera_axes(camera_position: Vector, target: Vector) -> tuple[Vector, Vector, Vector]:
    matrix = (target - camera_position).to_track_quat("-Z", "Y").to_matrix()
    return matrix @ Vector((1.0, 0.0, 0.0)), matrix @ Vector((0.0, 1.0, 0.0)), matrix @ Vector((0.0, 0.0, -1.0))


def setup_cameras(scene: bpy.types.Scene, contract: dict) -> tuple[bpy.types.Object, dict[str, dict]]:
    camera_data = bpy.data.cameras.new("GuideCameraQ2")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = contract["world_contract"]["orthographic_scale"]
    camera = bpy.data.objects.new("GuideCameraQ2", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    target = Vector((0.0, 0.0, contract["world_contract"]["camera_target_z"]))
    cameras = {}
    for direction, payload in contract["directions"].items():
        position = Vector(payload["camera_position"])
        cameras[direction] = {"position": position, "target": target}
    return camera, cameras


def setup_compositor(scene: bpy.types.Scene, render_dir: Path) -> bpy.types.Node:
    scene.use_nodes = True
    ntree = scene.node_tree
    ntree.nodes.clear()
    render_layers = ntree.nodes.new("CompositorNodeRLayers")
    output = ntree.nodes.new("CompositorNodeOutputFile")
    output.base_path = str(render_dir)
    slot = output.file_slots[0]
    slot.path = "beauty"
    slot.use_node_format = False
    slot.format.file_format = "PNG"
    slot.format.color_mode = "RGBA"
    slot.format.color_depth = "8"
    slot.save_as_render = True
    ntree.links.new(render_layers.outputs["Image"], output.inputs[0])
    return output


def split_mesh(source: bpy.types.Object, keep_verts) -> bpy.types.Object:
    """Duplicate `source`, removing every face whose vertices fail keep_verts."""
    mesh = bpy.data.meshes.new(source.name + ".part")
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.matrix_world = source.matrix_world
    bm = bmesh.new()
    bm.from_mesh(source.data)
    bm.faces.ensure_lookup_table()
    doomed = []
    for face in bm.faces:
        verts = list(face.verts)
        if not all(keep_verts(v) for v in verts):
            doomed.append(face)
    for face in doomed:
        bm.faces.remove(face)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bm.to_mesh(mesh)
    bm.free()
    return obj


def retarget(obj: bpy.types.Object, fn) -> None:
    """Apply an affine map to every vertex of `obj` (local == world here)."""
    for v in obj.data.vertices:
        v.co = fn(v.co)


def zs(v: Vector) -> float:
    return v.z + KIIRA_T_Z


def retarget_head(v: Vector) -> Vector:
    return Vector((
        v.x * KIIRA_HEAD_SCALE,
        KIIRA_HEAD_CY + (v.y - KIIRA_HEAD_CY) * KIIRA_HEAD_SCALE,
        Q_HEAD_Z + (v.z - KIIRA_HEAD_CZ) * KIIRA_HEAD_SCALE,
    ))


def retarget_torso(v: Vector) -> Vector:
    top = KIIRA_TORSO_TOP
    bottom = KIIRA_TORSO_BOTTOM
    target_top = Q_SHOULDER_Z
    target_bottom = Q_PELVIS_Z
    s = (target_top - target_bottom) / (top - bottom)
    return Vector((v.x * 1.242, v.y * 1.05, target_bottom + (zs(v) - bottom) * s))


def retarget_upper_arm(v: Vector, sign: float) -> Vector:
    z_bottom = KIIRA_ELBOW_Z
    z_top = KIIRA_ARM_TOP
    x_root = KIIRA_ARM_ROOT_X
    x_end = KIIRA_ARM_END_X
    sz = (Q_SHOULDER_Z - Q_ELBOW_Z) / (z_top - z_bottom)
    sx = (REST_ELBOW_X - REST_SHOULDER_X) / (x_end - x_root)
    return Vector((
        sign * (REST_SHOULDER_X + (abs(v.x) - x_root) * sx),
        v.y * 0.9,
        Q_ELBOW_Z + (zs(v) - z_bottom) * sz,
    ))


def retarget_forearm(v: Vector, sign: float) -> Vector:
    z_bottom = KIIRA_ANKLE_Z
    z_top = KIIRA_ELBOW_Z
    sz = (Q_HAND_Z_BASE - Q_ELBOW_Z) / (z_top - z_bottom)
    return Vector((
        sign * (REST_HAND_X + (abs(v.x) - KIIRA_ARM_END_X)),
        v.y * 0.9,
        Q_ELBOW_Z + (zs(v) - z_top) * sz,
    ))


def retarget_hand(v: Vector, sign: float) -> Vector:
    z_bottom = 1.324
    z_top = 1.700
    return Vector((
        sign * (REST_HAND_X + (abs(v.x) - KIIRA_ARM_END_X)),
        v.y * 0.6,
        Q_HAND_Z_BASE + (zs(v) - z_bottom) * (Q_HAND_Z_BASE + 0.15 - Q_HAND_Z_BASE) / (z_top - z_bottom),
    ))


def retarget_thigh(v: Vector, sign: float) -> Vector:
    z_bottom = KIIRA_KNEE_Z
    z_top = KIIRA_HIP_Z
    sz = (Q_HIP_Z - Q_KNEE_Z_BASE) / (z_top - z_bottom)
    return Vector((
        sign * (0.05 + abs(v.x) * 0.55),
        v.y,
        Q_KNEE_Z_BASE + (zs(v) - z_bottom) * sz,
    ))


def retarget_shin(v: Vector, sign: float) -> Vector:
    z_bottom = KIIRA_ANKLE_Z
    z_top = KIIRA_KNEE_Z
    sz = (Q_FOOT_Z_LAND - Q_KNEE_Z_BASE) / (z_top - z_bottom)
    return Vector((
        sign * (0.03 + abs(v.x) * 0.45),
        v.y,
        Q_KNEE_Z_BASE + (zs(v) - z_top) * sz,
    ))


def retarget_foot(v: Vector) -> Vector:
    return Vector((v.x * 0.6, v.y, zs(v) * (Q_FOOT_Z_LAND / KIIRA_FOOT_ANKLE)))


def build_arm_parts(arms_obj: bpy.types.Object, rig: bpy.types.Object, material: bpy.types.Material) -> None:
    def keep_upper(v) -> bool:
        return v.co.z >= -0.46

    def keep_left(v) -> bool:
        return v.co.x < 0.0

    upper = split_mesh(arms_obj, keep_upper)
    fore = split_mesh(arms_obj, lambda v: not keep_upper(v))
    upper_l = split_mesh(upper, keep_left)
    upper_r = split_mesh(upper, lambda v: not keep_left(v))
    fore_l = split_mesh(fore, keep_left)
    fore_r = split_mesh(fore, lambda v: not keep_left(v))
    for junk in (arms_obj, upper, fore):
        bpy.data.objects.remove(junk, do_unlink=True)
    for obj, fn, bone in (
        (upper_l, lambda v: retarget_upper_arm(v, -1.0), "upper_arm.L"),
        (upper_r, lambda v: retarget_upper_arm(v, 1.0), "upper_arm.R"),
        (fore_l, lambda v: retarget_forearm(v, -1.0), "lower_arm.L"),
        (fore_r, lambda v: retarget_forearm(v, 1.0), "lower_arm.R"),
    ):
        retarget(obj, fn)
        finalize(obj, material, rig, bone)


def build_leg_parts(legs_obj: bpy.types.Object, rig: bpy.types.Object, material: bpy.types.Material) -> None:
    def keep_thigh(v) -> bool:
        return v.co.z >= -1.35

    def keep_left(v) -> bool:
        return v.co.x < 0.0

    thigh = split_mesh(legs_obj, keep_thigh)
    shin = split_mesh(legs_obj, lambda v: not keep_thigh(v))
    thigh_l = split_mesh(thigh, keep_left)
    thigh_r = split_mesh(thigh, lambda v: not keep_left(v))
    shin_l = split_mesh(shin, keep_left)
    shin_r = split_mesh(shin, lambda v: not keep_left(v))
    for junk in (legs_obj, thigh, shin):
        bpy.data.objects.remove(junk, do_unlink=True)
    for obj, fn, bone in (
        (thigh_l, lambda v: retarget_thigh(v, -1.0), "thigh.L"),
        (thigh_r, lambda v: retarget_thigh(v, 1.0), "thigh.R"),
        (shin_l, lambda v: retarget_shin(v, -1.0), "shin.L"),
        (shin_r, lambda v: retarget_shin(v, 1.0), "shin.R"),
    ):
        retarget(obj, fn)
        finalize(obj, material, rig, bone)


def finalize(obj: bpy.types.Object, material: bpy.types.Material, rig: bpy.types.Object, bone_name: str) -> None:
    smooth_shade(obj)
    subsurf(obj)
    assign_material(obj, material)
    bind_bone(obj, bone_name, rig)


def prepare_scene(contract: dict, pose_contract: PoseContract) -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    scene = bpy.context.scene
    scene.name = "AssetsLab_Q2_KIIRA_3D_Guide"
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x, scene.render.resolution_y = contract["guide_canvas_px"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.render.filepath = str(Path(".").resolve() / "render.png")
    scene.render.fps = FRAME_COUNT
    scene.frame_start = 0
    scene.frame_end = 31
    scene.view_settings.view_transform = "Raw"
    try:
        scene.view_settings.look = "None"
    except TypeError:
        pass

    keep_names = {KIIRA_HEAD, KIIRA_TORSO, KIIRA_ARMS, KIIRA_HANDS, KIIRA_LEGS, KIIRA_FEET}
    for obj in list(bpy.data.objects):
        if obj.type == "MESH" and obj.name in keep_names:
            if obj.parent is not None:
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        else:
            bpy.data.objects.remove(obj, do_unlink=True)

    material = make_material("M_Skin", SKIN_COLOR)
    joints0 = compute_joints(pose_contract, 0)
    rig = build_armature(joints0)

    parts: list[bpy.types.Object] = []
    for obj in list(bpy.data.objects):
        if obj.name == KIIRA_HEAD:
            retarget(obj, retarget_head)
            finalize(obj, material, rig, "head")
            parts.append(obj)
        elif obj.name == KIIRA_TORSO:
            retarget(obj, retarget_torso)
            finalize(obj, material, rig, "spine")
            parts.append(obj)
        elif obj.name == KIIRA_ARMS:
            build_arm_parts(obj, rig, material)
        elif obj.name == KIIRA_HANDS:
            def retarget_hand_left(v: Vector) -> Vector:
                return retarget_hand(v, -1.0)
            def retarget_hand_right(v: Vector) -> Vector:
                return retarget_hand(v, 1.0)
            hand_l = split_mesh(obj, lambda v: v.co.x < 0.0)
            hand_r = split_mesh(obj, lambda v: v.co.x >= 0.0)
            retarget(hand_l, retarget_hand_left)
            retarget(hand_r, retarget_hand_right)
            finalize(hand_l, material, rig, "lower_arm.L")
            finalize(hand_r, material, rig, "lower_arm.R")
            bpy.data.objects.remove(obj, do_unlink=True)
        elif obj.name == KIIRA_LEGS:
            build_leg_parts(obj, rig, material)
        elif obj.name == KIIRA_FEET:
            foot_l = split_mesh(obj, lambda v: v.co.x < 0.0)
            foot_r = split_mesh(obj, lambda v: v.co.x >= 0.0)
            retarget(foot_l, retarget_foot)
            retarget(foot_r, retarget_foot)
            finalize(foot_l, material, rig, "shin.L")
            finalize(foot_r, material, rig, "shin.R")
            bpy.data.objects.remove(obj, do_unlink=True)

    light_data = bpy.data.lights.new("KeyLight", "AREA")
    light_data.energy = 550.0
    light_data.shape = "DISK"
    light_data.size = 5.0
    light = bpy.data.objects.new("KeyLight", light_data)
    bpy.context.collection.objects.link(light)
    light.location = (3.0, -4.0, 7.0)
    point_camera(light, light.location, Vector((0.0, 0.0, 3.0)))

    return rig, parts


def main() -> int:
    args = cli_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    pose_contract = PoseContract(args.pose_contract)
    if contract["guide_canvas_px"] != [256, 256] or contract["runtime_canvas_px"] != [64, 64]:
        raise ValueError("Q2 requires the locked 256px guide and 64px runtime contract")
    if contract["world_contract"]["orthographic_scale"] != 6.98 or contract["world_contract"]["camera_target_z"] != 3.05:
        raise ValueError("Q2 requires ortho scale 6.98 and camera target z 3.05")
    args.blend.parent.mkdir(parents=True, exist_ok=True)
    args.render_dir.mkdir(parents=True, exist_ok=True)
    args.pose_3d.parent.mkdir(parents=True, exist_ok=True)

    scene = bpy.context.scene
    rig, parts = prepare_scene(contract, pose_contract)
    camera, cameras = setup_cameras(scene, contract)
    scene.camera = camera
    beauty_out = setup_compositor(scene, args.render_dir)
    depsgraph = bpy.context.evaluated_depsgraph_get()

    for stale in args.render_dir.glob("*.png"):
        stale.unlink()
    for direction in DIRECTIONS:
        cell_root = args.render_dir / direction
        if cell_root.exists():
            shutil.rmtree(cell_root)

    pose3d_frames = []
    for direction_index, direction in enumerate(DIRECTIONS):
        cam = cameras[direction]
        camera_position = cam["position"]
        cam_x, cam_y, view_axis = camera_axes(camera_position, cam["target"])
        point_camera(camera, camera_position, cam["target"])
        for frame_index in range(FRAME_COUNT):
            frame_number = direction_index * FRAME_COUNT + frame_index
            joints = q_map_joints(compute_joints(pose_contract, frame_index))
            scene.frame_set(frame_number)
            pose_frame(rig, joints, frame_number, keyframe=True)
            depsgraph.update()

            beauty_out.mute = False
            bpy.ops.render.render(write_still=True)

            cell_dir = args.render_dir / direction / ("frame_%02d" % frame_index)
            cell_dir.mkdir(parents=True, exist_ok=True)
            source = args.render_dir / ("beauty%04d.png" % frame_number)
            if not source.is_file():
                raise RuntimeError("missing beauty output for %s frame %d" % (direction, frame_index))
            shutil.move(str(source), str(cell_dir / "beauty.png"))

            pose3d_frames.append({
                "direction": direction,
                "frame": frame_index,
                "joints_3d": {name: [round(v[0], 3), round(v[1], 3), round(v[2], 3)] for name, v in joints.items()},
            })

    pose3d = {
        "schema": "assetslab_3d_guide_v1_pose_3d",
        "stage": "Q2_kiira_skin_render",
        "guide_canvas_px": [256, 256],
        "px_per_unit": round(PX_PER_UNIT, 4),
        "depth_map": {"from": DEPTH_FROM, "to": DEPTH_TO},
        "depth_convention": "camera_plane_distance_along_view_axis",
        "directions": list(DIRECTIONS),
        "frames": pose3d_frames,
    }
    args.pose_3d.write_text(json.dumps(pose3d, indent=2), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(args.blend))
    print("Q2_BLEND_BUILD_PASS blend=%s frames=32 renders=%s pose3d=%s" % (args.blend, args.render_dir, args.pose_3d))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
