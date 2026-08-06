"""Drape GarmentCode's native stitched BoxMesh on its matching body."""

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
    parser.add_argument("--settle-frame", type=int, default=160)
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
    collision = body.modifiers.new("GarmentCodeMeanBodyCollision", "COLLISION")
    collision.settings.thickness_outer = 0.008
    collision.settings.thickness_inner = 0.008
    garment = import_mesh(
        options.garment_obj,
        "GarmentCodeNativeBoxMeshTshirt",
        options.scale,
        make_material("GarmentCodeNativeCotton", (0.12, 0.36, 0.72, 1.0)),
    )

    bpy.context.view_layer.update()
    pin_group = garment.vertex_groups.new(name="NativeBoxMeshShoulderPins")
    pinned = []
    for index, vertex in enumerate(garment.data.vertices):
        world = garment.matrix_world @ vertex.co
        # Imported OBJ is converted to the project's Z-up coordinates.
        # Pin only the upper shoulder/neck band; sleeves and hem must relax.
        if world.z >= 1.25 and abs(world.y) <= 0.22:
            pinned.append(index)
    if not pinned:
        raise RuntimeError("native BoxMesh produced no shoulder pin vertices")
    pin_group.add(pinned, 1.0, "REPLACE")

    cloth = garment.modifiers.new("NativeBoxMeshGarmentCloth", "CLOTH")
    cloth.settings.quality = 12
    cloth.settings.mass = 0.25
    cloth.settings.tension_stiffness = 35.0
    cloth.settings.compression_stiffness = 35.0
    cloth.settings.shear_stiffness = 18.0
    cloth.settings.bending_stiffness = 1.8
    cloth.settings.air_damping = 5.0
    cloth.settings.vertex_group_mass = pin_group.name
    cloth.settings.pin_stiffness = 100.0
    cloth.collision_settings.use_self_collision = True
    cloth.collision_settings.self_friction = 5.0

    scene.frame_start = 1
    scene.frame_end = options.settle_frame
    scene.frame_set(1)
    bpy.context.view_layer.update()
    scene.frame_set(options.settle_frame)
    bpy.context.view_layer.update()

    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    low, high = visible_bounds()
    center = (low + high) * 0.5
    configure_lighting(scene, center, "soft_flat")
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
        camera = make_camera(scene, center, f"NativeBoxMeshCloth_{direction}", (x, y, center.z), ortho_scale)
        scene.camera = camera
        frame_path = output / f"{direction}_00.png"
        scene.render.filepath = str(frame_path)
        bpy.ops.render.render(write_still=True)
        frames.append({"direction": direction, "path": frame_path.name})
        bpy.data.objects.remove(camera, do_unlink=True)

    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = garment.evaluated_get(depsgraph)
    baked_mesh = evaluated.to_mesh()
    baked = garment.copy()
    baked.data = baked_mesh.copy()
    baked.name = "GarmentCodeNativeBoxMeshTshirt_BAKED"
    scene.collection.objects.link(baked)
    baked.modifiers.clear()
    baked["assetslab_garmentcode_native_cloth_status"] = "matched_body_drape_baked"
    garment.hide_render = True
    garment.hide_viewport = True
    evaluated.to_mesh_clear()

    bpy.ops.wm.save_as_mainfile(filepath=str(output / "garmentcode_native_boxmesh_cloth.blend"))
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "assetslab_garmentcode_native_boxmesh_cloth_review_v1",
                "generator": "GarmentCode_native_BoxMesh_plus_Blender_Cloth",
                "body": str(options.body_obj.resolve()),
                "garment": str(options.garment_obj.resolve()),
                "garment_scale": options.scale,
                "settle_frame": options.settle_frame,
                "pinned_vertices": len(pinned),
                "status": "matched_body_drape_baked",
                "next_stage": "review_before_actor_transfer",
                "frames": frames,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "matched_body_drape_baked", "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
