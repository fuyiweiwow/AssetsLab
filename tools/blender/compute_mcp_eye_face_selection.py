"""Compute candidate front-face indices for an MCP edit-mode socket test."""

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
    parser.add_argument("--target", default="ChibiActor_MCP_PreciseEyeSocket_Test")
    parser.add_argument("--eye", default="MikuChibiEyeball")
    return parser.parse_args(argv)


def main() -> None:
    options = cli()
    target = bpy.data.objects.get(options.target)
    eye = bpy.data.objects.get(options.eye)
    if target is None or eye is None:
        raise RuntimeError("target or eye object missing")
    eye_points = [eye.matrix_world @ v.co for v in eye.data.vertices]
    left_eye = [p for p in eye_points if p.x < 0]
    right_eye = [p for p in eye_points if p.x >= 0]
    eye_centers = {
        "L": [sum(p.x for p in left_eye) / len(left_eye), sum(p.z for p in left_eye) / len(left_eye)],
        "R": [sum(p.x for p in right_eye) / len(right_eye), sum(p.z for p in right_eye) / len(right_eye)],
    }
    inv = target.matrix_world.inverted()
    candidates: dict[str, list[int]] = {"L": [], "R": []}
    samples: dict[str, list[dict[str, float]]] = {"L": [], "R": []}
    for poly in target.data.polygons:
        center_local = sum((target.data.vertices[index].co for index in poly.vertices), Vector()) / len(poly.vertices)
        center = target.matrix_world @ center_local
        normal = (target.matrix_world.to_3x3() @ poly.normal).normalized()
        for side, (cx, cz) in eye_centers.items():
            if abs(center.x - cx) <= 0.30 and abs(center.z - cz) <= 0.31 and center.y < -0.20 and normal.y < -0.25:
                candidates[side].append(poly.index)
                if len(samples[side]) < 12:
                    samples[side].append({"face": poly.index, "x": center.x, "y": center.y, "z": center.z, "normal_y": normal.y})
    payload = {
        "target": options.target,
        "eye": options.eye,
        "eye_centers_xz": eye_centers,
        "selection_rules": {"x_half_width": 0.30, "z_half_height": 0.31, "max_front_y": -0.20, "normal_y_max": -0.25},
        "candidate_face_counts": {side: len(values) for side, values in candidates.items()},
        "candidate_face_indices": candidates,
        "samples": samples,
    }
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"candidate_face_counts": payload["candidate_face_counts"], "eye_centers_xz": eye_centers}))


if __name__ == "__main__":
    main()
