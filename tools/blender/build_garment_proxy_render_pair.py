"""Build and render a physics-proxy/render-garment pair.

The input blend already contains the reviewed Actor-transfer garment with
nearest-Actor weights and an Armature modifier.  This pass keeps that mesh as
the animation/physics proxy, creates a separate render mesh, applies a small
render-only subdivision, and binds the render mesh with Surface Deform.

The important production boundary is intentional: only the proxy has the
Armature modifier.  The render garment follows the animated proxy through
Surface Deform, so a future high-resolution garment can replace the render
mesh without changing the physics or Actor-weight transfer stage.
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

from render_eye_assembly_blink_walk import (  # noqa: E402
    DIRECTIONS,
    configure_lighting,
    visible_bounds,
)
from render_procedural_anime_eye_on_accurig import make_camera  # noqa: E402


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--proxy-name", default="GarmentCodeShirt_ActorTransfer")
    parser.add_argument("--resolution", type=int, default=256)
    parser.add_argument("--subdivision-level", type=int, default=1)
    return parser.parse_args(argv)


def apply_render_subdivision(obj: bpy.types.Object, level: int) -> dict[str, int]:
    if level < 1:
        raise RuntimeError("render subdivision level must be at least 1")
    before = len(obj.data.vertices)
    modifier = obj.modifiers.new("RenderGarmentSubdivision", "SUBSURF")
    modifier.subdivision_type = "CATMULL_CLARK"
    modifier.levels = level
    modifier.render_levels = level
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj.data.update()
    return {"before_vertices": before, "after_vertices": len(obj.data.vertices), "level": level}


def bind_surface_deform(render_garment: bpy.types.Object, proxy: bpy.types.Object) -> dict[str, object]:
    modifier = render_garment.modifiers.new("SurfaceDeformFromPhysicsProxy", "SURFACE_DEFORM")
    modifier.target = proxy
    modifier.strength = 1.0
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = render_garment
    render_garment.select_set(True)
    result = bpy.ops.object.surfacedeform_bind(modifier=modifier.name)
    render_garment.select_set(False)
    if "FINISHED" not in result:
        raise RuntimeError(f"Surface Deform bind did not finish: {result}")
    bpy.context.view_layer.update()
    return {
        "modifier": modifier.name,
        "target": proxy.name,
        "strength": modifier.strength,
        "bound": bool(modifier.is_bound),
    }


def render_walk(scene: bpy.types.Scene, output: Path, resolution: int) -> list[dict[str, object]]:
    low, high = visible_bounds()
    center = (low + high) * 0.5
    configure_lighting(scene, center, "soft_flat")
    scene.view_settings.exposure = 0.35
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    armature = bpy.data.objects.get("Armature")
    if armature is None or not armature.animation_data or armature.animation_data.action is None:
        raise RuntimeError("Actor armature has no active walk action")
    action = armature.animation_data.action
    start, end = int(action.frame_range[0]), int(action.frame_range[1])
    sample_frames = [round(start + (end - start) * index / 7.0) for index in range(8)]
    ortho_scale = max(high.z - low.z, high.x - low.x, high.y - low.y) * 1.16
    frames: list[dict[str, object]] = []
    for direction, (x, y) in DIRECTIONS.items():
        camera = make_camera(scene, center, f"GarmentProxyRender_{direction}", (x, y, center.z), ortho_scale)
        scene.camera = camera
        for index, source_frame in enumerate(sample_frames):
            scene.frame_set(source_frame)
            bpy.context.view_layer.update()
            path = output / f"{direction}_{index:02d}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            frames.append({"direction": direction, "sample_index": index, "source_frame": source_frame, "path": path.name})
        bpy.data.objects.remove(camera, do_unlink=True)
    return frames


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.input_blend.resolve()))
    scene = bpy.context.scene
    scene.frame_set(1)
    proxy = bpy.data.objects.get(options.proxy_name)
    if proxy is None or proxy.type != "MESH":
        raise RuntimeError(f"input blend is missing mesh proxy: {options.proxy_name}")
    if not any(modifier.type == "ARMATURE" for modifier in proxy.modifiers):
        raise RuntimeError("physics proxy must retain its Actor Armature modifier")

    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for child in output.iterdir():
        if child.is_file() and child.suffix.lower() in {".png", ".blend", ".json"}:
            child.unlink()

    proxy.name = "GarmentCodeShirt_PhysicsProxy"
    proxy["assetslab_role"] = "physics_proxy"
    proxy["assetslab_proxy_source"] = "official_garmentcode_sim_obj_transferred_to_actor"
    proxy.hide_render = True
    proxy.display_type = "WIRE"

    render_garment = proxy.copy()
    render_garment.data = proxy.data.copy()
    render_garment.name = "GarmentCodeShirt_RenderGarment"
    render_garment["assetslab_role"] = "render_garment"
    render_garment["assetslab_deformation_source"] = proxy.name
    render_garment.parent = None
    render_garment.matrix_world = proxy.matrix_world.copy()
    render_garment.hide_render = False
    render_garment.hide_viewport = False
    render_garment.display_type = "TEXTURED"
    scene.collection.objects.link(render_garment)
    for modifier in list(render_garment.modifiers):
        render_garment.modifiers.remove(modifier)

    subdivision = apply_render_subdivision(render_garment, options.subdivision_level)
    surface_deform = bind_surface_deform(render_garment, proxy)
    bpy.context.view_layer.update()

    scene["assetslab_garment_proxy_render_pair_status"] = "review_required"
    scene["assetslab_garment_proxy_render_pair_method"] = "physics_proxy_armature_plus_render_subdivision_plus_surface_deform"
    frames = render_walk(scene, output, options.resolution)
    blend_path = output / "garmentcode_proxy_render_pair_candidate.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    report = {
        "schema": "assetslab_garmentcode_proxy_render_pair_review_v1",
        "input_blend": str(options.input_blend.resolve()),
        "physics_proxy": {
            "object": proxy.name,
            "vertex_count": len(proxy.data.vertices),
            "armature_modifier": next(modifier.name for modifier in proxy.modifiers if modifier.type == "ARMATURE"),
            "hide_render": proxy.hide_render,
        },
        "render_garment": {
            "object": render_garment.name,
            "vertex_count": len(render_garment.data.vertices),
            "subdivision": subdivision,
            "surface_deform": surface_deform,
            "armature_modifier": any(modifier.type == "ARMATURE" for modifier in render_garment.modifiers),
        },
        "animation": {
            "directions": list(DIRECTIONS),
            "frame_count": len(frames),
            "frames": frames,
        },
        "blend": str(blend_path),
        "status": "review_required",
    }
    (output / "manifest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
