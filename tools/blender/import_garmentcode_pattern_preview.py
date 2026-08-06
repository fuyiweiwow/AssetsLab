"""Import a GarmentCode sewing pattern as a fitted static Blender preview.

This is intentionally a pre-drape gate: it proves that the MIT-generated
panels can be placed around the project Actor with the expected low-detail
silhouette.  Cloth simulation, seam solving, weight transfer and animation
remain explicit later gates.
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


DIRECTIONS = {
    "front": (0.0, -12.0),
    "right": (12.0, 0.0),
    "back": (0.0, 12.0),
    "left": (-12.0, 0.0),
}


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor", required=True, type=Path)
    parser.add_argument("--pattern", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fit-scale", type=float, default=1.35)
    parser.add_argument("--resolution", type=int, default=256)
    return parser.parse_args(argv)


def make_material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    if shader is not None:
        shader.inputs["Base Color"].default_value = color
        shader.inputs["Roughness"].default_value = 0.82
    return material


def make_panel(
    name: str,
    panel: dict,
    collection: bpy.types.Collection,
    material: bpy.types.Material,
    scale: float,
    side: str,
    actor_waist_z: float,
    depth: float,
) -> bpy.types.Object:
    vertices = panel["vertices"]
    points: list[tuple[float, float, float]] = []
    for u, v in vertices:
        if "torso" in name:
            # GarmentCode already mirrors the left/right torso coordinates:
            # left uses positive U and right uses negative U.  A single
            # -U mapping therefore places both center seams at x=0.
            x = -u * scale
            y = -depth if side == "front" else depth
            z = actor_waist_z + 0.04 + v * scale
        else:
            sign = -1.0 if "left" in name else 1.0
            shoulder_x = sign * 0.40
            # Sleeve U already points outward for each mirrored panel.
            x = shoulder_x + u * scale
            y = -depth * 0.82 if side == "front" else depth * 0.82
            z = actor_waist_z + 0.50 + v * scale
        points.append((x, y, z))

    mesh = bpy.data.meshes.new(f"GarmentCode_{name}_Mesh")
    mesh.from_pydata(points, [], [list(range(len(points)))])
    mesh.update()
    obj = bpy.data.objects.new(f"GarmentCode_{name}", mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    solidify = obj.modifiers.new("LowDetailClothThickness", "SOLIDIFY")
    solidify.thickness = 0.008
    solidify.offset = 0.0
    obj["assetslab_pattern_panel"] = name
    obj["assetslab_pattern_source"] = "GarmentCode MIT"
    return obj


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.actor.resolve()))
    scene = bpy.context.scene
    scene.frame_set(1)

    pattern = json.loads(options.pattern.resolve().read_text(encoding="utf-8"))["pattern"]
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    collection = bpy.data.collections.new("GarmentCodePatternPreview")
    scene.collection.children.link(collection)
    material = make_material("GarmentCodePreviewCotton", (0.12, 0.36, 0.72, 1.0))

    actor = bpy.data.objects.get("ChibiBaseMesh_AccuRIG_InputMesh")
    if actor is None:
        raise RuntimeError("Actor mesh is missing")
    actor_waist_z = 0.70
    depth = 0.27
    panels = []
    for name, panel in pattern["panels"].items():
        side = "front" if "ftorso" in name or "sleeve_f" in name else "back"
        panels.append(make_panel(name, panel, collection, material, options.fit_scale * 0.01, side, actor_waist_z, depth))

    low, high = visible_bounds()
    center = (low + high) * 0.5
    configure_lighting(scene, center, "soft_flat")
    scene.view_settings.exposure = 0.25
    scene.render.resolution_x = options.resolution
    scene.render.resolution_y = options.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene["assetslab_garmentcode_preview"] = "static_pattern_fit_v1"
    scene["assetslab_garmentcode_pattern"] = str(options.pattern.resolve())
    scene["assetslab_garmentcode_status"] = "pre_drape_static_fit_only"
    preview_blend = output / "garmentcode_pattern_preview.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(preview_blend))

    ortho_scale = max(high.z - low.z, high.x - low.x, high.y - low.y) * 1.16
    for direction, (x, y) in DIRECTIONS.items():
        camera = make_camera(scene, center, f"GarmentCode_{direction}", (x, y, center.z), ortho_scale)
        scene.camera = camera
        scene.render.filepath = str(output / f"{direction}.png")
        bpy.ops.render.render(write_still=True)
    print(json.dumps({"preview_blend": str(preview_blend), "panels": len(panels), "status": scene["assetslab_garmentcode_status"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
