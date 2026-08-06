"""Render GarmentCode's native stitched BoxMesh beside its matching body."""

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
        "GarmentCodeNativeBoxMeshTshirt",
        options.scale,
        make_material("GarmentCodeNativeCotton", (0.12, 0.36, 0.72, 1.0)),
    )

    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.context.view_layer.update()
    low, high = visible_bounds()
    center = (low + high) * 0.5
    print(f"visible_bounds low={tuple(low)} high={tuple(high)} center={tuple(center)}")
    configure_lighting(scene, center, "soft_flat")
    scene.view_settings.exposure = 0.25
    # The matching body is Y-up while the project scene is Z-up.  Workbench
    # keeps this diagnostic preview readable without inheriting the Actor's
    # Z-up light rig, which would back-light the GarmentCode body.
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = options.resolution
    scene.render.resolution_y = options.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    ortho_scale = max(high.z - low.z, high.x - low.x, high.y - low.y) * 1.16
    frames = []
    for direction, (x, y) in DIRECTIONS.items():
        camera = make_camera(scene, center, f"NativeBoxMesh_{direction}", (x, y, center.z), ortho_scale)
        scene.camera = camera
        frame_path = output / f"{direction}_00.png"
        scene.render.filepath = str(frame_path)
        bpy.ops.render.render(write_still=True)
        frames.append({"direction": direction, "path": frame_path.name})
        bpy.data.objects.remove(camera, do_unlink=True)

    bpy.ops.wm.save_as_mainfile(filepath=str(output / "garmentcode_native_boxmesh_preview.blend"))
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "assetslab_garmentcode_native_boxmesh_review_v1",
                "generator": "GarmentCode_BoxMesh_native_topology",
                "body": str(options.body_obj.resolve()),
                "garment": str(options.garment_obj.resolve()),
                "garment_scale": options.scale,
                "status": "native_boxmesh_static_review",
                "frames": frames,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "native_boxmesh_static_review", "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
