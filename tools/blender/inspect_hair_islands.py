"""Split a hair-library OBJ into loose mesh islands and write component stats."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--hair-obj", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def main() -> int:
    options = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=str(options.hair_obj.resolve()), use_split_groups=True)
    parts = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    records = []
    for index, obj in enumerate(sorted(parts, key=lambda item: item.name)):
        points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        low = Vector((min(point[i] for point in points) for i in range(3)))
        high = Vector((max(point[i] for point in points) for i in range(3)))
        center = (low + high) * 0.5
        records.append(
            {
                "index": index,
                "name": obj.name,
                "vertices": len(obj.data.vertices),
                "polygons": len(obj.data.polygons),
                "center": [float(value) for value in center],
                "bounds_min": [float(value) for value in low],
                "bounds_max": [float(value) for value in high],
                "dimensions": [float(value) for value in high - low],
            }
        )
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(
        json.dumps(
            {
                "schema": "assetslab_hair_islands_v1",
                "source_obj": str(options.hair_obj.resolve()),
                "part_count": len(records),
                "parts": records,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"HAIR_ISLAND_AUDIT_PASS parts={len(records)} output={options.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
