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
    parser.add_argument("--resolution", type=int, default=256)
    parser.add_argument(
        "--smooth-shading",
        action="store_true",
        help="use smooth polygon normals on the transferred garment for a shading diagnostic",
    )
    parser.add_argument("--obj-scale", type=float, default=0.01)
    parser.add_argument(
        "--obj-orientation",
        choices=("garmentcode", "blender"),
        default="garmentcode",
        help="Coordinate convention for fitted OBJ; GarmentCode maps (X,Y,Z) to Actor (X,-Z,Y)",
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
            source_low, source_high = source_y_bins[round(world.z / 0.05)]
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
        "depth_fit": "actor_torso_slice_plus_clearance_by_0.05m_height_bin",
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
    if not options.skip_bone_shoulder_fit:
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
    if not options.skip_rig:
        transfer_actor_weights(garment, actor, armature)
        if not options.skip_upper_weight_repair and bone_shoulder_fit is not None:
            upper_weight_repair = repair_upper_garment_weights(
                garment,
                float(bone_shoulder_fit["shoulder_z"]),
            )
    bpy.context.view_layer.update()

    scene["assetslab_garmentcode_actor_transfer_status"] = "review_required"
    scene["assetslab_garmentcode_actor_transfer_method"] = "cage_bounds_plus_bone_shoulder_fit_plus_actor_surface_clearance_plus_nearest_vertex_weights"
    frames = render_walk(scene, armature, output, options.resolution)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "garmentcode_actor_transfer_candidate.blend"))
    report = {
        "schema": "assetslab_garmentcode_actor_transfer_review_v1",
        "actor_blend": str(options.actor_blend.resolve()),
        "cage_blend": str(options.cage_blend.resolve()),
        "fitted_source": str(fitted_source.resolve()),
        "fitted_source_type": "official_garmentcode_sim_obj" if options.fitted_obj else "blender_fitted_blend",
        "obj_scale": options.obj_scale if options.fitted_obj else None,
        "obj_orientation": options.obj_orientation if options.fitted_obj else None,
        "clearance": None if options.skip_surface_fit else options.clearance,
        "target_bounds": {"low": list(target_low), "high": list(target_high)},
        "pelvis_hem_fit": hem_fit,
        "fit_factors": {"width": options.width_factor, "depth": options.depth_factor, "width_margin": options.width_margin, "depth_margin": options.depth_margin},
        "rig_status": "not_applied" if options.skip_rig else "nearest_actor_vertex_weights_plus_armature_modifier",
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
        "surface_targets": [target.name for target in surface_targets],
        "status": "review_required",
        "frames": frames,
    }
    (output / "manifest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
