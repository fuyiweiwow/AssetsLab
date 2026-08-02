"""Import and render the downloaded standalone cartoon ear candidate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--obj", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--save-blend", required=True, type=Path)
    parser.add_argument("--scale", type=float, default=0.002085)
    return parser.parse_args(argv)


def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_material(name: str, color: tuple[float, float, float, float], roughness: float = 0.7):
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
    return material


def import_ear(path: Path, scale: float) -> list[bpy.types.Object]:
    bpy.ops.wm.obj_import(filepath=str(path.resolve()))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError("OBJ import did not create a mesh")
    source = max(meshes, key=lambda item: len(item.data.polygons))
    for obj in meshes:
        obj.hide_render = obj is not source
        obj.scale = (scale, scale, scale)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.select_set(False)
    bpy.context.view_layer.objects.active = source
    source.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    parts = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    material = make_material("CartoonEarOuter", (0.55, 0.22, 0.12, 1.0))
    for index, obj in enumerate(sorted(parts, key=lambda item: item.name)):
        obj.name = f"CartoonEarPart_{index:02d}"
        obj.hide_render = False
        obj.data.materials.append(material)
    return sorted(parts, key=lambda item: item.name)


def bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    low = Vector((min(point[i] for point in points) for i in range(3)))
    high = Vector((max(point[i] for point in points) for i in range(3)))
    return low, high


def setup_camera(scene: bpy.types.Scene, position: tuple[float, float, float], target: Vector, scale: float):
    data = bpy.data.cameras.new("EarReviewCamera")
    camera = bpy.data.objects.new("EarReviewCamera", data)
    scene.collection.objects.link(camera)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = scale
    camera.location = position
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    return camera


def configure_scene(scene: bpy.types.Scene) -> None:
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("CartoonEarReviewWorld")
    scene.world.color = (0.055, 0.055, 0.055)


def main() -> int:
    options = cli_args()
    reset_scene()
    objects = import_ear(options.obj, options.scale)
    configure_scene(bpy.context.scene)
    low, high = bounds(objects)
    center = (low + high) * 0.5
    extent = max(high - low)
    ortho = max(extent * 1.35, 1.0)
    output = options.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    views = {
        "axis_y": ((0.0, -extent * 3.0, center.z), "front"),
        "axis_x": ((extent * 3.0, 0.0, center.z), "side"),
        "axis_z": ((0.0, 0.0, extent * 3.0), "top"),
    }
    renders: dict[str, str] = {}
    for key, (position, label) in views.items():
        setup_camera(bpy.context.scene, position, center, ortho)
        target = output / f"{label}.png"
        bpy.context.scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        renders[label] = str(target)
    for index, part in enumerate(objects):
        part_low, part_high = bounds([part])
        part_center = (part_low + part_high) * 0.5
        for other in objects:
            other.hide_render = other is not part
        setup_camera(
            bpy.context.scene,
            (part_center.x + max(3.0, extent * 3.0), part_center.y, part_center.z),
            part_center,
            max(1.2, max(part_high.y - part_low.y, part_high.z - part_low.z) * 1.35),
        )
        target = output / f"part_{index:02d}_front.png"
        bpy.context.scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        renders[f"part_{index:02d}_front"] = str(target)
    for part in objects:
        part.hide_render = False
    options.save_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.save_blend.resolve()))
    manifest = {
        "schema": "assetslab_cartoon_ear_candidate_v1",
        "source_obj": str(options.obj.resolve()),
        "scale_applied": options.scale,
        "part_count": len(objects),
        "parts": [
            {
                "name": obj.name,
                "vertex_count": len(obj.data.vertices),
                "face_count": len(obj.data.polygons),
                "dimensions": list(obj.dimensions),
                "location": list(obj.location),
            }
            for obj in objects
        ],
        "bounds_min": list(low),
        "bounds_max": list(high),
        "dimensions": list(high - low),
        "renders": renders,
        "status": "isolated_geometry_review_pending",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"CARTOON_EAR_CANDIDATE_RENDER_PASS output={output} blend={options.save_blend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
