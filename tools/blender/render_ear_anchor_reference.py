"""Render clean front/right reference images for the browser ear annotator."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from render_procedural_anime_eye_on_accurig import bounds, make_camera  # noqa: E402


def args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-blend", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args(argv)


def main() -> int:
    options = args()
    bpy.ops.wm.open_mainfile(filepath=str(options.input_blend.resolve()))
    output = options.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    actor = next(obj for obj in bpy.data.objects if obj.type == "MESH" and obj.name.startswith("ChibiBase"))
    low, high = bounds(actor)
    center = (low + high) * 0.5
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    for name, location in {"front": (0.0, -12.0, center.z), "right": (12.0, 0.0, center.z)}.items():
        camera = make_camera(scene, center, name, location, max(4.0, high.z - low.z + 0.6))
        scene.camera = camera
        scene.render.filepath = str(output / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)
    print(f"EAR_ANCHOR_REFERENCE_PASS output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
