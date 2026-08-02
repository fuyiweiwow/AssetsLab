"""Attach a separated downloaded cartoon ear part to the actor head bone."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from render_procedural_anime_eye_on_accurig import bounds, make_camera  # noqa: E402


HEAD_BONE = "CC_Base_Head"


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-blend", required=True, type=Path)
    parser.add_argument("--source-blend", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--save-blend", required=True, type=Path)
    parser.add_argument("--part", default="CartoonEarPart_01")
    parser.add_argument("--ear-x", type=float, default=0.82)
    parser.add_argument("--ear-y", type=float, default=-0.08)
    parser.add_argument("--ear-z", type=float, default=2.08)
    parser.add_argument("--scale", type=float, default=0.52)
    parser.add_argument("--rotation-z", type=float, default=0.0)
    parser.add_argument("--left-rotation-y", type=float, default=180.0)
    parser.add_argument("--right-rotation-y", type=float, default=0.0)
    parser.add_argument("--mirror-left", action="store_true")
    return parser.parse_args(argv)


def make_skin_material() -> bpy.types.Material:
    material = bpy.data.materials.get("CartoonEarActorSkin") or bpy.data.materials.new("CartoonEarActorSkin")
    material.use_nodes = True
    material.diffuse_color = (0.88, 0.90, 0.95, 1.0)
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.88, 0.90, 0.95, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.82
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.18
    return material


def append_source_part(source_blend: Path, part_name: str) -> bpy.types.Object:
    with bpy.data.libraries.load(str(source_blend.resolve()), link=False) as (data_from, data_to):
        if part_name not in data_from.objects:
            raise RuntimeError(f"source blend is missing {part_name}")
        data_to.objects = [part_name]
    source = next((obj for obj in data_to.objects if obj is not None), None)
    if source is None:
        raise RuntimeError("source ear object could not be appended")
    bpy.context.scene.collection.objects.link(source)
    source.name = "CartoonEarSource"
    return source


def center_mesh(obj: bpy.types.Object) -> None:
    points = [Vector(corner) for corner in obj.bound_box]
    center = Vector((min(p[i] for p in points) for i in range(3)))
    high = Vector((max(p[i] for p in points) for i in range(3)))
    center = (center + high) * 0.5
    for vertex in obj.data.vertices:
        vertex.co -= center


def parent_to_head(obj: bpy.types.Object, armature: bpy.types.Object) -> None:
    world = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = HEAD_BONE
    obj.matrix_world = world


def duplicate_ear(source: bpy.types.Object, side: str, x: float, y: float, z: float, scale: float, rotation_y: float, rotation_z: float, mirror_x: bool, armature: bpy.types.Object, material: bpy.types.Material, rotation_x: float = 0.0) -> bpy.types.Object:
    obj = source.copy()
    obj.data = source.data.copy()
    bpy.context.scene.collection.objects.link(obj)
    obj.name = f"CartoonEar_{side}_Downloaded"
    obj.location = (x, y, z)
    obj.rotation_euler = (math.radians(rotation_x), math.radians(rotation_y), math.radians(rotation_z))
    obj.scale = (-scale if mirror_x else scale, scale, scale)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.select_set(False)
    obj.data.materials.clear()
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = False
    parent_to_head(obj, armature)
    return obj


def configure_render(scene: bpy.types.Scene) -> None:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 384
    scene.render.resolution_y = 384
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.input_blend.resolve()))
    output = options.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    actor = next(obj for obj in bpy.data.objects if obj.type == "MESH" and obj.name.startswith("ChibiBase"))
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    if HEAD_BONE not in armature.data.bones:
        raise RuntimeError(f"actor is missing {HEAD_BONE}")

    source = append_source_part(options.source_blend, options.part)
    center_mesh(source)
    skin = make_skin_material()
    left = duplicate_ear(source, "L", -abs(options.ear_x), options.ear_y, options.ear_z, options.scale, options.left_rotation_y, options.rotation_z, options.mirror_left, armature, skin)
    right = duplicate_ear(source, "R", abs(options.ear_x), options.ear_y, options.ear_z, options.scale, options.right_rotation_y, options.rotation_z, False, armature, skin)
    bpy.data.objects.remove(source, do_unlink=True)

    low, high = bounds(actor)
    actor_center = (low + high) * 0.5
    configure_render(bpy.context.scene)
    scene = bpy.context.scene
    specs = {
        "front": ((0.0, -12.0, actor_center.z), max(4.0, high.z - low.z + 0.6)),
        "right": ((12.0, 0.0, actor_center.z), max(4.0, high.z - low.z + 0.6)),
        "front_face_closeup": ((0.0, -12.0, options.ear_z), max(1.35, (high.z - low.z) * 0.38)),
        "right_face_closeup": ((12.0, 0.0, options.ear_z), max(1.35, (high.z - low.z) * 0.38)),
    }
    target = Vector((actor_center.x, actor_center.y, options.ear_z))
    for name, (location, camera_scale) in specs.items():
        camera = make_camera(scene, target if "closeup" in name else actor_center, name, location, camera_scale)
        scene.camera = camera
        scene.render.filepath = str(output / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)

    options.save_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.save_blend.resolve()))
    manifest = {
        "schema": "assetslab_downloaded_cartoon_ear_attachment_v1",
        "input_blend": str(options.input_blend.resolve()),
        "source_blend": str(options.source_blend.resolve()),
        "source_part": options.part,
        "parent_bone": HEAD_BONE,
        "parts": [left.name, right.name],
        "placement": {
            "ear_x": options.ear_x,
            "ear_y": options.ear_y,
            "ear_z": options.ear_z,
            "scale": options.scale,
            "left_rotation_y_degrees": options.left_rotation_y,
            "right_rotation_y_degrees": options.right_rotation_y,
            "rotation_z_degrees": options.rotation_z,
            "mirror_left": options.mirror_left,
        },
        "renders": {name: str(output / f"{name}.png") for name in specs},
        "status": "downloaded_geometry_attached_review_pending",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"DOWNLOADED_CARTOON_EAR_ATTACHMENT_PASS output={output} blend={options.save_blend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
