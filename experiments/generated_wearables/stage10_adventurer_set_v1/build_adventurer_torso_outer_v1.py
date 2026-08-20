from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent
STAGE9 = ROOT.parent / "stage9_hunyuan_adapter_transfer_v1"
if str(STAGE9) not in sys.path:
    sys.path.insert(0, str(STAGE9))

import build_hunyuan_jacket_adapter_v1 as compiler  # noqa: E402


compiler.GARMENT_NAME = "Wearable_Adventurer_TorsoOuterV1"
compiler.MASK_NAME = "WearableMask_AdventurerTorsoOuterV1"
compiler.SOURCE_ARM = [
    Vector((0.38, 0.0, 0.55)),
    Vector((0.62, 0.0, 0.28)),
    Vector((0.82, 0.0, 0.05)),
]
compiler.TARGET_ARM = [
    Vector((0.25, -0.005, 1.355)),
    Vector((0.34, 0.0, 1.270)),
    Vector((0.43, -0.002, 1.180)),
]
_TARGET_ARM_CALIBRATED = False

SOURCE_LOW = -0.905797
SOURCE_HIGH = 0.901176
TARGET_LOW = 0.700
TARGET_HIGH = 1.490
UPPER_SHOULDER_LIFT = 0.0
SLEEVE_ROOT_LIFT = 0.0
SLEEVE_TRANSITION_OFFSET = 0.008
OUTER_SHOULDER_RELAX = 0.035
ARM_TRANSITION_NAMES = {
    1: "ActorProfile_ArmTransition_L_ChibiActorV1",
    -1: "ActorProfile_ArmTransition_R_ChibiActorV1",
}


def arm_membership(point: Vector) -> float:
    z = min(0.65, max(0.02, point.z))
    source_arm_center_x = 0.86 - 0.82 * z
    source_torso_half = 0.45 + 0.05 * ((SOURCE_HIGH - z) / (SOURCE_HIGH - SOURCE_LOW))
    threshold = 0.5 * (source_arm_center_x + source_torso_half)
    return compiler.smoothstep(threshold - 0.055, threshold + 0.055, abs(point.x))


def calibrate_target_arm_from_actor() -> None:
    """Derive the short-sleeve centerline from the active Actor's rig."""
    global _TARGET_ARM_CALIBRATED
    if _TARGET_ARM_CALIBRATED:
        return
    armature = bpy.data.objects.get(compiler.ARMATURE_NAME)
    if armature is None:
        raise RuntimeError("Actor armature missing during sleeve calibration")
    upperarm_name = compiler.SIDE_BONES[1][1]
    forearm_name = compiler.SIDE_BONES[1][2]
    upperarm = armature.data.bones.get(upperarm_name)
    forearm = armature.data.bones.get(forearm_name)
    if upperarm is None or forearm is None:
        raise RuntimeError("Actor upperarm/forearm semantics missing during sleeve calibration")
    shoulder = armature.matrix_world @ upperarm.head_local
    elbow = armature.matrix_world @ forearm.head_local
    compiler.TARGET_ARM = [
        Vector((abs(shoulder.x), shoulder.y, shoulder.z)),
        Vector((abs(shoulder.lerp(elbow, 0.45).x), shoulder.lerp(elbow, 0.45).y, shoulder.lerp(elbow, 0.45).z)),
        Vector((abs(shoulder.lerp(elbow, 0.90).x), shoulder.lerp(elbow, 0.90).y, shoulder.lerp(elbow, 0.90).z)),
    ]
    _TARGET_ARM_CALIBRATED = True


def map_torso(point: Vector) -> Vector:
    t = (point.z - SOURCE_LOW) / (SOURCE_HIGH - SOURCE_LOW)
    z = TARGET_LOW + t * (TARGET_HIGH - TARGET_LOW)
    # The generated tunic flares at hand height.  Keep the accepted shoulder
    # width, but taper the lower shell enough that the Actor's forearms can
    # swing beside it without crossing the side seams.
    x_scale = 0.47 + 0.03 * compiler.smoothstep(0.88, 1.10, z) + 0.14 * compiler.smoothstep(1.12, 1.34, z)
    x = point.x * x_scale
    # Lift the generated shoulder bridges, not the inner collar rim.  The
    # source already has a valid neck hole, so a uniform top-shell offset
    # would move the collar toward the Actor's jaw again.
    z += (
        UPPER_SHOULDER_LIFT
        * compiler.smoothstep(1.28, 1.44, z)
        * compiler.smoothstep(0.055, 0.22, abs(x))
    )
    # The source reconstruction carries a rounded shoulder mound.  Relax only
    # the outer top shell; the inner collar rim is deliberately excluded.
    z -= (
        OUTER_SHOULDER_RELAX
        * compiler.smoothstep(1.31, 1.47, z)
        * compiler.smoothstep(0.21, 0.38, abs(x))
    )
    lower_shell = 1.0 - compiler.smoothstep(0.88, 1.12, z)
    y_scale = 0.50 - 0.045 * lower_shell
    return Vector((x, point.y * y_scale - 0.008, z))


def map_arm(point: Vector, side: int) -> tuple[Vector, float]:
    calibrate_target_arm_from_actor()
    source_xz = Vector((abs(point.x), point.z))
    parameter, source_center_xz, source_tangent = compiler.closest_polyline_parameter(
        source_xz, compiler.SOURCE_ARM
    )
    target_centers = [Vector((abs(item.x), item.y, item.z)) for item in compiler.TARGET_ARM]
    target_center, target_tangent = compiler.sample_polyline(parameter, target_centers)
    source_normal = Vector((-source_tangent.y, source_tangent.x))
    target_normal = Vector((-target_tangent.y, target_tangent.x))
    radial = (source_xz - source_center_xz).dot(source_normal)
    radial_scale = 0.40 + 0.10 * compiler.smoothstep(0.0, 0.55, parameter)
    mapped_xz = Vector((target_center.x, target_center.z)) + target_normal * (radial * radial_scale)
    mapped_xz.y -= 0.012 * (1.0 - compiler.smoothstep(0.0, 0.32, parameter))
    mapped_xz.y += SLEEVE_ROOT_LIFT * (1.0 - compiler.smoothstep(0.0, 0.28, parameter))
    return Vector((side * mapped_xz.x, point.y * 0.55 - 0.006, mapped_xz.y)), parameter


def arm_weights(parameter: float, side: int) -> dict[str, float]:
    clavicle, upperarm, forearm, _hand = compiler.SIDE_BONES[side]
    if parameter <= 0.18:
        t = parameter / 0.18
        return {clavicle: 0.72 * (1.0 - t), upperarm: 0.28 + 0.72 * t}
    t = (parameter - 0.18) / 0.82
    return {upperarm: 1.0 - 0.35 * t, forearm: 0.35 * t}


def add_actor_arm_transitions(actor: bpy.types.Object, armature: bpy.types.Object) -> dict[str, int]:
    """Compile an Actor-fitted cloth band between generated sleeve and forearm.

    Hunyuan 2mv reconstructs a watertight sleeve cap.  The garment remains the
    generated asset; this ActorProfile component extends its terminal band on
    the Actor's own arm surface and keeps the Actor's original rig weights.
    Unlike the rejected skin-coloured transition, this band uses the garment
    material and a small normal offset.  The visible forearm begins after the
    band, so the arm reads as passing through one sleeve opening.
    """
    calibrate_target_arm_from_actor()
    mask = actor.vertex_groups.get(compiler.MASK_NAME)
    if mask is None:
        raise RuntimeError("torso body mask must exist before arm transitions")
    masked_vertices = {
        vertex.index
        for vertex in actor.data.vertices
        if any(item.group == mask.index and item.weight > 0.0 for item in vertex.groups)
    }
    actor_group_names = {group.index: group.name for group in actor.vertex_groups}
    reports = {}
    for side, object_name in ARM_TRANSITION_NAMES.items():
        old = bpy.data.objects.get(object_name)
        if old is not None:
            bpy.data.objects.remove(old, do_unlink=True)
        source_faces = []
        for polygon in actor.data.polygons:
            center = actor.matrix_world @ polygon.center
            if side * center.x <= 0.0 or center.z < 0.94:
                continue
            parameter, distance = compiler.target_arm_coordinates(center, side)
            if (
                0.56 <= parameter <= 1.02
                and distance <= 0.235
                and any(index in masked_vertices for index in polygon.vertices)
            ):
                source_faces.append(polygon)

        source_indices = sorted({index for polygon in source_faces for index in polygon.vertices})
        remap = {source_index: index for index, source_index in enumerate(source_indices)}
        mesh = bpy.data.meshes.new(f"{object_name}_Mesh")
        mesh.from_pydata(
            [
                actor.data.vertices[index].co.copy()
                + actor.data.vertices[index].normal.normalized() * SLEEVE_TRANSITION_OFFSET
                for index in source_indices
            ],
            [],
            [[remap[index] for index in polygon.vertices] for polygon in source_faces],
        )
        mesh.update()
        transition = bpy.data.objects.new(object_name, mesh)
        bpy.context.collection.objects.link(transition)
        transition.matrix_world = actor.matrix_world.copy()
        garment = bpy.data.objects.get(compiler.GARMENT_NAME)
        if garment is None or not garment.data.materials:
            raise RuntimeError("generated garment material missing before arm transition")
        transition.data.materials.append(garment.data.materials[0])
        for target_polygon in transition.data.polygons:
            target_polygon.material_index = 0

        groups = {}
        for new_index, source_index in enumerate(source_indices):
            source_vertex = actor.data.vertices[source_index]
            for item in source_vertex.groups:
                name = actor_group_names.get(item.group)
                if name is None or armature.data.bones.get(name) is None:
                    continue
                group = groups.get(name)
                if group is None:
                    group = transition.vertex_groups.new(name=name)
                    groups[name] = group
                group.add([new_index], item.weight, "REPLACE")
        modifier = transition.modifiers.new("ActorArmature", "ARMATURE")
        modifier.object = armature
        modifier.use_vertex_groups = True
        transition["actor_profile_component"] = "short_sleeve_cloth_transition"
        transition["wearable_slot"] = "torso_outer"
        transition["source_actor"] = actor.name
        reports[object_name] = len(source_faces)
    return reports


def add_neck_and_arm_transitions(
    actor: bpy.types.Object,
    armature: bpy.types.Object,
) -> bpy.types.Object:
    report = add_actor_arm_transitions(actor, armature)
    neck_seal = compiler._adventurer_original_add_actor_neck_seal(actor, armature)
    neck_seal["arm_transition_face_counts"] = json.dumps(report, sort_keys=True)
    return neck_seal


def add_body_mask(actor: bpy.types.Object) -> int:
    """Hide only Actor surfaces physically covered by this short tunic.

    Stage 9's mask follows a long sleeve down to the elbow.  This slot ends at
    the upper arm, so it needs rig-semantic selection: torso and clavicle skin
    can be hidden broadly under the shell while forearms and hands remain
    visible even when they cross the chest during the walk cycle.
    """
    calibrate_target_arm_from_actor()
    existing = actor.vertex_groups.get(compiler.MASK_NAME)
    if existing is not None:
        actor.vertex_groups.remove(existing)
    group = actor.vertex_groups.new(name=compiler.MASK_NAME)
    group_names = {item.index: item.name for item in actor.vertex_groups}
    torso_bones = {"CC_Base_Waist", "CC_Base_Spine01", "CC_Base_Spine02"}
    clavicle_bones = {"CC_Base_L_Clavicle", "CC_Base_R_Clavicle"}
    upperarm_bones = {"CC_Base_L_Upperarm", "CC_Base_R_Upperarm"}
    hand_bones = {"CC_Base_L_Hand", "CC_Base_R_Hand"}

    selected: list[int] = []
    for vertex in actor.data.vertices:
        point = actor.matrix_world @ vertex.co
        weights = {
            group_names.get(item.group): item.weight
            for item in vertex.groups
            if group_names.get(item.group) is not None
        }
        torso_weight = sum(weights.get(name, 0.0) for name in torso_bones)
        clavicle_weight = sum(weights.get(name, 0.0) for name in clavicle_bones)
        upperarm_weight = sum(weights.get(name, 0.0) for name in upperarm_bones)
        hand_weight = sum(weights.get(name, 0.0) for name in hand_bones)
        upper_body_weight = torso_weight + clavicle_weight + upperarm_weight

        # A sleeve may overlap the wrist ring, but it must never hide the hand
        # to manufacture continuity.  Mixed wrist vertices remain visible as
        # soon as they carry meaningful hand ownership.
        if hand_weight >= 0.15:
            continue

        # Preserve the accepted V11 spatial core because some vertices in the
        # Actor body mesh have blended/non-torso rig semantics.  Add the
        # semantic expansion around it instead of replacing it.
        base_torso = 0.70 <= point.z <= 1.43 and abs(point.x) <= 0.34
        semantic_torso = (
            0.68 <= point.z <= 1.47
            and abs(point.x) <= 0.43
            and torso_weight >= 0.18
        )
        base_clavicle = (
            1.30 <= point.z <= 1.50
            and abs(point.x) <= 0.40
            and upper_body_weight >= 0.20
        )
        semantic_clavicle = (
            1.18 <= point.z <= 1.51
            and abs(point.x) <= 0.44
            and clavicle_weight >= 0.12
        )
        side = 1 if point.x >= 0.0 else -1
        parameter, arm_distance = compiler.target_arm_coordinates(point, side)
        # End the hidden Actor surface inside the generated sleeve.  The
        # terminal sleeve band must overlap visible Actor skin; otherwise the
        # short sleeve and the exposed forearm read as disconnected pieces.
        base_arm = 0.94 <= point.z <= 1.44 and arm_distance <= 0.235
        semantic_upperarm = (
            parameter <= 0.94
            and 1.02 <= point.z <= 1.47
            and arm_distance <= 0.255
            and (clavicle_weight + upperarm_weight) >= 0.18
        )
        if (
            base_torso
            or semantic_torso
            or base_clavicle
            or semantic_clavicle
            or base_arm
            or semantic_upperarm
        ):
            selected.append(vertex.index)
    if selected:
        group.add(selected, 1.0, "REPLACE")
    return len(selected)


compiler.arm_membership = arm_membership
compiler.map_torso = map_torso
compiler.map_arm = map_arm
compiler.arm_weights = arm_weights
compiler.add_body_mask = add_body_mask
compiler._adventurer_original_add_actor_neck_seal = compiler.add_actor_neck_seal
compiler.add_actor_neck_seal = add_neck_and_arm_transitions
compiler.UPPER_TORSO_LIFT = UPPER_SHOULDER_LIFT
compiler.SHOULDER_ARM_LIFT = SLEEVE_ROOT_LIFT


if __name__ == "__main__":
    compiler.main()
