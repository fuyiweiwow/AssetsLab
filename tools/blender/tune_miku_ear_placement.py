"""Apply a small, explicit placement correction to head-bone-parented Miku ears."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


EARS = (("MikuEar_L_SourceV1", "L"), ("MikuEar_R_SourceV1", "R"))


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--forward", type=float, default=0.025, help="negative world Y moves toward front camera")
    parser.add_argument("--inward", type=float, default=0.012, help="move both ears toward world X=0")
    parser.add_argument("--scale", type=float, default=1.0, help="uniform ear scale around its inner root; preserves the connection point")
    parser.add_argument(
        "--rim-to-face-degrees",
        type=float,
        default=0.0,
        help="rotate each ear around its inner root; sign is selected to bring the outer rim closer to the actor head",
    )
    parser.add_argument("--rim-axis", choices=("Y", "Z"), default="Z")
    parser.add_argument(
        "--head-object",
        default="ChibiBaseMesh_AccuRIG_InputMesh",
        help="actor mesh used to select the horizontal rotation sign",
    )
    parser.add_argument("--snap-root-to-head", action="store_true", help="project the ear-root band onto the side-head surface after rotation")
    parser.add_argument("--root-surface-offset", type=float, default=0.006, help="outward gap applied after root projection")
    return parser.parse_args(argv)


def root_and_outer_centers(ear: bpy.types.Object, side: str) -> tuple[Vector, Vector]:
    points = [ear.matrix_world @ vertex.co for vertex in ear.data.vertices]
    values = [point.x for point in points]
    minimum, maximum = min(values), max(values)
    band = max((maximum - minimum) * 0.16, 1e-6)
    root_points = [point for point in points if point.x >= maximum - band] if side == "L" else [point for point in points if point.x <= minimum + band]
    outer_points = [point for point in points if point.x <= minimum + band] if side == "L" else [point for point in points if point.x >= maximum - band]
    return sum(root_points, Vector()) / len(root_points), sum(outer_points, Vector()) / len(outer_points)


def head_bvh(head: bpy.types.Object) -> BVHTree:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = head.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        vertices = [head.matrix_world @ vertex.co for vertex in mesh.vertices]
        polygons = [tuple(polygon.vertices) for polygon in mesh.polygons]
        return BVHTree.FromPolygons(vertices, polygons, all_triangles=False)
    finally:
        evaluated.to_mesh_clear()


def outer_band_points(ear: bpy.types.Object, side: str) -> list[Vector]:
    points = [ear.matrix_world @ vertex.co for vertex in ear.data.vertices]
    values = [point.x for point in points]
    minimum, maximum = min(values), max(values)
    band = max((maximum - minimum) * 0.16, 1e-6)
    return [point for point in points if point.x <= minimum + band] if side == "L" else [point for point in points if point.x >= maximum - band]


def mean_head_distance(points: list[Vector], tree: BVHTree) -> float:
    distances = [tree.find_nearest(point)[3] for point in points]
    return sum(distances) / len(distances)


def main() -> int:
    options = parse_args()
    if not 0.5 <= options.scale <= 1.5:
        raise ValueError("scale must be within 0.5..1.5")
    bpy.ops.wm.open_mainfile(filepath=str(options.blend.resolve()))
    scene = bpy.context.scene
    scene.frame_set(1)
    bpy.context.view_layer.update()
    head = bpy.data.objects.get(options.head_object)
    if head is None or head.type != "MESH":
        raise RuntimeError(f"head mesh not found: {options.head_object}")
    tree = head_bvh(head)
    decisions = {}
    for name, side in EARS:
        ear = bpy.data.objects.get(name)
        if ear is None:
            raise RuntimeError(f"missing ear: {name}")
        inward = options.inward if side == "L" else -options.inward
        # Actor front camera is at -Y, hence a negative Y translation is forward.
        transform = Matrix.Translation(Vector((inward, -options.forward, 0.0)))
        ear.matrix_world = transform @ ear.matrix_world
        bpy.context.view_layer.update()
        root, _outer = root_and_outer_centers(ear, side)
        if options.scale != 1.0:
            scale = Matrix.Diagonal((options.scale, options.scale, options.scale, 1.0))
            ear.matrix_world = Matrix.Translation(root) @ scale @ Matrix.Translation(-root) @ ear.matrix_world
        if options.rim_to_face_degrees:
            bpy.context.view_layer.update()
            root, _outer = root_and_outer_centers(ear, side)
            candidates = []
            for sign in (-1.0, 1.0):
                rotation = Matrix.Rotation(math.radians(sign * options.rim_to_face_degrees), 4, options.rim_axis)
                pivoted = Matrix.Translation(root) @ rotation @ Matrix.Translation(-root) @ ear.matrix_world
                transform_outer = Matrix.Translation(root) @ rotation @ Matrix.Translation(-root)
                ring = [transform_outer @ point for point in outer_band_points(ear, side)]
                candidates.append((mean_head_distance(ring, tree), sign, pivoted))
            distance, sign, chosen = min(candidates, key=lambda item: item[0])
            ear.matrix_world = chosen
            decisions[side] = {"sign": sign, "outer_rim_mean_head_distance": distance}
        if options.snap_root_to_head:
            bpy.context.view_layer.update()
            root, _outer = root_and_outer_centers(ear, side)
            location, normal, _index, before_distance = tree.find_nearest(root)
            if normal is None:
                raise RuntimeError(f"could not find head surface near {name}")
            # Source L lives on +X and R on -X.  Keep the nearest normal on
            # the corresponding side so an underside normal cannot pull the
            # ear root downward into the jaw/neck region.
            outward_x = 1.0 if side == "L" else -1.0
            if normal.x * outward_x < 0.0:
                normal.negate()
            target = location + normal.normalized() * options.root_surface_offset
            delta = target - root
            ear.matrix_world = Matrix.Translation(delta) @ ear.matrix_world
            decision = decisions.setdefault(side, {})
            decision["root_surface_distance_before"] = before_distance
            decision["root_snap_delta"] = list(delta)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.output.resolve()))
    options.output.with_suffix(".json").write_text(
        json.dumps(
            {
                "schema": "assetslab_miku_ear_placement_tune_v1",
                "source_blend": str(options.blend.resolve()),
                "forward": options.forward,
                "inward": options.inward,
                "scale": options.scale,
                "rim_to_face_degrees": options.rim_to_face_degrees,
                "rim_axis": options.rim_axis,
                "head_object": options.head_object,
                "snap_root_to_head": options.snap_root_to_head,
                "root_surface_offset": options.root_surface_offset,
                "rotation_sign_by_head_distance": decisions,
                "status": "WIP_candidate_for_visual_comparison",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"MIKU_EAR_PLACEMENT_PASS output={options.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
