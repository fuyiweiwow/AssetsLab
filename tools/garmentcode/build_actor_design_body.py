"""Build a GarmentCode body preset from the Actor torso design profile.

GarmentCode's body YAML is scalar, while the Actor fit is height dependent.
This tool keeps the validated circumferences and vertical landmarks, then
derives the panel-facing shoulder/back widths from the sampled Actor torso
profile before pattern generation.  The full profile is retained beside the
YAML for auditability; it is not applied as a late Blender deformation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-body", required=True, type=Path)
    parser.add_argument("--profile-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def nearest(samples: list[tuple[float, float]], z: float) -> float:
    return min(samples, key=lambda item: abs(item[0] - z))[1]


def main() -> int:
    options = parse_args()
    base = yaml.safe_load(options.base_body.read_text(encoding="utf-8"))
    body = dict(base["body"])
    manifest = json.loads(options.profile_manifest.read_text(encoding="utf-8"))
    fit = manifest["bone_shoulder_fit"]
    width_fit = fit["width_fit"]
    samples = [(float(z), float(width)) for z, width in width_fit["samples"]]
    hip_z = float(fit["hip_z"])
    shoulder_z = float(fit["shoulder_z"])
    shoulder_half = float(fit["shoulder_half_width"])
    ease = float(fit["ease"])

    # These are the same design landmarks used by the transfer pass.  The
    # profile-derived values describe the torso panel, not the arms or hands.
    bust_half = nearest(samples, hip_z + (shoulder_z - hip_z) * 0.78)
    waist_half = nearest(samples, hip_z + (shoulder_z - hip_z) * 0.50)
    hip_half = nearest(samples, hip_z + (shoulder_z - hip_z) * 0.25)
    body["shoulder_w"] = round((shoulder_half + ease) * 2.0 * 100.0, 4)
    body["back_width"] = round(bust_half * 2.0 * 100.0, 4)
    body["waist_back_width"] = round(waist_half * 2.0 * 100.0, 4)
    body["hip_back_width"] = round(hip_half * 2.0 * 100.0, 4)

    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "actor_v1_design_body.yaml").write_text(
        yaml.safe_dump({"body": body}, sort_keys=False), encoding="utf-8"
    )
    report = {
        "schema": "assetslab_actor_design_body_profile_v1",
        "base_body": str(options.base_body.resolve()),
        "profile_manifest": str(options.profile_manifest.resolve()),
        "units": "centimetres for body YAML; metres for source profile",
        "method": "scalar panel widths derived from the Actor height-dependent torso profile",
        "derived": {
            "shoulder_w": body["shoulder_w"],
            "back_width": body["back_width"],
            "waist_back_width": body["waist_back_width"],
            "hip_back_width": body["hip_back_width"],
            "landmark_z_m": {"hip": hip_z, "shoulder": shoulder_z},
            "selected_profile_half_width_m": {
                "bust": bust_half,
                "waist": waist_half,
                "hips": hip_half,
            },
        },
        "profile_samples": width_fit["samples"],
        "body": body,
    }
    (output / "actor_v1_design_body_profile.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
