"""Measure lower-body cross sections of an Actor GarmentCode proxy.

The report is a calibration aid for Pants pattern generation. It deliberately
does not rewrite body measurements: the proxy is an explicit collision surface,
while GarmentCode body YAML values are pattern parameters and must be reviewed
before being changed.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import trimesh
import yaml


def ellipse_circumference(width: float, depth: float) -> float:
    a = max(width * 0.5, 1e-6)
    b = max(depth * 0.5, 1e-6)
    h = ((a - b) ** 2) / ((a + b) ** 2)
    return math.pi * (a + b) * (1.0 + (3.0 * h) / (10.0 + math.sqrt(4.0 - 3.0 * h)))


def section(vertices_cm: np.ndarray, y: float, tolerance: float) -> dict[str, float | int]:
    points = vertices_cm[np.abs(vertices_cm[:, 1] - y) <= tolerance]
    if len(points) == 0:
        raise RuntimeError(f"proxy has no vertices near y={y:.3f} cm")
    # Voxel proxies have sparse grid extrema; percentiles keep one isolated
    # marching-cubes corner from dominating the calibration report.
    x0, x1 = np.percentile(points[:, 0], [2.5, 97.5])
    z0, z1 = np.percentile(points[:, 2], [2.5, 97.5])
    width = float(x1 - x0)
    depth = float(z1 - z0)
    return {
        "sample_y_cm": float(y),
        "vertex_count": int(len(points)),
        "x_min_cm": float(x0),
        "x_max_cm": float(x1),
        "z_min_cm": float(z0),
        "z_max_cm": float(z1),
        "width_cm": width,
        "depth_cm": depth,
        "ellipse_circumference_cm": ellipse_circumference(width, depth),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proxy", required=True, type=Path)
    parser.add_argument("--body-measurements", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--tolerance-cm", type=float, default=2.5)
    args = parser.parse_args()

    mesh = trimesh.load(args.proxy.resolve(), process=False)
    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise RuntimeError("proxy must be a non-empty triangle mesh")
    vertices_cm = np.asarray(mesh.vertices, dtype=float) * 100.0
    body = yaml.safe_load(args.body_measurements.read_text(encoding="utf-8"))["body"]
    waist_y = float(body["height"] - body["head_l"] - body["waist_line"])
    hip_y = waist_y - float(body["hips_line"])
    leg_y = hip_y - float(body["crotch_hip_diff"])
    sections = {
        "waist": section(vertices_cm, waist_y, args.tolerance_cm),
        "hips": section(vertices_cm, hip_y, args.tolerance_cm),
        "leg": section(vertices_cm, leg_y, args.tolerance_cm),
    }
    nominal = {
        "waist": float(body["waist"]),
        "hips": float(body["hips"]),
        "leg": float(body["leg_circ"]),
    }
    for name, values in sections.items():
        values["body_yaml_nominal_cm"] = nominal[name]
        values["circumference_delta_cm"] = values["ellipse_circumference_cm"] - nominal[name]

    report = {
        "schema": "assetslab_actor_garmentcode_proxy_sections_v1",
        "proxy": str(args.proxy.resolve()),
        "body_measurements": str(args.body_measurements.resolve()),
        "units": "centimetres",
        "method": "mesh vertices within a fixed Y tolerance, 2.5/97.5 percentiles, Ramanujan ellipse estimate",
        "body_levels": {"waist_y_cm": waist_y, "hip_y_cm": hip_y, "leg_y_cm": leg_y},
        "bounds_cm": np.asarray(mesh.bounds * 100.0).tolist(),
        "sections": sections,
        "interpretation": "Review these differences before changing body YAML or Pants design; this report does not apply a fit automatically.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
