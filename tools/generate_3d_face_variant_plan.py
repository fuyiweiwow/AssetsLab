"""Create deterministic 3D face-actor parameters from an appearance seed.

This is the first gate of the 3D face workflow. It defines geometry in head
local space before any Blender render: eyes, brows, optional blush, and their
shared registration anchors. The next Blender step will instantiate these
parameters as temporary face meshes on the neutral actor.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "prototype" / "assets" / "characters" / "generated" / "face_actor_variants_v1"
MODULUS = 2_147_483_647
MULTIPLIER = 1_103_515_245
INCREMENT = 12_345


def rng(seed: int) -> tuple[int, callable]:
    state = seed % MODULUS

    def next_value() -> float:
        nonlocal state
        state = (state * MULTIPLIER + INCREMENT) % MODULUS
        return state / MODULUS

    return state, next_value


def choose(next_value, values):
    return values[min(len(values) - 1, math.floor(next_value() * len(values)))]


def build_plan(seed: int) -> dict:
    _, next_value = rng(seed)
    eye_style = choose(next_value, ["round", "soft_round", "wide_round"])
    brow_style = choose(next_value, ["straight", "soft_arc", "short_arc"])
    blush = next_value() >= 0.45
    eye_spacing = round(0.30 + next_value() * 0.10, 4)
    eye_height = round(0.00 + (next_value() - 0.5) * 0.06, 4)
    eye_scale = round(0.90 + next_value() * 0.20, 4)
    brow_height = round(0.18 + (next_value() - 0.5) * 0.05, 4)
    face_width = round(1.72 + (next_value() - 0.5) * 0.08, 4)
    return {
        "schema": "assetslab_3d_face_variant_plan_v1",
        "seed": seed % MODULUS,
        "source_style_anchor": "front-character-anchor.png",
        "actor": "featureless_chibi_head",
        "coordinate_system": "head_local_x_right_y_forward_z_up",
        "head_contract": {
            "center": [0.0, 0.0, 0.0],
            "face_forward": [0.0, -1.0, 0.0],
            "face_width": face_width,
            "eye_line_z": 0.08,
            "neck_anchor_z": -0.92,
        },
        "features": {
            "eyes": {
                "style": eye_style,
                "spacing_x": eye_spacing,
                "offset_z": eye_height,
                "scale": eye_scale,
                "depth_y": -0.83,
            },
            "brows": {
                "style": brow_style,
                "spacing_x": eye_spacing,
                "offset_z": round(eye_height + brow_height, 4),
                "scale": eye_scale,
                "depth_y": -0.86,
            },
            "blush": {
                "enabled": blush,
                "offset_x": round(eye_spacing * 0.72, 4),
                "offset_z": round(eye_height - 0.15, 4),
                "depth_y": -0.87,
                "scale": 0.85,
            },
        },
        "render_contract": {
            "directions": ["front", "right", "back", "left"],
            "frames_per_direction": 8,
            "render_canvas_px": [256, 256],
            "runtime_canvas_px": [64, 64],
            "layer_order": ["HeadBase", "Eyes", "Brows", "Blush"],
            "randomization_stage": "3d_geometry_before_2d_export",
        },
        "status": "plan_only",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    plan = build_plan(args.seed)
    target = args.output / f"seed_{plan['seed']:010d}.json"
    target.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    manifest = {
        "schema": "assetslab_3d_face_variant_manifest_v1",
        "style_anchor": "front-character-anchor.png",
        "purpose": "Deterministic 3D face geometry plans before Blender rendering.",
        "plans": [target.name],
        "status": "plan_only",
        "next_step": "instantiate feature meshes on the neutral Blender actor and render separate layers",
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"FACE_3D_PLAN_PASS seed={plan['seed']} output={target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
