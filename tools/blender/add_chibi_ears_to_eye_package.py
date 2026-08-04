"""Add a rounded, shallow 3D chibi-ear pair to the current actor eye package."""

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

from render_procedural_anime_eye_on_accurig import bounds, make_camera  # noqa: E402


HEAD_BONE = "CC_Base_Head"


def args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-blend", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--save-blend", type=Path, required=True)
    parser.add_argument("--ear-x", type=float, default=0.77)
    parser.add_argument("--ear-y", type=float, default=-0.35)
    parser.add_argument("--ear-z", type=float, default=2.08)
    parser.add_argument("--ear-width", type=float, default=0.24)
    parser.add_argument("--ear-height", type=float, default=0.34)
    parser.add_argument("--ear-depth", type=float, default=0.16)
    return parser.parse_args(argv)


def material(name: str, color: tuple[float, float, float, float], roughness: float = 0.82) -> bpy.types.Material:
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Specular IOR Level"].default_value = 0.18
    return mat


def parent_to_head(obj: bpy.types.Object, armature: bpy.types.Object) -> None:
    world = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = HEAD_BONE
    obj.matrix_world = world


def make_ear(
    side: str,
    x: float,
    y: float,
    z: float,
    width: float,
    height: float,
    depth: float,
    outer_mat: bpy.types.Material,
    inner_mat: bpy.types.Material,
    armature: bpy.types.Object,
) -> list[bpy.types.Object]:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, location=(x, y, z))
    outer = bpy.context.object
    outer.name = f"ChibiEar_{side}_Outer"
    outer.scale = (width * 0.5, depth * 0.5, height * 0.5)
    bpy.context.view_layer.objects.active = outer
    outer.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    outer.data.materials.append(outer_mat)
    for poly in outer.data.polygons:
        poly.use_smooth = True
    parent_to_head(outer, armature)

    # A smaller, flattened oval sits slightly toward the camera (negative Y),
    # giving the ear a readable inner bowl in front and a visible thickness in side view.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=28, ring_count=16, location=(x, y - depth * 0.52, z + height * 0.01))
    inner = bpy.context.object
    inner.name = f"ChibiEar_{side}_Inner"
    inner.scale = (width * 0.27, depth * 0.10, height * 0.31)
    bpy.context.view_layer.objects.active = inner
    inner.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    inner.data.materials.append(inner_mat)
    for poly in inner.data.polygons:
        poly.use_smooth = True
    parent_to_head(inner, armature)
    return [outer, inner]


def configure_render(scene: bpy.types.Scene) -> None:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 384
    scene.render.resolution_y = 384
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False


def main() -> int:
    options = args()
    bpy.ops.wm.open_mainfile(filepath=str(options.input_blend.resolve()))
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    actor_mesh = next(obj for obj in bpy.data.objects if obj.type == "MESH" and not obj.name.startswith(("EyePackage", "ChibiEar_")))
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    if HEAD_BONE not in armature.data.bones:
        raise RuntimeError(f"actor is missing {HEAD_BONE}")

    outer_mat = material("ChibiEar_Outer_Mat", (0.72, 0.73, 0.77, 1.0))
    inner_mat = material("ChibiEar_Inner_Mat", (0.48, 0.27, 0.30, 1.0))
    parts = []
    parts += make_ear("L", -abs(options.ear_x), options.ear_y, options.ear_z, options.ear_width, options.ear_height, options.ear_depth, outer_mat, inner_mat, armature)
    parts += make_ear("R", abs(options.ear_x), options.ear_y, options.ear_z, options.ear_width, options.ear_height, options.ear_depth, outer_mat, inner_mat, armature)

    low, high = bounds(actor_mesh)
    actor_center = (low + high) * 0.5
    target = Vector((actor_center.x, actor_center.y, options.ear_z))
    configure_render(bpy.context.scene)
    specs = {
        "front": ((0.0, -12.0, actor_center.z), max(4.0, high.z - low.z + 0.6)),
        "right": ((12.0, 0.0, actor_center.z), max(4.0, high.z - low.z + 0.6)),
        "front_face_closeup": ((0.0, -12.0, options.ear_z), max(1.35, (high.z - low.z) * 0.38)),
        "right_face_closeup": ((12.0, 0.0, options.ear_z), max(1.35, (high.z - low.z) * 0.38)),
    }
    scene = bpy.context.scene
    for name, (location, scale) in specs.items():
        camera = make_camera(scene, target if "closeup" in name else actor_center, name, location, scale)
        scene.camera = camera
        scene.render.filepath = str(output / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)

    save_blend = options.save_blend.resolve()
    save_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(save_blend))
    manifest = {
        "schema": "assetslab_chibi_ears_test_v1",
        "input_blend": str(options.input_blend.resolve()),
        "parent_bone": HEAD_BONE,
        "parts": [obj.name for obj in parts],
        "placement": {
            "ear_x": options.ear_x,
            "ear_y": options.ear_y,
            "ear_z": options.ear_z,
            "ear_width": options.ear_width,
            "ear_height": options.ear_height,
            "ear_depth": options.ear_depth,
        },
        "directions": list(specs),
        "status": "front_side_attachment_test",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"CHIBI_EARS_PASS output={output} blend={save_blend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
