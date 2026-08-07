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
from trimesh.smoothing import filter_taubin
from trimesh.voxel import VoxelGrid
from trimesh.voxel.encoding import DenseEncoding


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


def pants_core_half_width(y: float) -> float:
    """Return the intended lower-body half width in source centimetres."""
    # Keep the hip envelope compatible with hips=103.5 cm while removing the
    # isolated arm spikes visible in the raw proxy.  The profile is deliberately
    # smooth; hard narrowing at the thighs made Warp spend the whole budget
    # resolving an artificial vertical collision wall.
    samples = ((35.0, 32.0), (55.0, 36.0), (75.0, 46.0), (95.0, 52.0), (115.0, 50.0), (135.0, 40.0))
    if y <= samples[0][0]:
        return samples[0][1]
    if y >= samples[-1][0]:
        return samples[-1][1]
    for (y0, width0), (y1, width1) in zip(samples, samples[1:]):
        if y0 <= y <= y1:
            ratio = (y - y0) / (y1 - y0)
            return width0 + (width1 - width0) * ratio
    return samples[-1][1]


def map_piecewise(values: np.ndarray, source: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Map three anatomical source levels to three GarmentCode levels."""
    result = np.interp(values, source, target)
    low = values < source[0]
    high = values > source[-1]
    result[low] = target[0] + (values[low] - source[0]) * (target[1] - target[0]) / (source[1] - source[0])
    result[high] = target[-1] + (values[high] - source[-1]) * (target[-1] - target[-2]) / (source[-1] - source[-2])
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-obj", type=Path, required=True)
    parser.add_argument("--output-obj", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    parser.add_argument("--segmentation-json", type=Path, required=True)
    parser.add_argument("--pitch", type=float, default=4.0)
    parser.add_argument("--crop-y-min", type=float)
    parser.add_argument("--crop-y-max", type=float)
    parser.add_argument(
        "--pants-core",
        action="store_true",
        help="remove lateral arm-volume voxels with a lower-body height/width envelope before meshing",
    )
    parser.add_argument(
        "--output-scale",
        type=float,
        default=0.01,
        help="Scale source Actor centimetres to GarmentCode OBJ units (metres)",
    )
    parser.add_argument(
        "--z-scale",
        type=float,
        default=1.0,
        help="Scale the source Actor front/back depth around Z before exporting",
    )
    parser.add_argument(
        "--x-scale",
        type=float,
        default=1.0,
        help="Scale the source Actor horizontal width around X before exporting",
    )
    parser.add_argument(
        "--y-map-source",
        type=float,
        nargs=3,
        metavar=("LEG", "HIP", "WAIST"),
        help="Source Actor Y levels in centimetres for piecewise anatomical mapping",
    )
    parser.add_argument(
        "--y-map-target",
        type=float,
        nargs=3,
        metavar=("LEG", "HIP", "WAIST"),
        help="Target GarmentCode Y levels in centimetres for piecewise anatomical mapping",
    )
    parser.add_argument(
        "--smooth-iterations",
        type=int,
        default=0,
        help="Apply volume-preserving Taubin smoothing after proxy construction",
    )
    args = parser.parse_args()

    source = trimesh.load(args.input_obj, process=False)
    if not isinstance(source, trimesh.Trimesh):
        raise TypeError(f"Expected a single mesh, got {type(source).__name__}")
    if source.is_empty:
        raise ValueError("Input mesh is empty")

    # Fill first, then optionally crop the filled voxel volume before extracting
    # an iso-surface. Cropping the binary volume keeps the new cut faces closed
    # and avoids trimesh's optional shapely-dependent triangle slicer.
    voxels = source.voxelized(pitch=args.pitch).fill()
    if args.crop_y_min is not None or args.crop_y_max is not None:
        matrix = np.asarray(voxels.matrix, dtype=bool)
        origin_y = float(voxels.transform[1, 3])
        pitch_y = float(voxels.transform[1, 1])
        start = 0 if args.crop_y_min is None else max(0, int(np.ceil((args.crop_y_min - origin_y) / pitch_y)))
        stop = matrix.shape[1] if args.crop_y_max is None else min(
            matrix.shape[1], int(np.floor((args.crop_y_max - origin_y) / pitch_y)) + 1
        )
        if stop <= start:
            raise ValueError("Y crop does not overlap the voxel volume")
        cropped = matrix[:, start:stop, :]
        transform = np.array(voxels.transform, copy=True)
        transform[1, 3] += start * pitch_y
        voxels = VoxelGrid(DenseEncoding(cropped), transform=transform)
    if args.pants_core:
        matrix = np.asarray(voxels.matrix, dtype=bool)
        origin_x = float(voxels.transform[0, 3])
        origin_y = float(voxels.transform[1, 3])
        pitch_x = float(voxels.transform[0, 0])
        pitch_y = float(voxels.transform[1, 1])
        x_centers = origin_x + np.arange(matrix.shape[0]) * pitch_x
        y_centers = origin_y + np.arange(matrix.shape[1]) * pitch_y
        widths = np.asarray([pants_core_half_width(y) for y in y_centers])
        matrix &= np.abs(x_centers[:, None, None]) <= widths[None, :, None]
        if not matrix.any():
            raise ValueError("pants core envelope removed the entire voxel body")
        voxels = VoxelGrid(DenseEncoding(matrix), transform=voxels.transform)
    proxy = voxels.marching_cubes
    # marching_cubes returns voxel-local coordinates; restore the source OBJ
    # centimetre coordinate system before exporting and labeling.
    proxy.apply_transform(voxels.transform)
    if proxy.is_empty:
        raise ValueError("Y-cropped Actor proxy is empty")
    if args.z_scale <= 0:
        raise ValueError("--z-scale must be greater than zero")
    if args.x_scale <= 0:
        raise ValueError("--x-scale must be greater than zero")
    proxy.vertices[:, 0] *= args.x_scale
    proxy.vertices[:, 2] *= args.z_scale
    if (args.y_map_source is None) != (args.y_map_target is None):
        raise ValueError("--y-map-source and --y-map-target must be provided together")
    if args.y_map_source is not None:
        source_levels = np.asarray(args.y_map_source, dtype=float)
        target_levels = np.asarray(args.y_map_target, dtype=float)
        if not (np.all(np.diff(source_levels) > 0) and np.all(np.diff(target_levels) > 0)):
            raise ValueError("Y mapping levels must be strictly increasing: leg < hip < waist")
        proxy.vertices[:, 1] = map_piecewise(proxy.vertices[:, 1], source_levels, target_levels)
    if args.smooth_iterations < 0:
        raise ValueError("--smooth-iterations must be non-negative")
    if args.smooth_iterations:
        filter_taubin(proxy, lamb=0.4, nu=0.53, iterations=args.smooth_iterations)
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
        "crop_y_min": args.crop_y_min,
        "crop_y_max": args.crop_y_max,
        "pants_core": args.pants_core,
        "z_scale": args.z_scale,
        "x_scale": args.x_scale,
        "y_map_source_cm": args.y_map_source,
        "y_map_target_cm": args.y_map_target,
        "smooth_iterations": args.smooth_iterations,
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
