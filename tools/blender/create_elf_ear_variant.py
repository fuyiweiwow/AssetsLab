"""Create a non-destructive pointed-elf-ear variant from the accepted ear mesh."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


EAR_PREFIX = "CartoonEar_"
HEAD_BONE = "CC_Base_Head"


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-blend", required=True, type=Path)
    parser.add_argument("--output-blend", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--length-scale", type=float, default=1.42)
    parser.add_argument("--tip-outward", type=float, default=0.13)
    parser.add_argument("--tip-back", type=float, default=0.055)
    return parser.parse_args(argv)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def smoothstep(value: float) -> float:
    value = clamp(value, 0.0, 1.0)
    return value * value * (3.0 - 2.0 * value)


def bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    return (
        Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points))),
        Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points))),
    )


def deform_ear(
    ear: bpy.types.Object,
    side: float,
    length_scale: float,
    tip_outward: float,
    tip_back: float,
) -> dict[str, object]:
    """Taper an ear above its root while preserving the attachment band."""
    bpy.context.view_layer.update()
    low, high = bounds(ear)
    root_x = high.x if side < 0.0 else low.x
    width = max(1e-5, high.x - low.x)
    # The root is the narrow side nearest the head.  Its centroid is retained
    # exactly so changing the upper pinna never breaks the approved attachment.
    root_band = width * 0.18
    world_vertices = [ear.matrix_world @ vertex.co for vertex in ear.data.vertices]
    root_points = [
        point
        for point in world_vertices
        if abs(point.x - root_x) <= root_band
    ]
    root_center = sum(root_points, Vector()) / len(root_points)
    top_span = max(1e-5, high.z - root_center.z)
    world_to_local = ear.matrix_world.inverted()
    ear.data = ear.data.copy()
    for vertex in ear.data.vertices:
        point = ear.matrix_world @ vertex.co
        height = clamp((point.z - root_center.z) / top_span, 0.0, 1.0)
        # The inner 18% is fully locked; the deformation smoothly reaches its
        # intended amount at the tip. This preserves both mesh continuity and
        # the head contact point.
        # Keep every point in the declared root band fixed, not only the
        # mathematical extreme.  This is the contact-preservation guarantee
        # for later head-bone animation as well as static previews.
        root_distance = clamp(
            (abs(point.x - root_x) - root_band) / max(1e-5, width - root_band),
            0.0,
            1.0,
        )
        influence = smoothstep(height) * smoothstep(root_distance)
        point.z += (point.z - root_center.z) * (length_scale - 1.0) * influence
        point.x += side * tip_outward * (height**1.65) * influence
        point.y += tip_back * (height**1.65) * influence
        vertex.co = world_to_local @ point
    return {
        "name": ear.name,
        "parent_bone": ear.parent_bone,
        "root_center_world": [round(value, 6) for value in root_center],
        "bounds_before": {"low": [round(value, 6) for value in low], "high": [round(value, 6) for value in high]},
        "bounds_after": {
            "low": [round(value, 6) for value in bounds(ear)[0]],
            "high": [round(value, 6) for value in bounds(ear)[1]],
        },
    }


def main() -> int:
    options = cli_args()
    if options.length_scale <= 1.0:
        raise RuntimeError("elf-ear length scale must be greater than one")
    bpy.ops.wm.open_mainfile(filepath=str(options.input_blend.resolve()))
    ears = sorted(
        (obj for obj in bpy.data.objects if obj.type == "MESH" and obj.name.startswith(EAR_PREFIX)),
        key=lambda obj: obj.name,
    )
    if [ear.name for ear in ears] != ["CartoonEar_L_Downloaded", "CartoonEar_R_Downloaded"]:
        raise RuntimeError(f"expected accepted left/right ear meshes, found {[ear.name for ear in ears]}")
    armature = next((obj for obj in bpy.data.objects if obj.type == "ARMATURE"), None)
    if armature is None or HEAD_BONE not in armature.data.bones:
        raise RuntimeError(f"actor must contain {HEAD_BONE}")
    records = [
        deform_ear(ears[0], -1.0, options.length_scale, options.tip_outward, options.tip_back),
        deform_ear(ears[1], 1.0, options.length_scale, options.tip_outward, options.tip_back),
    ]
    if any(record["parent_bone"] != HEAD_BONE for record in records):
        raise RuntimeError("elf-ear candidate lost its head-bone attachment")
    options.output_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.output_blend.resolve()))
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.write_text(
        json.dumps(
            {
                "schema": "assetslab_elf_ear_variant_v1",
                "input_blend": str(options.input_blend.resolve()),
                "output_blend": str(options.output_blend.resolve()),
                "parent_bone": HEAD_BONE,
                "style": "long_elf_ear",
                "parameters": {
                    "length_scale": options.length_scale,
                    "tip_outward": options.tip_outward,
                    "tip_back": options.tip_back,
                    "root_band_policy": "locked_inner_18_percent",
                },
                "ears": records,
                "status": "candidate_review_required",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"ELF_EAR_VARIANT_PASS ears={len(records)} output={options.output_blend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
