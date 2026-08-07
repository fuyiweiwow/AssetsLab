"""Build and render a physics-proxy/render-garment pair.

The input blend already contains the reviewed Actor-transfer garment with
nearest-Actor weights and an Armature modifier.  This pass keeps that mesh as
the animation/physics proxy, creates a separate render mesh, applies a small
render-only subdivision, and binds the render mesh with Surface Deform.

The important production boundary is intentional: only the proxy has the
Armature modifier.  The render garment follows the animated proxy through
Surface Deform, so a future high-resolution garment can replace the render
mesh without changing the physics or Actor-weight transfer stage.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from render_eye_assembly_blink_walk import (  # noqa: E402
    DIRECTIONS,
    configure_lighting,
    visible_bounds,
)
from render_procedural_anime_eye_on_accurig import make_camera  # noqa: E402


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--proxy-name", default="GarmentCodeShirt_ActorTransfer")
    parser.add_argument("--resolution", type=int, default=256)
    parser.add_argument("--subdivision-level", type=int, default=1)
    parser.add_argument("--clean-render-surface", action="store_true")
    parser.add_argument("--render-surface-clearance", type=float, default=0.035)
    parser.add_argument("--build-clean-render-garment", action="store_true")
    parser.add_argument("--build-clean-short-sleeve-render-garment", action="store_true")
    parser.add_argument(
        "--reuse-existing-render-pair",
        action="store_true",
        help="keep the confirmed RenderGarment/AnimationProxy pair from the input blend",
    )
    parser.add_argument("--sleeve-length-fraction", type=float, default=0.42)
    parser.add_argument("--sleeve-clearance", type=float, default=0.012)
    parser.add_argument("--sleeve-forward-offset", type=float, default=0.04)
    parser.add_argument("--sleeve-lateral-offset", type=float, default=0.035)
    parser.add_argument("--proxy-weighted-render", action="store_true")
    parser.add_argument("--clean-animation-proxy", action="store_true")
    parser.add_argument("--animation-proxy-smooth-iterations", type=int, default=6)
    parser.add_argument("--animation-proxy-smooth-factor", type=float, default=0.35)
    parser.add_argument("--animation-proxy-decimate-ratio", type=float, default=0.30)
    parser.add_argument("--post-deform-smooth-iterations", type=int, default=4)
    parser.add_argument("--post-deform-smooth-factor", type=float, default=0.30)
    parser.add_argument("--render-surface-smoothing-iterations", type=int, default=2)
    parser.add_argument("--render-surface-smoothing-factor", type=float, default=0.15)
    return parser.parse_args(argv)


def apply_render_subdivision(obj: bpy.types.Object, level: int) -> dict[str, int]:
    if level < 1:
        raise RuntimeError("render subdivision level must be at least 1")
    before = len(obj.data.vertices)
    modifier = obj.modifiers.new("RenderGarmentSubdivision", "SUBSURF")
    # The demo shell is continuous across the shoulders and sides, with only
    # the hem intentionally open. Catmull-Clark is appropriate for this
    # connected version and restores the rounded cloth silhouette; the former
    # internal-vertex problem came from disconnected bridge/cap topology.
    modifier.subdivision_type = "CATMULL_CLARK"
    modifier.levels = level
    modifier.render_levels = level
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    # Apply the render-only subdivision before any deformation modifier. This
    # is especially important for the short sleeves: their Armature modifier
    # must remain after subdivision so the generated cuff follows the upperarm
    # without Blender warning that the requested modifier is not first.
    while obj.modifiers.find(modifier.name) > 0:
        bpy.ops.object.modifier_move_up(modifier=modifier.name)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj.data.update()
    return {"before_vertices": before, "after_vertices": len(obj.data.vertices), "level": level}


def apply_render_surface_smoothing(
    obj: bpy.types.Object,
    iterations: int = 2,
    factor: float = 0.15,
) -> dict[str, object]:
    """Soften the low-poly side transition without changing its landmarks."""
    if iterations < 0 or not 0.0 < factor <= 1.0:
        raise RuntimeError("invalid render surface smoothing parameters")
    if iterations == 0:
        return {"enabled": False, "iterations": 0, "factor": factor}
    modifier = obj.modifiers.new("RenderGarmentSurfaceSmoothing", "SMOOTH")
    modifier.factor = factor
    modifier.iterations = iterations
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    result = bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)
    if "FINISHED" not in result:
        raise RuntimeError(f"render surface smoothing did not finish: {result}")
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj.data.update()
    return {"enabled": True, "iterations": iterations, "factor": factor}


def apply_render_weighted_normals(obj: bpy.types.Object) -> dict[str, object]:
    """Keep the side arc visually continuous at the low-resolution render scale."""
    modifier = obj.modifiers.new("RenderGarmentWeightedNormals", "WEIGHTED_NORMAL")
    modifier.keep_sharp = False
    modifier.weight = 50
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    result = bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)
    if "FINISHED" not in result:
        raise RuntimeError(f"weighted normal calculation did not finish: {result}")
    obj.data.update()
    return {"enabled": True, "weight": 50, "keep_sharp": False}


def add_post_deform_surface_smoothing(
    obj: bpy.types.Object,
    iterations: int = 4,
    factor: float = 0.30,
) -> dict[str, object]:
    """Smooth the deformed result, where the visible side highlight is formed."""
    if iterations < 0 or not 0.0 < factor <= 1.0:
        raise RuntimeError("invalid post-deform smoothing parameters")
    if iterations == 0:
        return {"enabled": False, "iterations": 0, "factor": factor}
    modifier = obj.modifiers.new("PostDeformSurfaceSmoothing", "SMOOTH")
    modifier.factor = factor
    modifier.iterations = iterations
    obj.data.update()
    return {"enabled": True, "iterations": iterations, "factor": factor, "order": "after_deformation"}


def apply_animation_proxy_cleanup(
    obj: bpy.types.Object,
    armature: bpy.types.Object,
    smooth_iterations: int,
    smooth_factor: float,
    decimate_ratio: float,
) -> dict[str, object]:
    if smooth_iterations < 0 or not 0.0 < smooth_factor <= 1.0:
        raise RuntimeError("invalid animation proxy smoothing parameters")
    if not 0.0 < decimate_ratio <= 1.0:
        raise RuntimeError("animation proxy decimate ratio must be in (0, 1]")
    before = len(obj.data.vertices)
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
    if smooth_iterations > 0:
        smooth = obj.modifiers.new("AnimationProxySurfaceSmoothing", "SMOOTH")
        smooth.factor = smooth_factor
        smooth.iterations = smooth_iterations
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.modifier_apply(modifier=smooth.name)
        obj.select_set(False)
    decimate = obj.modifiers.new("AnimationProxyDecimate", "DECIMATE")
    decimate.decimate_type = "COLLAPSE"
    decimate.ratio = decimate_ratio
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=decimate.name)
    obj.select_set(False)
    armature_modifier = obj.modifiers.new("AnimationProxyArmatureDeform", "ARMATURE")
    armature_modifier.object = armature
    obj.data.update()
    return {
        "enabled": True,
        "before_vertices": before,
        "after_vertices": len(obj.data.vertices),
        "smooth_iterations": smooth_iterations,
        "smooth_factor": smooth_factor,
        "decimate_ratio": decimate_ratio,
        "armature_modifier": armature_modifier.name,
    }


def bind_surface_deform(render_garment: bpy.types.Object, proxy: bpy.types.Object) -> dict[str, object]:
    modifier = render_garment.modifiers.new("SurfaceDeformFromPhysicsProxy", "SURFACE_DEFORM")
    modifier.target = proxy
    modifier.strength = 1.0
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = render_garment
    render_garment.select_set(True)
    result = bpy.ops.object.surfacedeform_bind(modifier=modifier.name)
    render_garment.select_set(False)
    if "FINISHED" not in result:
        raise RuntimeError(f"Surface Deform bind did not finish: {result}")
    bpy.context.view_layer.update()
    return {
        "modifier": modifier.name,
        "target": proxy.name,
        "strength": modifier.strength,
        "bound": bool(modifier.is_bound),
    }


def bind_proxy_weighted_armature(
    render_garment: bpy.types.Object,
    source_proxy: bpy.types.Object,
    armature: bpy.types.Object,
) -> dict[str, object]:
    """Bind the clean shell to a measured, explicit torso/shoulder schema.

    The simulated proxy remains useful for the animation experiment, but its
    interpolated weights are not a reliable source for a newly rebuilt shell:
    tiny hip assignments at the hem and arm assignments at the shoulder can
    split an otherwise continuous garment.  The render shell therefore uses a
    small, auditable bone-space schema based on normalized height and x side.
    """
    required = (
        "CC_Base_Waist",
        "CC_Base_Spine01",
        "CC_Base_Spine02",
        "CC_Base_L_Clavicle",
        "CC_Base_R_Clavicle",
        "CC_Base_L_Upperarm",
        "CC_Base_R_Upperarm",
    )
    groups = {}
    for name in required:
        group = render_garment.vertex_groups.get(name) or render_garment.vertex_groups.new(name=name)
        groups[name] = group
    for vertex in render_garment.data.vertices:
        for group_index in [assignment.group for assignment in vertex.groups]:
            render_garment.vertex_groups[group_index].remove([vertex.index])

    min_z = min(vertex.co.z for vertex in render_garment.data.vertices)
    max_z = max(vertex.co.z for vertex in render_garment.data.vertices)
    height = max(max_z - min_z, 1e-6)
    explicit_regions = {"waist": 0, "spine01": 0, "spine02": 0, "shoulder": 0}
    for vertex in render_garment.data.vertices:
        t = max(0.0, min(1.0, (vertex.co.z - min_z) / height))
        side = -1 if vertex.co.x < 0.0 else 1
        if t < 0.23:
            weights = (("CC_Base_Waist", 0.70), ("CC_Base_Spine01", 0.30))
            explicit_regions["waist"] += 1
        elif t < 0.58:
            weights = (("CC_Base_Spine01", 0.65), ("CC_Base_Spine02", 0.35))
            explicit_regions["spine01"] += 1
        elif t < 0.80 or abs(vertex.co.x) < 0.18:
            weights = (("CC_Base_Spine02", 0.65), (f"CC_Base_{'L' if side < 0 else 'R'}_Clavicle", 0.35))
            explicit_regions["spine02"] += 1
        else:
            prefix = "L" if side < 0 else "R"
            weights = ((f"CC_Base_{prefix}_Clavicle", 0.60), (f"CC_Base_{prefix}_Upperarm", 0.40))
            explicit_regions["shoulder"] += 1
        for name, weight in weights:
            groups[name].add([vertex.index], weight, "REPLACE")
    armature_modifier = render_garment.modifiers.new("RenderGarmentProxyArmatureDeform", "ARMATURE")
    armature_modifier.object = armature
    bpy.context.view_layer.update()
    return {
        "method": "explicit_bone_space_torso_shoulders_plus_armature",
        "source": source_proxy.name,
        "armature": armature.name,
        "vertex_groups": len(required),
        "armature_modifier": armature_modifier.name,
        "region_vertex_counts": explicit_regions,
        "normalization": "height_and_x_side",
    }


def evaluated_world_points(obj: bpy.types.Object) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


ACTOR_TORSO_BONES = {
    "CC_Base_Pelvis",
    "CC_Base_Waist",
    "CC_Base_Spine01",
    "CC_Base_Spine02",
    "CC_Base_L_Clavicle",
    "CC_Base_R_Clavicle",
    "CC_Base_L_Upperarm",
    "CC_Base_R_Upperarm",
}


def evaluated_actor_torso_points(obj: bpy.types.Object) -> list[Vector]:
    """Return posed Actor surface points excluding the head and face meshes."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        group_names = {group.index: group.name for group in obj.vertex_groups}
        torso_indices = {
            vertex.index
            for vertex in obj.data.vertices
            if sum(
                assignment.weight
                for assignment in vertex.groups
                if group_names.get(assignment.group) in ACTOR_TORSO_BONES
            ) >= 0.20
        }
        if len(torso_indices) < 32:
            raise RuntimeError("Actor torso bone-weight filter returned too few vertices")
        return [evaluated.matrix_world @ mesh.vertices[index].co for index in sorted(torso_indices)]
    finally:
        evaluated.to_mesh_clear()


def interpolation_samples(points: list[Vector], axis: str, step: float) -> list[tuple[float, float, float]]:
    if not points:
        raise RuntimeError("cannot build render surface envelope from an empty mesh")
    axis_index = {"x": 0, "y": 1, "z": 2}[axis]
    bins: dict[int, list[float]] = {}
    for point in points:
        key = round(float(point.z) / step)
        bins.setdefault(key, []).append(float(point[axis_index]))
    result = []
    for key in sorted(bins):
        values = sorted(bins[key])
        result.append((key * step, values[0], values[-1]))
    return result


def robust_depth_range(points: list[Vector]) -> tuple[float, float]:
    """Ignore sparse head/face outliers when taking a torso cross-section."""
    values = sorted(point.y for point in points)
    if not values:
        raise RuntimeError("cannot calculate depth from an empty point set")
    lower = values[int((len(values) - 1) * 0.05)]
    upper = values[int((len(values) - 1) * 0.95)]
    return lower, upper


def interpolate_envelope(samples: list[tuple[float, float, float]], z: float) -> tuple[float, float]:
    if z <= samples[0][0]:
        return samples[0][1], samples[0][2]
    if z >= samples[-1][0]:
        return samples[-1][1], samples[-1][2]
    for lower, upper in zip(samples, samples[1:]):
        if lower[0] <= z <= upper[0]:
            span = max(upper[0] - lower[0], 1e-6)
            t = (z - lower[0]) / span
            return (
                lower[1] + (upper[1] - lower[1]) * t,
                lower[2] + (upper[2] - lower[2]) * t,
            )
    return samples[-1][1], samples[-1][2]


def torso_depth_envelope(actor: bpy.types.Object, step: float = 0.025) -> list[tuple[float, float, float]]:
    points = evaluated_actor_torso_points(actor)
    if not points:
        raise RuntimeError("Actor has no evaluated points for render surface")
    low = min(point.z for point in points)
    high = max(point.z for point in points)
    samples: list[tuple[float, float, float]] = []
    for index in range(round((high - low) / step) + 1):
        z = low + index * step
        torso = [point for point in points if abs(point.z - z) <= step * 0.8 and abs(point.x) <= 0.21]
        if len(torso) < 8:
            torso = [point for point in points if abs(point.z - z) <= step * 1.2 and abs(point.x) <= 0.27]
        if torso:
            front, back = robust_depth_range(torso)
            samples.append((z, front, back))
    if len(samples) < 3:
        raise RuntimeError("Actor torso depth envelope has too few samples")
    return samples


def build_clean_render_surface(
    render_garment: bpy.types.Object,
    proxy: bpy.types.Object,
    actor: bpy.types.Object,
    clearance: float,
) -> dict[str, object]:
    source_points = evaluated_world_points(proxy)
    source_samples = interpolation_samples(source_points, "y", 0.025)
    actor_samples = torso_depth_envelope(actor)
    inverse = render_garment.matrix_world.inverted()
    changed = 0
    for vertex in render_garment.data.vertices:
        world = render_garment.matrix_world @ vertex.co
        source_front, source_back = interpolate_envelope(source_samples, world.z)
        source_half = max((source_back - source_front) * 0.5, 1e-4)
        source_mid = (source_front + source_back) * 0.5
        depth_ratio = max(-1.0, min(1.0, (world.y - source_mid) / source_half))
        actor_front, actor_back = interpolate_envelope(actor_samples, world.z)
        actor_half = max((actor_back - actor_front) * 0.5 + clearance, 1e-4)
        actor_mid = (actor_front + actor_back) * 0.5
        world.y = actor_mid + depth_ratio * actor_half
        vertex.co = inverse @ world
        changed += 1
    render_garment.data.update()
    return {
        "enabled": True,
        "changed_vertices": changed,
        "clearance": clearance,
        "method": "source_depth_ratio_to_actor_torso_envelope_preserving_xy_boundary_topology",
        "sample_step": 0.025,
    }


def build_clean_tank_render_mesh(
    render_garment: bpy.types.Object,
    actor: bpy.types.Object,
    proxy: bpy.types.Object,
    armature: bpy.types.Object,
    clearance: float,
) -> dict[str, object]:
    """Replace the sim-folded render copy with a clean quad tank-top shell."""
    actor_points = evaluated_actor_torso_points(actor)
    samples = torso_depth_envelope(actor)
    required_bones = [
        armature.pose.bones.get("CC_Base_L_Upperarm"),
        armature.pose.bones.get("CC_Base_R_Upperarm"),
        armature.pose.bones.get("CC_Base_L_Clavicle"),
        armature.pose.bones.get("CC_Base_R_Clavicle"),
    ]
    if any(bone is None for bone in required_bones):
        raise RuntimeError("Actor shoulder landmark bones are missing")
    upperarm_heads = [armature.matrix_world @ bone.head for bone in required_bones[:2]]
    clavicle_tails = [armature.matrix_world @ bone.tail for bone in required_bones[2:]]
    shoulder_z = sum(point.z for point in upperarm_heads) / len(upperarm_heads)
    clavicle_z = sum(point.z for point in clavicle_tails) / len(clavicle_tails)
    # The bone head is the shoulder joint, not the top of the chibi shoulder
    # surface.  Leave a measured vertical margin so the strap is visibly over
    # the shoulder rather than merely ending at its joint.
    shoulder_top_z = max(shoulder_z, clavicle_z) + 0.080
    waist_bone = armature.pose.bones.get("CC_Base_Waist")
    if waist_bone is None:
        raise RuntimeError("Actor waist landmark bone is missing")
    # Keep the hem above the waist/upper-thigh transition; the previous small
    # clearance still let the moving thigh meet the lower edge in side frames.
    # Match the last striped demo's lower edge: it sits just below the waist
    # tail and is wide enough to cover the upper thigh instead of ending inside
    # the thigh volume.
    hem_z = (armature.matrix_world @ waist_bone.tail).z - 0.015
    span = shoulder_top_z - hem_z
    z_rows = [
        hem_z,
        hem_z + span * 0.09,
        hem_z + span * 0.31,
        hem_z + span * 0.575,
        hem_z + span * 0.72,
        hem_z + span * 0.88,
        shoulder_top_z,
    ]
    # Restore the accepted demo proportions: a compact upper panel and a broad
    # continuous shoulder material that reads as one shirt. The side transition
    # is sampled separately below, but the outer panel must retain this width so
    # Catmull-Clark has enough support around the open hem.
    # Add a small lower support allowance for the open hem. This is not a
    # global scale change: the extra 0.015--0.020 m only covers the upper-thigh
    # envelope where Catmull-Clark otherwise pulls the side transition inward.
    half_widths = [0.370, 0.375, 0.365, 0.325, 0.300, 0.290, 0.300]
    # Keep the front/back panel just inside the lateral ridge. The extra ridge
    # vertex below turns the former 90-degree side wall into a three-part
    # rounded transition: front panel -> side arc -> back panel.
    x_profile = (-0.92, -0.68, -0.34, 0.34, 0.68, 0.92)
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int, int]] = []

    def depth_at(x: float, z: float) -> tuple[float, float]:
        # The center torso envelope is not valid at the shoulder: above the
        # chest it samples the neck and makes the front/back shoulder bridge
        # float in the side view.  Query the Actor surface near each garment
        # vertex instead, with the torso envelope only as a fallback.
        window = max(0.055, min(0.085, abs(x) * 0.22))
        candidates = [
            point
            for point in actor_points
            if abs(point.x - x) <= window
            and abs(point.z - z) <= 0.045
            and -0.32 <= point.y <= 0.32
        ]
        if len(candidates) < 6:
            front, back = interpolate_envelope(samples, z)
        else:
            front, back = robust_depth_range(candidates)
        return front - clearance, back + clearance

    def add_panel(back: bool) -> list[list[int]]:
        rows: list[list[int]] = []
        for row, (z, width) in enumerate(zip(z_rows, half_widths)):
            row_profile = x_profile
            if not back and row >= 4:
                # Match the demo neckline. Its apparent size is controlled by
                # the compact top width, not by pushing the opening across the
                # full shoulder span.
                opening_half = (0.34, 0.50, 0.60)[min(row - 4, 2)]
                row_profile = (-0.92, -0.68, -opening_half, opening_half, 0.68, 0.92)
            row_indices: list[int] = []
            for normalized_x in row_profile:
                front, rear = depth_at(normalized_x * width, z)
                y = rear if back else front
                # The official demo begins wrapping before the panel edge.
                # Blend the outer 0.68 -> 0.92 band toward the side midpoint
                # so the first side-arc sample is tangent instead of reading
                # as a sewn vertical line.
                side_wrap = max(0.0, min(1.0, (abs(normalized_x) - 0.68) / 0.24))
                if side_wrap > 0.0:
                    if back:
                        y -= (rear - front) * 0.30 * side_wrap
                    else:
                        y += (rear - front) * 0.30 * side_wrap
                local_z = z
                if row == len(z_rows) - 1:
                    # A sleeveless shoulder rises from the neckline toward the
                    # shoulder end.  A flat raised top edge reads as a floating
                    # horizontal strip in the side view.
                    shoulder_band = min(abs(normalized_x) / 0.68, 1.0)
                    local_z -= 0.035 * (1.0 - shoulder_band)
                if back and row == len(z_rows) - 1:
                    # A shallow rear neckline keeps the back edge below the neck
                    # while preserving the shoulder strap endpoints.
                    local_z -= 0.035 * (1.0 - shoulder_band)
                row_indices.append(len(vertices))
                vertices.append((normalized_x * width, y, local_z))
            rows.append(row_indices)
        for row in range(len(rows) - 1):
            for column in range(len(x_profile) - 1):
                # Leave a real U-shaped front neckline between the two
                # shoulder straps above the chest row.
                if not back and column == 2 and row >= 3:
                    continue
                a, b = rows[row][column], rows[row][column + 1]
                c, d = rows[row + 1][column + 1], rows[row + 1][column]
                faces.append((a, b, c, d))
        return rows

    front_rows = add_panel(back=False)
    back_rows = add_panel(back=True)
    left_arcs: list[list[int]] = []
    right_arcs: list[list[int]] = []
    for z, width in zip(z_rows, half_widths):
        left_front, left_back = depth_at(-width, z)
        right_front, right_back = depth_at(width, z)
        left_row: list[int] = []
        right_row: list[int] = []
        # Use three shallow arc samples instead of a single visible ridge.
        # This follows the dense demo mesh's gradual front/side/back normal
        # change and prevents one highlight line at the side seam.
        for x_factor, depth_fraction in ((0.94, 0.30), (0.97, 0.50), (0.94, 0.70)):
            left_row.append(len(vertices))
            vertices.append((-width * x_factor, left_front + (left_back - left_front) * depth_fraction, z))
            right_row.append(len(vertices))
            vertices.append((width * x_factor, right_front + (right_back - right_front) * depth_fraction, z))
        left_arcs.append(left_row)
        right_arcs.append(right_row)
    for row in range(len(z_rows) - 1):
        left_chain = [front_rows[row][0], *left_arcs[row], back_rows[row][0]]
        left_next = [front_rows[row + 1][0], *left_arcs[row + 1], back_rows[row + 1][0]]
        right_chain = [front_rows[row][5], *right_arcs[row], back_rows[row][5]]
        right_next = [front_rows[row + 1][5], *right_arcs[row + 1], back_rows[row + 1][5]]
        for segment in range(4):
            faces.append((left_chain[segment], left_chain[segment + 1], left_next[segment + 1], left_next[segment]))
            faces.append((right_chain[segment], right_next[segment], right_next[segment + 1], right_chain[segment + 1]))

    # The demo joins the outer and inner bands into continuous shoulders. This
    # keeps the side silhouette connected and avoids floating shoulder tabs.
    top = len(z_rows) - 1
    for column in (0, 1, 4):
        faces.append((front_rows[top][column], front_rows[top][column + 1], back_rows[top][column + 1], back_rows[top][column]))

    # Leave the lower hem open.  A horizontal front-to-back cap is inside the
    # Actor torso by construction; after subdivision it creates interior
    # vertices that read as thigh penetration and a semicircular notch.  The
    # front/back hem edges are an intentional, continuous clothing boundary.

    mesh = bpy.data.meshes.new("GarmentCodeCleanTankRenderMesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    old_mesh = render_garment.data
    render_garment.data = mesh
    if old_mesh.users == 0:
        bpy.data.meshes.remove(old_mesh)
    if proxy.data.materials:
        render_garment.data.materials.append(proxy.data.materials[0])
    # The generated vertices are already in Actor world coordinates.  Do not
    # inherit the imported OBJ's scale/rotation transform from the proxy.
    render_garment.matrix_world = Matrix.Identity(4)
    return {
        "enabled": True,
        "method": "procedural_demo_style_tank_top_from_actor_torso_depth_envelope_open_hem",
        "vertices": len(vertices),
        "faces": len(faces),
        "z_rows": z_rows,
        "half_widths": half_widths,
        "landmarks": {
            "shoulder_z": shoulder_z,
            "clavicle_tail_z": clavicle_z,
            "shoulder_top_z": shoulder_top_z,
            "waist_tail_z": (armature.matrix_world @ waist_bone.tail).z,
            "hem_z": hem_z,
        },
        "clearance": clearance,
        "neckline": "front_u_opening_back_shallow_scoop",
        "side_transition": {
            "enabled": True,
            "panel_outer_x": 0.92,
            "lateral_ridge_x": [0.94, 0.97, 0.94],
            "ridge_depth": [0.30, 0.50, 0.70],
            "faces_per_side_per_row": 4,
        },
    }


def build_clean_short_sleeve_mesh(
    scene: bpy.types.Scene,
    actor: bpy.types.Object,
    armature: bpy.types.Object,
    proxy: bpy.types.Object,
    clearance: float,
    length_fraction: float,
    forward_offset: float,
    lateral_offset: float,
) -> tuple[bpy.types.Object, dict[str, object]]:
    """Build short sleeve tubes from the Actor upper-arm bones.

    The confirmed milestone torso remains the Surface Deform garment. Sleeves
    are separate rigid-ish shells because the milestone animation proxy has no
    arm geometry for Surface Deform to follow. Their construction follows the
    official GarmentCode short-sleeve idea: a connected armhole-side band,
    short length, and an open cuff with no hand coverage.
    """
    if not 0.25 <= length_fraction <= 0.90:
        raise RuntimeError("sleeve length fraction must stay between 0.25 and 0.90")
    # The sleeve mesh will be deformed by an Armature modifier.  Therefore its
    # source vertices must be authored in the armature rest space, not from
    # the frame-1 posed bone coordinates.  The previous implementation used
    # pose-space centers and then applied the pose a second time, which put the
    # blue sleeve shell inside the Actor upper arm and left only a side sliver
    # visible.
    previous_pose_position = armature.data.pose_position
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()
    actor_points = evaluated_world_points(actor)
    rest_bones: dict[str, tuple[Vector, Vector]] = {}
    for side, bone_name in (("left", "CC_Base_L_Upperarm"), ("right", "CC_Base_R_Upperarm")):
        bone = armature.data.bones.get(bone_name)
        if bone is None:
            armature.data.pose_position = previous_pose_position
            bpy.context.view_layer.update()
            raise RuntimeError(f"missing sleeve rest bone: {bone_name}")
        rest_bones[side] = (
            armature.matrix_world @ bone.head_local,
            armature.matrix_world @ bone.tail_local,
        )
    armature.data.pose_position = previous_pose_position
    bpy.context.view_layer.update()
    actor_points_by_side: dict[str, list[Vector]] = {}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated_actor = actor.evaluated_get(depsgraph)
    evaluated_mesh = evaluated_actor.to_mesh()
    try:
        group_indices = {group.name: group.index for group in actor.vertex_groups}
        group_names = {
            "left": "CC_Base_L_Upperarm",
            "right": "CC_Base_R_Upperarm",
        }
        for side, group_name in group_names.items():
            group_index = group_indices.get(group_name)
            if group_index is None:
                actor_points_by_side[side] = list(actor_points)
                continue
            actor_points_by_side[side] = [
                evaluated_actor.matrix_world @ evaluated_mesh.vertices[vertex.index].co
                for vertex in actor.data.vertices
                if any(assignment.group == group_index and assignment.weight >= 0.20 for assignment in vertex.groups)
            ]
            if len(actor_points_by_side[side]) < 32:
                actor_points_by_side[side] = list(actor_points)
    finally:
        evaluated_actor.to_mesh_clear()
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int, int]] = []
    side_indices: dict[str, list[int]] = {"left": [], "right": []}
    ring_indices: dict[str, list[list[int]]] = {"left": [], "right": []}
    segments = 10
    ring_fractions = (0.02, 0.22, 0.52, 0.82, 1.0)

    def add_sleeve(side: str, bone_name: str, sign: float) -> None:
        head, tail = rest_bones[side]
        axis = (tail - head).normalized()
        length = (tail - head).length * length_fraction
        reference = Vector((0.0, 0.0, 1.0))
        if abs(axis.dot(reference)) > 0.92:
            reference = Vector((0.0, 1.0, 0.0))
        radial_a = axis.cross(reference).normalized()
        radial_b = axis.cross(radial_a).normalized()

        side_actor_points = actor_points_by_side[side]
        rings: list[list[int]] = []
        for ring_number, fraction in enumerate(ring_fractions):
            center = head + axis * (length * fraction)
            nearby = []
            for point in side_actor_points:
                projection = (point - head).dot(axis)
                if -0.025 <= projection <= length + 0.035:
                    radial = point - (head + axis * max(0.0, min(length, projection)))
                    if radial.length <= 0.20 and point.x * sign > -0.015:
                        nearby.append(radial.length)
            measured = sorted(nearby)
            if measured:
                # The 88th percentile was too conservative for this chibi
                # arm: it estimated the inner half of the low-poly limb, so
                # the sleeve stayed visually inside the skin. Use a robust
                # outer-surface percentile and a small floor so the cloth
                # shell is actually visible from the front and side.
                measured_radius = measured[int((len(measured) - 1) * 0.95)]
            else:
                measured_radius = 0.10
            # The Actor upper-arm envelope is much fuller than the torso
            # cross-section (roughly 0.10--0.13 m in this chibi rig). Keep a
            # dedicated arm-shell range so the sleeve cannot collapse inside
            # the skin merely because a ring has sparse samples.
            base_radius = max(0.10, min(0.18, measured_radius + clearance))
            if ring_number == 0:
                base_radius += 0.008
            if ring_number == len(ring_fractions) - 1:
                base_radius *= 0.96
            ring: list[int] = []
            for segment in range(segments):
                angle = 2.0 * 3.141592653589793 * segment / segments
                point = center + radial_a * (base_radius * math.cos(angle)) + radial_b * (base_radius * math.sin(angle))
                # The Actor's relaxed arms sit slightly behind the torso in
                # the front camera. A small rest-space forward offset keeps
                # the sleeve surface visible without changing the armature
                # binding or touching the confirmed torso garment.
                point.y -= forward_offset
                # Keep the sleeve tube outside the torso silhouette.  The
                # sign follows the arm side, so both sleeves remain visible
                # as continuous shells in the front/back review views.
                point.x += sign * lateral_offset
                ring.append(len(vertices))
                vertices.append(tuple(point))
                side_indices[side].append(ring[-1])
            rings.append(ring)
        ring_indices[side] = rings
        for ring_a, ring_b in zip(rings, rings[1:]):
            for segment in range(segments):
                a = ring_a[segment]
                b = ring_a[(segment + 1) % segments]
                c = ring_b[(segment + 1) % segments]
                d = ring_b[segment]
                faces.append((a, b, c, d))

    add_sleeve("left", "CC_Base_L_Upperarm", -1.0)
    add_sleeve("right", "CC_Base_R_Upperarm", 1.0)
    mesh = bpy.data.meshes.new("GarmentCodeCleanShortSleeveMesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    sleeves = bpy.data.objects.new("GarmentCodeShirt_ShortSleeves", mesh)
    scene.collection.objects.link(sleeves)
    sleeves["assetslab_role"] = "short_sleeve_render_garment"
    sleeves["assetslab_deformation_source"] = "Actor upper-arm bones"
    sleeves.matrix_world = Matrix.Identity(4)
    if proxy.data.materials:
        sleeves.data.materials.append(proxy.data.materials[0])
    return sleeves, {
        "enabled": True,
        "method": "official_demo_short_sleeve_ratio_as_rest_space_bone_following_outer_surface_shell",
        "source_space": "armature_rest_pose",
        "length_fraction_of_upperarm": length_fraction,
        "clearance": clearance,
        "forward_offset": forward_offset,
        "lateral_offset": lateral_offset,
        "segments_per_ring": segments,
        "ring_fractions": list(ring_fractions),
        "radius_floor": 0.10,
        "radius_cap": 0.18,
        "vertex_count": len(vertices),
        "face_count": len(faces),
        "left_vertex_indices": side_indices["left"],
        "right_vertex_indices": side_indices["right"],
    }


def bind_short_sleeve_armature(
    sleeves: bpy.types.Object,
    armature: bpy.types.Object,
    metadata: dict[str, object],
) -> dict[str, object]:
    """Bind each sleeve to its own upper-arm bone without hand weights."""
    left = sleeves.vertex_groups.new(name="CC_Base_L_Upperarm")
    right = sleeves.vertex_groups.new(name="CC_Base_R_Upperarm")
    left_indices = [int(index) for index in metadata["left_vertex_indices"]]
    right_indices = [int(index) for index in metadata["right_vertex_indices"]]
    left.add(left_indices, 1.0, "REPLACE")
    right.add(right_indices, 1.0, "REPLACE")
    modifier = sleeves.modifiers.new("ShortSleevesArmatureDeform", "ARMATURE")
    modifier.object = armature
    for polygon in sleeves.data.polygons:
        polygon.use_smooth = True
    sleeves.data.update()
    return {
        "method": "rigid_upperarm_bone_groups",
        "modifier": modifier.name,
        "left_group": left.name,
        "right_group": right.name,
        "left_vertices": len(left_indices),
        "right_vertices": len(right_indices),
    }


def render_walk(scene: bpy.types.Scene, output: Path, resolution: int) -> list[dict[str, object]]:
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
    armature = bpy.data.objects.get("Armature")
    if armature is None or not armature.animation_data or armature.animation_data.action is None:
        raise RuntimeError("Actor armature has no active walk action")
    action = armature.animation_data.action
    start, end = int(action.frame_range[0]), int(action.frame_range[1])
    sample_frames = [round(start + (end - start) * index / 7.0) for index in range(8)]
    ortho_scale = max(high.z - low.z, high.x - low.x, high.y - low.y) * 1.16
    frames: list[dict[str, object]] = []
    for direction, (x, y) in DIRECTIONS.items():
        camera = make_camera(scene, center, f"GarmentProxyRender_{direction}", (x, y, center.z), ortho_scale)
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
    bpy.ops.wm.open_mainfile(filepath=str(options.input_blend.resolve()))
    scene = bpy.context.scene
    scene.frame_set(1)
    proxy = bpy.data.objects.get(options.proxy_name)
    if proxy is None or proxy.type != "MESH":
        raise RuntimeError(f"input blend is missing mesh proxy: {options.proxy_name}")
    if not any(modifier.type == "ARMATURE" for modifier in proxy.modifiers):
        raise RuntimeError("physics proxy must retain its Actor Armature modifier")

    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for child in output.iterdir():
        if child.is_file() and child.suffix.lower() in {".png", ".blend", ".json"}:
            child.unlink()

    proxy.name = "GarmentCodeShirt_PhysicsProxy"
    proxy["assetslab_role"] = "physics_proxy"
    proxy["assetslab_proxy_source"] = "official_garmentcode_sim_obj_transferred_to_actor"
    proxy.hide_render = True
    proxy.display_type = "WIRE"

    armature = bpy.data.objects.get("Armature")
    if armature is None:
        raise RuntimeError("input blend is missing Armature")

    reused_render_pair = bool(options.reuse_existing_render_pair)
    if reused_render_pair:
        animation_proxy = bpy.data.objects.get("GarmentCodeShirt_AnimationProxy")
        render_garment = bpy.data.objects.get("GarmentCodeShirt_RenderGarment")
        if animation_proxy is None or render_garment is None:
            raise RuntimeError("--reuse-existing-render-pair requires the confirmed AnimationProxy and RenderGarment")
        if animation_proxy.type != "MESH" or render_garment.type != "MESH":
            raise RuntimeError("existing render pair must contain mesh objects")
        animation_proxy.hide_render = True
        animation_proxy.hide_viewport = False
        render_garment.hide_render = False
        render_garment.hide_viewport = False
        render_garment.display_type = "TEXTURED"
    else:
        animation_proxy = proxy.copy()
        animation_proxy.data = proxy.data.copy()
        animation_proxy.name = "GarmentCodeShirt_AnimationProxy"
        animation_proxy["assetslab_role"] = "animation_deform_proxy"
        animation_proxy["assetslab_source"] = proxy.name
        animation_proxy.parent = None
        animation_proxy.matrix_world = proxy.matrix_world.copy()
        animation_proxy.hide_render = True
        animation_proxy.hide_viewport = False
        animation_proxy.display_type = "WIRE"
        scene.collection.objects.link(animation_proxy)

        render_garment = proxy.copy()
        render_garment.data = proxy.data.copy()
        render_garment.name = "GarmentCodeShirt_RenderGarment"
        render_garment["assetslab_role"] = "render_garment"
        render_garment["assetslab_deformation_source"] = proxy.name
        render_garment.parent = None
        render_garment.matrix_world = proxy.matrix_world.copy()
        render_garment.hide_render = False
        render_garment.hide_viewport = False
        render_garment.display_type = "TEXTURED"
        scene.collection.objects.link(render_garment)
        for modifier in list(render_garment.modifiers):
            render_garment.modifiers.remove(modifier)

    actor = bpy.data.objects.get("ChibiBaseMesh_AccuRIG_InputMesh")
    if actor is None:
        raise RuntimeError("input blend is missing Actor mesh")
    # Surface Deform must be authored in its bind pose (frame 1), matching the
    # demo route. Only the explicit Armature comparison route uses rest-pose
    # authoring; mixing rest-pose geometry with a frame-1 Surface Deform bind
    # makes the shoulder and hem start from different coordinate spaces.
    previous_pose_position = armature.data.pose_position
    authoring_pose = "bind_frame"
    if options.proxy_weighted_render:
        armature.data.pose_position = "REST"
        authoring_pose = "rest"
        bpy.context.view_layer.update()
    clean_render_garment = (
        build_clean_tank_render_mesh(
            render_garment,
            actor,
            proxy,
            armature,
            options.render_surface_clearance,
        )
        if options.build_clean_render_garment and not reused_render_pair
        else {
            "enabled": False,
            "method": "reused_confirmed_milestone_render_garment" if reused_render_pair else "not_requested",
        }
    )
    short_sleeves = None
    short_sleeve_geometry = {"enabled": False}
    if options.build_clean_short_sleeve_render_garment:
        short_sleeves, short_sleeve_geometry = build_clean_short_sleeve_mesh(
            scene,
            actor,
            armature,
            proxy,
            options.sleeve_clearance,
            options.sleeve_length_fraction,
            options.sleeve_forward_offset,
            options.sleeve_lateral_offset,
        )
    clean_surface = (
        build_clean_render_surface(
            render_garment,
            proxy,
            actor,
            options.render_surface_clearance,
        )
        if options.clean_render_surface and not reused_render_pair
        else {"enabled": False, "method": "reused_confirmed_milestone_surface" if reused_render_pair else "not_requested"}
    )
    if options.proxy_weighted_render:
        armature.data.pose_position = previous_pose_position
        bpy.context.view_layer.update()
    animation_cleanup = (
        apply_animation_proxy_cleanup(
            animation_proxy,
            armature,
            options.animation_proxy_smooth_iterations,
            options.animation_proxy_smooth_factor,
            options.animation_proxy_decimate_ratio,
        )
        if options.clean_animation_proxy and not reused_render_pair
        else {
            "enabled": False,
            "method": "reused_confirmed_milestone_animation_proxy" if reused_render_pair else "not_requested",
            "vertex_count": len(animation_proxy.data.vertices),
        }
    )
    subdivision = (
        apply_render_subdivision(render_garment, options.subdivision_level)
        if not reused_render_pair
        else {"enabled": False, "method": "reused_confirmed_milestone_subdivision"}
    )
    render_surface_smoothing = (
        apply_render_surface_smoothing(
            render_garment,
            options.render_surface_smoothing_iterations,
            options.render_surface_smoothing_factor,
        )
        if not reused_render_pair
        else {"enabled": False, "method": "reused_confirmed_milestone_surface_smoothing"}
    )
    render_weighted_normals = {"enabled": False, "reason": "continuous smooth normals are preferred for the demo side transition"}
    deformation = (
        bind_proxy_weighted_armature(render_garment, animation_proxy, armature)
        if options.proxy_weighted_render and not reused_render_pair
        else bind_surface_deform(render_garment, animation_proxy)
        if not reused_render_pair
        else {"enabled": True, "method": "reused_confirmed_milestone_surface_deform"}
    )
    short_sleeve_binding = {"enabled": False}
    short_sleeve_subdivision = {"enabled": False}
    if short_sleeves is not None:
        short_sleeve_binding = bind_short_sleeve_armature(short_sleeves, armature, short_sleeve_geometry)
        short_sleeve_subdivision = apply_render_subdivision(short_sleeves, 1)
    post_deform_smoothing = (
        add_post_deform_surface_smoothing(
            render_garment,
            options.post_deform_smooth_iterations,
            options.post_deform_smooth_factor,
        )
        if not options.proxy_weighted_render and not reused_render_pair
        else {
            "enabled": False,
            "method": "reused_confirmed_milestone_post_deform_smoothing" if reused_render_pair else "weighted_render_route",
        }
    )
    bpy.context.view_layer.update()

    scene["assetslab_garment_proxy_render_pair_status"] = "review_required"
    scene["assetslab_garment_proxy_render_pair_method"] = "physics_proxy_armature_plus_render_subdivision_plus_surface_deform"
    frames = render_walk(scene, output, options.resolution)
    blend_path = output / "garmentcode_proxy_render_pair_candidate.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    report = {
        "schema": "assetslab_garmentcode_proxy_render_pair_review_v1",
        "input_blend": str(options.input_blend.resolve()),
        "physics_proxy": {
            "object": proxy.name,
            "vertex_count": len(proxy.data.vertices),
            "armature_modifier": next(modifier.name for modifier in proxy.modifiers if modifier.type == "ARMATURE"),
            "hide_render": proxy.hide_render,
        },
        "animation_proxy": {
            "object": animation_proxy.name,
            "cleanup": animation_cleanup,
            "hide_render": animation_proxy.hide_render,
        },
        "render_garment": {
            "object": render_garment.name,
            "vertex_count": len(render_garment.data.vertices),
            "clean_render_garment": clean_render_garment,
            "clean_surface": clean_surface,
            "subdivision": subdivision,
            "surface_smoothing": render_surface_smoothing,
            "weighted_normals": render_weighted_normals,
            "post_deform_smoothing": post_deform_smoothing,
            "deformation": deformation,
            "armature_modifier": any(modifier.type == "ARMATURE" for modifier in render_garment.modifiers),
        },
        "short_sleeves": {
            "object": short_sleeves.name if short_sleeves is not None else None,
            "geometry": short_sleeve_geometry,
            "binding": short_sleeve_binding,
            "subdivision": short_sleeve_subdivision,
            "vertex_count": len(short_sleeves.data.vertices) if short_sleeves is not None else 0,
        },
        "animation": {
            "directions": list(DIRECTIONS),
            "frame_count": len(frames),
            "frames": frames,
        },
        "blend": str(blend_path),
        "status": "review_required",
    }
    (output / "manifest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
