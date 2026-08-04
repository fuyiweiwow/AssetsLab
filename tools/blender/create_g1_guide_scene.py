"""G1: key the accepted eight-frame skeleton onto the guide rig and render passes.

Run only through Blender's bundled Python.  The scene derives every joint from
the Godot-exported pose contract (g1_pose_contract.json); the front-view cycle
is the 3D authority.  For every direction/frame the script exports:

- beauty.png    EEVEE render with guide materials + key light (Raw output)
- depth.png     orthographic depth along the view axis, linear-mapped 0..1
- id.png        flat per-part colors used as the part-ID mask

Conventions (verified empirically against the locked G0 camera contract):

- Camera: orthographic, 256x256, ortho_scale 6.98, pointed at (0, 0, 3.05).
  The view layer must enable use_pass_z for the compositor Depth output.
- The compositor Depth pass reports positive distance from the camera plane
  along the view axis (background = far clip).  The scene uses the "Raw"
  view transform so PNG values are the exact linear map values.
- Screen mapping per camera: sx_px = 128 + ((P-cam) . cam_x) * PX_PER_UNIT,
  row_px  = 128 - ((P-cam) . cam_y) * PX_PER_UNIT, depth = (P-cam) . view_axis
  where cam_x/cam_y/view_axis are the camera's right/up/forward axes derived
  from (target - cam_pos).to_track_quat("-Z", "Y").

The geometry-derived expectations (projected part centroids, the part visible
at each centroid pixel via object ray casts, and its camera depth) are written
to g1_pose_3d.json so the Python validator can compare the render against the
contract without duplicating the mesh math.
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

K = 0.015          # screen px -> world units (locks floor y=470 to z=0, head y=150 to z=4.8)
PX_PER_UNIT = 256.0 / 6.98
DEPTH_FROM = 7.5
DEPTH_TO = 12.5
FRAME_COUNT = 8
DIRECTIONS = ("front", "right", "back", "left")

PARTS = (
    ("head", (0.95, 0.30, 0.30, 1.0)),
    ("torso", (0.25, 0.55, 0.95, 1.0)),
    ("pelvis", (0.95, 0.85, 0.30, 1.0)),
    ("arm_L", (0.30, 0.90, 0.40, 1.0)),
    ("arm_R", (0.90, 0.35, 0.90, 1.0)),
    ("leg_L", (0.35, 0.45, 0.95, 1.0)),
    ("leg_R", (0.95, 0.60, 0.25, 1.0)),
)

PART_OBJECT_NAMES = {
    "head": ("Head",),
    "torso": ("Torso",),
    "pelvis": ("Pelvis",),
    "arm_L": ("Shoulder.L", "UpperArm.L", "LowerArm.L", "Elbow.L", "Hand.L"),
    "arm_R": ("Shoulder.R", "UpperArm.R", "LowerArm.R", "Elbow.R", "Hand.R"),
    "leg_L": ("Thigh.L", "Shin.L", "Knee.L", "Foot.L"),
    "leg_R": ("Thigh.R", "Shin.R", "Knee.R", "Foot.R"),
}

BEAUTY_COLORS = {
    "head": (0.92, 0.94, 0.97, 1.0),
    "torso": (0.55, 0.64, 0.75, 1.0),
    "pelvis": (0.55, 0.64, 0.75, 1.0),
    "arm_L": (0.72, 0.81, 0.89, 1.0),
    "arm_R": (0.72, 0.81, 0.89, 1.0),
    "leg_L": (0.62, 0.69, 0.77, 1.0),
    "leg_R": (0.62, 0.69, 0.77, 1.0),
}

HEAD_RADIUS = 68.0 * K          # 2D skeleton head circle radius
TORSO_RADIUS = 0.30
PELVIS_RADIUS = 0.38            # belt around the lower torso; larger than TORSO_RADIUS so its
PELVIS_HALF_HEIGHT = 0.22       # surface never coincides with the torso wall (no z-fighting)
SHOULDER_RADIUS = 0.16
UPPER_ARM_RADIUS = 0.14
LOWER_ARM_RADIUS = 0.12
ELBOW_RADIUS = 0.12
HAND_RADIUS = 0.15
THIGH_RADIUS = 0.18
SHIN_RADIUS = 0.16
KNEE_RADIUS = 0.16
FOOT_RADIUS = 0.17


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--pose-contract", required=True, type=Path)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--render-dir", required=True, type=Path)
    parser.add_argument("--pose-3d", required=True, type=Path)
    return parser.parse_args(argv)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.armatures, bpy.data.lights, bpy.data.images):
        for datablock in list(datablocks):
            if datablock.users == 0 or datablock.name not in ("Render Result",):
                try:
                    datablocks.remove(datablock)
                except RuntimeError:
                    pass


def make_material(name: str, rgba: tuple[float, float, float, float], emission: bool = False) -> bpy.types.Material:
    item = bpy.data.materials.new(name)
    item.use_nodes = True
    nodes = item.node_tree.nodes
    nodes.clear()
    if emission:
        shader = nodes.new("ShaderNodeEmission")
        shader.inputs["Color"].default_value = rgba
    else:
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


def cylinder(name: str, start: Vector, end: Vector, radius: float, material: bpy.types.Material, bone_name: str, rig: bpy.types.Object) -> bpy.types.Object:
    direction = end - start
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=radius, depth=direction.length, location=(start + end) * 0.5)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(direction.normalized())
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    smooth_shade(obj)
    assign_material(obj, material)
    bind_bone(obj, bone_name, rig)
    return obj


def sphere(name: str, center: Vector, radius: float, material: bpy.types.Material, bone_name: str, rig: bpy.types.Object) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.scale = Vector((radius, radius, radius))
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth_shade(obj)
    assign_material(obj, material)
    bind_bone(obj, bone_name, rig)
    return obj


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


def build_armature(joints: dict[str, Vector]) -> bpy.types.Object:
    bpy.ops.object.armature_add(enter_editmode=True, location=(0.0, 0.0, 0.0))
    rig = bpy.context.object
    rig.name = "GuideRigG1"
    rig.data.name = "GuideRigDataG1"
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


def build_meshes(joints: dict[str, Vector], materials: dict[str, bpy.types.Material], rig: bpy.types.Object) -> dict[str, list[bpy.types.Object]]:
    part_objects: dict[str, list[bpy.types.Object]] = {part: [] for part, _ in PARTS}
    part_objects["head"].append(sphere("Head", joints["head"], HEAD_RADIUS, materials["head"], "head", rig))
    part_objects["torso"].append(cylinder("Torso", joints["pelvis"], joints["neck"], TORSO_RADIUS, materials["torso"], "spine", rig))
    pelvis_center = joints["pelvis"]
    part_objects["pelvis"].append(cylinder("Pelvis", pelvis_center + Vector((0.0, 0.0, -PELVIS_HALF_HEIGHT)), pelvis_center + Vector((0.0, 0.0, PELVIS_HALF_HEIGHT)), PELVIS_RADIUS, materials["pelvis"], "pelvis", rig))
    for side, bone_side in (("L", "left"), ("R", "right")):
        part = "arm_" + side
        part_objects[part].append(sphere("Shoulder." + side, joints["shoulder_" + bone_side], SHOULDER_RADIUS, materials[part], "upper_arm." + side, rig))
        part_objects[part].append(cylinder("UpperArm." + side, joints["shoulder_" + bone_side], joints["elbow_" + bone_side], UPPER_ARM_RADIUS, materials[part], "upper_arm." + side, rig))
        part_objects[part].append(cylinder("LowerArm." + side, joints["elbow_" + bone_side], joints["hand_" + bone_side], LOWER_ARM_RADIUS, materials[part], "lower_arm." + side, rig))
        part_objects[part].append(sphere("Elbow." + side, joints["elbow_" + bone_side], ELBOW_RADIUS, materials[part], "lower_arm." + side, rig))
        part_objects[part].append(sphere("Hand." + side, joints["hand_" + bone_side], HAND_RADIUS, materials[part], "lower_arm." + side, rig))
        part = "leg_" + side
        part_objects[part].append(cylinder("Thigh." + side, joints["hip_" + bone_side], joints["knee_" + bone_side], THIGH_RADIUS, materials[part], "thigh." + side, rig))
        part_objects[part].append(cylinder("Shin." + side, joints["knee_" + bone_side], joints["foot_" + bone_side], SHIN_RADIUS, materials[part], "shin." + side, rig))
        part_objects[part].append(sphere("Knee." + side, joints["knee_" + bone_side], KNEE_RADIUS, materials[part], "shin." + side, rig))
        part_objects[part].append(sphere("Foot." + side, joints["foot_" + bone_side], FOOT_RADIUS, materials[part], "shin." + side, rig))
    return part_objects


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
    """Return (cam_x, cam_y, view_axis): screen-right, screen-up, forward."""
    matrix = (target - camera_position).to_track_quat("-Z", "Y").to_matrix()
    return matrix @ Vector((1.0, 0.0, 0.0)), matrix @ Vector((0.0, 1.0, 0.0)), matrix @ Vector((0.0, 0.0, -1.0))


def setup_cameras(scene: bpy.types.Scene, contract: dict) -> tuple[bpy.types.Object, dict[str, dict]]:
    camera_data = bpy.data.cameras.new("GuideCameraG1")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = contract["world_contract"]["orthographic_scale"]
    camera = bpy.data.objects.new("GuideCameraG1", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    target = Vector((0.0, 0.0, contract["world_contract"]["camera_target_z"]))
    cameras = {}
    for direction, payload in contract["directions"].items():
        position = Vector(payload["camera_position"])
        cameras[direction] = {"position": position, "target": target}
    return camera, cameras


def setup_compositor(scene: bpy.types.Scene, render_dir: Path) -> tuple[bpy.types.Node, bpy.types.Node, bpy.types.Node]:
    scene.use_nodes = True
    ntree = scene.node_tree
    ntree.nodes.clear()
    render_layers = ntree.nodes.new("CompositorNodeRLayers")

    def output_node(name: str, mode: str, color_depth: str = "8") -> bpy.types.Node:
        node = ntree.nodes.new("CompositorNodeOutputFile")
        node.base_path = str(render_dir)
        slot = node.file_slots[0]
        slot.path = name
        slot.use_node_format = False
        slot.format.file_format = "PNG"
        slot.format.color_mode = mode
        slot.format.color_depth = color_depth
        slot.save_as_render = True
        return node

    beauty_out = output_node("beauty", "RGBA")
    ntree.links.new(render_layers.outputs["Image"], beauty_out.inputs[0])

    depth_map = ntree.nodes.new("CompositorNodeMapRange")
    depth_map.inputs["From Min"].default_value = DEPTH_FROM
    depth_map.inputs["From Max"].default_value = DEPTH_TO
    depth_map.inputs["To Min"].default_value = 0.0
    depth_map.inputs["To Max"].default_value = 1.0
    depth_out = output_node("depth", "BW", "16")
    ntree.links.new(render_layers.outputs["Depth"], depth_map.inputs[0])
    ntree.links.new(depth_map.outputs[0], depth_out.inputs[0])

    id_out = output_node("id", "RGBA")
    ntree.links.new(render_layers.outputs["Image"], id_out.inputs[0])
    return beauty_out, depth_out, id_out


def part_for_object(obj_name: str) -> str | None:
    for part, prefixes in PART_OBJECT_NAMES.items():
        if obj_name in prefixes:
            return part
    return None


def set_materials(id_mode: bool, materials: dict[str, bpy.types.Material]) -> None:
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        part = part_for_object(obj.name)
        if part is not None:
            assign_material(obj, materials[part])


def project(point: Vector, camera_position: Vector, cam_x: Vector, cam_y: Vector, view_axis: Vector) -> tuple[float, float, float]:
    """Map a world point to (sx_px, row_px, depth) with the locked ortho camera.

    Coordinates are in pixel-center space: a projected point at (sx, sy) is
    sampled by the pixel whose center is nearest, and EEVEE evaluates each
    pixel at its center, so the ray cast for pixel (col, row) goes through
    (col + 0.5, row + 0.5).
    """
    offset = point - camera_position
    return 128.5 + offset.dot(cam_x) * PX_PER_UNIT, 128.5 - offset.dot(cam_y) * PX_PER_UNIT, offset.dot(view_axis)


def raycast_visible(part_objects: dict[str, list[bpy.types.Object]], camera_position: Vector, cam_x: Vector, cam_y: Vector, view_axis: Vector, col: int, row: int, depsgraph) -> tuple[str | None, float | None]:
    """Nearest part and camera depth visible at the given pixel via geometry ray casts.

    The ray goes through the pixel center (col + 0.5, row + 0.5), matching how
    EEVEE samples the rendered depth/id passes.
    """
    origin = camera_position + cam_x * (col - 127.5) / PX_PER_UNIT + cam_y * (127.5 - row) / PX_PER_UNIT
    results = []
    for part, objects in part_objects.items():
        for obj in objects:
            evaluated = obj.evaluated_get(depsgraph)
            inverse = evaluated.matrix_world.inverted()
            local_origin = inverse @ origin
            local_direction = inverse.to_3x3() @ view_axis
            hit_ok, hit_local, _, _ = evaluated.ray_cast(local_origin, local_direction)
            if not hit_ok:
                continue
            hit_world = evaluated.matrix_world @ hit_local
            results.append(((hit_world - camera_position).dot(view_axis), part))
    if not results:
        return None, None
    distance, part = min(results, key=lambda item: item[0])
    return part, distance


def part_geometry(joints: dict[str, Vector]) -> dict[str, dict]:
    """Volume-weighted centroids and foot bottoms per part from posed joints."""
    def cylinder_centroid(start: Vector, end: Vector) -> Vector:
        return (start + end) * 0.5

    def volume_weighted(pieces: list[tuple[float, Vector]]) -> Vector:
        total = sum(weight for weight, _ in pieces)
        return sum((Vector(center) * weight for weight, center in pieces), Vector((0.0, 0.0, 0.0))) / total

    parts = {}
    parts["head"] = {"centroid": Vector(joints["head"]), "bottom": joints["head"].z - HEAD_RADIUS}
    parts["torso"] = {"centroid": cylinder_centroid(joints["pelvis"], joints["neck"])}
    parts["pelvis"] = {"centroid": Vector(joints["pelvis"])}
    for side, base in (("L", "left"), ("R", "right")):
        shoulder = joints["shoulder_" + base]
        elbow = joints["elbow_" + base]
        hand = joints["hand_" + base]
        hip = joints["hip_" + base]
        knee = joints["knee_" + base]
        foot = joints["foot_" + base]
        arm_volume = math.pi * (UPPER_ARM_RADIUS ** 2) * (shoulder - elbow).length + math.pi * (LOWER_ARM_RADIUS ** 2) * (elbow - hand).length
        arm_centroid = volume_weighted([
            (math.pi * (UPPER_ARM_RADIUS ** 2) * (shoulder - elbow).length, cylinder_centroid(shoulder, elbow)),
            (math.pi * (LOWER_ARM_RADIUS ** 2) * (elbow - hand).length, cylinder_centroid(elbow, hand)),
            (4.0 / 3.0 * math.pi * SHOULDER_RADIUS ** 3, shoulder),
            (4.0 / 3.0 * math.pi * ELBOW_RADIUS ** 3, elbow),
            (4.0 / 3.0 * math.pi * HAND_RADIUS ** 3, hand),
        ])
        parts["arm_" + side] = {"centroid": arm_centroid, "volume": arm_volume}
        leg_centroid = volume_weighted([
            (math.pi * (THIGH_RADIUS ** 2) * (hip - knee).length, cylinder_centroid(hip, knee)),
            (math.pi * (SHIN_RADIUS ** 2) * (knee - foot).length, cylinder_centroid(knee, foot)),
            (4.0 / 3.0 * math.pi * KNEE_RADIUS ** 3, knee),
            (4.0 / 3.0 * math.pi * FOOT_RADIUS ** 3, foot),
        ])
        parts["leg_" + side] = {"centroid": leg_centroid, "bottom": foot.z - FOOT_RADIUS, "foot": Vector(foot)}
    return parts


def build_scene(contract: dict, pose_contract: PoseContract, render_dir: Path) -> tuple[bpy.types.Object, dict[str, list[bpy.types.Object]]]:
    clear_scene()
    scene = bpy.context.scene
    scene.name = "AssetsLab_G1_3D_Guide"
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x, scene.render.resolution_y = contract["guide_canvas_px"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.render.filepath = str(render_dir / "render.png")
    scene.render.fps = FRAME_COUNT
    scene.frame_start = 0
    scene.frame_end = 31
    scene.view_layers[0].use_pass_z = True
    scene.view_settings.view_transform = "Raw"
    try:
        scene.view_settings.look = "None"
    except TypeError:
        pass

    materials = {}
    for part, rgba in PARTS:
        materials[part] = make_material("M_Beauty_" + part, BEAUTY_COLORS[part])
    id_materials = {}
    for part, rgba in PARTS:
        id_materials[part] = make_material("M_ID_" + part, rgba, emission=True)

    joints0 = compute_joints(pose_contract, 0)
    rig = build_armature(joints0)
    part_objects = build_meshes(joints0, materials, rig)

    light_data = bpy.data.lights.new("KeyLight", "AREA")
    light_data.energy = 550.0
    light_data.shape = "DISK"
    light_data.size = 5.0
    light = bpy.data.objects.new("KeyLight", light_data)
    bpy.context.collection.objects.link(light)
    light.location = (3.0, -4.0, 7.0)
    point_camera(light, light.location, Vector((0.0, 0.0, 3.0)))

    return rig, part_objects


def main() -> int:
    args = cli_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    pose_contract = PoseContract(args.pose_contract)
    if contract["guide_canvas_px"] != [256, 256] or contract["runtime_canvas_px"] != [64, 64]:
        raise ValueError("G1 requires the locked 256px guide and 64px runtime contract")
    if contract["world_contract"]["orthographic_scale"] != 6.98 or contract["world_contract"]["camera_target_z"] != 3.05:
        raise ValueError("G1 requires ortho scale 6.98 and camera target z 3.05")
    args.blend.parent.mkdir(parents=True, exist_ok=True)
    args.render_dir.mkdir(parents=True, exist_ok=True)
    args.pose_3d.parent.mkdir(parents=True, exist_ok=True)

    scene = bpy.context.scene
    rig, part_objects = build_scene(contract, pose_contract, args.render_dir)
    camera, cameras = setup_cameras(scene, contract)
    scene.camera = camera
    beauty_out, depth_out, id_out = setup_compositor(scene, args.render_dir)
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
            joints = compute_joints(pose_contract, frame_index)
            scene.frame_set(frame_number)
            pose_frame(rig, joints, frame_number, keyframe=True)
            depsgraph.update()

            geometry = part_geometry(joints)
            expected = []
            for part, payload in geometry.items():
                centroid = payload["centroid"]
                sx, sy, cdepth = project(centroid, camera_position, cam_x, cam_y, view_axis)
                col, row = int(round(sx)), int(round(sy))
                visible_part, visible_depth = raycast_visible(part_objects, camera_position, cam_x, cam_y, view_axis, col, row, depsgraph)
                entry = {
                    "part": part,
                    "centroid_px": [round(sx, 2), round(sy, 2)],
                    "depth_px": [col, row],
                    "depth": round(cdepth, 3),
                    "visible_part": visible_part,
                    "visible_depth": round(visible_depth, 3) if visible_depth is not None else None,
                }
                if "bottom" in payload:
                    entry["bottom_px"] = round(project(Vector((centroid.x, centroid.y, payload["bottom"])), camera_position, cam_x, cam_y, view_axis)[1], 2)
                expected.append(entry)

            beauty_out.mute = False
            depth_out.mute = False
            id_out.mute = True
            set_materials(False, {part: bpy.data.materials["M_Beauty_" + part] for part, _ in PARTS})
            bpy.ops.render.render(write_still=True)

            beauty_out.mute = True
            depth_out.mute = True
            id_out.mute = False
            set_materials(True, {part: bpy.data.materials["M_ID_" + part] for part, _ in PARTS})
            bpy.ops.render.render(write_still=True)

            cell_dir = args.render_dir / direction / ("frame_%02d" % frame_index)
            cell_dir.mkdir(parents=True, exist_ok=True)
            for name, target in (("beauty", "beauty.png"), ("depth", "depth.png"), ("id", "id.png")):
                source = args.render_dir / ("%s%04d.png" % (name, frame_number))
                if not source.is_file():
                    raise RuntimeError("missing %s output for %s frame %d" % (name, direction, frame_index))
                shutil.move(str(source), str(cell_dir / target))

            pose3d_frames.append({
                "direction": direction,
                "frame": frame_index,
                "joints_3d": {name: [round(v[0], 3), round(v[1], 3), round(v[2], 3)] for name, v in joints.items()},
                "expected": expected,
            })

    pose3d = {
        "schema": "assetslab_3d_guide_v1_pose_3d",
        "stage": "G1_eight_frame_pose_and_part_masks",
        "guide_canvas_px": [256, 256],
        "px_per_unit": round(PX_PER_UNIT, 4),
        "depth_map": {"from": DEPTH_FROM, "to": DEPTH_TO},
        "depth_convention": "camera_plane_distance_along_view_axis",
        "parts": [{"id": part, "color": [int(round(c * 255)) for c in rgba[:3]]} for part, rgba in PARTS],
        "directions": list(DIRECTIONS),
        "frames": pose3d_frames,
    }
    args.pose_3d.write_text(json.dumps(pose3d, indent=2), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(args.blend))
    print("G1_BLEND_BUILD_PASS blend=%s frames=32 renders=%s pose3d=%s" % (args.blend, args.render_dir, args.pose_3d))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
