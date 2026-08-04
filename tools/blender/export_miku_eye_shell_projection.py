"""Export the Miku skin eye-shell mesh as front X/Z polygons for 2D reconstruction."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--shell", default="eye_007_22_0_node")
    return parser.parse_args(argv)


def main() -> None:
    options = cli()
    source = bpy.data.objects.get(options.shell)
    if source is None or source.type != "MESH":
        raise RuntimeError("Miku eye shell source is missing")
    points = [source.matrix_world @ vertex.co for vertex in source.data.vertices]
    polygons = [[int(index) for index in polygon.vertices] for polygon in source.data.polygons]
    payload = {
        "source": options.shell,
        "points_xz": [[point.x, point.z] for point in points],
        "polygons": polygons,
        "bounds_xz": [[min(point.x for point in points), min(point.z for point in points)], [max(point.x for point in points), max(point.z for point in points)]],
    }
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print({"source": options.shell, "vertices": len(points), "polygons": len(polygons), "bounds_xz": payload["bounds_xz"]})


if __name__ == "__main__":
    main()
