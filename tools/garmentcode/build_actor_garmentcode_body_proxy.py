"""Build a closed GarmentCode-compatible collision body from an Actor OBJ.

The Actor mesh contains disconnected cosmetic pieces and is not suitable as a
cloth collision surface.  A filled voxel volume gives GarmentCode one closed,
single-component body while preserving the Actor's X/Y/Z centimetre space.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh


def classify_vertices(vertices: np.ndarray) -> dict[str, list[int]]:
    """Create conservative body-part labels for GarmentCode's vertex filters.

    These labels are intentionally mutually exclusive.  They are collision
    filtering hints, not an anatomical rig; the proxy geometry remains the
    source of truth.
    """

    x = vertices[:, 0]
    y = vertices[:, 1]
    labels = {
        "body": [],
        "left_arm": [],
        "left_leg": [],
        "right_arm": [],
        "right_leg": [],
        "face_internal": [],
    }

    # Actor is in GarmentCode's convention: X horizontal, Y up, Z depth.
    for index, (px, py) in enumerate(zip(x, y)):
        if py < 78.0:
            labels["left_leg" if px < 0.0 else "right_leg"].append(index)
        elif py < 195.0 and px > 31.0:
            labels["left_arm"].append(index)
        elif py < 195.0 and px < -31.0:
            labels["right_arm"].append(index)
        else:
            labels["body"].append(index)

    # The voxel proxy has no internal eyeball/mouth geometry.
    return labels


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-obj", type=Path, required=True)
    parser.add_argument("--output-obj", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    parser.add_argument("--segmentation-json", type=Path, required=True)
    parser.add_argument("--pitch", type=float, default=4.0)
    parser.add_argument(
        "--output-scale",
        type=float,
        default=0.01,
        help="Scale source Actor centimetres to GarmentCode OBJ units (metres)",
    )
    args = parser.parse_args()

    source = trimesh.load(args.input_obj, process=False)
    if not isinstance(source, trimesh.Trimesh):
        raise TypeError(f"Expected a single mesh, got {type(source).__name__}")
    if source.is_empty:
        raise ValueError("Input mesh is empty")

    # Fill first, then extract an iso-surface.  marching_cubes preserves the
    # voxel transform, so the output remains in the input OBJ's coordinates.
    voxels = source.voxelized(pitch=args.pitch).fill()
    proxy = voxels.marching_cubes
    # marching_cubes returns voxel-local coordinates; restore the source OBJ
    # centimetre coordinate system before exporting and labeling.
    proxy.apply_transform(voxels.transform)
    proxy.process(validate=True)

    source_bounds = np.asarray(proxy.bounds).tolist()
    segmentation = classify_vertices(np.asarray(proxy.vertices))
    proxy.apply_scale(args.output_scale)

    args.output_obj.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.segmentation_json.parent.mkdir(parents=True, exist_ok=True)
    proxy.export(args.output_obj)

    args.segmentation_json.write_text(
        json.dumps(segmentation, indent=2) + "\n", encoding="utf-8"
    )
    report = {
        "source": str(args.input_obj),
        "pitch": args.pitch,
        "output_scale": args.output_scale,
        "vertices": int(len(proxy.vertices)),
        "faces": int(len(proxy.faces)),
        "source_bounds_cm": source_bounds,
        "output_bounds_m": np.asarray(proxy.bounds).tolist(),
        "watertight": bool(proxy.is_watertight),
        "winding_consistent": bool(proxy.is_winding_consistent),
        "connected_components": int(len(proxy.split(only_watertight=False))),
        "segmentation_counts": {key: len(value) for key, value in segmentation.items()},
    }
    args.output_report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
