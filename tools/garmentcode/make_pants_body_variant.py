"""Create an auditable Pants body-measurement variant.

Only circumference-like Pants inputs are scaled. Vertical landmarks and all
upper-body measurements remain unchanged so a simulation comparison isolates
pattern ease rather than changing the Actor coordinate system.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-body", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--waist-scale", type=float, default=1.05)
    parser.add_argument("--hips-scale", type=float, default=1.05)
    parser.add_argument("--leg-scale", type=float, default=1.05)
    return parser.parse_args()


def main() -> int:
    options = parse_args()
    payload = yaml.safe_load(options.base_body.read_text(encoding="utf-8"))
    body = dict(payload["body"])
    original = dict(body)
    for key in ("waist", "waist_back_width"):
        body[key] = round(float(body[key]) * options.waist_scale, 6)
    for key in ("hips", "hip_back_width"):
        body[key] = round(float(body[key]) * options.hips_scale, 6)
    body["leg_circ"] = round(float(body["leg_circ"]) * options.leg_scale, 6)

    output = options.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump({"body": body}, sort_keys=False), encoding="utf-8")
    report = {
        "schema": "assetslab_pants_body_variant_v1",
        "base_body": str(options.base_body.resolve()),
        "scales": {
            "waist": options.waist_scale,
            "hips": options.hips_scale,
            "leg_circ": options.leg_scale,
        },
        "changed_keys": ["waist", "waist_back_width", "hips", "hip_back_width", "leg_circ"],
        "body": body,
        "original": {key: original[key] for key in ("waist", "waist_back_width", "hips", "hip_back_width", "leg_circ")},
    }
    report_path = output.with_suffix(".json")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
