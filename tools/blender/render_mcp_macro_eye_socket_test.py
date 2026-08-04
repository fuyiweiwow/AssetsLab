"""Render close front/right evidence for an MCP macro eye-socket test."""

from __future__ import annotations

import argparse
from pathlib import Path

import bpy
from mathutils import Vector


def args() -> argparse.Namespace:
    argv = __import__("sys").argv
    values = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--body", default="ChibiBaseMesh_AccuRIG_InputMesh.001")
    parser.add_argument("--frame", type=int, default=1)
    return parser.parse_args(values)


def bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return Vector((min(p[i] for p in points) for i in range(3))), Vector((max(p[i] for p in points) for i in range(3)))


def main() -> None:
    options = args()
    options.out.mkdir(parents=True, exist_ok=True)
    body = bpy.data.objects.get(options.body)
    eye = bpy.data.objects.get("MikuChibiEyeball")
    if body is None or eye is None:
        raise RuntimeError("MCP macro test scene is missing body duplicate or eye assembly")
    scene = bpy.context.scene
    scene.frame_set(options.frame)
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    world = scene.world or bpy.data.worlds.new("MCPMacroWorld")
    scene.world = world
    world.color = (0.025, 0.025, 0.04)
    for index, (location, energy, size) in enumerate((((0.0, -4.0, 5.0), 700.0, 4.0), ((-3.0, -2.0, 2.0), 350.0, 3.0))):
        light_data = bpy.data.lights.new(f"MCPMacroLight{index}", "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(f"MCPMacroLight{index}", light_data)
        scene.collection.objects.link(light)
        light.location = location
    low, high = bounds(eye)
    target = (low + high) * 0.5
    for direction, location in (("front", target + Vector((0.0, -10.0, 0.0))), ("right", target + Vector((10.0, 0.0, 0.0)))):
        camera_data = bpy.data.cameras.new(f"MCPMacroCamera_{direction}")
        camera_data.type = "ORTHO"
        camera_data.ortho_scale = 2.0
        camera = bpy.data.objects.new(f"MCPMacroCamera_{direction}", camera_data)
        scene.collection.objects.link(camera)
        camera.location = location
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.camera = camera
        scene.render.filepath = str(options.out / f"{direction}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)


if __name__ == "__main__":
    main()
