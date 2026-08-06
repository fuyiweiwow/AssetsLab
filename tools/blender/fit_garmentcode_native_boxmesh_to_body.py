"""Fit the native GarmentCode BoxMesh to the matching body surface.

This is a pre-cloth gate. It deliberately renders the shrinkwrapped static
pose first so self-intersections and side closure can be reviewed separately
from any physics solver.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from render_eye_assembly_blink_walk import configure_lighting, visible_bounds  # noqa: E402
from render_procedural_anime_eye_on_accurig import make_camera  # noqa: E402
from simulate_garmentcode_pattern_cloth import DIRECTIONS  # noqa: E402


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-blend", required=True, type=Path)
    parser.add_argument("--body-obj", required=True, type=Path)
    parser.add_argument("--garment-obj", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scale", type=float, default=0.01)
    parser.add_argument("--offset", type=float, default=0.025)
    parser.add_argument("--resolution", type=int, default=256)
    return parser.parse_args(argv)


def make_material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    result = bpy.data.materials.new(name)
    result.diffuse_color = color
    result.use_nodes = True
    shader = result.node_tree.nodes.get("Principled BSDF")
    if shader:
        shader.inputs["Base Color"].default_value = color
        shader.inputs["Roughness"].default_value = 0.86
    return result


def import_mesh(path: Path, name: str, scale: float, material: bpy.types.Material) -> bpy.types.Object:
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(path.resolve()))
    imported = [obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH"]
    if not imported:
        raise RuntimeError(f"No mesh imported from {path}")
    obj = imported[-1]
    obj.name = name
    obj.scale = (scale, scale, scale)
    obj.data.materials.append(material)
    return obj


def render_four_views(scene: bpy.types.Scene, output: Path) -> list[dict[str, str]]:
    bpy.context.view_layer.update()
    low, high = visible_bounds()
    center = (low + high) * 0.5
    configure_lighting(scene, center, "soft_flat")
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = 256
    scene.render.resolution_y = 256
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    ortho_scale = max(high.z - low.z, high.x - low.x, high.y - low.y) * 1.16
    frames = []
    for direction, (x, y) in DIRECTIONS.items():
        camera = make_camera(scene, center, f"NativeBoxMeshFit_{direction}", (x, y, center.z), ortho_scale)
        scene.camera = camera
        frame_path = output / f"{direction}_00.png"
        scene.render.filepath = str(frame_path)
        bpy.ops.render.render(write_still=True)
        frames.append({"direction": direction, "path": frame_path.name})
        bpy.data.objects.remove(camera, do_unlink=True)
    return frames


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.base_blend.resolve()))
    scene = bpy.context.scene
    scene.frame_set(1)
    for obj in scene.objects:
        if obj.type == "MESH":
            obj.hide_render = True
            obj.hide_viewport = True

    body = import_mesh(
        options.body_obj,
        "GarmentCodeMeanBody",
        1.0,
        make_material("GarmentCodeMeanBodyMaterial", (0.62, 0.65, 0.70, 1.0)),
    )
    garment = import_mesh(
        options.garment_obj,
        "GarmentCodeNativeBoxMeshTshirt_Fitted",
        options.scale,
        make_material("GarmentCodeNativeFittedCotton", (0.12, 0.36, 0.72, 1.0)),
    )
    bpy.context.view_layer.update()

    shrinkwrap = garment.modifiers.new("FitToMatchingBodySurface", "SHRINKWRAP")
    shrinkwrap.target = body
    shrinkwrap.wrap_method = "NEAREST_SURFACEPOINT"
    shrinkwrap.wrap_mode = "ON_SURFACE"
    shrinkwrap.offset = options.offset

    bpy.context.view_layer.objects.active = garment
    garment.select_set(True)
    bpy.ops.object.modifier_apply(modifier=shrinkwrap.name)
    garment.select_set(False)
    bpy.context.view_layer.update()

    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    frames = render_four_views(scene, output)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "garmentcode_native_boxmesh_fitted.blend"))
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "assetslab_garmentcode_native_boxmesh_fit_review_v1",
                "generator": "GarmentCode_native_BoxMesh_plus_Blender_Shrinkwrap",
                "body": str(options.body_obj.resolve()),
                "garment": str(options.garment_obj.resolve()),
                "garment_scale": options.scale,
                "surface_offset": options.offset,
                "status": "body_surface_fit_static_review",
                "next_stage": "inspect_self_intersection_and_side_closure",
                "frames": frames,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "body_surface_fit_static_review", "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
