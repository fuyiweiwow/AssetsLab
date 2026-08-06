"""Fit selected clothing-library meshes to Actor V1 for static review.

The uploaded clothing blend is a catalog of unrigged Colin garments arranged
around a small dummy. This script copies selected garment groups into the
Actor V1 scene, normalizes their catalog placement, applies a review-only fit,
and renders four static directions with the validated soft-flat lighting.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from render_eye_assembly_blink_walk import configure_lighting, visible_bounds  # noqa: E402
from render_procedural_anime_eye_on_accurig import make_camera  # noqa: E402


DIRECTIONS = {
    "front": (0.0, -12.0),
    "right": (12.0, 0.0),
    "back": (0.0, 12.0),
    "left": (-12.0, 0.0),
}


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor-blend", required=True, type=Path)
    parser.add_argument("--clothes-blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--top", default="Colin_shirt_short")
    parser.add_argument("--bottom", default="Colin_trouser_long")
    parser.add_argument("--scale", type=float, default=2.5)
    parser.add_argument("--depth-scale", type=float, default=2.25)
    parser.add_argument("--top-depth-scale", type=float)
    parser.add_argument("--bottom-depth-scale", type=float)
    parser.add_argument("--top-bottom-z", type=float, default=0.58)
    parser.add_argument("--bottom-bottom-z", type=float, default=0.05)
    parser.add_argument("--resolution", type=int, default=256)
    parser.add_argument("--animate", action="store_true")
    parser.add_argument("--diagnostic-colors", action="store_true")
    return parser.parse_args(argv)


def local_matrix(obj: bpy.types.Object) -> Matrix:
    return (
        Matrix.Translation(obj.location)
        @ obj.rotation_euler.to_matrix().to_4x4()
        @ Matrix.Diagonal((*obj.scale, 1.0))
    )


def catalog_world_matrix(obj: bpy.types.Object, cache: dict[bpy.types.Object, Matrix]) -> Matrix:
    if obj in cache:
        return cache[obj]
    if obj.parent is None:
        result = local_matrix(obj)
    else:
        result = catalog_world_matrix(obj.parent, cache) @ local_matrix(obj)
    cache[obj] = result
    return result


def bounds_for(objects: list[bpy.types.Object], matrices: dict[bpy.types.Object, Matrix]) -> tuple[Vector, Vector]:
    points = [
        matrices[obj] @ Vector(corner)
        for obj in objects
        if obj.type == "MESH"
        for corner in obj.bound_box
    ]
    if not points:
        raise RuntimeError("selected clothing group contains no mesh")
    return (
        Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points))),
        Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points))),
    )


def descendants(root: bpy.types.Object, source_objects: list[bpy.types.Object]) -> list[bpy.types.Object]:
    selected = {root}
    changed = True
    while changed:
        changed = False
        for obj in source_objects:
            if obj.parent in selected and obj not in selected:
                selected.add(obj)
                changed = True
    return [obj for obj in source_objects if obj in selected]


def load_catalog(path: Path) -> list[bpy.types.Object]:
    before = set(bpy.data.objects)
    with bpy.data.libraries.load(str(path.resolve()), link=False) as (data_from, data_to):
        data_to.objects = list(data_from.objects)
    loaded = [obj for obj in bpy.data.objects if obj not in before]
    bpy.context.view_layer.update()
    return loaded


def copy_fitted_group(
    source_root: bpy.types.Object,
    source_objects: list[bpy.types.Object],
    source_matrices: dict[bpy.types.Object, Matrix],
    collection: bpy.types.Collection,
    scale: float,
    depth_scale: float,
    target_bottom_z: float,
    label: str,
) -> list[bpy.types.Object]:
    group = descendants(source_root, source_objects)
    low, high = bounds_for(group, source_matrices)
    source_center_x = (low.x + high.x) * 0.5
    source_center_y = (low.y + high.y) * 0.5
    fit = (
        Matrix.Translation(Vector((-source_center_x * scale, -source_center_y * scale, target_bottom_z - low.z * scale)))
        @ Matrix.Diagonal((scale, scale * depth_scale, scale, 1.0))
    )
    copied = []
    for source in group:
        if source.type != "MESH":
            continue
        target = source.copy()
        target.data = source.data.copy()
        target.name = f"ClothesFit_{label}_{source.name}"
        target.parent = None
        target.matrix_world = fit @ source_matrices[source]
        target.hide_render = False
        target.hide_viewport = False
        collection.objects.link(target)
        copied.append(target)
    if not copied:
        raise RuntimeError(f"no mesh copied for clothing group: {source_root.name}")
    return copied


def brighten_clothes_review(scene: bpy.types.Scene) -> None:
    """Compensate for the darker base Actor material in this review scene only."""

    for light in (obj for obj in scene.objects if obj.type == "LIGHT"):
        if light.name == "AssetsLabSoftFlatKey":
            light.data.energy = 1500.0
        elif light.name == "AssetsLabSoftFlatFill":
            light.data.energy = 850.0
    if scene.world is not None and scene.world.use_nodes:
        background = scene.world.node_tree.nodes.get("Background")
        if background is not None:
            background.inputs["Strength"].default_value = 0.58
    scene.view_settings.exposure = 0.35


def auto_rig_clothing(armature: bpy.types.Object, clothing_objects: list[bpy.types.Object]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in clothing_objects:
        obj.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")


def apply_diagnostic_colors(objects: list[bpy.types.Object]) -> None:
    colors = {
        "top": (0.16, 0.38, 0.86, 1.0),
        "bottom": (0.42, 0.16, 0.08, 1.0),
    }
    for label, color in colors.items():
        material = bpy.data.materials.new(f"ClothesFitDiagnostic_{label}")
        material.diffuse_color = color
        material.use_nodes = True
        shader = material.node_tree.nodes.get("Principled BSDF")
        if shader is not None:
            shader.inputs["Base Color"].default_value = color
            shader.inputs["Roughness"].default_value = 0.82
        for obj in objects:
            if f"ClothesFit_{label}_" not in obj.name:
                continue
            obj.data.materials.clear()
            obj.data.materials.append(material)


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.actor_blend.resolve()))
    scene = bpy.context.scene
    scene.frame_set(1)

    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    clothes_collection = bpy.data.collections.new("ClothesFitCandidate")
    scene.collection.children.link(clothes_collection)

    source_objects = load_catalog(options.clothes_blend)
    source_matrices = {}
    for source in source_objects:
        catalog_world_matrix(source, source_matrices)
    top_depth_scale = options.top_depth_scale if options.top_depth_scale is not None else options.depth_scale
    bottom_depth_scale = options.bottom_depth_scale if options.bottom_depth_scale is not None else options.depth_scale
    top_root = next((obj for obj in source_objects if obj.name == options.top), None)
    bottom_root = next((obj for obj in source_objects if obj.name == options.bottom), None)
    if top_root is None:
        raise RuntimeError(f"missing top clothing object: {options.top}")
    if bottom_root is None:
        raise RuntimeError(f"missing bottom clothing object: {options.bottom}")

    top_objects = copy_fitted_group(
        top_root,
        source_objects,
        source_matrices,
        clothes_collection,
        options.scale,
        top_depth_scale,
        options.top_bottom_z,
        "top",
    )
    bottom_objects = copy_fitted_group(
        bottom_root,
        source_objects,
        source_matrices,
        clothes_collection,
        options.scale,
        bottom_depth_scale,
        options.bottom_bottom_z,
        "bottom",
    )
    clothing_objects = top_objects + bottom_objects
    if options.diagnostic_colors:
        apply_diagnostic_colors(clothing_objects)
    armature = bpy.data.objects.get("Armature")
    if options.animate:
        if armature is None:
            raise RuntimeError("actor scene has no Armature for animated clothing review")
        auto_rig_clothing(armature, clothing_objects)
    for source in source_objects:
        bpy.data.objects.remove(source, do_unlink=True)

    low, high = visible_bounds()
    center = (low + high) * 0.5
    configure_lighting(scene, center, "soft_flat")
    brighten_clothes_review(scene)
    scene["assetslab_clothes_candidate"] = "static_fit_review_v1"
    scene["assetslab_clothes_top"] = options.top
    scene["assetslab_clothes_bottom"] = options.bottom
    scene["assetslab_clothes_fit_scale"] = options.scale

    scene.render.resolution_x = options.resolution
    scene.render.resolution_y = options.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    candidate_blend = output / "clothes_fit_candidate.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(candidate_blend))

    ortho_scale = max(high.z - low.z, high.x - low.x, high.y - low.y) * 1.16
    action = armature.animation_data.action if armature and armature.animation_data else None
    if options.animate and action is None:
        raise RuntimeError("animated clothing review requires an active armature action")
    if options.animate:
        start, end = int(action.frame_range[0]), int(action.frame_range[1])
        sample_frames = [round(start + (end - start) * index / 7.0) for index in range(8)]
    else:
        sample_frames = [1]

    frames = []
    for direction, (x, y) in DIRECTIONS.items():
        camera = make_camera(scene, center, f"ClothesFit_{direction}", (x, y, center.z), ortho_scale)
        scene.camera = camera
        for index, source_frame in enumerate(sample_frames):
            scene.frame_set(source_frame)
            bpy.context.view_layer.update()
            path = output / (f"{direction}_{index:02d}.png" if options.animate else f"{direction}.png")
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            frames.append(
                {
                    "direction": direction,
                    "frame": index,
                    "source_frame": source_frame,
                    "path": path.name,
                }
            )
        bpy.data.objects.remove(camera, do_unlink=True)

    manifest = {
        "schema": "assetslab_clothes_fit_review_v1",
        "actor_blend": str(options.actor_blend.resolve()),
        "clothes_blend": str(options.clothes_blend.resolve()),
        "top": options.top,
        "bottom": options.bottom,
        "scale": options.scale,
        "depth_scale": options.depth_scale,
        "top_depth_scale": top_depth_scale,
        "bottom_depth_scale": bottom_depth_scale,
        "top_bottom_z": options.top_bottom_z,
        "bottom_bottom_z": options.bottom_bottom_z,
        "resolution": options.resolution,
        "direction_count": 4,
        "frame_count_per_direction": len(sample_frames),
        "body_sample_frames": sample_frames,
        "rig_status": "automatic_weights_review" if options.animate else "unrigged_static_review_only",
        "lighting_profile": "soft_flat_v1",
        "frames": frames,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"CLOTHES_FIT_REVIEW_PASS directions=4 output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
