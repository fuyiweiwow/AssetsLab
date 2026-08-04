"""Apply a small, explicit placement correction to head-bone-parented Miku ears."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


EARS = (("MikuEar_L_SourceV1", "L"), ("MikuEar_R_SourceV1", "R"))


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--forward", type=float, default=0.025, help="negative world Y moves toward front camera")
    parser.add_argument("--inward", type=float, default=0.012, help="move both ears toward world X=0")
    parser.add_argument(
        "--rim-to-face-degrees",
        type=float,
        default=0.0,
        help="rotate each ear around its inner root; sign is selected to move the outer rim toward world X=0",
    )
    parser.add_argument("--rim-axis", choices=("Y", "Z"), default="Z")
    return parser.parse_args(argv)


def root_and_outer_centers(ear: bpy.types.Object, side: str) -> tuple[Vector, Vector]:
    points = [ear.matrix_world @ vertex.co for vertex in ear.data.vertices]
    values = [point.x for point in points]
    minimum, maximum = min(values), max(values)
    band = max((maximum - minimum) * 0.16, 1e-6)
    root_points = [point for point in points if point.x >= maximum - band] if side == "L" else [point for point in points if point.x <= minimum + band]
    outer_points = [point for point in points if point.x <= minimum + band] if side == "L" else [point for point in points if point.x >= maximum - band]
    return sum(root_points, Vector()) / len(root_points), sum(outer_points, Vector()) / len(outer_points)


def main() -> int:
    options = parse_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.blend.resolve()))
    scene = bpy.context.scene
    scene.frame_set(1)
    bpy.context.view_layer.update()
    for name, side in EARS:
        ear = bpy.data.objects.get(name)
        if ear is None:
            raise RuntimeError(f"missing ear: {name}")
        inward = options.inward if side == "L" else -options.inward
        # Actor front camera is at -Y, hence a negative Y translation is forward.
        transform = Matrix.Translation(Vector((inward, -options.forward, 0.0)))
        ear.matrix_world = transform @ ear.matrix_world
        if options.rim_to_face_degrees:
            bpy.context.view_layer.update()
            root, outer = root_and_outer_centers(ear, side)
            candidates = []
            for sign in (-1.0, 1.0):
                rotation = Matrix.Rotation(math.radians(sign * options.rim_to_face_degrees), 4, options.rim_axis)
                pivoted = Matrix.Translation(root) @ rotation @ Matrix.Translation(-root) @ ear.matrix_world
                transformed_outer = Matrix.Translation(root) @ rotation @ Matrix.Translation(-root) @ outer
                candidates.append((abs(transformed_outer.x), pivoted))
            ear.matrix_world = min(candidates, key=lambda item: item[0])[1]
    options.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.output.resolve()))
    options.output.with_suffix(".json").write_text(
        json.dumps(
            {
                "schema": "assetslab_miku_ear_placement_tune_v1",
                "source_blend": str(options.blend.resolve()),
                "forward": options.forward,
                "inward": options.inward,
                "rim_to_face_degrees": options.rim_to_face_degrees,
                "rim_axis": options.rim_axis,
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
