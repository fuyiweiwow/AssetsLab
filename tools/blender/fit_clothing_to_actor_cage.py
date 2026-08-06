"""Fit one clothing-library item against the Actor Clothing Cage.

This is the first deterministic soft-garment baseline.  The source garment is
normalized in its own local bounds, then fitted to Cage-derived torso/arm
dimensions.  Shrinkwrap supplies the small body clearance at rest; transferred
Actor weights and the existing armature carry the garment during the walk.

This script intentionally does not simulate sewing or generate a garment.
Those are separate authoring/research routes.  It creates a review candidate
from an existing mesh that can be accepted or rejected with four directions
and eight action samples.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector, kdtree

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from build_clothes_fit_candidate import (  # noqa: E402
    DIRECTIONS,
    bounds_for,
    catalog_world_matrix,
    copy_fitted_group,
    descendants,
    load_catalog,
)
from render_eye_assembly_blink_walk import configure_lighting, visible_bounds  # noqa: E402
from render_procedural_anime_eye_on_accurig import make_camera  # noqa: E402


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor-blend", required=True, type=Path)
    parser.add_argument("--clothes-blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--top", default="Colin_Tshirt_wide")
    parser.add_argument("--profile", choices=("legacy_actor_scaled", "cage_bbox"), default="legacy_actor_scaled")
    parser.add_argument("--scale", type=float, default=2.5)
    parser.add_argument("--depth-scale", type=float, default=2.25)
    parser.add_argument("--top-bottom-z", type=float, default=0.62)
    parser.add_argument("--clearance", type=float, default=0.025)
    parser.add_argument("--torso-bottom-z", type=float, default=0.62)
    parser.add_argument("--torso-top-z", type=float, default=1.46)
    parser.add_argument("--width-margin", type=float, default=0.06)
    parser.add_argument("--depth-margin", type=float, default=0.05)
    parser.add_argument("--height-margin", type=float, default=0.0)
    parser.add_argument("--width-factor", type=float, default=0.85)
    parser.add_argument("--depth-factor", type=float, default=2.2)
    parser.add_argument(
        "--shrinkwrap",
        action="store_true",
        help="diagnostic only: conform the garment to the Cage after fitting",
    )
    parser.add_argument("--resolution", type=int, default=256)
    parser.add_argument("--diagnostic-colors", action="store_true")
    return parser.parse_args(argv)


def mesh_world_points(obj: bpy.types.Object) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def cage_region_bounds(cage: bpy.types.Object, bottom_z: float, top_z: float) -> tuple[Vector, Vector]:
    points = [point for point in mesh_world_points(cage) if bottom_z <= point.z <= top_z]
    if not points:
        raise RuntimeError("Cage has no points in the requested torso range")
    return (
        Vector((min(point.x for point in points), min(point.y for point in points), bottom_z)),
        Vector((max(point.x for point in points), max(point.y for point in points), top_z)),
    )


def evaluated_source_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    """Measure the rendered source shape, including Mirror/Solidify modifiers."""

    depsgraph = bpy.context.evaluated_depsgraph_get()
    points: list[Vector] = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            points.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
        finally:
            evaluated.to_mesh_clear()
    if not points:
        raise RuntimeError("selected clothing group has no evaluated mesh vertices")
    return (
        Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points))),
        Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points))),
    )


def fit_matrix(source_low: Vector, source_high: Vector, target_low: Vector, target_high: Vector) -> Matrix:
    source_size = source_high - source_low
    target_size = target_high - target_low
    if min(source_size.x, source_size.y, source_size.z) <= 0.00001:
        raise RuntimeError(f"source clothing has degenerate bounds: {source_size}")
    scale = Vector((target_size.x / source_size.x, target_size.y / source_size.y, target_size.z / source_size.z))
    source_center = (source_low + source_high) * 0.5
    target_center = (target_low + target_high) * 0.5
    return Matrix.Translation(target_center) @ Matrix.Diagonal((*scale, 1.0)) @ Matrix.Translation(-source_center)


def copy_fitted_top(
    source_root: bpy.types.Object,
    source_objects: list[bpy.types.Object],
    source_matrices: dict[bpy.types.Object, Matrix],
    collection: bpy.types.Collection,
    target_low: Vector,
    target_high: Vector,
) -> list[bpy.types.Object]:
    group = descendants(source_root, source_objects)
    # Bake catalog geometry first.  Measuring an evaluated Mirror result and
    # then applying that same modifier after the fit can double the effective
    # span on imported Proxy objects.  The baked mesh is the single source of
    # truth for both bounds and the copied candidate.
    for source in group:
        if source.type != "MESH":
            continue
        apply_source_geometry_modifiers(source)
    source_low, source_high = bounds_for(group, source_matrices)
    transform = fit_matrix(source_low, source_high, target_low, target_high)
    copied: list[bpy.types.Object] = []
    for source in group:
        if source.type != "MESH":
            continue
        target = source.copy()
        target.data = source.data.copy()
        target.name = f"ClothesCageFit_Top_{source.name}"
        target.parent = None
        target.matrix_world = transform @ source_matrices[source]
        target.hide_render = False
        target.hide_viewport = False
        collection.objects.link(target)
        copied.append(target)
    if not copied:
        raise RuntimeError(f"no mesh copied for clothing group: {source_root.name}")
    return copied


def apply_shrinkwrap(obj: bpy.types.Object, cage: bpy.types.Object, clearance: float) -> None:
    modifier = obj.modifiers.new("CageClearance", "SHRINKWRAP")
    modifier.target = cage
    modifier.wrap_method = "NEAREST_SURFACEPOINT"
    modifier.wrap_mode = "OUTSIDE"
    modifier.offset = clearance
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)


def apply_source_geometry_modifiers(obj: bpy.types.Object) -> None:
    """Bake catalog symmetry/thickness before assigning Actor weights.

    Proxy garments are authored with Mirror and Solidify modifiers.  Keeping
    those modifiers above a transfer modifier makes Blender warn that the
    transfer is not first, and can leave the copied mesh without usable
    groups.  The fitted candidate is a review mesh, so baking these two
    source-shape modifiers is the deterministic choice here.
    """

    for modifier in list(obj.modifiers):
        if modifier.type not in {"MIRROR", "SOLIDIFY"}:
            continue
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        obj.select_set(False)


def transfer_actor_weights(obj: bpy.types.Object, actor: bpy.types.Object, armature: bpy.types.Object) -> None:
    """Copy the nearest Actor vertex's complete weight set to each garment vertex."""

    tree = kdtree.KDTree(len(actor.data.vertices))
    for vertex in actor.data.vertices:
        tree.insert(actor.matrix_world @ vertex.co, vertex.index)
    tree.balance()

    destination_groups = {
        group.name: obj.vertex_groups.new(name=group.name)
        for group in actor.vertex_groups
    }
    for vertex in obj.data.vertices:
        _, source_index, _ = tree.find(obj.matrix_world @ vertex.co)
        source_vertex = actor.data.vertices[source_index]
        for assignment in source_vertex.groups:
            source_group = actor.vertex_groups[assignment.group]
            destination_groups[source_group.name].add(
                [vertex.index], assignment.weight, "REPLACE"
            )

    armature_modifier = obj.modifiers.new("ActorArmatureDeform", "ARMATURE")
    armature_modifier.object = armature


def diagnostic_material() -> bpy.types.Material:
    material = bpy.data.materials.new("ClothesCageFitDiagnostic")
    material.diffuse_color = (0.15, 0.42, 0.9, 1.0)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    if shader:
        shader.inputs["Base Color"].default_value = (0.15, 0.42, 0.9, 1.0)
        shader.inputs["Roughness"].default_value = 0.82
    return material


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.actor_blend.resolve()))
    scene = bpy.context.scene
    scene.frame_set(1)
    actor = bpy.data.objects.get("ChibiBaseMesh_AccuRIG_InputMesh")
    armature = bpy.data.objects.get("Armature")
    cage = bpy.data.objects.get("ActorClothingCage_Outer")
    if actor is None or armature is None:
        raise RuntimeError("actor blend must contain Actor mesh and Armature")
    if cage is None:
        # The legacy profile may validate directly against the original Actor
        # scene; a separate Cage blend is not required for that control run.
        cage = actor

    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    collection = bpy.data.collections.new("ClothesCageFitCandidate")
    scene.collection.children.link(collection)

    source_objects = load_catalog(options.clothes_blend)
    source_collection = bpy.data.collections.new("ClothesCatalogSource")
    scene.collection.children.link(source_collection)
    for source in source_objects:
        source_collection.objects.link(source)
    source_matrices: dict[bpy.types.Object, Matrix] = {}
    for source in source_objects:
        catalog_world_matrix(source, source_matrices)
    source_root = next((obj for obj in source_objects if obj.name == options.top), None)
    if source_root is None:
        raise RuntimeError(f"missing top clothing object: {options.top}")

    if options.profile == "legacy_actor_scaled":
        clothing = copy_fitted_group(
            source_root,
            source_objects,
            source_matrices,
            collection,
            options.scale,
            options.depth_scale,
            options.top_bottom_z,
            "top",
        )
        cage_low, cage_high = cage_region_bounds(cage, options.torso_bottom_z, options.torso_top_z)
        target_low, target_high = cage_low, cage_high
        fit_method = "legacy_actor_scaled_plus_cage_validation_weight_transfer"
    else:
        cage_low, cage_high = cage_region_bounds(cage, options.torso_bottom_z, options.torso_top_z)
        cage_center = (cage_low + cage_high) * 0.5
        cage_size = cage_high - cage_low
        target_size = Vector(
            (
                cage_size.x * options.width_factor + 2.0 * options.width_margin,
                cage_size.y * options.depth_factor + 2.0 * options.depth_margin,
                cage_size.z + 2.0 * options.height_margin,
            )
        )
        target_low = Vector(
            (
                cage_center.x - target_size.x * 0.5,
                cage_center.y - target_size.y * 0.5,
                cage_low.z - options.height_margin,
            )
        )
        target_high = Vector(
            (
                cage_center.x + target_size.x * 0.5,
                cage_center.y + target_size.y * 0.5,
                cage_high.z + options.height_margin,
            )
        )
        clothing = copy_fitted_top(source_root, source_objects, source_matrices, collection, target_low, target_high)
        fit_method = "cage_local_bounds_weight_transfer"
    for source in source_objects:
        bpy.data.objects.remove(source, do_unlink=True)
    bpy.data.collections.remove(source_collection)

    material = diagnostic_material()
    for obj in clothing:
        apply_source_geometry_modifiers(obj)
        obj.data.materials.clear()
        obj.data.materials.append(material)
        if options.shrinkwrap:
            apply_shrinkwrap(obj, cage, options.clearance)
        transfer_actor_weights(obj, actor, armature)

    low, high = visible_bounds()
    center = (low + high) * 0.5
    configure_lighting(scene, center, "soft_flat")
    scene.view_settings.exposure = 0.35
    scene["assetslab_clothes_candidate"] = "cage_fit_soft_garment_v1"
    scene["assetslab_clothes_top"] = options.top
    if options.shrinkwrap:
        fit_method += "_shrinkwrap_diagnostic"
    scene["assetslab_clothes_fit_method"] = fit_method
    scene["assetslab_clothes_clearance"] = options.clearance

    scene.render.resolution_x = options.resolution
    scene.render.resolution_y = options.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    candidate_blend = output / "clothes_cage_fit_candidate.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(candidate_blend))

    action = armature.animation_data.action if armature.animation_data else None
    if action is None:
        raise RuntimeError("Actor armature has no active walk action")
    start, end = int(action.frame_range[0]), int(action.frame_range[1])
    sample_frames = [round(start + (end - start) * index / 7.0) for index in range(8)]
    ortho_scale = max(high.z - low.z, high.x - low.x, high.y - low.y) * 1.16
    frames = []
    for direction, (x, y) in DIRECTIONS.items():
        camera = make_camera(scene, center, f"ClothesCageFit_{direction}", (x, y, center.z), ortho_scale)
        scene.camera = camera
        for index, source_frame in enumerate(sample_frames):
            scene.frame_set(source_frame)
            bpy.context.view_layer.update()
            path = output / f"{direction}_{index:02d}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            frames.append({"direction": direction, "sample_index": index, "source_frame": source_frame, "path": path.name})
        bpy.data.objects.remove(camera, do_unlink=True)

    report = {
        "schema": "assetslab_clothes_cage_fit_review_v1",
        "actor_blend": str(options.actor_blend.resolve()),
        "clothes_blend": str(options.clothes_blend.resolve()),
        "top": options.top,
        "fit_method": fit_method,
        "profile": options.profile,
        "legacy_scale": options.scale if options.profile == "legacy_actor_scaled" else None,
        "legacy_depth_scale": options.depth_scale if options.profile == "legacy_actor_scaled" else None,
        "legacy_top_bottom_z": options.top_bottom_z if options.profile == "legacy_actor_scaled" else None,
        "clearance": options.clearance,
        "cage_region": {"bottom_z": options.torso_bottom_z, "top_z": options.torso_top_z},
        "width_factor": options.width_factor,
        "depth_factor": options.depth_factor,
        "target_bounds": {"low": list(target_low), "high": list(target_high)},
        "direction_count": 4,
        "frame_count_per_direction": len(sample_frames),
        "sample_frames": sample_frames,
        "rig_status": "actor_weight_transfer_plus_armature_modifier",
        "lighting_profile": "soft_flat_v1",
        "status": "review_required",
        "frames": frames,
    }
    (output / "manifest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
