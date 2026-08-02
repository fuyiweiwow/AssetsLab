"""Flatten and recess the experimental eye assembly without changing X/Z shape."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--eye", default="MikuChibiEyeball")
    parser.add_argument("--depth-scale", type=float, default=0.45)
    parser.add_argument("--inward", type=float, default=0.055)
    return parser.parse_args(argv)


def main() -> None:
    options = cli()
    eye = bpy.data.objects.get(options.eye)
    if eye is None or eye.type != "MESH":
        raise RuntimeError("eye mesh missing")
    matrix = eye.matrix_world.copy()
    inverse = matrix.inverted()
    world_points = [matrix @ vertex.co for vertex in eye.data.vertices]
    center = sum(world_points[1:], world_points[0]) / len(world_points)
    before_y = [point.y for point in world_points]
    for vertex, point in zip(eye.data.vertices, world_points):
        flattened = Vector((point.x, center.y + (point.y - center.y) * options.depth_scale + options.inward, point.z))
        vertex.co = inverse @ flattened
    eye.data.update()
    after_points = [matrix @ vertex.co for vertex in eye.data.vertices]
    after_y = [point.y for point in after_points]
    eye["TEST_depth_scale"] = options.depth_scale
    eye["TEST_inward_offset"] = options.inward
    options.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.output.resolve()), compress=True)
    print({"output": str(options.output), "before_depth": max(before_y) - min(before_y), "after_depth": max(after_y) - min(after_y), "inward": options.inward})


if __name__ == "__main__":
    main()
