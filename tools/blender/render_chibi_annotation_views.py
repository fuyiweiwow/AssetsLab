"""Render simple front/side images for the browser-based binding annotator."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_original_chibi_actor_test import load_source_mesh  # noqa: E402


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh = load_source_mesh(options.source, center_source=False)
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    from render_original_chibi_actor_test import apply_source_display_modifiers
    apply_source_display_modifiers(mesh)
    points = [mesh.matrix_world @ Vector(corner) for corner in mesh.bound_box]
    low = Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points)))
    high = Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)))
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
        scene.render.filepath = str(options.output / (name + ".png"))
        bpy.ops.render.render(write_still=True)
    print("CHIBI_ANNOTATION_VIEWS_PASS output=%s" % options.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
