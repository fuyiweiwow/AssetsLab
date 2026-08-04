"""Render eight-frame four-direction previews for an animation candidate."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


DIRECTIONS = ("front", "right", "back", "left")


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--resolution", type=int, default=256)
    parser.add_argument("--frames", type=int, default=8)
    parser.add_argument(
        "--color-type",
        choices=("MATERIAL", "TEXTURE", "OBJECT", "RANDOM", "VERTEX", "SINGLE"),
        default="TEXTURE",
        help="Workbench shading source; TEXTURE keeps transparent eye cards inspectable.",
    )
    return parser.parse_args(argv)


def visible_meshes() -> list[bpy.types.Object]:
    return [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and not obj.hide_render]


def bounds(meshes: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    if not points:
        raise RuntimeError("no visible mesh objects found")
    low = Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points)))
    high = Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)))
    return low, high


def make_camera(scene: bpy.types.Scene, center: Vector, distance: float, ortho_scale: float, direction: str):
    data = bpy.data.cameras.new(f"AnimationPreviewCamera_{direction}")
    data.type = "ORTHO"
    data.ortho_scale = ortho_scale
    data.clip_start = 0.001
    data.clip_end = 100.0
    camera = bpy.data.objects.new(f"AnimationPreviewCamera_{direction}", data)
    scene.collection.objects.link(camera)
    offsets = {
        "front": Vector((0.0, -distance, 0.0)),
        "right": Vector((distance, 0.0, 0.0)),
        "back": Vector((0.0, distance, 0.0)),
        "left": Vector((-distance, 0.0, 0.0)),
    }
    camera.location = center + offsets[direction]
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    return camera


def configure_scene(scene: bpy.types.Scene, resolution: int, color_type: str) -> None:
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = color_type
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.curvature_ridge_factor = 1.3
    scene.display.shading.curvature_valley_factor = 1.0


def main() -> int:
    options = parse_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.blend.resolve()))
    scene = bpy.context.scene
    meshes = visible_meshes()
    if not meshes:
        raise RuntimeError("candidate blend has no visible meshes")
    configure_scene(scene, options.resolution, options.color_type)
    action = None
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE" and obj.animation_data and obj.animation_data.action:
            action = obj.animation_data.action
            break
    if action is None:
        raise RuntimeError("candidate blend has no armature action")
    start, end = int(action.frame_range[0]), int(action.frame_range[1])
    sample_frames = [round(start + (end - start) * index / max(options.frames - 1, 1)) for index in range(options.frames)]
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for frame_index, frame in enumerate(sample_frames):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        low, high = bounds(meshes)
        center = (low + high) * 0.5
        height = max(high.z - low.z, 0.1)
        horizontal = max(high.x - low.x, high.y - low.y, 0.1)
        camera_scale = max(height * 1.16, horizontal * 1.35)
        distance = max(height * 2.0, 1.0)
        for direction in DIRECTIONS:
            camera = make_camera(scene, center, distance, camera_scale, direction)
            scene.camera = camera
            scene.render.filepath = str(output / f"{direction}_{frame_index:02d}.png")
            bpy.ops.render.render(write_still=True)
            bpy.data.objects.remove(camera, do_unlink=True)
    manifest = {
        "schema": "assetslab_animation_candidate_render_v1",
        "blend": str(options.blend.resolve()),
        "action": action.name,
        "frame_range": [start, end],
        "sample_frames": sample_frames,
        "directions": list(DIRECTIONS),
        "resolution": options.resolution,
        "color_type": options.color_type,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"ANIMATION_RENDER_PASS frames={len(sample_frames)} directions={len(DIRECTIONS)} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
