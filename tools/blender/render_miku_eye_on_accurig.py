"""Attach Miku chibi's textured eye parts to the AssetsLab actor."""

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

from render_procedural_anime_eye_on_accurig import (  # noqa: E402
    annotation_world_point,
    bounds,
    group_bounds,
    load_calibration,
    make_camera,
    setup_render,
)


MIKU_EYE_OBJECTS = {
    "eyeball_1_0_node": "MikuChibiEyeball",
    "eye_007_22_0_node": "MikuChibiEyeOutline",
}
MIKU_BROW_SOURCE = "eyebrow_008_56_0_node"
MIKU_BROW_OUTPUT = "MikuChibiEyebrow"


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--fbx", required=True, type=Path, help="AccuRIG actor FBX")
    parser.add_argument("--miku-fbx", required=True, type=Path)
    parser.add_argument("--calibration", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scale", type=float, default=1.0, help="Additional eye scale multiplier")
    parser.add_argument("--spacing-multiplier", type=float, default=1.0, help="Horizontal spacing multiplier without changing base eye size")
    parser.add_argument("--surface-inset", type=float, default=0.0, help="Move the eye deeper behind the annotated face surface")
    parser.add_argument("--brow-inset", type=float, default=0.0, help="Move the eyebrow deeper behind the annotated face surface")
    parser.add_argument("--no-eye-outline", action="store_true")
    parser.add_argument("--include-eyebrow", action="store_true")
    parser.add_argument("--conform-outline", action="store_true", help="Shrinkwrap the Miku skin eye outline onto the actor head")
    parser.add_argument("--save-blend", type=Path)
    return parser.parse_args(argv)


def world_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector((min(point[i] for point in points) for i in range(3))),
        Vector((max(point[i] for point in points) for i in range(3))),
    )


def world_vertex_center_by_side(obj: bpy.types.Object, negative_x: bool) -> Vector:
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    selected = [point for point in points if (point.x < 0.0) == negative_x]
    if not selected:
        raise RuntimeError(f"could not find {'left' if negative_x else 'right'} eye vertices in {obj.name}")
    return sum(selected, Vector()) / len(selected)


def static_copy(source: bpy.types.Object, name: str) -> bpy.types.Object:
    original_world = source.matrix_world.copy()
    copied = source.copy()
    copied.data = source.data.copy()
    copied.name = name
    copied.parent = None
    copied.matrix_world = original_world
    while copied.modifiers:
        copied.modifiers.remove(copied.modifiers[0])
    bpy.context.collection.objects.link(copied)
    copied["assetslab_role"] = "miku_chibi_eye_candidate"
    copied["assetslab_source_object"] = source.name
    return copied


def hide_imported_source(objects: list[bpy.types.Object]) -> None:
    for obj in objects:
        obj.hide_render = True
        obj.hide_viewport = True


def load_actor_and_miku(actor_fbx: Path, miku_fbx: Path) -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(actor_fbx.resolve()), use_anim=True)
    actor_mesh = next(obj for obj in bpy.data.objects if obj.type == "MESH")
    before_miku = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(miku_fbx.resolve()), use_anim=True)
    imported = [obj for obj in bpy.data.objects if obj not in before_miku]
    source_names = set(MIKU_EYE_OBJECTS)
    missing = source_names - {obj.name for obj in imported}
    if missing:
        raise RuntimeError(f"Miku FBX is missing eye objects: {sorted(missing)}")
    return actor_mesh, imported


def place_miku_eyes(
    actor_mesh: bpy.types.Object,
    imported: list[bpy.types.Object],
    calibration: dict,
    include_outline: bool,
    scale_multiplier: float,
    surface_inset: float,
    brow_inset: float,
    conform_outline: bool,
    include_eyebrow: bool,
    spacing_multiplier: float,
) -> tuple[list[bpy.types.Object], dict]:
    source_by_name = {obj.name: obj for obj in imported if obj.name in MIKU_EYE_OBJECTS}
    if include_eyebrow:
        if MIKU_BROW_SOURCE not in {obj.name for obj in imported}:
            raise RuntimeError(f"Miku FBX is missing eyebrow object: {MIKU_BROW_SOURCE}")
        source_by_name[MIKU_BROW_SOURCE] = next(obj for obj in imported if obj.name == MIKU_BROW_SOURCE)
    eyeball = source_by_name["eyeball_1_0_node"]
    source_left = world_vertex_center_by_side(eyeball, True)
    source_right = world_vertex_center_by_side(eyeball, False)
    source_mid = (source_left + source_right) * 0.5
    source_gap = abs(source_right.x - source_left.x)

    low, high = bounds(actor_mesh)
    actor_center = (low + high) * 0.5
    annotation_scale = max(4.0, (high.z - low.z) * 1.25)
    front = {item["key"]: item for item in calibration["views"]["front"]}
    side = {item["key"]: item for item in calibration["views"]["side"]}
    screen_left = annotation_world_point(front["screen_left_eye_center"], "front", actor_center.z, annotation_scale)
    screen_right = annotation_world_point(front["screen_right_eye_center"], "front", actor_center.z, annotation_scale)
    side_center = annotation_world_point(side["eye_center"], "side", actor_center.z, annotation_scale)
    surface_point = (
        annotation_world_point(side["face_front_surface"], "side", actor_center.z, annotation_scale)
        if "face_front_surface" in side
        else None
    )
    target_mid = Vector(((screen_left.x + screen_right.x) * 0.5, side_center.y, (screen_left.z + screen_right.z + side_center.z) / 3.0))
    base_target_gap = abs(screen_right.x - screen_left.x)
    target_gap = base_target_gap * spacing_multiplier
    target_left = Vector((target_mid.x - target_gap * 0.5, target_mid.y, target_mid.z))
    target_right = Vector((target_mid.x + target_gap * 0.5, target_mid.y, target_mid.z))
    scale = base_target_gap / max(source_gap, 1e-6) * scale_multiplier
    if surface_point is not None:
        # Align the Miku eyeball's actual front-most surface to the annotated
        # face surface. Its depth differs from the procedural sphere used before.
        source_low, _ = world_bounds(eyeball)
        target_mid.y = surface_point.y - scale * (source_low.y - source_mid.y) + surface_inset
        target_left.y = target_mid.y
        target_right.y = target_mid.y
    transform = (
        Matrix.Translation(target_mid)
        @ Matrix.Scale(scale, 4)
        @ Matrix.Scale(spacing_multiplier, 4, (1.0, 0.0, 0.0))
        @ Matrix.Translation(-source_mid)
    )

    copies = []
    for source_name, output_name in MIKU_EYE_OBJECTS.items():
        if source_name == "eye_007_22_0_node" and not include_outline:
            continue
        source = source_by_name[source_name]
        copied = static_copy(source, output_name)
        object_transform = transform
        if surface_point is not None and source_name == "eye_007_22_0_node" and not conform_outline:
            # The Miku eyelid/outline mesh is much deeper than the eyeball.
            # Give it its own depth alignment so the skin-colored patch does
            # not sit in front of the actor's head like a sticker.
            outline_low, _ = world_bounds(source)
            outline_target_y = surface_point.y - scale * (outline_low.y - source_mid.y) + surface_inset
            outline_target = Vector((target_mid.x, outline_target_y, target_mid.z))
            object_transform = Matrix.Translation(outline_target) @ Matrix.Scale(scale, 4) @ Matrix.Translation(-source_mid)
        copied.matrix_world = object_transform @ source.matrix_world
        if source_name == "eye_007_22_0_node" and conform_outline:
            copied.matrix_world = transform @ source.matrix_world
            copied.data.materials.clear()
            if actor_mesh.data.materials:
                copied.data.materials.append(actor_mesh.data.materials[0])
            shrink = copied.modifiers.new("ConformMikuEyeOutlineToActorHead", "SHRINKWRAP")
            shrink.target = actor_mesh
            shrink.wrap_method = "NEAREST_SURFACEPOINT"
            shrink.wrap_mode = "ON_SURFACE"
            shrink.offset = 0.002
        copies.append(copied)

    if include_eyebrow:
        source = source_by_name[MIKU_BROW_SOURCE]
        copied = static_copy(source, MIKU_BROW_OUTPUT)
        brow_low, _ = world_bounds(source)
        brow_target_y = (
            surface_point.y - scale * (brow_low.y - source_mid.y) + brow_inset
            if surface_point is not None
            else target_mid.y
        )
        brow_target = Vector((target_mid.x, brow_target_y, target_mid.z))
        copied.matrix_world = Matrix.Translation(brow_target) @ Matrix.Scale(scale, 4) @ Matrix.Translation(-source_mid) @ source.matrix_world
        copies.append(copied)

    return copies, {
        "source_left": list(source_left),
        "source_right": list(source_right),
        "target_left": list(target_left),
        "target_right": list(target_right),
        "scale": scale,
        "scale_multiplier": scale_multiplier,
        "spacing_multiplier": spacing_multiplier,
        "source_objects": [obj.name for obj in copies],
    }


def main() -> int:
    options = cli_args()
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    actor_mesh, imported = load_actor_and_miku(options.fbx, options.miku_fbx)
    calibration = load_calibration(options.calibration)
    copies, placement = place_miku_eyes(
        actor_mesh,
        imported,
        calibration,
        include_outline=not options.no_eye_outline,
        scale_multiplier=options.scale,
        surface_inset=options.surface_inset,
        brow_inset=options.brow_inset,
        conform_outline=options.conform_outline,
        include_eyebrow=options.include_eyebrow,
        spacing_multiplier=options.spacing_multiplier,
    )
    source_objects = [obj for obj in imported if obj.name not in MIKU_EYE_OBJECTS]
    hide_imported_source(source_objects)
    for obj in imported:
        if obj.name in MIKU_EYE_OBJECTS:
            obj.hide_render = True
            obj.hide_viewport = True

    low, high = bounds(actor_mesh)
    actor_center = (low + high) * 0.5
    scene = bpy.context.scene
    scene.frame_set(1)
    setup_render(scene, -1.0)
    camera_specs = {
        "front": (0.0, -12.0, actor_center.z),
        "right": (12.0, 0.0, actor_center.z),
        "back": (0.0, 12.0, actor_center.z),
        "left": (-12.0, 0.0, actor_center.z),
    }
    for direction, location in camera_specs.items():
        camera = make_camera(scene, actor_center, direction, location, max(4.0, high.z - low.z + 0.6))
        scene.camera = camera
        scene.render.filepath = str(output / f"{direction}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)

    if options.save_blend:
        options.save_blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(options.save_blend.resolve()))
        print(f"MIKU_EYE_BLEND_SAVED path={options.save_blend.resolve()}")
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "assetslab_miku_chibi_eye_on_accurig_v1",
                "actor_fbx": str(options.fbx.resolve()),
                "source_miku_fbx": str(options.miku_fbx.resolve()),
                "calibration": str(options.calibration.resolve()),
                "placement": placement,
                "surface_inset": options.surface_inset,
                "brow_inset": options.brow_inset,
                "conform_outline": options.conform_outline,
                "include_eyebrow": options.include_eyebrow,
                "spacing_multiplier": options.spacing_multiplier,
                "status": "static_four_direction_review_only",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"MIKU_EYE_ON_ACCURIG_PASS output={output}")
    print(f"MIKU_EYE_PLACEMENT {placement}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
