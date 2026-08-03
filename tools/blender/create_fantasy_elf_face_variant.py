"""Build a non-destructive western-fantasy elf face on the long-elf-ear actor."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


HEAD_BONE = "CC_Base_Head"
EYE_PREFIX = "EyePackageV1_"


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-blend", required=True, type=Path)
    parser.add_argument("--output-blend", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--eye-width", type=float, default=0.92)
    parser.add_argument("--eye-height", type=float, default=1.14)
    parser.add_argument("--eye-raise", type=float, default=0.075)
    parser.add_argument("--brow-thickness", type=float, default=0.034)
    parser.add_argument("--brow-arch", type=float, default=0.11)
    parser.add_argument("--brow-raise", type=float, default=0.025)
    return parser.parse_args(argv)


def mesh_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    return (
        Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points))),
        Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points))),
    )


def transform_eye(obj: bpy.types.Object, width: float, height: float, raise_z: float) -> None:
    low, high = mesh_bounds(obj)
    center = Vector(((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, (low.z + high.z) * 0.5))
    world_to_local = obj.matrix_world.inverted()
    obj.data = obj.data.copy()
    for vertex in obj.data.vertices:
        point = obj.matrix_world @ vertex.co
        point.x = center.x + (point.x - center.x) * width
        point.z = center.z + (point.z - center.z) * height + raise_z
        vertex.co = world_to_local @ point


def make_brow_material() -> bpy.types.Material:
    # Bright gold-copper deliberately survives 64px downsampling and stays
    # visually distinct from the emerald eye texture beneath it.
    colour = (0.80, 0.255, 0.030, 1.0)
    material = bpy.data.materials.new("ElfFaceBrowMaterial")
    material.diffuse_color = colour
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled:
        principled.inputs["Base Color"].default_value = colour
        principled.inputs["Roughness"].default_value = 0.70
        principled.inputs["Emission Color"].default_value = colour
        principled.inputs["Emission Strength"].default_value = 0.58
    return material


def add_brow(
    armature: bpy.types.Object,
    name: str,
    points: tuple[Vector, Vector, Vector],
    material: bpy.types.Material,
    thickness: float,
) -> None:
    curve = bpy.data.curves.new(name + "Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 3
    curve.bevel_depth = thickness
    curve.bevel_resolution = 2
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(2)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = HEAD_BONE
    bpy.context.view_layer.update()
    world_to_local = obj.matrix_world.inverted()
    for point, coordinate in zip(spline.bezier_points, points):
        point.co = world_to_local @ coordinate
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    curve.materials.append(material)


def add_elf_brows(
    armature: bpy.types.Object,
    eye_objects: list[bpy.types.Object],
    thickness: float,
    arch: float,
    raise_z: float,
) -> None:
    for obj in list(bpy.data.objects):
        if obj.name.startswith("ElfFaceBrow"):
            bpy.data.objects.remove(obj, do_unlink=True)
    low = Vector((min(mesh_bounds(obj)[0].x for obj in eye_objects), 0.0, min(mesh_bounds(obj)[0].z for obj in eye_objects)))
    high = Vector((max(mesh_bounds(obj)[1].x for obj in eye_objects), 0.0, max(mesh_bounds(obj)[1].z for obj in eye_objects)))
    # Keep the brow base close to the visible eye package. Exaggeration comes
    # from width, thickness and the local arch, not from moving it to the scalp.
    brow_z = high.z + 0.015 + raise_z
    brow_y = -0.812
    material = make_brow_material()
    # A higher, tapered arch gives the eye package a less doll-like and more
    # western-fantasy silhouette without adding an unstable nose or mouth dot.
    add_brow(
        armature,
        "ElfFaceBrowL",
        (
            Vector((-0.705, brow_y, brow_z - 0.035)),
            Vector((-0.420, brow_y, brow_z + arch)),
            Vector((-0.135, brow_y, brow_z + 0.042)),
        ),
        material,
        thickness,
    )
    add_brow(
        armature,
        "ElfFaceBrowR",
        (
            Vector((0.135, brow_y, brow_z + 0.042)),
            Vector((0.420, brow_y, brow_z + arch)),
            Vector((0.705, brow_y, brow_z - 0.035)),
        ),
        material,
        thickness,
    )


def tint_iris_materials() -> None:
    for material_name in ("EyePackageV1_MikuLeft", "EyePackageV1_MikuRight"):
        material = bpy.data.materials.get(material_name)
        if material is None or not material.use_nodes:
            raise RuntimeError(f"missing image-based eye material: {material_name}")
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        image = next((node for node in nodes if node.type == "TEX_IMAGE"), None)
        principled = nodes.get("Principled BSDF")
        if image is None or principled is None:
            raise RuntimeError(f"eye material has no expected image/principled nodes: {material_name}")
        tint = nodes.get("ElfEmeraldTint")
        if tint is None:
            tint = nodes.new("ShaderNodeHueSaturation")
            tint.name = "ElfEmeraldTint"
        tint.inputs["Hue"].default_value = 0.22
        tint.inputs["Saturation"].default_value = 1.10
        tint.inputs["Value"].default_value = 0.92
        for link in list(links):
            if link.to_node == principled and link.to_socket == principled.inputs["Base Color"]:
                links.remove(link)
        links.new(image.outputs["Color"], tint.inputs["Color"])
        links.new(tint.outputs["Color"], principled.inputs["Base Color"])
    outline = bpy.data.materials.get("EyePackageV1_UpperLineMaterial")
    if outline and outline.use_nodes:
        principled = outline.node_tree.nodes.get("Principled BSDF")
        if principled:
            principled.inputs["Base Color"].default_value = (0.095, 0.028, 0.012, 1.0)
            principled.inputs["Roughness"].default_value = 0.72


def main() -> int:
    options = cli_args()
    if not (0.75 <= options.eye_width <= 1.10 and 0.90 <= options.eye_height <= 1.30):
        raise RuntimeError("elf face eye scale is outside the tested safe range")
    if not (0.015 <= options.brow_thickness <= 0.060 and 0.03 <= options.brow_arch <= 0.16):
        raise RuntimeError("elf face brow parameters are outside the tested safe range")
    bpy.ops.wm.open_mainfile(filepath=str(options.input_blend.resolve()))
    armature = next((obj for obj in bpy.data.objects if obj.type == "ARMATURE"), None)
    if armature is None or HEAD_BONE not in armature.data.bones:
        raise RuntimeError(f"actor is missing {HEAD_BONE}")
    eye_objects = [obj for obj in bpy.data.objects if obj.type == "MESH" and obj.name.startswith(EYE_PREFIX)]
    if len(eye_objects) != 4:
        raise RuntimeError(f"expected four eye-package meshes, found {len(eye_objects)}")
    for obj in eye_objects:
        transform_eye(obj, options.eye_width, options.eye_height, options.eye_raise)
    tint_iris_materials()
    add_elf_brows(
        armature,
        eye_objects,
        options.brow_thickness,
        options.brow_arch,
        options.brow_raise,
    )
    brows = [obj for obj in bpy.data.objects if obj.name.startswith("ElfFaceBrow")]
    if len(brows) != 2 or any(obj.parent_type != "BONE" or obj.parent_bone != HEAD_BONE for obj in brows):
        raise RuntimeError("elf brow generation lost the head-bone attachment")
    options.output_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.output_blend.resolve()))
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.write_text(
        json.dumps(
            {
                "schema": "assetslab_fantasy_elf_face_v1",
                "input_blend": str(options.input_blend.resolve()),
                "output_blend": str(options.output_blend.resolve()),
                "style": "western_fantasy_elf",
                "head_bone": HEAD_BONE,
                "features": {
                    "ears": "long_elf_ear_v4",
                    "eyes": {
                        "iris": "emerald_tint",
                        "width": options.eye_width,
                        "height": options.eye_height,
                        "raise": options.eye_raise,
                    },
                    "brows": {
                        "style": "high_tapered_arch",
                        "thickness": options.brow_thickness,
                        "arch": options.brow_arch,
                        "raise": options.brow_raise,
                    },
                    "nose_and_mouth": "deferred_for_64px_readability",
                },
                "status": "candidate_review_required",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"FANTASY_ELF_FACE_PASS eyes={len(eye_objects)} brows={len(brows)} output={options.output_blend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
