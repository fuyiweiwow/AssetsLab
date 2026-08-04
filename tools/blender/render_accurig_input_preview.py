"""Render front and side previews of an exported AccuRIG FBX input."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--fbx", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def object_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points))),
        Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points))),
    )


def main() -> int:
    options = cli_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(options.fbx), use_anim=False)
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"expected one mesh, got {len(meshes)}")
    mesh = meshes[0]
    low, high = object_bounds(mesh)
    target_z = (low.z + high.z) * 0.5
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = True
    options.output.mkdir(parents=True, exist_ok=True)
    for name, location in (("front", (0.0, -12.0, target_z)), ("side", (-12.0, 0.0, target_z))):
        camera_data = bpy.data.cameras.new(name + "Data")
        camera_data.type = "ORTHO"
        camera_data.ortho_scale = max(4.0, (high.z - low.z) * 1.25)
        camera = bpy.data.objects.new(name + "Camera", camera_data)
        scene.collection.objects.link(camera)
        camera.location = location
        camera.rotation_euler = (Vector((0.0, 0.0, target_z)) - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.camera = camera
        scene.render.filepath = str(options.output / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    print(f"CHIBI_ACCURIG_PREVIEW_PASS mesh={mesh.name} vertices={len(mesh.data.vertices)} output={options.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
