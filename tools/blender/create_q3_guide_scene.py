"""Q3: KIIRA chibi with its ORIGINAL skin weights driven by the G1 walk.

Unlike Q2 (which split the KIIRA parts and bound them rigidly), Q3 keeps the
KIIRA mesh skinning intact: meshes keep their armature modifier and vertex
weights, bones are renamed onto the G1 semantics, and every frame the G1 walk
joints (q_map_joints) absolutely drive the KIIRA bones. Elbows and knees
therefore bend through the model's own weights instead of static part joints.

The mesh parts are still split at elbow/knee lines and each segment is
retargeted onto the Q proportions (head center z=4.69, shoulder 2.83,
pelvis 1.41, knee 0.70, foot baseline 0), so geometry matches the Q canvas
while the weights provide natural deformation.

Run with the KIIRA blend loaded:
    blender --background third_party/kiira_chibi/Character\ Base.blend \
        --python tools/blender/create_q3_guide_scene.py -- --contract ... ...
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

KIIRA_PELVIS_Z = -0.929
KIIRA_HEAD_CY = 0.016
KIIRA_HEAD_CZ = 1.1005
KIIRA_HEAD_SCALE = 1.91

BONE_MAP = {
    "Bone": "pelvis",
    "Bone.001": "shoulder.R",
    "Bone.002": "upper_arm.R",
    "Bone.003": "lower_arm.R",
    "Bone.004": "hand.R",
    "Bone.005": "shoulder.L",
    "Bone.006": "upper_arm.L",
    "Bone.007": "lower_arm.L",
    "Bone.008": "hand.L",
    "Bone.009": "spine",
    "Bone.010": "head",
    "Bone.011": "hip.R",
    "Bone.012": "thigh.R",
    "Bone.013": "shin.R",
    "Bone.014": "foot.R",
    "Bone.015": "hip.L",
    "Bone.016": "thigh.L",
    "Bone.017": "shin.L",
    "Bone.018": "foot.L",
}

REST_BONES = {
    "pelvis": ((0.0, 0.0, Q_PELVIS_Z), (0.0, 0.0, Q_PELVIS_Z + 0.35)),
    "spine": ((0.0, 0.0, Q_PELVIS_Z + 0.01), (0.0, 0.0, Q_NECK_Z)),
    "head": ((0.0, 0.0, Q_NECK_Z), (0.0, 0.0, Q_HEAD_Z)),
    "shoulder": ((Q_SHOULDER_X, 0.0, Q_SHOULDER_Z + 0.01), (Q_SHOULDER_X + 0.05, 0.0, Q_SHOULDER_Z)),
    "upper_arm": ((Q_SHOULDER_X, 0.0, Q_SHOULDER_Z), (Q_SHOULDER_X, 0.0, Q_ELBOW_Z)),
    "lower_arm": ((Q_SHOULDER_X, 0.0, Q_ELBOW_Z), (0.78, 0.0, Q_HAND_Z_BASE)),
    "hand": ((0.78, 0.0, Q_HAND_Z_BASE), (0.83, 0.0, Q_HAND_Z_BASE)),
    "hip": ((0.40, 0.0, Q_HIP_Z + 0.10), (0.40, 0.0, Q_HIP_Z)),
    "thigh": ((0.40, 0.0, Q_HIP_Z), (0.35, 0.0, Q_KNEE_Z_BASE)),
    "shin": ((0.35, 0.0, Q_KNEE_Z_BASE), (0.30, 0.0, Q_FOOT_Z_LAND)),
    "foot": ((0.30, 0.0, Q_FOOT_Z_LAND), (0.30, 0.0, Q_FOOT_Z_LAND + 0.05)),
}


def set_rest_pose(arm: bpy.types.Object) -> None:
    """Place every bone rest chain on the Q coordinates so the skin weights
    see rest length == pose length (no stretch when G1 drives the rig)."""
    def rest_pair(name: str, side: str) -> tuple[Vector, Vector]:
        head, tail = REST_BONES[name]
        if side == "L":
            head = (-head[0], head[1], head[2])
            tail = (-tail[0], tail[1], tail[2])
        return Vector(head), Vector(tail)

    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones = arm.data.edit_bones
    for ebone in edit_bones:
        ebone.use_connect = False
    for side in ("L", "R"):
        for name in ("shoulder", "upper_arm", "lower_arm", "hand", "hip", "thigh", "shin", "foot"):
            full = name + "." + side
            head, tail = rest_pair(name, side)
            edit_bones[full].head = head
            edit_bones[full].tail = tail
    for name in ("pelvis", "spine", "head"):
        head, tail = rest_pair(name, "R")
        edit_bones[name].head = head
        edit_bones[name].tail = tail
    bpy.ops.object.mode_set(mode="OBJECT")


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


# ---- KIIRA segment retarget maps (original world coords -> Q coords) ----

def retarget_head(v: Vector) -> Vector:
    return Vector((
        v.x * KIIRA_HEAD_SCALE,
        KIIRA_HEAD_CY + (v.y - KIIRA_HEAD_CY) * KIIRA_HEAD_SCALE,
        Q_HEAD_Z + (v.z - KIIRA_HEAD_CZ) * KIIRA_HEAD_SCALE,
    ))


def retarget_torso(v: Vector) -> Vector:
    return Vector((v.x * 1.242, v.y * 1.05, Q_PELVIS_Z + (v.z - KIIRA_PELVIS_Z) * 1.117))


def retarget_upper_arm(v: Vector, sign: float) -> Vector:
    z = 1.90 + (v.z + 0.46) * ((Q_SHOULDER_Z - Q_ELBOW_Z) / 0.446)
    x = sign * (0.55 + (abs(v.x) - 0.398) * 0.403)
    return Vector((x, v.y * 0.9, z))


def retarget_forearm(v: Vector, sign: float) -> Vector:
    z = 1.45 + (v.z + 0.963) * ((Q_ELBOW_Z - Q_HAND_Z_BASE) / 0.503)
    x = sign * (0.70 + (abs(v.x) - 0.771) * 0.5)
    return Vector((x, v.y * 0.9, z))


def retarget_hand(v: Vector, sign: float) -> Vector:
    z = 1.45 + (v.z + 1.230) * 0.4
    x = sign * (0.85 + (abs(v.x) - 1.067) * 0.5)
    return Vector((x, v.y * 0.6, z))


def retarget_thigh(v: Vector, sign: float) -> Vector:
    z = 0.70 + (v.z + 1.35) * ((Q_HIP_Z - Q_KNEE_Z_BASE) / 0.527)
    return Vector((sign * (0.05 + abs(v.x) * 0.55), v.y, z))


def retarget_shin(v: Vector, sign: float) -> Vector:
    z = 0.26 + (v.z + 2.2) * ((Q_KNEE_Z_BASE - Q_FOOT_Z_LAND) / 0.85)
    return Vector((sign * (0.03 + abs(v.x) * 0.45), v.y, z))


def retarget_foot(v: Vector) -> Vector:
    return Vector((v.x * 0.6, v.y, (v.z + 2.554) * (Q_FOOT_Z_LAND / 0.381)))


# ---- mesh helpers ----

def split_mesh(source: bpy.types.Object, keep_verts) -> bpy.types.Object:
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
    bm.to_mesh(mesh)
    bm.free()
    for group in source.vertex_groups:
        idx = obj.vertex_groups.new(name=group.name)
        for v in obj.data.vertices:
            if v.groups:
                w = next((g.weight for g in v.groups if g.group == group.index), None)
                if w is not None:
                    idx.add([v.index], w, "REPLACE")
    for modifier in source.modifiers:
        if modifier.type == "ARMATURE":
            mod = obj.modifiers.new(modifier.name, "ARMATURE")
            mod.object = modifier.object
    return obj


def retarget(obj: bpy.types.Object, fn) -> None:
    for v in obj.data.vertices:
        v.co = fn(v.co)


def rename_groups(obj: bpy.types.Object) -> None:
    for group in obj.vertex_groups:
        if group.name in BONE_MAP:
            group.name = BONE_MAP[group.name]


def keep_side(v, sign: float) -> bool:
    return (v.co.x < 0.0) if sign < 0 else (v.co.x >= 0.0)


def split_and_retarget(src: bpy.types.Object, maps: list[tuple[float, object]], fn_arm: object = None) -> list[bpy.types.Object]:
    """Split src at z thresholds; each piece retargeted with its map, then
    split left/right for limbs. `maps` = [(z_lo, retarget_fn, side_split)]."""
    pieces = []
    if len(maps) == 1:
        z_lo, fn = maps[0]
        piece = split_mesh(src, lambda v: v.co.z >= z_lo)
        pieces.append((piece, fn))
    else:
        z_lo, fn = maps[0]
        current = src
        for i, (z_next, fn_next) in enumerate(maps[1:]):
            piece = split_mesh(current, lambda v: v.co.z >= z_next)
            pieces.append((piece, fn))
            current = split_mesh(current, lambda v: v.co.z < z_next)
            fn = fn_next
        pieces.append((current, fn))
    out = []
    for piece, fn in pieces:
        retarget(piece, fn)
        out.append(piece)
    bpy.data.objects.remove(src, do_unlink=True)
    return out


def prepare_scene(contract: dict, pose_contract: PoseContract) -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    scene = bpy.context.scene
    scene.name = "AssetsLab_Q3_KIIRA_SKIN_3D_Guide"
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

    material = make_material("M_Skin", SKIN_COLOR)

    arm = None
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            arm = obj
            break
    if arm is None:
        raise RuntimeError("KIIRA armature not found")

    for obj in list(bpy.data.objects):
        if obj.type == "ARMATURE":
            continue
        if obj.type != "MESH" or obj.name == "FACE":
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        if obj.parent is not None:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    if arm.matrix_world != Matrix.Identity(4):
        arm.matrix_world = Matrix.Identity(4)
    for bone in list(arm.data.bones):
        if bone.name in BONE_MAP:
            bone.name = BONE_MAP[bone.name]
    set_rest_pose(arm)

    parts: list[bpy.types.Object] = []
    for obj in list(bpy.data.objects):
        if obj.type != "MESH":
            continue
        name = obj.name
        zs = [v.co.z for v in obj.data.vertices]
        print("Q3_DEBUG pre %-16s z[%.3f, %.3f] n=%d" % (name, min(zs), max(zs), len(zs)))
        if name == "HEAD":
            retarget(obj, retarget_head)
            assign_material(obj, material)
            smooth_shade(obj)
            rename_groups(obj)
            parts.append(obj)
        elif name == "TORSO":
            retarget(obj, retarget_torso)
            assign_material(obj, material)
            smooth_shade(obj)
            rename_groups(obj)
            parts.append(obj)
        elif name == "ARMS":
            upper = split_mesh(obj, lambda v: v.co.z >= -0.46)
            fore = split_mesh(obj, lambda v: v.co.z < -0.46)
            bpy.data.objects.remove(obj, do_unlink=True)
            for piece, fn in ((upper, retarget_upper_arm), (fore, retarget_forearm)):
                for side in (-1.0, 1.0):
                    half = split_mesh(piece, lambda v, s=side: keep_side(v, s))
                    retarget(half, lambda v, f=fn, s=side: f(v, s))
                    assign_material(half, material)
                    smooth_shade(half)
                    rename_groups(half)
                    parts.append(half)
                bpy.data.objects.remove(piece, do_unlink=True)
        elif name == "HANDS":
            for side in (-1.0, 1.0):
                half = split_mesh(obj, lambda v, s=side: keep_side(v, s))
                retarget(half, lambda v, s=side: retarget_hand(v, s))
                assign_material(half, material)
                smooth_shade(half)
                rename_groups(half)
                parts.append(half)
            bpy.data.objects.remove(obj, do_unlink=True)
        elif name == "LEGS":
            thigh = split_mesh(obj, lambda v: v.co.z >= -1.35)
            shin = split_mesh(obj, lambda v: v.co.z < -1.35)
            bpy.data.objects.remove(obj, do_unlink=True)
            for piece, fn in ((thigh, retarget_thigh), (shin, retarget_shin)):
                for side in (-1.0, 1.0):
                    half = split_mesh(piece, lambda v, s=side: keep_side(v, s))
                    retarget(half, lambda v, f=fn, s=side: f(v, s))
                    assign_material(half, material)
                    smooth_shade(half)
                    rename_groups(half)
                    parts.append(half)
                bpy.data.objects.remove(piece, do_unlink=True)
        elif name == "FEET":
            for side in (-1.0, 1.0):
                half = split_mesh(obj, lambda v, s=side: keep_side(v, s))
                retarget(half, retarget_foot)
                assign_material(half, material)
                smooth_shade(half)
                rename_groups(half)
                parts.append(half)
            bpy.data.objects.remove(obj, do_unlink=True)

    light_data = bpy.data.lights.new("KeyLight", "AREA")
    light_data.energy = 550.0
    light_data.shape = "DISK"
    light_data.size = 5.0
    light = bpy.data.objects.new("KeyLight", light_data)
    bpy.context.collection.objects.link(light)
    light.location = (3.0, -4.0, 7.0)
    point_camera(light, light.location, Vector((0.0, 0.0, 3.0)))

    return arm, parts


def build_pose_bones(rig: bpy.types.Object, joints: dict[str, Vector]) -> dict[str, tuple[Vector, Vector]]:
    bones: dict[str, tuple[Vector, Vector]] = {
        "pelvis": (joints["pelvis"], joints["pelvis"] + Vector((0.0, 0.0, 0.35))),
        "spine": (joints["pelvis"], joints["neck"]),
        "head": (joints["neck"], joints["head"]),
    }
    for side, base in (("R", "right"), ("L", "left")):
        shoulder = joints["shoulder_" + base]
        elbow = joints["elbow_" + base]
        hand = joints["hand_" + base]
        hip = joints["hip_" + base]
        knee = joints["knee_" + base]
        foot = joints["foot_" + base]
        bones["shoulder." + side] = (shoulder, shoulder + Vector((0.0, 0.05, 0.0)))
        bones["upper_arm." + side] = (shoulder, elbow)
        bones["lower_arm." + side] = (elbow, hand)
        bones["hand." + side] = (hand, hand + Vector((0.0, 0.05, 0.0)))
        bones["hip." + side] = (hip, hip + Vector((0.0, 0.05, 0.0)))
        bones["thigh." + side] = (hip, knee)
        bones["shin." + side] = (knee, foot)
        bones["foot." + side] = (foot, foot + Vector((0.0, 0.05, 0.0)))
    return bones


def pose_frame(rig: bpy.types.Object, joints: dict[str, Vector], frame: int, keyframe: bool) -> None:
    targets = build_pose_bones(rig, joints)
    pose_mats: dict[str, Matrix] = {}
    for bone_name, (head, tail) in targets.items():
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
    camera_data = bpy.data.cameras.new("GuideCameraQ3")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = contract["world_contract"]["orthographic_scale"]
    camera = bpy.data.objects.new("GuideCameraQ3", camera_data)
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


def main() -> int:
    args = cli_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    pose_contract = PoseContract(args.pose_contract)
    if contract["guide_canvas_px"] != [256, 256] or contract["runtime_canvas_px"] != [64, 64]:
        raise ValueError("Q3 requires the locked 256px guide and 64px runtime contract")
    if contract["world_contract"]["orthographic_scale"] != 6.98 or contract["world_contract"]["camera_target_z"] != 3.05:
        raise ValueError("Q3 requires ortho scale 6.98 and camera target z 3.05")
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
        "stage": "Q3_kiira_skin_weights_render",
        "guide_canvas_px": [256, 256],
        "px_per_unit": round(PX_PER_UNIT, 4),
        "depth_map": {"from": DEPTH_FROM, "to": DEPTH_TO},
        "depth_convention": "camera_plane_distance_along_view_axis",
        "directions": list(DIRECTIONS),
        "frames": pose3d_frames,
    }
    args.pose_3d.write_text(json.dumps(pose3d, indent=2), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(args.blend))
    print("Q3_BLEND_BUILD_PASS blend=%s frames=32 renders=%s pose3d=%s" % (args.blend, args.render_dir, args.pose_3d))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
