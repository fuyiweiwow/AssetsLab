"""Render the downloaded BlenderKit Stylised Eye from multiple directions."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_camera(scene: bpy.types.Scene, name: str, location: tuple[float, float, float]) -> bpy.types.Object:
    data = bpy.data.cameras.new(name + "Data")
    data.type = "ORTHO"
    data.ortho_scale = 0.075
    camera = bpy.data.objects.new(name, data)
    scene.collection.objects.link(camera)
    camera.location = location
    look_at(camera, Vector((0.0, 0.0, 0.0)))
    return camera


def add_area(scene: bpy.types.Scene, location: tuple[float, float, float], energy: float, size: float) -> None:
    data = bpy.data.lights.new("StylisedEyeTestArea", "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    light = bpy.data.objects.new("StylisedEyeTestArea", data)
    scene.collection.objects.link(light)
    light.location = location
    look_at(light, Vector((0.0, 0.0, 0.0)))


def main() -> int:
    options = args()
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(options.source.resolve()))
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("StylisedEyeTestWorld")
    scene.world.color = (0.06, 0.06, 0.08)
    scene.view_settings.look = "Medium High Contrast"
    eye = bpy.data.objects.get("eye")
    if eye is None:
        raise RuntimeError("Stylised Eye source is missing the eye mesh")
    eye.hide_render = False
    add_area(scene, (0.0, -0.06, 0.05), 420.0, 0.06)
    add_area(scene, (0.04, 0.02, 0.02), 180.0, 0.04)
    views = {
        "front": (0.0, -0.10, 0.0),
        "back": (0.0, 0.10, 0.0),
        "left": (-0.10, 0.0, 0.0),
        "right": (0.10, 0.0, 0.0),
        "three_quarter": (-0.085, -0.085, 0.0),
    }
    for name, location in views.items():
        camera = add_camera(scene, "StylisedEyeCamera_" + name, location)
        scene.camera = camera
        scene.render.filepath = str(output / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)
    print("BLENDERKIT_STYLISED_EYE_SOURCE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
