"""Rasterize projected source faces and emit clean outer/hole contours."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--preview", required=True, type=Path)
    parser.add_argument("--size", type=int, default=1024)
    return parser.parse_args()


def main() -> None:
    options = cli()
    source = json.loads(options.input.read_text(encoding="utf-8"))
    points = np.asarray(source["points_xz"], dtype=np.float64)
    low = points.min(axis=0)
    high = points.max(axis=0)
    extent = np.maximum(high - low, 1e-9)
    scale = (options.size - 32) / max(extent)
    canvas_points = np.round((points - low) * scale + 16).astype(np.int32)
    mask = np.zeros((options.size, options.size), dtype=np.uint8)
    for polygon in source["polygons"]:
        if len(polygon) < 3:
            continue
        cv2.fillPoly(mask, [canvas_points[polygon]], 255)
    kernel = np.ones((5, 5), dtype=np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        raise RuntimeError("No projected shell contour found")
    hierarchy = hierarchy[0]
    candidates = []
    for index, contour in enumerate(contours):
        if hierarchy[index][3] != -1:
            continue
        area = abs(cv2.contourArea(contour))
        if area >= options.size * options.size * 0.002:
            candidates.append((area, index))
    candidates.sort(reverse=True)
    contours_out = []
    for area, index in candidates:
        contour = contours[index][:, 0, :].astype(np.float64)
        mapped = ((contour - 16.0) / scale + low).tolist()
        holes = []
        child = hierarchy[index][2]
        while child != -1:
            hole = contours[child][:, 0, :].astype(np.float64)
            holes.append(((hole - 16.0) / scale + low).tolist())
            child = hierarchy[child][0]
        contours_out.append({"area_px": area, "outer_xz": mapped, "holes_xz": holes})
    payload = {"source": source["source"], "canvas_size": options.size, "contour_count": len(contours_out), "contours": contours_out, "source_bounds_xz": source["bounds_xz"]}
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    options.preview.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(options.preview), mask)
    print({"contour_count": len(contours_out), "areas_px": [round(item["area_px"], 1) for item in contours_out]})


if __name__ == "__main__":
    main()
