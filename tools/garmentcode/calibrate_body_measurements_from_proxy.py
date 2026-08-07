"""Calibrate GarmentCode circumference fields from a closed Actor proxy.

The proxy is the collision surface used by Warp.  This tool measures its
closed horizontal sections instead of guessing from sparse OBJ vertices, then
copies the input body YAML with waist, hip, and upper-leg circumferences
replaced.  The upper-leg section can contain both legs in one connected path,
so its default divisor is two.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import trimesh
import yaml


def section_length_cm(mesh: trimesh.Trimesh, y_cm: float) -> tuple[float, int]:
    section = mesh.section(
        plane_origin=[0.0, y_cm / 100.0, 0.0],
        plane_normal=[0.0, 1.0, 0.0],
    )
    if section is None or section.is_empty:
        raise RuntimeError(f"proxy has no closed section at y={y_cm:.6f} cm")
    return float(section.length * 100.0), len(section.entities)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proxy", required=True, type=Path)
    parser.add_argument("--body", required=True, type=Path)
    parser.add_argument("--output-body", required=True, type=Path)
    parser.add_argument("--output-report", required=True, type=Path)
    parser.add_argument(
        "--leg-divisor",
        type=float,
        default=2.0,
        help="Divide the lower-body section into this many leg circumferences.",
    )
    args = parser.parse_args()
    if args.leg_divisor <= 0:
        raise ValueError("--leg-divisor must be greater than zero")

    mesh = trimesh.load(args.proxy.resolve(), process=False)
    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise RuntimeError("proxy must be a non-empty triangle mesh")
    source = yaml.safe_load(args.body.read_text(encoding="utf-8"))
    body = copy.deepcopy(source["body"])
    waist_y = float(body["height"] - body["head_l"] - body["waist_line"])
    hip_y = waist_y - float(body["hips_line"])
    leg_y = hip_y - float(body["crotch_hip_diff"])

    waist_cm, waist_entities = section_length_cm(mesh, waist_y)
    hips_cm, hip_entities = section_length_cm(mesh, hip_y)
    leg_total_cm, leg_entities = section_length_cm(mesh, leg_y)
    calibrated = {
        "waist": waist_cm,
        "hips": hips_cm,
        "leg_circ": leg_total_cm / args.leg_divisor,
    }
    for name, value in calibrated.items():
        body[name] = round(value, 6)

    output_body = copy.deepcopy(source)
    output_body["body"] = body
    output_body["assetslab_calibration"] = {
        "schema": "assetslab_body_measurements_from_proxy_v1",
        "source_proxy": str(args.proxy.resolve()),
        "section_units": "centimetres",
        "leg_divisor": args.leg_divisor,
        "body_levels_cm": {"waist": waist_y, "hips": hip_y, "leg": leg_y},
        "section_entities": {
            "waist": waist_entities,
            "hips": hip_entities,
            "leg_total": leg_entities,
        },
        "calibrated_values_cm": calibrated,
        "interpretation": "Use this YAML only with the same closed proxy; it is an Actor-fit diagnostic, not a universal human body preset.",
    }
    args.output_body.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_body.write_text(yaml.safe_dump(output_body, sort_keys=False), encoding="utf-8")
    args.output_report.write_text(
        json.dumps(output_body["assetslab_calibration"], indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output_body["assetslab_calibration"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
