"""Fit a static FBX hair mesh to the current chibi actor in background Blender."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_hair_style_candidate as fit_tools


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--hair-fbx", required=True, type=Path)
    parser.add_argument("--actor-blend", required=True, type=Path)
    parser.add_argument("--output-blend", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--q-height-ratio", type=float, default=1.15)
    parser.add_argument("--rotation-z", type=float, default=0.0)
    parser.add_argument("--color", nargs=4, type=float, default=(0.12, 0.045, 0.025, 1.0))
    return parser.parse_args(argv)


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.actor_blend.resolve()))
    before = {obj.as_pointer() for obj in bpy.data.objects}
    bpy.ops.import_scene.fbx(filepath=str(options.hair_fbx.resolve()), use_anim=False)
    imported = [
        obj for obj in bpy.data.objects
        if obj.as_pointer() not in before and obj.type == "MESH"
    ]
    if len(imported) != 1:
        raise RuntimeError(f"expected one imported FBX hair mesh, found {len(imported)}")
    tile = imported[0]
    tile.name = "HairCandidate_StaticFBX"
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    body = next(obj for obj in bpy.data.objects if obj.type == "MESH" and obj.name.startswith("ChibiBase"))

    # Normalize the source in its current FBX orientation, then fit its width
    # and cap its height for the chibi head.
    bpy.context.view_layer.objects.active = tile
    bpy.ops.object.select_all(action="DESELECT")
    tile.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if options.rotation_z:
        tile.rotation_euler.z += options.rotation_z
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    low, high = fit_tools.bounds(tile)
    head_center, head_width, head_top = fit_tools.head_target(armature, body)
    current_width = max(high.x - low.x, 0.001)
    fit_scale = (head_width * 1.08) / current_width
    tile.scale = (fit_scale, fit_scale, fit_scale)
    bpy.context.view_layer.update()
    low, high = fit_tools.bounds(tile)
    current_height = max(high.z - low.z, 0.001)
    max_height = max(head_width * options.q_height_ratio, 0.001)
    q_height_scale = min(1.0, max_height / current_height)
    tile.scale.z *= q_height_scale
    bpy.context.view_layer.update()
    low, high = fit_tools.bounds(tile)
    tile.location += Vector(
        (
            head_center.x - (low.x + high.x) * 0.5,
            head_center.y - (low.y + high.y) * 0.5,
            head_top + 0.06 - high.z,
        )
    )
    bpy.context.view_layer.update()

    material = fit_tools.make_material(tuple(options.color))
    tile.data.materials.clear()
    tile.data.materials.append(material)
    for polygon in tile.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True
    world = tile.matrix_world.copy()
    tile.parent = armature
    tile.parent_type = "BONE"
    tile.parent_bone = fit_tools.HEAD_BONE
    tile.matrix_world = world

    fit_tools.configure_render(bpy.context.scene)
    output_dir = options.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    renders = fit_tools.render_views(bpy.context.scene, output_dir, body, tile)
    options.output_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.output_blend.resolve()))
    manifest = {
        "schema": "assetslab_chibi_static_fbx_hair_candidate_v1",
        "source_fbx": str(options.hair_fbx.resolve()),
        "actor_blend": str(options.actor_blend.resolve()),
        "object": tile.name,
        "vertices": len(tile.data.vertices),
        "polygons": len(tile.data.polygons),
        "fit": {
            "fit_scale": fit_scale,
            "q_height_ratio": options.q_height_ratio,
            "q_height_scale": q_height_scale,
            "rotation_z": options.rotation_z,
            "dimensions": [float(value) for value in tile.dimensions],
            "parent_bone": fit_tools.HEAD_BONE,
            "head_width": head_width,
            "head_top": head_top,
        },
        "renders": renders,
        "status": "attached_candidate_review_required",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"CHIBI_STATIC_FBX_HAIR_CANDIDATE_PASS vertices={len(tile.data.vertices)} output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
