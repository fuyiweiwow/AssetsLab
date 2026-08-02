"""Create a thin, shrinkwrapped upper-eyelid decal from the Miku contour."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.geometry import convex_hull_2d


def cli() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target", default="ChibiActor_MCP_PreciseEyeSocket_Test")
    parser.add_argument("--eye", default="MikuChibiEyeball")
    parser.add_argument("--armature", default="Armature")
    parser.add_argument("--miku-fbx", required=True, type=Path)
    return parser.parse_args(argv)


def smooth_closed(points: list[Vector]) -> list[Vector]:
    refined: list[Vector] = []
    for index, point in enumerate(points):
        nxt = points[(index + 1) % len(points)]
        refined.extend((point * 0.75 + nxt * 0.25, point * 0.25 + nxt * 0.75))
    return refined


def contour_for_side(source_points: list[Vector], target_points: list[Vector], side: str) -> list[Vector]:
    source_side = [p for p in source_points if (p.x < 0 if side == "L" else p.x >= 0)]
    target_side = [p for p in target_points if (p.x < 0 if side == "L" else p.x >= 0)]
    unique = []
    seen = set()
    for point in source_side:
        key = (round(point.x, 6), round(point.z, 6))
        if key not in seen:
            seen.add(key)
            unique.append(Vector((point.x, point.z)))
    hull_indices = convex_hull_2d(unique)
    hull = [unique[index] for index in hull_indices] if hull_indices and isinstance(hull_indices[0], int) else list(hull_indices)
    ref_low = Vector((min(p.x for p in hull), min(p.y for p in hull)))
    ref_high = Vector((max(p.x for p in hull), max(p.y for p in hull)))
    low = Vector((min(p.x for p in target_side), min(p.z for p in target_side)))
    high = Vector((max(p.x for p in target_side), max(p.z for p in target_side)))
    ref_center = (ref_low + ref_high) * 0.5
    target_center = (low + high) * 0.5
    sx = (high.x - low.x) / max(ref_high.x - ref_low.x, 1e-6)
    sz = (high.y - low.y) / max(ref_high.y - ref_low.y, 1e-6)
    mapped = [Vector((target_center.x + (p.x - ref_center.x) * sx, target_center.y + (p.y - ref_center.y) * sz)) for p in hull]
    mapped = smooth_closed(mapped)
    center = sum(mapped[1:], mapped[0]) / len(mapped)
    upper = [point for point in mapped if point.y >= center.y - 0.055]
    # Leave a small central gap; otherwise the two upper eyelids read as a
    # glasses frame instead of two independent anime eye shapes.
    if side == "L":
        upper = [point for point in upper if point.x <= -0.06]
    else:
        upper = [point for point in upper if point.x >= 0.06]
    return upper


def create_decal(name: str, arc: list[Vector], target: bpy.types.Object, material: bpy.types.Material, armature: bpy.types.Object) -> bpy.types.Object:
    center = sum(arc[1:], arc[0]) / len(arc)
    outer = [center + (point - center) * 1.06 for point in arc]
    inner = [center + (point - center) * 1.015 for point in arc]
    # Start well in front and let Shrinkwrap project onto the rest-pose socket rim.
    verts = [(point.x, -1.4, point.y) for point in outer] + [(point.x, -1.4, point.y) for point in inner]
    n = len(arc)
    faces = [[i, i + 1, n + i + 1, n + i] for i in range(n - 1)]
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    shrink = obj.modifiers.new("EyelidShrinkwrap", "SHRINKWRAP")
    shrink.target = target
    shrink.wrap_method = "PROJECT"
    shrink.wrap_mode = "ON_SURFACE"
    shrink.use_project_y = True
    shrink.use_positive_direction = True
    shrink.use_negative_direction = False
    shrink.offset = 0.004
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=shrink.name)
    obj.select_set(False)
    for poly in mesh.polygons:
        poly.use_smooth = True
    group = obj.vertex_groups.new(name="CC_Base_Head")
    group.add(list(range(len(mesh.vertices))), 1.0, "REPLACE")
    arm_mod = obj.modifiers.new("EyelidDecalHeadDeform", "ARMATURE")
    arm_mod.object = armature
    arm_mod.use_deform_preserve_volume = True
    return obj


def make_material() -> bpy.types.Material:
    material = bpy.data.materials.get("MAT_EyelidShadow") or bpy.data.materials.new("MAT_EyelidShadow")
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.16, 0.20, 0.23, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.92
    return material


def main() -> None:
    options = cli()
    target = bpy.data.objects.get(options.target)
    eye = bpy.data.objects.get(options.eye)
    armature = bpy.data.objects.get(options.armature)
    if target is None or eye is None or armature is None:
        raise RuntimeError("target, eye, or armature missing")
    bpy.context.scene.frame_set(1)
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=str(options.miku_fbx.resolve()), automatic_bone_orientation=False)
    imported = [obj for obj in bpy.context.scene.objects if obj not in before]
    source = next((obj for obj in imported if obj.name == "eyeball_1_0_node" or obj.name.startswith("eyeball_1_0_node.")), None)
    if source is None:
        raise RuntimeError("Miku FBX is missing eyeball_1_0_node")
    source_points = [source.matrix_world @ vertex.co for vertex in source.data.vertices]
    target_points = [eye.matrix_world @ vertex.co for vertex in eye.data.vertices]
    material = make_material()
    created = []
    for side in ("L", "R"):
        created.append(create_decal(f"GEO_ShrinkwrapUpperEyelid_{side}", contour_for_side(source_points, target_points, side), target, material, armature))
    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.output.resolve()), compress=True)
    print({"output": str(options.output), "created": [obj.name for obj in created], "vertices_each": len(created[0].data.vertices), "material": material.name})


if __name__ == "__main__":
    main()
