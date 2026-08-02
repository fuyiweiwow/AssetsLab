"""Map the Miku eyeball contour to the actor and select contained front faces."""

from __future__ import annotations

import argparse
import json
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
    parser.add_argument("--miku-fbx", required=True, type=Path)
    parser.add_argument("--margin", type=float, default=1.08)
    return parser.parse_args(argv)


def inside(point: Vector, polygon: list[Vector]) -> bool:
    result = False
    previous = polygon[-1]
    for current in polygon:
        if (current.y > point.y) != (previous.y > point.y):
            # Keep the denominator sign. Clamping it with max(..., 1e-12)
            # makes half of the polygon test invert and can select faces from
            # the opposite eye as well.
            denominator = previous.y - current.y
            cross_x = (previous.x - current.x) * (point.y - current.y) / denominator + current.x
            if point.x < cross_x:
                result = not result
        previous = current
    return result


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
    contours: dict[str, list[Vector]] = {}
    eye_bounds: dict[str, tuple[Vector, Vector]] = {}
    for side in ("L", "R"):
        ref_side = [p for p in source_points if (p.x < 0 if side == "L" else p.x >= 0)]
        target_side = [p for p in target_points if p.x < 0] if side == "L" else [p for p in target_points if p.x >= 0]
        ref_unique = []
        seen = set()
        for p in ref_side:
            key = (round(p.x, 6), round(p.z, 6))
            if key not in seen:
                seen.add(key)
                ref_unique.append(Vector((p.x, p.z)))
        hull = convex_hull_2d(ref_unique)
        hull_points = [ref_unique[index] for index in hull] if hull and isinstance(hull[0], int) else hull
        ref_low = Vector((min(p.x for p in hull_points), min(p.y for p in hull_points)))
        ref_high = Vector((max(p.x for p in hull_points), max(p.y for p in hull_points)))
        low = Vector((min(p.x for p in target_side), min(p.z for p in target_side)))
        high = Vector((max(p.x for p in target_side), max(p.z for p in target_side)))
        ref_center = (ref_low + ref_high) * 0.5
        target_center = (low + high) * 0.5
        sx = (high.x - low.x) / max(ref_high.x - ref_low.x, 1e-6) * options.margin
        sz = (high.y - low.y) / max(ref_high.y - ref_low.y, 1e-6) * options.margin
        contours[side] = [Vector((target_center.x + (p.x - ref_center.x) * sx, target_center.y + (p.y - ref_center.y) * sz)) for p in hull_points]
        eye_bounds[side] = (low, high)
    candidates: dict[str, list[int]] = {"L": [], "R": []}
    samples: dict[str, list[dict[str, float]]] = {"L": [], "R": []}
    for poly in target.data.polygons:
        local = sum((target.data.vertices[index].co for index in poly.vertices), Vector()) / len(poly.vertices)
        center = target.matrix_world @ local
        normal = (target.matrix_world.to_3x3() @ poly.normal).normalized()
        for side, contour in contours.items():
            if inside(Vector((center.x, center.z)), contour) and center.y < -0.20 and normal.y < -0.25:
                candidates[side].append(poly.index)
                if len(samples[side]) < 12:
                    samples[side].append({"face": poly.index, "x": center.x, "y": center.y, "z": center.z, "normal_y": normal.y})
    payload = {
        "target": options.target,
        "source": str(options.miku_fbx.resolve()),
        "margin": options.margin,
        "candidate_face_counts": {side: len(values) for side, values in candidates.items()},
        "candidate_face_indices": candidates,
        "samples": samples,
        "contours_xz": {side: [[p.x, p.y] for p in contour] for side, contour in contours.items()},
    }
    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"candidate_face_counts": payload["candidate_face_counts"], "margin": options.margin}))


if __name__ == "__main__":
    main()
