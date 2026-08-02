"""Create a clean, Miku-shaped eye-socket Boolean test on a duplicate actor."""

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
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target", default="ChibiActor_MCP_PreciseEyeSocket_Test")
    parser.add_argument("--eye", default="MikuChibiEyeball")
    parser.add_argument("--miku-fbx", required=True, type=Path)
    parser.add_argument("--margin", type=float, default=1.0)
    return parser.parse_args(argv)


def make_prism(name: str, contour: list[Vector], y_front: float, y_back: float) -> bpy.types.Object:
    verts = [(p.x, y_front, p.y) for p in contour] + [(p.x, y_back, p.y) for p in contour]
    n = len(contour)
    # Reverse one cap so normals are well-defined; the Boolean solver only
    # needs a closed, non-self-intersecting cutter.
    faces = [list(range(n - 1, -1, -1)), list(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, n + j, n + i])
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def main() -> None:
    options = cli()
    target = bpy.data.objects.get(options.target)
    eye = bpy.data.objects.get(options.eye)
    if target is None or eye is None:
        raise RuntimeError("target or eye object missing")

    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=str(options.miku_fbx.resolve()), automatic_bone_orientation=False)
    imported = [obj for obj in bpy.context.scene.objects if obj not in before]
    source = next((obj for obj in imported if obj.name == "eyeball_1_0_node" or obj.name.startswith("eyeball_1_0_node.")), None)
    if source is None:
        raise RuntimeError("Miku FBX is missing eyeball_1_0_node")

    source_points = [source.matrix_world @ vertex.co for vertex in source.data.vertices]
    target_points = [eye.matrix_world @ vertex.co for vertex in eye.data.vertices]
    cutters = []
    for side in ("L", "R"):
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
        sx *= options.margin
        sz *= options.margin
        contour = [Vector((target_center.x + (p.x - ref_center.x) * sx, target_center.y + (p.y - ref_center.y) * sz)) for p in hull]
        cutter = make_prism(f"TEST_EyeSocketCutter_{side}", contour, -1.05, -0.18)
        cutters.append(cutter)

    # Put Boolean before the armature in the stack so the rest-pose cut remains
    # compatible with animation.
    for cutter in cutters:
        modifier = target.modifiers.new(f"TEST_EyeSocketBoolean_{cutter.name[-1]}", "BOOLEAN")
        modifier.operation = "DIFFERENCE"
        modifier.solver = "EXACT"
        modifier.object = cutter
        bpy.context.view_layer.objects.active = target
        try:
            target.modifiers.move(len(target.modifiers) - 1, 0)
        except RuntimeError:
            pass
        bpy.ops.object.modifier_apply(modifier=modifier.name)

    for cutter in cutters:
        bpy.data.objects.remove(cutter, do_unlink=True)
    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.output.resolve()), compress=True)
    print({"output": str(options.output), "polygons": len(target.data.polygons), "modifiers": [m.name for m in target.modifiers]})


if __name__ == "__main__":
    main()
