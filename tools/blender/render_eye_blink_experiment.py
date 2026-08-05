"""Render a few frames of the derived 3D eye-blink experiment headlessly."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frames", type=int, nargs="+", default=[1, 30, 40])
    return parser.parse_args(argv)


def bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector((min(point[i] for point in points) for i in range(3))),
        Vector((max(point[i] for point in points) for i in range(3))),
    )


def make_camera(scene: bpy.types.Scene, target: Vector, location: Vector, scale: float) -> bpy.types.Object:
    camera_data = bpy.data.cameras.new("EyeBlinkReviewCameraData")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = scale
    camera = bpy.data.objects.new("EyeBlinkReviewCamera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = location
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    return camera


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.blend.resolve()))
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    actor = next(obj for obj in bpy.data.objects if obj.type == "MESH" and obj.name.startswith("ChibiBaseMesh"))
    low, high = bounds(actor)
    center = (low + high) * 0.5
    scene = bpy.context.scene
    # The Actor V1 open eyes are imagegen-derived texture materials. Workbench
    # ignores their node-based alpha/color path, so the review must use Eevee.
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.render.film_transparent = False

    camera_specs = {
        "front": Vector((0.0, -12.0, center.z)),
        "threequarter": Vector((8.5, -8.5, center.z)),
        "right": Vector((12.0, 0.0, center.z)),
        "back": Vector((0.0, 12.0, center.z)),
    }
    for view_name, location in camera_specs.items():
        camera = make_camera(scene, center, location, max(4.0, high.z - low.z + 0.6))
        scene.camera = camera
        for frame in options.frames:
            scene.frame_set(frame)
            scene.render.filepath = str(output / f"{view_name}_frame{frame:03d}.png")
            bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)
    print(f"EYE_BLINK_RENDER_PASS output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
