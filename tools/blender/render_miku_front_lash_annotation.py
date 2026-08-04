"""Render a clean high-resolution front face image for manual lash annotation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from render_easy_anime_eye_on_accurig import make_camera, world_bounds  # noqa: E402


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--size", type=int, default=1024)
    parser.add_argument("--ortho-scale", type=float, default=1.55)
    return parser.parse_args(argv)


def main() -> int:
    options = cli_args()
    output = options.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(options.base_blend.resolve()))

    actor = bpy.data.objects.get("ChibiBaseMesh_AccuRIG_InputMesh")
    eye = bpy.data.objects.get("MikuChibiEyeball")
    if actor is None or eye is None:
        raise RuntimeError("base blend is missing actor or MikuChibiEyeball")

    eye_low, eye_high = world_bounds([eye])
    eye_center = (eye_low + eye_high) * 0.5
    actor_low, actor_high = world_bounds([actor])

    # Hide any previously generated facial add-ons if a later scene is used.
    for obj in bpy.data.objects:
        if obj.name.startswith(("ConceptEyebrow", "ConceptEyelash", "eyelashes.")):
            obj.hide_render = True

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = options.size
    scene.render.resolution_y = options.size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.look = "None"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("MikuLashAnnotationWorld")
    scene.world.color = (0.055, 0.055, 0.07)

    camera = make_camera(scene, eye_center, "MikuLashAnnotationCamera", (eye_center.x, -12.0, eye_center.z), options.ortho_scale)
    scene.camera = camera
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)
    print(f"MIKU_LASH_ANNOTATION_PASS output={output} size={options.size} ortho={options.ortho_scale}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
