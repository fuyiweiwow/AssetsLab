"""Transfer the fitted GarmentCode shirt to the Q-style Actor.

The source is already body-surface-fitted on the matching GarmentCode body.
This pass only performs deterministic cage-bounds fitting, Actor-surface
clearance, and nearest-vertex weight transfer. No Cloth simulation is used.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from build_clothes_fit_candidate import DIRECTIONS  # noqa: E402
from fit_clothing_to_actor_cage import transfer_actor_weights  # noqa: E402
from render_eye_assembly_blink_walk import configure_lighting, visible_bounds  # noqa: E402
from render_procedural_anime_eye_on_accurig import make_camera  # noqa: E402


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor-blend", required=True, type=Path)
    parser.add_argument("--cage-blend", required=True, type=Path)
    parser.add_argument("--garment-kind", choices=("shirt", "pants"), default="shirt")
    parser.add_argument(
        "--pants-weight-mode",
        choices=("segmented", "pelvis"),
        default="segmented",
        help="segmented pelvis/thigh weights for walk motion, or pelvis-only stability diagnostic",
    )
    parser.add_argument(
        "--pants-waist-profile",
        choices=("pelvis", "highrise"),
        default="pelvis",
        help="fit the pants top to the pelvis tail or the pelvis-to-Spine01 waist region",
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--fitted-blend", type=Path)
    source_group.add_argument("--fitted-obj", type=Path, help="official GarmentCode sim.obj")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--clearance", type=float, default=0.025)
    parser.add_argument("--width-factor", type=float, default=0.95)
    parser.add_argument("--depth-factor", type=float, default=1.0)
    parser.add_argument("--width-margin", type=float, default=0.04)
    parser.add_argument("--depth-margin", type=float, default=0.05)
    parser.add_argument("--skip-surface-fit", action="store_true")
    parser.add_argument(
        "--post-armature-clearance",
        action="store_true",
        help="add a live post-armature outside shrinkwrap for pants walk clearance",
    )
    parser.add_argument(
        "--post-armature-projection",
        action="store_true",
        help="use live bidirectional X/Y projection after armature deformation",
    )
    parser.add_argument("--skip-rig", action="store_true")
    parser.add_argument("--projection", choices=("nearest", "raycast"), default="nearest")
    parser.add_argument(
        "--project-side-x",
        action="store_true",
        help="allow raycast projection to Actor arm/side surfaces; off for sleeveless torso garments",
    )
    parser.add_argument(
        "--projection-max-z",
        type=float,
        default=0.0,
        help="upper Z limit for raycast projection; 0 uses the Actor shoulder height",
    )
    parser.add_argument(
        "--skip-upper-weight-repair",
        action="store_true",
        help="keep nearest-Actor head weights on upper garment vertices",
    )
    parser.add_argument("--surface-target", default="", help="comma-separated mesh objects used for side-preserving projection")
    parser.add_argument(
        "--preserve-sleeve-edges",
        action="store_true",
        help="leave short-sleeve cuff vertices in the fitted shape instead of per-vertex projection",
    )
    parser.add_argument("--debug-hide-actor", action="store_true")
    parser.add_argument("--depth-bias", type=float, default=0.0)
    parser.add_argument(
        "--pants-front-clearance",
        type=float,
        default=0.0,
        help="push only the camera-facing pants panel outward; preserves the back and side profile",
    )
    parser.add_argument(
        "--pants-crotch-band-below",
        type=float,
        default=0.11,
        help="distance above the pants hem where the pelvis-owned crotch bridge ends",
    )
    parser.add_argument("--resolution", type=int, default=256)
    parser.add_argument(
        "--smooth-shading",
        action="store_true",
        help="use smooth polygon normals on the transferred garment for a shading diagnostic",
    )
    parser.add_argument("--obj-scale", type=float, default=0.01)
    parser.add_argument(
        "--obj-orientation",
        choices=("garmentcode", "garmentcode_y_front", "garmentcode_neg_z_front", "blender"),
        default="garmentcode",
        help="Coordinate convention for fitted OBJ; official GarmentCode uses X width, Y depth, Z up",
    )
    parser.add_argument("--front-flatten", type=float, default=0.0)
    parser.add_argument("--back-clearance", type=float, default=0.0)
    parser.add_argument("--sleeve-clearance", type=float, default=0.0)
    parser.add_argument(
        "--skip-bone-shoulder-fit",
        action="store_true",
        help="disable the Actor upper-arm/torso shoulder-region fit",
    )
    parser.add_argument("--shoulder-ease", type=float, default=0.055)
    parser.add_argument("--shoulder-band-below", type=float, default=0.20)
    parser.add_argument("--shoulder-band-above", type=float, default=0.10)
    parser.add_argument(
        "--pelvis-hem-clearance",
        type=float,
        default=0.03,
        help="keep the top garment hem this far above the CC_Base_Pelvis tail",
    )
    parser.add_argument(
        "--skip-pelvis-hem-fit",
        action="store_true",
        help="keep the legacy cage torso bottom instead of the pelvis-bone hem",
    )
    return parser.parse_args(argv)


def mesh_world_points(obj: bpy.types.Object) -> list[Vector]:
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def region_bounds(cage: bpy.types.Object, bottom_z: float, top_z: float) -> tuple[Vector, Vector]:
    points = [point for point in mesh_world_points(cage) if bottom_z <= point.z <= top_z]
    if not points:
        raise RuntimeError("Actor cage has no torso points")
    return (
        Vector((min(point.x for point in points), min(point.y for point in points), bottom_z)),
        Vector((max(point.x for point in points), max(point.y for point in points), top_z)),
    )


PANTS_BODY_BONES = {
    "CC_Base_Pelvis",
    "CC_Base_L_Thigh",
    "CC_Base_R_Thigh",
}


def weighted_region_bounds(
    actor: bpy.types.Object,
    bottom_z: float,
    top_z: float,
    bone_names: set[str],
) -> tuple[Vector, Vector]:
    """Measure a clothing region from body weights, excluding arms/hands."""
    group_names = {group.index: group.name for group in actor.vertex_groups}
    points = []
    for vertex in actor.data.vertices:
        if not any(
            group_names.get(assignment.group) in bone_names and assignment.weight >= 0.20
            for assignment in vertex.groups
        ):
            continue
        point = actor.matrix_world @ vertex.co
        if bottom_z <= point.z <= top_z:
            points.append(point)
    if not points:
        raise RuntimeError("Actor has no weighted pants-body points in the requested z range")
    return (
        Vector((min(point.x for point in points), min(point.y for point in points), bottom_z)),
        Vector((max(point.x for point in points), max(point.y for point in points), top_z)),
    )


def object_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = mesh_world_points(obj)
    return (
        Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points))),
        Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points))),
    )


def fit_matrix(source_low: Vector, source_high: Vector, target_low: Vector, target_high: Vector) -> Matrix:
    source_size = source_high - source_low
    target_size = target_high - target_low
    if min(source_size.x, source_size.y, source_size.z) <= 1e-5:
        raise RuntimeError(f"source garment has degenerate bounds: {source_size}")
    scale = Vector((target_size.x / source_size.x, target_size.y / source_size.y, target_size.z / source_size.z))
    return (
        Matrix.Translation((target_low + target_high) * 0.5)
        @ Matrix.Diagonal((*scale, 1.0))
        @ Matrix.Translation(-(source_low + source_high) * 0.5)
    )


def load_fitted_garment(source_blend: Path, scene: bpy.types.Scene) -> bpy.types.Object:
    with bpy.data.libraries.load(str(source_blend.resolve()), link=False) as (data_from, data_to):
        wanted = "GarmentCodeNativeBoxMeshTshirt_Fitted"
        if wanted not in data_from.objects:
            raise RuntimeError(f"fitted blend is missing {wanted}")
        data_to.objects = [wanted]
    garment = data_to.objects[0]
    scene.collection.objects.link(garment)
    garment.name = "GarmentCodeShirt_ActorTransfer"
    return garment


def load_fitted_obj(
    source_obj: Path,
    scene: bpy.types.Scene,
    scale: float,
    orientation: str,
) -> bpy.types.Object:
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(source_obj.resolve()))
    imported = [obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH"]
    if not imported:
        raise RuntimeError(f"official GarmentCode OBJ produced no mesh: {source_obj}")
    garment = imported[-1]
    garment.name = "GarmentCodeShirt_ActorTransfer"
    garment.scale = (scale, scale, scale)
    if orientation == "garmentcode":
        # GarmentCode: X right, Y up, Z front. Actor Blender: X right,
        # Y depth (front is -Y), Z up. Rx(+90deg) gives (X, -Z, Y).
        garment.rotation_euler.x = math.radians(90.0)
    elif orientation == "garmentcode_y_front":
        # Official GarmentCode scene/render data uses X=width, Y=depth
        # (front camera at +Y), Z=up. Actor uses -Y as camera-facing front.
        # Reflect only depth so the demo front and back panels stay vertical.
        for vertex in garment.data.vertices:
            vertex.co.y = -vertex.co.y
        garment.data.update()
    elif orientation == "garmentcode_neg_z_front":
        # Some GarmentCode exports place the camera-facing front on -Z.
        # Rx(-90deg) maps that side to Actor -Y; keep this explicit so the
        # demo front/back coverage can be validated instead of guessed.
        garment.rotation_euler.x = math.radians(-90.0)
    return garment


def apply_actor_surface_fit(garment: bpy.types.Object, actor: bpy.types.Object, clearance: float) -> None:
    modifier = garment.modifiers.new("ActorSurfaceClearance", "SHRINKWRAP")
    modifier.target = actor
    modifier.wrap_method = "NEAREST_SURFACEPOINT"
    modifier.wrap_mode = "OUTSIDE"
    modifier.offset = clearance
    bpy.context.view_layer.objects.active = garment
    garment.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    garment.select_set(False)


def apply_smooth_shading(garment: bpy.types.Object) -> int:
    """Smooth only polygon normals; do not alter garment geometry."""
    for polygon in garment.data.polygons:
        polygon.use_smooth = True
    garment.data.update()
    return len(garment.data.polygons)


def evaluated_world_points(obj: bpy.types.Object) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def project_to_actor_sides(
    garment: bpy.types.Object,
    targets: list[bpy.types.Object],
    clearance: float,
    preserve_sleeve_edges: bool = False,
    project_side_x: bool = True,
    max_projection_z: float | None = None,
) -> int:
    """Project each garment vertex from its current side onto the Actor.

    Unlike nearest-surface shrinkwrap, this never lets a front vertex choose a
    back/side surface simply because it is geometrically closer.
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    actor_points: list[Vector] = []
    actor_faces: list[tuple[int, int, int]] = []
    for target in targets:
        target_eval = target.evaluated_get(depsgraph)
        target_mesh = target_eval.to_mesh()
        base = len(actor_points)
        actor_points.extend(target_eval.matrix_world @ vertex.co for vertex in target_mesh.vertices)
        actor_faces.extend(tuple(base + index for index in polygon.vertices) for polygon in target_mesh.polygons)
        target_eval.to_mesh_clear()
    tree = BVHTree.FromPolygons(actor_points, actor_faces)
    low = Vector((min(point.x for point in actor_points), min(point.y for point in actor_points), min(point.z for point in actor_points)))
    high = Vector((max(point.x for point in actor_points), max(point.y for point in actor_points), max(point.z for point in actor_points)))
    center = (low + high) * 0.5
    half = (high - low) * 0.5
    changed = 0
    for vertex in garment.data.vertices:
        world = garment.matrix_world @ vertex.co
        if max_projection_z is not None and world.z > max_projection_z:
            continue
        # The official shirt's short sleeves already have a coherent cuff
        # shape.  Projecting every cuff vertex independently onto the Actor
        # arm produces the visible split at the upper arm, so the corrective
        # pass leaves the outer sleeve band in its fitted shape.
        if preserve_sleeve_edges and abs(world.x - center.x) > half.x * 0.72 and center.z - half.z * 0.28 < world.z < center.z + half.z * 0.18:
            continue
        nx = abs((world.x - center.x) / max(half.x, 1e-5))
        ny = abs((world.y - center.y) / max(half.y, 1e-5))
        if not project_side_x and nx > ny:
            # Side rays hit the Actor's arms/hands at the lower torso levels.
            # The bone torso profile already supplies the correct lateral
            # limit, so leave these vertices in that profile and only project
            # front/back vertices below.
            continue
        if ny >= nx:
            outward = Vector((0.0, -1.0 if world.y < center.y else 1.0, 0.0))
        else:
            outward = Vector((-1.0 if world.x < center.x else 1.0, 0.0, 0.0))
        origin = world + outward * 2.0
        location, normal, face_index, distance = tree.ray_cast(origin, -outward, 4.0)
        if location is None:
            continue
        # Keep the garment's tangential shape. Only push a vertex outward
        # when the affine-fit garment is inside the target surface.
        world_after = world.copy()
        if outward.y < 0.0:
            desired = location.y - clearance
            if world.y > desired:
                world_after.y = desired
        elif outward.y > 0.0:
            desired = location.y + clearance
            if world.y < desired:
                world_after.y = desired
        elif outward.x < 0.0:
            desired = location.x - clearance
            if world.x > desired:
                world_after.x = desired
        else:
            desired = location.x + clearance
            if world.x < desired:
                world_after.x = desired
        if world_after != world:
            vertex.co = garment.matrix_world.inverted() @ world_after
            changed += 1
    garment.data.update()
    return changed


def project_pants_depth(
    garment: bpy.types.Object,
    targets: list[bpy.types.Object],
    clearance: float,
) -> int:
    """Fit pants depth without allowing a front panel to select the back.

    The generic nearest-surface shrinkwrap is unsafe for a garment with two
    legs: a front vertex near the crotch can be closer to the opposite/back
    body surface than to the intended front surface.  Pants keep their
    actor-space X/Z outline and are projected only along Y, separately from
    the front and back sides.
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    actor_points: list[Vector] = []
    actor_faces: list[tuple[int, int, int]] = []
    for target in targets:
        target_eval = target.evaluated_get(depsgraph)
        target_mesh = target_eval.to_mesh()
        base = len(actor_points)
        actor_points.extend(target_eval.matrix_world @ vertex.co for vertex in target_mesh.vertices)
        actor_faces.extend(tuple(base + index for index in polygon.vertices) for polygon in target_mesh.polygons)
        target_eval.to_mesh_clear()
    tree = BVHTree.FromPolygons(actor_points, actor_faces)
    center_y = (min(point.y for point in actor_points) + max(point.y for point in actor_points)) * 0.5
    inverse = garment.matrix_world.inverted()
    changed = 0
    for vertex in garment.data.vertices:
        world = garment.matrix_world @ vertex.co
        outward = Vector((0.0, -1.0 if world.y <= center_y else 1.0, 0.0))
        origin = world + outward * 2.0
        location, _normal, _face_index, _distance = tree.ray_cast(origin, -outward, 4.0)
        if location is None:
            continue
        desired_y = location.y - clearance if outward.y < 0.0 else location.y + clearance
        if outward.y < 0.0:
            if world.y > desired_y:
                world.y = desired_y
        elif world.y < desired_y:
            world.y = desired_y
        else:
            continue
        vertex.co = inverse @ world
        changed += 1
    garment.data.update()
    return changed


def fit_pants_width_profile(
    garment: bpy.types.Object,
    actor: bpy.types.Object,
    pants_bottom_z: float,
    pelvis_top_z: float,
    clearance: float,
) -> dict[str, object]:
    """Expand only the narrow parts of a shorts silhouette to the Actor.

    The official shorts preserve their source body's vertical silhouette. A
    global X scale makes the hem too wide while leaving the waist and upper
    thigh too narrow, so the body hides those panels in side views. Sample the
    Actor's pelvis/thigh envelope per height and expand the garment around its
    center only when its current half-width is smaller.
    """
    actor_points = mesh_world_points(actor)
    step = 0.025
    samples: list[tuple[float, float]] = []
    sample_z = pants_bottom_z
    while sample_z <= pelvis_top_z + 1e-6:
        points = [
            point
            for point in actor_points
            if abs(point.z - sample_z) <= 0.018 and abs(point.x) <= 0.40
        ]
        if points:
            samples.append((sample_z, max(abs(point.x) for point in points) + clearance))
        sample_z += step
    if not samples:
        return {"status": "skipped", "reason": "no_actor_pelvis_thigh_samples"}

    def actor_half_width(z: float) -> float:
        if z <= samples[0][0]:
            return samples[0][1]
        if z >= samples[-1][0]:
            return samples[-1][1]
        for (z0, w0), (z1, w1) in zip(samples, samples[1:]):
            if z0 <= z <= z1:
                ratio = (z - z0) / max(z1 - z0, 1e-6)
                return w0 + (w1 - w0) * ratio
        return samples[-1][1]

    garment_points = [garment.matrix_world @ vertex.co for vertex in garment.data.vertices]
    source_bins: dict[int, float] = {}
    for point in garment_points:
        key = round(point.z / step)
        source_bins[key] = max(source_bins.get(key, 0.0), abs(point.x))

    def source_half_width(z: float) -> float:
        key = round(z / step)
        if key in source_bins:
            return source_bins[key]
        nearby = [width for index, width in source_bins.items() if abs(index * step - z) <= step * 1.5]
        return max(nearby, default=1e-5)

    inverse = garment.matrix_world.inverted()
    changed = 0
    max_scale = 1.35
    scale_samples: list[tuple[float, float]] = []
    for vertex in garment.data.vertices:
        world = garment.matrix_world @ vertex.co
        if not pants_bottom_z - 0.02 <= world.z <= pelvis_top_z + 0.02:
            continue
        source_half = max(source_half_width(world.z), 1e-5)
        target_half = actor_half_width(world.z)
        scale = min(max_scale, max(1.0, target_half / source_half))
        scale_samples.append((world.z, scale))
        if scale <= 1.0001:
            continue
        world.x *= scale
        vertex.co = inverse @ world
        changed += 1
    garment.data.update()
    return {
        "status": "applied",
        "changed_vertices": changed,
        "max_scale": max((scale for _z, scale in scale_samples), default=1.0),
        "sample_step": step,
        "clearance": clearance,
        "samples": [[round(z, 4), round(width, 4)] for z, width in samples],
    }


def add_post_armature_clearance(
    garment: bpy.types.Object,
    actor: bpy.types.Object,
    clearance: float,
    projection: bool = False,
    lower_bound_z: float | None = None,
) -> str:
    """Keep a rigged pants surface outside the animated Actor mesh."""
    modifier = garment.modifiers.new("AnimatedActorOutsideClearance", "SHRINKWRAP")
    modifier.target = actor
    modifier.wrap_method = "PROJECT" if projection else "NEAREST_SURFACEPOINT"
    modifier.wrap_mode = "OUTSIDE"
    modifier.offset = clearance
    if projection:
        modifier.use_project_x = True
        modifier.use_project_y = True
        modifier.use_negative_direction = True
        modifier.use_positive_direction = True
    if lower_bound_z is not None:
        group = garment.vertex_groups.get("PantsLowerClearance") or garment.vertex_groups.new(
            name="PantsLowerClearance"
        )
        for vertex in garment.data.vertices:
            world = garment.matrix_world @ vertex.co
            if world.z <= lower_bound_z:
                group.add([vertex.index], 1.0, "REPLACE")
        modifier.vertex_group = group.name
    return modifier.name


def material() -> bpy.types.Material:
    result = bpy.data.materials.new("GarmentCodeActorTransferCotton")
    result.diffuse_color = (0.12, 0.36, 0.72, 1.0)
    result.use_nodes = True
    shader = result.node_tree.nodes.get("Principled BSDF")
    if shader:
        shader.inputs["Base Color"].default_value = (0.12, 0.36, 0.72, 1.0)
        shader.inputs["Roughness"].default_value = 0.86
    return result


def apply_surface_bias(
    garment: bpy.types.Object,
    front_flatten: float,
    back_clearance: float,
    sleeve_clearance: float,
) -> int:
    """Apply small actor-space corrections after projection.

    These are deliberately millimetre-scale review controls. They are not a
    replacement for generating a pattern against the Actor body.
    """
    if max(front_flatten, back_clearance, sleeve_clearance) <= 0.0:
        return 0
    low, high = object_bounds(garment)
    center = (low + high) * 0.5
    half = (high - low) * 0.5
    changed = 0
    inverse = garment.matrix_world.inverted()
    for vertex in garment.data.vertices:
        world = garment.matrix_world @ vertex.co
        delta = Vector((0.0, 0.0, 0.0))
        if front_flatten > 0.0 and world.y < center.y and abs(world.x - center.x) < half.x * 0.68:
            if low.z + half.z * 0.15 < world.z < high.z - half.z * 0.12:
                delta.y += front_flatten
        if back_clearance > 0.0 and world.y > center.y:
            delta.y += back_clearance
        if sleeve_clearance > 0.0 and abs(world.x - center.x) > half.x * 0.60:
            if low.z + half.z * 0.18 < world.z < high.z - half.z * 0.20:
                delta.x += sleeve_clearance if world.x >= center.x else -sleeve_clearance
        if delta.length > 0.0:
            vertex.co = inverse @ (world + delta)
            changed += 1
    garment.data.update()
    return changed


def apply_pants_front_clearance(garment: bpy.types.Object, amount: float) -> int:
    """Push only the front pants panel toward the Actor camera.

    The official Pants simulation has a continuous front crotch panel.  A
    whole-object depth bias fixes an occluded front panel but also floats the
    side hem; this localized correction keeps the back and side silhouette.
    """
    if amount <= 0.0:
        return 0
    low, high = object_bounds(garment)
    center_y = (low.y + high.y) * 0.5
    half_y = max((high.y - low.y) * 0.5, 1e-5)
    center_x = (low.x + high.x) * 0.5
    half_x = max((high.x - low.x) * 0.5, 1e-5)
    inverse = garment.matrix_world.inverted()
    changed = 0
    for vertex in garment.data.vertices:
        world = garment.matrix_world @ vertex.co
        frontness = max(0.0, min(1.0, (center_y - world.y) / half_y))
        if frontness <= 0.0:
            continue
        # Restrict the correction to the front-center/crotch bridge.  Moving
        # the complete front half fixes occlusion but floats the side hem.
        center_factor = max(0.0, min(1.0, 1.0 - abs(world.x - center_x) / (half_x * 0.50)))
        weight = frontness * frontness * center_factor * center_factor
        if weight <= 1e-5:
            continue
        world.y -= amount * weight
        vertex.co = inverse @ world
        changed += 1
    garment.data.update()
    return changed


def _bone_point(armature: bpy.types.Object, name: str, tail: bool = False) -> Vector:
    bone = armature.data.bones.get(name)
    if bone is None:
        raise RuntimeError(f"Actor armature is missing required bone: {name}")
    return armature.matrix_world @ (bone.tail_local if tail else bone.head_local)


def repair_upper_garment_weights(
    garment: bpy.types.Object,
    shoulder_z: float,
    band_below: float = 0.05,
) -> dict[str, object]:
    """Keep a collar from inheriting the Actor head's deformation.

    Nearest-vertex transfer is useful for the torso but can select the head
    around a high collar.  A shirt collar follows the neck/chest transition,
    not the head, so redistribute any head weight in the shoulder band to the
    neck and upper-spine groups and normalize each affected vertex.
    """
    head = garment.vertex_groups.get("CC_Base_Head")
    neck = garment.vertex_groups.get("CC_Base_NeckTwist01")
    spine = garment.vertex_groups.get("CC_Base_Spine02")
    if head is None or neck is None or spine is None:
        return {"repaired_vertices": 0, "head_weight_removed": 0.0, "status": "groups_missing"}
    repaired = 0
    removed_weight = 0.0
    for vertex in garment.data.vertices:
        world = garment.matrix_world @ vertex.co
        if world.z < shoulder_z - band_below:
            continue
        head_weight = next(
            (item.weight for item in vertex.groups if item.group == head.index),
            0.0,
        )
        if head_weight <= 1e-6:
            continue
        head.remove([vertex.index])
        neck.add([vertex.index], head_weight * 0.70, "ADD")
        spine.add([vertex.index], head_weight * 0.30, "ADD")
        repaired += 1
        removed_weight += head_weight
    return {
        "repaired_vertices": repaired,
        "head_weight_removed": removed_weight,
        "band_low_z": shoulder_z - band_below,
        "status": "applied",
    }


def assign_segmented_pants_weights(
    garment: bpy.types.Object,
    armature: bpy.types.Object,
    pants_bottom_z: float,
    pelvis_top_z: float,
    mode: str = "segmented",
    waist_top_z: float | None = None,
    waist_profile: str = "pelvis",
    crotch_band_below: float = 0.11,
) -> dict[str, object]:
    """Give the waistband pelvis weights and each leg its matching thigh.

    Nearest-Actor transfer is unsafe for shorts: a waistband vertex can pick
    up an arm or torso weight, while a leg vertex can pick up the opposite
    thigh across the crotch. That produces the torn fragments seen during
    walk frames. Shorts have a simple semantic rig, so assign it directly.
    """
    pelvis_name = "CC_Base_Pelvis"
    thigh_candidates = ["CC_Base_L_Thigh", "CC_Base_R_Thigh"]
    if armature.data.bones.get(pelvis_name) is None or any(
        armature.data.bones.get(name) is None for name in thigh_candidates
    ):
        raise RuntimeError("Actor pants bones are incomplete")
    positive_name, negative_name = sorted(
        thigh_candidates,
        key=lambda name: (armature.matrix_world @ armature.data.bones[name].head_local).x,
        reverse=True,
    )
    for group in list(garment.vertex_groups):
        garment.vertex_groups.remove(group)
    pelvis = garment.vertex_groups.new(name=pelvis_name)
    positive = garment.vertex_groups.new(name=positive_name)
    negative = garment.vertex_groups.new(name=negative_name)
    spine = None
    spine_name = "CC_Base_Spine01"
    if waist_profile == "highrise":
        if armature.data.bones.get(spine_name) is None or waist_top_z is None:
            raise RuntimeError("highrise pants require CC_Base_Spine01 and a waist top height")
        spine = garment.vertex_groups.new(name=spine_name)
    if mode == "pelvis":
        indices = [vertex.index for vertex in garment.data.vertices]
        pelvis.add(indices, 1.0, "REPLACE")
        return {
            "method": "diagnostic_pants_rig_pelvis_only",
            "pelvis_top_z": pelvis_top_z,
            "pants_bottom_z": pants_bottom_z,
            "vertex_assignment_counts": {"pelvis": len(indices), positive_name: 0, negative_name: 0},
            "status": "applied",
        }
    top_band = 0.075
    transition_band = 0.105
    # GarmentCode's Pants demo keeps the front/back crotch panels continuous
    # into the pelvis before the left/right leg panels separate.  A narrow
    # x=0 split with thigh weights makes the seam open during a walk pose.
    # Keep a wider pelvis-owned crotch bridge down to just above the hem.
    center_band = 0.085
    if crotch_band_below < 0.0:
        raise RuntimeError("pants crotch band distance must be non-negative")
    crotch_band_bottom = pants_bottom_z + crotch_band_below
    assigned = {"pelvis": 0, positive_name: 0, negative_name: 0}
    if spine is not None:
        assigned[spine_name] = 0
    for vertex in garment.data.vertices:
        world = garment.matrix_world @ vertex.co
        if spine is not None and world.z >= waist_top_z - 0.06:
            spine.add([vertex.index], 0.70, "REPLACE")
            pelvis.add([vertex.index], 0.30, "ADD")
            assigned[spine_name] += 1
            continue
        if spine is not None and world.z >= waist_top_z - 0.14:
            ratio = max(0.0, min(1.0, (world.z - (waist_top_z - 0.14)) / 0.08))
            spine_weight = 0.70 * ratio
            if spine_weight > 1e-5:
                spine.add([vertex.index], spine_weight, "REPLACE")
                pelvis.add([vertex.index], 1.0 - spine_weight, "REPLACE")
                assigned[spine_name] += 1
            else:
                pelvis.add([vertex.index], 1.0, "REPLACE")
            assigned["pelvis"] += 1
            continue
        if world.z >= pelvis_top_z - top_band:
            pelvis.add([vertex.index], 1.0, "REPLACE")
            assigned["pelvis"] += 1
            continue
        if world.z >= crotch_band_bottom and abs(world.x) <= center_band:
            pelvis.add([vertex.index], 1.0, "REPLACE")
            assigned["pelvis"] += 1
            continue
        side_group = positive if world.x >= 0.0 else negative
        side_name = positive_name if world.x >= 0.0 else negative_name
        side_weight = min(1.0, max(0.0, (pelvis_top_z - world.z) / transition_band))
        pelvis_weight = 1.0 - side_weight
        if pelvis_weight > 1e-5:
            pelvis.add([vertex.index], pelvis_weight, "REPLACE")
        side_group.add([vertex.index], side_weight, "REPLACE")
        assigned[side_name] += 1
    return {
        "method": "semantic_pants_rig_pelvis_waistband_plus_side_thighs",
        "pelvis_top_z": pelvis_top_z,
        "pants_bottom_z": pants_bottom_z,
        "positive_thigh": positive_name,
        "negative_thigh": negative_name,
        "vertex_assignment_counts": assigned,
        "center_band_top": center_band,
        "center_band_bottom": crotch_band_bottom,
        "crotch_band_below": crotch_band_below,
        "center_band_fade_height": 0.0,
        "waist_profile": waist_profile,
        "waist_top_z": waist_top_z,
        "status": "applied",
    }


def apply_bone_shoulder_fit(
    garment: bpy.types.Object,
    actor: bpy.types.Object,
    armature: bpy.types.Object,
    clearance: float,
    ease: float,
    band_below: float,
    band_above: float,
) -> dict[str, object]:
    """Constrain the sleeveless upper edge to the Actor's actual shoulder bones.

    The clothing cage intentionally has authoring ease and is wider than this
    chibi Actor.  A global scale would damage the hem, so this pass only fits
    the shoulder/armhole band to the upper-arm roots and compresses its depth
    against the torso slices.  The later raycast pass restores the required
    outward clearance.
    """
    left = _bone_point(armature, "CC_Base_L_Upperarm")
    right = _bone_point(armature, "CC_Base_R_Upperarm")
    left_hip = _bone_point(armature, "CC_Base_L_Thigh")
    right_hip = _bone_point(armature, "CC_Base_R_Thigh")
    shoulder_center_x = (left.x + right.x) * 0.5
    shoulder_half = abs(left.x - right.x) * 0.5
    shoulder_z = (left.z + right.z) * 0.5
    hip_center_x = (left_hip.x + right_hip.x) * 0.5
    hip_half = abs(left_hip.x - right_hip.x) * 0.5
    hip_z = (left_hip.z + right_hip.z) * 0.5
    low_z = shoulder_z - max(band_below, 0.01)
    high_z = shoulder_z + max(band_above, 0.01)

    actor_points = mesh_world_points(actor)
    garment_points = [garment.matrix_world @ vertex.co for vertex in garment.data.vertices]
    band_points = [point for point in garment_points if low_z <= point.z <= high_z]
    if not band_points:
        raise RuntimeError("garment has no vertices in the bone shoulder band")
    garment_low_z = min(point.z for point in garment_points)
    source_y_bins: dict[int, tuple[float, float]] = {}
    for point in garment_points:
        key = round(point.z / 0.05)
        current = source_y_bins.get(key)
        if current is None:
            source_y_bins[key] = (point.y, point.y)
        else:
            source_y_bins[key] = (min(current[0], point.y), max(current[1], point.y))

    source_depth_samples = [
        (key * 0.05, bounds[0], bounds[1])
        for key, bounds in sorted(source_y_bins.items())
    ]

    def source_depth(z: float) -> tuple[float, float]:
        """Continuously interpolate the source garment's depth envelope."""
        if z <= source_depth_samples[0][0]:
            return source_depth_samples[0][1:]
        if z >= source_depth_samples[-1][0]:
            return source_depth_samples[-1][1:]
        for first, second in zip(source_depth_samples, source_depth_samples[1:]):
            z0, low0, high0 = first
            z1, low1, high1 = second
            if z0 <= z <= z1:
                ratio = (z - z0) / max(z1 - z0, 1e-6)
                return (
                    low0 + (low1 - low0) * ratio,
                    high0 + (high1 - high0) * ratio,
                )
        return source_depth_samples[-1][1:]

    def sampled_torso_half_width(z: float) -> float:
        """Sample the central torso, excluding detached arm lobes."""
        samples = [
            point for point in actor_points
            if abs(point.z - z) <= 0.025 and abs(point.x - shoulder_center_x) <= shoulder_half + 0.17
        ]
        if not samples:
            return hip_half + (shoulder_half - hip_half) * max(
                0.0, min(1.0, (z - hip_z) / max(shoulder_z - hip_z, 1e-5))
            )
        return max(abs(point.x - shoulder_center_x) for point in samples)

    sample_start = min(garment_low_z, hip_z)
    sample_end = high_z
    sample_step = 0.05
    width_samples = []
    sample_z = sample_start
    while sample_z < sample_end:
        width_samples.append((sample_z, sampled_torso_half_width(sample_z)))
        sample_z += sample_step
    width_samples.append((sample_end, sampled_torso_half_width(sample_end)))

    def sampled_width(z: float) -> float:
        if z <= width_samples[0][0]:
            return width_samples[0][1]
        if z >= width_samples[-1][0]:
            return width_samples[-1][1]
        for (z0, w0), (z1, w1) in zip(width_samples, width_samples[1:]):
            if z0 <= z <= z1:
                t = (z - z0) / max(z1 - z0, 1e-5)
                return w0 + (w1 - w0) * t
        return width_samples[-1][1]

    def torso_depth(z: float) -> tuple[float, float]:
        # Exclude the arms while sampling the body surface.  The narrow
        # shoulder band is deliberately based on the torso, not the cage.
        torso_half = min(sampled_width(z), shoulder_half + 0.17)
        samples = [
            point for point in actor_points
            if abs(point.z - z) <= 0.025 and abs(point.x - shoulder_center_x) <= torso_half + 0.10
        ]
        if not samples:
            samples = [point for point in actor_points if abs(point.z - z) <= 0.025]
        return min(point.y for point in samples), max(point.y for point in samples)

    inverse = garment.matrix_world.inverted()
    changed = 0
    x_clamped = 0
    for vertex in garment.data.vertices:
        world = garment.matrix_world @ vertex.co
        if world.z < garment_low_z or world.z > high_z:
            continue
        # Use sampled torso width with a smooth shoulder cap. Bone roots remain
        # anchors, but the middle follows the Actor's actual silhouette.
        profile = max(0.0, min(1.0, (world.z - hip_z) / max(shoulder_z - hip_z, 1e-5)))
        shoulder_cap = shoulder_half + ease + (1.0 - profile) * 0.08
        half_limit = min(sampled_width(world.z) + clearance, shoulder_cap)
        center_x = hip_center_x + (shoulder_center_x - hip_center_x) * profile
        new_x = max(center_x - half_limit, min(center_x + half_limit, world.x))
        if abs(new_x - world.x) > 1e-6:
            world.x = new_x
            x_clamped += 1

        if garment_low_z <= world.z <= high_z:
            source_low, source_high = source_depth(world.z)
            torso_low, torso_high = torso_depth(world.z)
            target_y_low = torso_low - clearance
            target_y_high = torso_high + clearance
            source_size = max(source_high - source_low, 1e-5)
            target_size = max(target_y_high - target_y_low, 1e-5)
            mapped_y = target_y_low + (world.y - source_low) * target_size / source_size
            # The source OBJ contains a few collar/edge vertices outside its
            # local height-bin envelope. Do not let those become floating
            # strips or penetrate the Actor after depth fitting.
            world.y = max(target_y_low, min(target_y_high, mapped_y))
        vertex.co = inverse @ world
        changed += 1
    garment.data.update()
    return {
        "changed_vertices": changed,
        "x_clamped_vertices": x_clamped,
        "upperarm_span": abs(left.x - right.x),
        "shoulder_center_x": shoulder_center_x,
        "shoulder_z": shoulder_z,
        "shoulder_half_width": shoulder_half,
        "hip_span": abs(left_hip.x - right_hip.x),
        "hip_z": hip_z,
        "hip_half_width": hip_half,
        "ease": ease,
        "band": {"low_z": low_z, "high_z": high_z},
        "depth_fit": "actor_torso_slice_plus_clearance_with_continuous_source_depth_interpolation",
        "width_fit": {
            "method": "sampled_actor_torso_width_linear_interpolation_with_shoulder_cap",
            "sample_step": sample_step,
            "samples": [[round(z, 4), round(width, 4)] for z, width in width_samples],
        },
    }


def render_walk(scene: bpy.types.Scene, armature: bpy.types.Object, output: Path, resolution: int) -> list[dict[str, object]]:
    low, high = visible_bounds()
    center = (low + high) * 0.5
    configure_lighting(scene, center, "soft_flat")
    scene.view_settings.exposure = 0.35
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    action = armature.animation_data.action if armature.animation_data else None
    if action is None:
        raise RuntimeError("Actor armature has no active walk action")
    start, end = int(action.frame_range[0]), int(action.frame_range[1])
    sample_frames = [round(start + (end - start) * index / 7.0) for index in range(8)]
    ortho_scale = max(high.z - low.z, high.x - low.x, high.y - low.y) * 1.16
    frames: list[dict[str, object]] = []
    for direction, (x, y) in DIRECTIONS.items():
        camera = make_camera(scene, center, f"GarmentCodeActorTransfer_{direction}", (x, y, center.z), ortho_scale)
        scene.camera = camera
        for index, source_frame in enumerate(sample_frames):
            scene.frame_set(source_frame)
            bpy.context.view_layer.update()
            path = output / f"{direction}_{index:02d}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            frames.append({"direction": direction, "sample_index": index, "source_frame": source_frame, "path": path.name})
        bpy.data.objects.remove(camera, do_unlink=True)
    return frames


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.actor_blend.resolve()))
    scene = bpy.context.scene
    scene.frame_set(1)
    actor = bpy.data.objects.get("ChibiBaseMesh_AccuRIG_InputMesh")
    armature = bpy.data.objects.get("Armature")
    if actor is None or armature is None:
        raise RuntimeError("actor blend must contain Actor mesh and Armature")
    previous_pose_position = armature.data.pose_position
    rest_authoring = options.garment_kind == "pants"
    if rest_authoring:
        # Author fitting and shrinkwrap against the unposed body. The
        # Armature modifier is restored to POSE only for the walk render;
        # fitting against frame 1 and then deforming again causes fragments.
        armature.data.pose_position = "REST"
        bpy.context.view_layer.update()
    if options.debug_hide_actor:
        actor.hide_render = True
        actor.hide_viewport = True

    # Load the cage object from the authoring blend into the Actor scene.
    with bpy.data.libraries.load(str(options.cage_blend.resolve()), link=False) as (data_from, data_to):
        if "ActorClothingCage_Outer" not in data_from.objects:
            raise RuntimeError("cage blend is missing ActorClothingCage_Outer")
        data_to.objects = ["ActorClothingCage_Outer"]
    cage = data_to.objects[0]
    scene.collection.objects.link(cage)
    cage.name = "ActorClothingCage_Outer_TransferReference"
    cage.hide_render = True
    cage.hide_viewport = True

    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if options.fitted_obj:
        garment = load_fitted_obj(options.fitted_obj, scene, options.obj_scale, options.obj_orientation)
        fitted_source = options.fitted_obj
    else:
        garment = load_fitted_garment(options.fitted_blend, scene)
        fitted_source = options.fitted_blend
    smooth_polygons = apply_smooth_shading(garment) if options.smooth_shading else 0
    source_low, source_high = object_bounds(garment)
    hem_fit = None
    pants_waist_top_z = None
    if options.garment_kind == "pants":
        pelvis_top_z = _bone_point(armature, "CC_Base_Pelvis", tail=True).z
        thigh_tails = [
            _bone_point(armature, name, tail=True).z
            for name in ("CC_Base_L_Thigh", "CC_Base_R_Thigh")
        ]
        pants_bottom_z = max(min(thigh_tails) + 0.02, pelvis_top_z - 0.34)
        pants_waist_top_z = (
            _bone_point(armature, "CC_Base_Spine01").z
            if options.pants_waist_profile == "highrise"
            else pelvis_top_z
        )
        # Pants must use the actual Actor hip/thigh envelope.  The clothing
        # cage is intentionally a torso reference and is much wider in this
        # z-band, which made the first shorts transfer read like a skirt.
        if options.pants_waist_profile == "highrise":
            # Raise only the top boundary. Keep X/Y from the pelvis-thigh
            # envelope; including the whole Spine01 weighted region here can
            # capture torso/arm-side outliers and make the waistband float.
            base_low, base_high = weighted_region_bounds(
                actor,
                pants_bottom_z,
                pelvis_top_z,
                PANTS_BODY_BONES,
            )
            cage_low = Vector((base_low.x, base_low.y, pants_bottom_z))
            cage_high = Vector((base_high.x, base_high.y, pants_waist_top_z))
        else:
            cage_low, cage_high = weighted_region_bounds(
                actor,
                pants_bottom_z,
                pants_waist_top_z,
                PANTS_BODY_BONES,
            )
        hem_fit = {
            "reference_bone": "CC_Base_Pelvis.tail",
            "pelvis_top_z": pelvis_top_z,
            "waist_top_z": pants_waist_top_z,
            "waist_profile": options.pants_waist_profile,
            "pants_bottom_z": pants_bottom_z,
            "clearance": options.pelvis_hem_clearance,
        }
    else:
        if options.skip_pelvis_hem_fit:
            torso_bottom_z = 0.62
        else:
            pelvis_top_z = _bone_point(armature, "CC_Base_Pelvis", tail=True).z
            torso_bottom_z = pelvis_top_z + options.pelvis_hem_clearance
            hem_fit = {
                "reference_bone": "CC_Base_Pelvis.tail",
                "pelvis_top_z": pelvis_top_z,
                "hem_z": torso_bottom_z,
                "clearance": options.pelvis_hem_clearance,
            }
        cage_low, cage_high = region_bounds(cage, torso_bottom_z, 1.46)
    target_size = Vector(
        (
            (cage_high.x - cage_low.x) * options.width_factor + 2.0 * options.width_margin,
            (cage_high.y - cage_low.y) * options.depth_factor + 2.0 * options.depth_margin,
            cage_high.z - cage_low.z,
        )
    )
    target_center = (cage_low + cage_high) * 0.5
    target_low = Vector((target_center.x - target_size.x * 0.5, target_center.y - target_size.y * 0.5, cage_low.z))
    target_high = Vector((target_center.x + target_size.x * 0.5, target_center.y + target_size.y * 0.5, cage_high.z))
    garment.matrix_world = fit_matrix(source_low, source_high, target_low, target_high) @ garment.matrix_world
    garment.location.y += options.depth_bias
    bpy.context.view_layer.update()

    garment.data.materials.clear()
    garment.data.materials.append(material())
    bone_shoulder_fit = None
    pants_width_profile = None
    pants_front_clearance = 0
    if options.garment_kind == "pants":
        pants_width_profile = fit_pants_width_profile(
            garment,
            actor,
            pants_bottom_z,
            pants_waist_top_z,
            options.clearance,
        )
        pants_front_clearance = apply_pants_front_clearance(
            garment,
            options.pants_front_clearance,
        )
    if options.garment_kind == "shirt" and not options.skip_bone_shoulder_fit:
        bone_shoulder_fit = apply_bone_shoulder_fit(
            garment,
            actor,
            armature,
            options.clearance,
            options.shoulder_ease,
            options.shoulder_band_below,
            options.shoulder_band_above,
        )
    projection_method = "none"
    projected_vertices = 0
    projection_max_z = options.projection_max_z if options.projection_max_z > 0.0 else None
    if projection_max_z is None and bone_shoulder_fit is not None:
        projection_max_z = float(bone_shoulder_fit["shoulder_z"])
    surface_targets = [actor]
    if options.surface_target:
        surface_targets = []
        for name in options.surface_target.split(","):
            target = bpy.data.objects.get(name.strip())
            if target is None or target.type != "MESH":
                raise RuntimeError(f"surface target mesh is missing: {name}")
            surface_targets.append(target)
    if not options.skip_surface_fit:
        if options.projection == "raycast":
            if options.garment_kind == "pants":
                projected_vertices = project_pants_depth(
                    garment,
                    surface_targets,
                    options.clearance,
                )
                projection_method = "pants_front_back_depth_projection"
            else:
                projected_vertices = project_to_actor_sides(
                    garment,
                    surface_targets,
                    options.clearance,
                    preserve_sleeve_edges=options.preserve_sleeve_edges,
                    project_side_x=options.project_side_x,
                    max_projection_z=projection_max_z,
                )
                projection_method = "side_preserving_clearance_push"
        else:
            if len(surface_targets) != 1:
                raise RuntimeError("nearest shrinkwrap accepts exactly one surface target")
            apply_actor_surface_fit(garment, surface_targets[0], options.clearance)
            projection_method = "nearest_surfacepoint_shrinkwrap"
    biased_vertices = apply_surface_bias(
        garment,
        options.front_flatten,
        options.back_clearance,
        options.sleeve_clearance,
    )
    for target in surface_targets:
        if target != actor:
            target.hide_render = True
            target.hide_viewport = True
    upper_weight_repair = None
    pants_weight_repair = None
    post_armature_clearance = None
    if not options.skip_rig:
        transfer_actor_weights(garment, actor, armature)
        if options.garment_kind == "pants":
            pants_weight_repair = assign_segmented_pants_weights(
                garment,
                armature,
                pants_bottom_z,
                pelvis_top_z,
                options.pants_weight_mode,
                waist_top_z=pants_waist_top_z,
                waist_profile=options.pants_waist_profile,
                crotch_band_below=options.pants_crotch_band_below,
            )
        elif not options.skip_upper_weight_repair and bone_shoulder_fit is not None:
            upper_weight_repair = repair_upper_garment_weights(
                garment,
                float(bone_shoulder_fit["shoulder_z"]),
            )
        if options.garment_kind == "pants" and (options.post_armature_clearance or options.post_armature_projection):
            post_armature_clearance = add_post_armature_clearance(
                garment,
                actor,
                options.clearance,
                projection=options.post_armature_projection,
                lower_bound_z=pants_bottom_z + (pelvis_top_z - pants_bottom_z) * 0.58,
            )
    bpy.context.view_layer.update()

    if rest_authoring:
        armature.data.pose_position = previous_pose_position
        bpy.context.view_layer.update()

    scene["assetslab_garmentcode_actor_transfer_status"] = "review_required"
    scene["assetslab_garmentcode_actor_transfer_method"] = (
        "weighted_pelvis_thigh_bounds_plus_segmented_pants_weights_plus_actor_surface_clearance"
        if options.garment_kind == "pants"
        else "cage_bounds_plus_bone_shoulder_fit_plus_actor_surface_clearance_plus_nearest_vertex_weights"
    )
    frames = render_walk(scene, armature, output, options.resolution)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "garmentcode_actor_transfer_candidate.blend"))
    report = {
        "schema": "assetslab_garmentcode_actor_transfer_review_v1",
        "garment_kind": options.garment_kind,
        "actor_blend": str(options.actor_blend.resolve()),
        "cage_blend": str(options.cage_blend.resolve()),
        "fitted_source": str(fitted_source.resolve()),
        "fitted_source_type": "official_garmentcode_sim_obj" if options.fitted_obj else "blender_fitted_blend",
        "obj_scale": options.obj_scale if options.fitted_obj else None,
        "obj_orientation": options.obj_orientation if options.fitted_obj else None,
        "authoring_pose": "REST" if rest_authoring else previous_pose_position,
        "render_pose": previous_pose_position,
        "clearance": None if options.skip_surface_fit else options.clearance,
        "target_bounds": {"low": list(target_low), "high": list(target_high)},
        "pelvis_hem_fit": hem_fit,
        "fit_factors": {"width": options.width_factor, "depth": options.depth_factor, "width_margin": options.width_margin, "depth_margin": options.depth_margin},
        "rig_status": "not_applied" if options.skip_rig else (
            "semantic_pelvis_waistband_plus_left_right_thighs_plus_armature_modifier"
            if options.garment_kind == "pants"
            else "nearest_actor_vertex_weights_plus_armature_modifier"
        ),
        "surface_fit": not options.skip_surface_fit,
        "projection_method": projection_method,
        "projected_vertices": projected_vertices,
        "project_side_x": options.project_side_x,
        "projection_max_z": projection_max_z,
        "preserve_sleeve_edges": options.preserve_sleeve_edges,
        "smooth_shading": options.smooth_shading,
        "smooth_polygons": smooth_polygons,
        "surface_bias": {
            "front_flatten": options.front_flatten,
            "back_clearance": options.back_clearance,
            "sleeve_clearance": options.sleeve_clearance,
            "biased_vertices": biased_vertices,
        },
        "bone_shoulder_fit": bone_shoulder_fit,
        "upper_weight_repair": upper_weight_repair,
        "pants_weight_repair": pants_weight_repair,
        "pants_weight_mode": options.pants_weight_mode if options.garment_kind == "pants" else None,
        "pants_waist_profile": options.pants_waist_profile if options.garment_kind == "pants" else None,
        "pants_width_profile": pants_width_profile,
        "pants_front_clearance": {
            "amount": options.pants_front_clearance,
            "changed_vertices": pants_front_clearance,
        } if options.garment_kind == "pants" else None,
        "post_armature_clearance": post_armature_clearance,
        "surface_targets": [target.name for target in surface_targets],
        "status": "review_required",
        "frames": frames,
    }
    (output / "manifest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
