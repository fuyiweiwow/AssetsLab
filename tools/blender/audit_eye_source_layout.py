"""Print object bounds for an eye/eyelash source and target scene."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector((min(point[i] for point in points) for i in range(3))),
        Vector((max(point[i] for point in points) for i in range(3))),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--objects", nargs="+", required=True)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    options = parser.parse_args(argv)
    bpy.ops.wm.open_mainfile(filepath=str(options.blend.resolve()))
    for name in options.objects:
        obj = bpy.data.objects.get(name)
        if obj is None:
            print(name, "MISSING")
            continue
        low, high = bounds(obj)
        center = (low + high) * 0.5
        print(name, "low", tuple(round(v, 5) for v in low), "high", tuple(round(v, 5) for v in high), "center", tuple(round(v, 5) for v in center))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
