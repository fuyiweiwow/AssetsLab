"""Run a restrained Cloth pass from the body-surface-fitted BoxMesh pose."""

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
    parser.add_argument("--fitted-blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--settle-frame", type=int, default=100)
    parser.add_argument("--resolution", type=int, default=256)
    return parser.parse_args(argv)


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
        camera = make_camera(scene, center, f"FittedBoxMeshCloth_{direction}", (x, y, center.z), ortho_scale)
        scene.camera = camera
        frame_path = output / f"{direction}_00.png"
        scene.render.filepath = str(frame_path)
        bpy.ops.render.render(write_still=True)
        frames.append({"direction": direction, "path": frame_path.name})
        bpy.data.objects.remove(camera, do_unlink=True)
    return frames


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.fitted_blend.resolve()))
    scene = bpy.context.scene
    scene.frame_set(1)
    body = bpy.data.objects.get("GarmentCodeMeanBody")
    garment = bpy.data.objects.get("GarmentCodeNativeBoxMeshTshirt_Fitted")
    if body is None or garment is None:
        raise RuntimeError("fitted blend is missing the expected body or garment object")

    body.hide_render = False
    body.hide_viewport = False
    garment.hide_render = False
    garment.hide_viewport = False
    collision = body.modifiers.get("FittedBodyCollision") or body.modifiers.new("FittedBodyCollision", "COLLISION")
    collision.settings.thickness_outer = 0.006
    collision.settings.thickness_inner = 0.006

    pin_group = garment.vertex_groups.get("FittedClothShoulderPins") or garment.vertex_groups.new(name="FittedClothShoulderPins")
    pinned = []
    for index, vertex in enumerate(garment.data.vertices):
        world = garment.matrix_world @ vertex.co
        if world.z >= 1.24 and abs(world.y) <= 0.23:
            pinned.append(index)
    if not pinned:
        raise RuntimeError("fitted garment produced no shoulder pin vertices")
    pin_group.add(pinned, 1.0, "REPLACE")

    cloth = garment.modifiers.get("FittedBoxMeshCloth") or garment.modifiers.new("FittedBoxMeshCloth", "CLOTH")
    cloth.settings.quality = 10
    cloth.settings.mass = 0.18
    cloth.settings.tension_stiffness = 18.0
    cloth.settings.compression_stiffness = 18.0
    cloth.settings.shear_stiffness = 10.0
    cloth.settings.bending_stiffness = 1.2
    cloth.settings.air_damping = 8.0
    cloth.settings.vertex_group_mass = pin_group.name
    cloth.settings.pin_stiffness = 100.0
    cloth.collision_settings.use_self_collision = False

    scene.frame_start = 1
    scene.frame_end = options.settle_frame
    scene.frame_set(1)
    bpy.context.view_layer.update()
    scene.frame_set(options.settle_frame)
    bpy.context.view_layer.update()

    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    frames = render_four_views(scene, output)

    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = garment.evaluated_get(depsgraph)
    baked_mesh = evaluated.to_mesh()
    baked = garment.copy()
    baked.data = baked_mesh.copy()
    baked.name = "GarmentCodeNativeBoxMeshTshirt_Fitted_BAKED"
    scene.collection.objects.link(baked)
    baked.modifiers.clear()
    baked["assetslab_garmentcode_fitted_cloth_status"] = "matched_body_drape_baked"
    garment.hide_render = True
    garment.hide_viewport = True
    evaluated.to_mesh_clear()

    bpy.ops.wm.save_as_mainfile(filepath=str(output / "garmentcode_fitted_boxmesh_cloth.blend"))
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "assetslab_garmentcode_fitted_boxmesh_cloth_review_v1",
                "generator": "GarmentCode_native_BoxMesh_Shrinkwrap_plus_Blender_Cloth",
                "source_blend": str(options.fitted_blend.resolve()),
                "settle_frame": options.settle_frame,
                "pinned_vertices": len(pinned),
                "self_collision": False,
                "status": "fitted_pose_cloth_baked",
                "next_stage": "inspect_cloth_stability_before_actor_transfer",
                "frames": frames,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "fitted_pose_cloth_baked", "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
