"""Add source-contour-locked, shallow recessed eyelid rings to the Boolean socket test."""

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


def smooth_closed(points: list[Vector], passes: int = 1) -> list[Vector]:
    result = points
    for _ in range(passes):
        refined: list[Vector] = []
        for index, point in enumerate(result):
            nxt = result[(index + 1) % len(result)]
            refined.extend((point * 0.75 + nxt * 0.25, point * 0.25 + nxt * 0.75))
        result = refined
    return result


def contour_for_side(source_points: list[Vector], target_points: list[Vector], side: str) -> list[Vector]:
    source_side = [p for p in source_points if (p.x < 0 if side == "L" else p.x >= 0)]
    target_side = [p for p in target_points if (p.x < 0 if side == "L" else p.x >= 0)]
    unique: list[Vector] = []
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
    return [Vector((target_center.x + (p.x - ref_center.x) * sx, target_center.y + (p.y - ref_center.y) * sz)) for p in hull]


def ray_front_y(scene: bpy.types.Scene, depsgraph, target: bpy.types.Object, x: float, z: float) -> float:
    origin = Vector((x, -2.0, z))
    hit, location, _, _, obj, _ = scene.ray_cast(depsgraph, origin, Vector((0.0, 1.0, 0.0)), distance=4.0)
    if hit and obj == target:
        return location.y
    return -0.72


def create_ring(name: str, contour: list[Vector], target: bpy.types.Object, material: bpy.types.Material, armature: bpy.types.Object) -> bpy.types.Object:
    center = sum(contour[1:], contour[0]) / len(contour)
    outer = [center + (point - center) * 1.08 for point in contour]
    inner = [center + (point - center) * 0.86 for point in contour]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    verts = []
    for point in outer:
        verts.append((point.x, ray_front_y(bpy.context.scene, depsgraph, target, point.x, point.y) - 0.012, point.y))
    for point in inner:
        outer_y = ray_front_y(bpy.context.scene, depsgraph, target, point.x, point.y)
        verts.append((point.x, outer_y + 0.085, point.y))
    n = len(contour)
    faces = [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    bevel = obj.modifiers.new("EyelidEdgeSoftening", "BEVEL")
    bevel.width = 0.018
    bevel.segments = 2
    bevel.limit_method = "ANGLE"
    group = obj.vertex_groups.new(name="CC_Base_Head")
    group.add(list(range(len(mesh.vertices))), 1.0, "REPLACE")
    arm_mod = obj.modifiers.new("EyelidHeadDeform", "ARMATURE")
    arm_mod.object = armature
    arm_mod.use_deform_preserve_volume = True
    return obj


def main() -> None:
    options = cli()
    target = bpy.data.objects.get(options.target)
    eye = bpy.data.objects.get(options.eye)
    armature = bpy.data.objects.get(options.armature)
    if target is None or eye is None or armature is None:
        raise RuntimeError("target, eye, or armature missing")
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=str(options.miku_fbx.resolve()), automatic_bone_orientation=False)
    imported = [obj for obj in bpy.context.scene.objects if obj not in before]
    source = next((obj for obj in imported if obj.name == "eyeball_1_0_node" or obj.name.startswith("eyeball_1_0_node.")), None)
    if source is None:
        raise RuntimeError("Miku FBX is missing eyeball_1_0_node")
    source_points = [source.matrix_world @ vertex.co for vertex in source.data.vertices]
    target_points = [eye.matrix_world @ vertex.co for vertex in eye.data.vertices]
    material = target.data.materials[0]
    created = []
    for side in ("L", "R"):
        contour = smooth_closed(contour_for_side(source_points, target_points, side), passes=1)
        created.append(create_ring(f"GEO_EyelidFrame_{side}", contour, target, material, armature))
    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.output.resolve()), compress=True)
    print({"output": str(options.output), "created": [obj.name for obj in created], "vertices_each": len(created[0].data.vertices)})


if __name__ == "__main__":
    main()
