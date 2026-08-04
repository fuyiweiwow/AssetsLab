"""Render a close front reference of the original Miku chibi model."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--fbx", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--size", type=int, default=1024)
    parser.add_argument("--ortho-scale", type=float, default=175.0)
    return parser.parse_args(argv)


def bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    return (
        Vector((min(point[i] for point in points) for i in range(3))),
        Vector((max(point[i] for point in points) for i in range(3))),
    )


def look_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def main() -> int:
    options = args()
    options.output.resolve().parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(options.fbx.resolve()), use_anim=True)

    keep_exact = {
        "head_org_0_0_node",
        "head_back_2_0_node",
        "head_set_2_0_node",
        "eye_007_22_0_node",
        "eyeball_1_0_node",
        "eyebrow_008_56_0_node",
        "mouth_000_0_0_node",
    }
    keep_prefix = ("front_MZ_", "back_MZ_", "hair_tie_")
    kept = []
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        keep = obj.name in keep_exact or obj.name.startswith(keep_prefix)
        obj.hide_render = not keep
        obj.hide_viewport = not keep
        if keep:
            kept.append(obj)

    low, high = bounds(kept)
    target = Vector(((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, 244.0))
    camera_data = bpy.data.cameras.new("MikuFaceReferenceCamera")
    camera = bpy.data.objects.new("MikuFaceReferenceCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location = (target.x, -650.0, target.z)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = options.ortho_scale
    look_at(camera, target)

    scene = bpy.context.scene
    scene.camera = camera
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = options.size
    scene.render.resolution_y = options.size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("MikuFaceReferenceWorld")
    scene.world.color = (0.035, 0.045, 0.065)
    scene.view_settings.look = "None"
    scene.render.filepath = str(options.output.resolve())
    bpy.ops.render.render(write_still=True)
    print(f"MIKU_FACE_REFERENCE_PASS output={options.output.resolve()} size={options.size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
