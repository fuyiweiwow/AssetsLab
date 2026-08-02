"""Render Miku source face/eye candidates from both possible front directions."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args(argv)


def main() -> None:
    options = cli()
    names = {"head_org_0_0_node", "head_back_2_0_node", "eye_007_22_0_node", "eyeball_1_0_node", "eyebrow_008_56_0_node"}
    shown = []
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            obj.hide_render = obj.name not in names
            obj.hide_viewport = obj.name not in names
            obj.hide_set(obj.name not in names)
            if obj.name in names:
                shown.append(obj)
    if not shown:
        raise RuntimeError("Miku source eye candidates are missing")
    points = [obj.matrix_world @ Vector(corner) for obj in shown for corner in obj.bound_box]
    low = Vector((min(p[i] for p in points) for i in range(3)))
    high = Vector((max(p[i] for p in points) for i in range(3)))
    target = (low + high) * 0.5
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    world = scene.world or bpy.data.worlds.new("MikuDiagnosticWorld")
    scene.world = world
    world.color = (0.025, 0.025, 0.04)
    for index, (location, energy, size) in enumerate((((0.0, -6.0, 4.0), 900.0, 5.0), ((-3.0, -3.0, 1.0), 350.0, 3.0))):
        light_data = bpy.data.lights.new(f"MikuDiagnosticLight{index}", "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(f"MikuDiagnosticLight{index}", light_data)
        scene.collection.objects.link(light)
        light.location = location
    options.out.mkdir(parents=True, exist_ok=True)
    extent = max(high.x - low.x, high.z - low.z)
    for label, direction in (("front_minus_y", Vector((0.0, -12.0, 0.0))), ("front_plus_y", Vector((0.0, 12.0, 0.0)))):
        camera_data = bpy.data.cameras.new(f"MikuDiagnosticCamera_{label}")
        camera_data.type = "ORTHO"
        camera_data.ortho_scale = extent * 1.15
        camera = bpy.data.objects.new(f"MikuDiagnosticCamera_{label}", camera_data)
        scene.collection.objects.link(camera)
        camera.location = target + direction
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.camera = camera
        scene.render.filepath = str(options.out / f"{label}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)
    print({"shown": sorted(names & {obj.name for obj in shown}), "bounds": [list(low), list(high)]})


if __name__ == "__main__":
    main()
