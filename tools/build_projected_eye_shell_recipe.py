"""Triangulate a projected Miku shell contour into an actor-space mesh recipe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from shapely.geometry import Polygon
from shapely.ops import triangulate


def cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target-low-x", type=float, default=-0.68)
    parser.add_argument("--target-high-x", type=float, default=0.62)
    parser.add_argument("--target-low-z", type=float, default=1.70)
    parser.add_argument("--target-high-z", type=float, default=2.50)
    parser.add_argument("--y", type=float, default=-0.704)
    return parser.parse_args()


def main() -> None:
    options = cli()
    source = json.loads(options.input.read_text(encoding="utf-8"))
    if not source["contours"]:
        raise RuntimeError("projected shell contour is empty")
    contour = source["contours"][0]
    outer = contour["outer_xz"]
    holes = contour["holes_xz"]
    poly = Polygon(outer, holes).buffer(0)
    if poly.is_empty:
        raise RuntimeError("projected shell polygon is invalid")
    if poly.geom_type != "Polygon":
        poly = max(poly.geoms, key=lambda item: item.area)
    low_x = min(point[0] for point in outer)
    high_x = max(point[0] for point in outer)
    low_z = min(point[1] for point in outer)
    high_z = max(point[1] for point in outer)
    scale_x = (options.target_high_x - options.target_low_x) / max(high_x - low_x, 1e-9)
    scale_z = (options.target_high_z - options.target_low_z) / max(high_z - low_z, 1e-9)
    center_x = (low_x + high_x) * 0.5
    center_z = (low_z + high_z) * 0.5

    def map_point(point):
        return (options.target_low_x + (point[0] - low_x) * scale_x, options.y, options.target_low_z + (point[1] - low_z) * scale_z)

    vertices = []
    lookup = {}
    faces = []
    for triangle in triangulate(poly):
        if not poly.covers(triangle.representative_point()):
            continue
        coords = list(triangle.exterior.coords)[:-1]
        indices = []
        for point in coords:
            key = (round(point[0], 8), round(point[1], 8))
            if key not in lookup:
                lookup[key] = len(vertices)
                vertices.append(map_point(point))
            indices.append(lookup[key])
        if len(set(indices)) == 3:
            faces.append(indices)
    payload = {"source": source["source"], "target_y": options.y, "vertices": vertices, "faces": faces, "source_area": poly.area, "vertex_count": len(vertices), "face_count": len(faces)}
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print({"vertices": len(vertices), "faces": len(faces), "source_area": round(poly.area, 6)})


if __name__ == "__main__":
    main()
