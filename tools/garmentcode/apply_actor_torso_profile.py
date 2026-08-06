"""Apply a restrained Actor torso profile to generated torso panel boundaries.

GarmentCode's standard T-shirt program exposes scalar body measurements. This
design-stage pass keeps the validated body preset and modifies only the panel
side-boundary x coordinates with a smooth, low-strength profile blend. Sewing
relationships and panel topology remain unchanged, and the source profile is
stored in the output specification for review.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


TORSO_NAMES = ("ftorso", "btorso")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern-spec", required=True, type=Path)
    parser.add_argument("--profile-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--strength", type=float, default=0.30)
    return parser.parse_args()


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def interpolated(samples: list[tuple[float, float]], z: float) -> float:
    if z <= samples[0][0]:
        return samples[0][1]
    if z >= samples[-1][0]:
        return samples[-1][1]
    for (z0, w0), (z1, w1) in zip(samples, samples[1:]):
        if z0 <= z <= z1:
            ratio = (z - z0) / max(z1 - z0, 1e-6)
            return w0 + (w1 - w0) * ratio
    return samples[-1][1]


def normalized_profile(profile: dict[str, object]) -> list[tuple[float, float]]:
    fit = profile["bone_shoulder_fit"]
    width_fit = fit["width_fit"]
    raw = [(float(z), float(width)) for z, width in width_fit["samples"]]
    hip_z = float(fit["hip_z"])
    shoulder_z = float(fit["shoulder_z"])
    bust_z = hip_z + (shoulder_z - hip_z) * 0.78
    bust_width = max(interpolated(raw, bust_z), 1e-6)
    return [
        (0.0, interpolated(raw, hip_z) / bust_width),
        (0.5, interpolated(raw, hip_z + (shoulder_z - hip_z) * 0.50) / bust_width),
        (0.78, 1.0),
        (1.0, 1.0),
    ]


def profile_ratio(profile: list[tuple[float, float]], t: float) -> float:
    if t <= profile[0][0]:
        return profile[0][1]
    if t >= profile[-1][0]:
        return profile[-1][1]
    for (t0, r0), (t1, r1) in zip(profile, profile[1:]):
        if t0 <= t <= t1:
            blend = (t - t0) / max(t1 - t0, 1e-6)
            return r0 + (r1 - r0) * blend
    return profile[-1][1]


def main() -> int:
    options = parse_args()
    strength = clamp(options.strength, 0.0, 1.0)
    source = json.loads(options.pattern_spec.read_text(encoding="utf-8"))
    profile_manifest = json.loads(options.profile_manifest.read_text(encoding="utf-8"))
    result = copy.deepcopy(source)
    pattern = result["pattern"]
    curve = normalized_profile(profile_manifest)
    changed = 0

    for name, panel in pattern["panels"].items():
        if not any(token in name for token in TORSO_NAMES):
            continue
        vertices = panel["vertices"]
        max_y = max(float(point[1]) for point in vertices)
        for point in vertices:
            y = float(point[1])
            t = clamp(y / max(max_y, 1e-6), 0.0, 1.0)
            target_ratio = profile_ratio(curve, t)
            scale = 1.0 - strength * (1.0 - target_ratio)
            original_x = float(point[0])
            point[0] = original_x * scale
            if abs(point[0] - original_x) > 1e-7:
                changed += 1

    result["assetslab_design_profile"] = {
        "schema": "assetslab_actor_torso_panel_profile_v1",
        "source_pattern_spec": str(options.pattern_spec.resolve()),
        "source_profile_manifest": str(options.profile_manifest.resolve()),
        "strength": strength,
        "panel_scope": "front/back torso panels only",
        "topology_changed": False,
        "sewing_relationships_changed": False,
        "normalized_curve": curve,
        "changed_vertices": changed,
        "next_stage": "GarmentCode physics gate, then Actor cage transfer",
    }
    output = options.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["assetslab_design_profile"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
