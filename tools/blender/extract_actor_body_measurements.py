"""Extract a first-pass GarmentCode body preset from the project Actor mesh.

This deliberately stays inside Blender and does not depend on the GPL
GarmentMeasurements repository.  The result is an approximation intended to
seed parametric garment generation; clothing still has to pass the project's
Clothing Cage and four-direction animation gates.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


SECTION_FRACTIONS = {
    "neck": 0.84,
    "bust": 0.70,
    "underbust": 0.64,
    "waist": 0.55,
    "hips": 0.43,
    "leg": 0.25,
    "wrist": 0.16,
}


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--object", default="ChibiBaseMesh_AccuRIG_InputMesh")
    parser.add_argument("--frame", type=int, default=1)
    return parser.parse_args(argv)


def evaluated_world_vertices(obj: bpy.types.Object) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        matrix = evaluated.matrix_world
        return [matrix @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def ellipse_circumference(width: float, depth: float) -> float:
    """Ramanujan approximation for an ellipse, in Blender units."""

    a = max(width * 0.5, 1e-6)
    b = max(depth * 0.5, 1e-6)
    h = ((a - b) ** 2) / ((a + b) ** 2)
    return math.pi * (a + b) * (1.0 + (3.0 * h) / (10.0 + math.sqrt(4.0 - 3.0 * h)))


def slice_bounds(
    vertices: list[Vector],
    z: float,
    half_thickness: float,
    x_radius: float | None = None,
) -> tuple[float, float, float, float]:
    points = [
        point
        for point in vertices
        if abs(point.z - z) <= half_thickness
        and (x_radius is None or abs(point.x) <= x_radius)
    ]
    if not points:
        raise RuntimeError(f"Actor has no vertices near z={z:.4f}")

    # Percentiles remove isolated toes, fingers and modifier spikes from this
    # first-pass measurement.  The source Actor is stylised, so these values
    # are only a stable design seed, not a tailoring-grade body scan.
    xs = sorted(point.x for point in points)
    ys = sorted(point.y for point in points)
    lo = max(0, int(len(xs) * 0.05))
    hi = min(len(xs) - 1, int(len(xs) * 0.95))
    ylo = max(0, int(len(ys) * 0.05))
    yhi = min(len(ys) - 1, int(len(ys) * 0.95))
    return xs[lo], xs[hi], ys[ylo], ys[yhi]


def bone_length_cm(armature: bpy.types.Object, names: tuple[str, ...], scale: float) -> float | None:
    if armature is None or armature.type != "ARMATURE":
        return None
    for name in names:
        bone = armature.data.bones.get(name)
        if bone is not None:
            return float((armature.matrix_world.to_3x3() @ (bone.tail_local - bone.head_local)).length * scale)
    return None


def bone_world_point(armature: bpy.types.Object | None, name: str, tail: bool = False) -> Vector | None:
    if armature is None or armature.type != "ARMATURE":
        return None
    bone = armature.data.bones.get(name)
    if bone is None:
        return None
    return armature.matrix_world @ (bone.tail_local if tail else bone.head_local)


def write_yaml_compatible_json(path: Path, body: dict[str, float]) -> None:
    # JSON is a valid YAML 1.2 document and avoids adding a YAML dependency to
    # Blender's bundled Python.  GarmentCode's yaml.safe_load reads it as the
    # same mapping as its native body preset.
    path.write_text(json.dumps({"body": body}, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.actor.resolve()))
    bpy.context.scene.frame_set(options.frame)
    bpy.context.view_layer.update()

    actor = bpy.data.objects.get(options.object)
    if actor is None or actor.type != "MESH":
        raise RuntimeError(f"Actor mesh not found: {options.object}")

    vertices = evaluated_world_vertices(actor)
    if not vertices:
        raise RuntimeError("Actor mesh has no evaluated vertices")
    low = Vector((min(point.x for point in vertices), min(point.y for point in vertices), min(point.z for point in vertices)))
    high = Vector((max(point.x for point in vertices), max(point.y for point in vertices), max(point.z for point in vertices)))
    height = high.z - low.z
    if height <= 0:
        raise RuntimeError("Actor height is zero")

    armature = bpy.data.objects.get("Armature")
    # The project Actor is authored in metres; GarmentCode body presets use cm.
    cm = 100.0
    measurements: dict[str, float] = {
        "height": height * cm,
    }
    landmarks = {
        "hips": bone_world_point(armature, "CC_Base_Pelvis"),
        "waist": bone_world_point(armature, "CC_Base_Waist"),
        "bust": bone_world_point(armature, "CC_Base_Spine02"),
        "neck": bone_world_point(armature, "CC_Base_NeckTwist01"),
    }
    if all(value is not None for value in landmarks.values()):
        landmarks["bust"] = (landmarks["bust"] + bone_world_point(armature, "CC_Base_Spine02", tail=True)) * 0.5
        landmark_z = {name: point.z for name, point in landmarks.items()}
        landmark_z.update({"underbust": landmark_z["bust"] * 0.82 + landmark_z["waist"] * 0.18, "leg": low.z + height * 0.15, "wrist": low.z + height * 0.30})
    else:
        landmark_z = {name: low.z + height * fraction for name, fraction in SECTION_FRACTIONS.items()}

    # Arms are deliberately excluded from torso slices.  This is the key
    # correction over the initial naive full-silhouette pass.
    slices: dict[str, dict[str, float]] = {}
    for name, z in landmark_z.items():
        x_radius = 0.42 if name in {"bust", "underbust", "waist", "hips", "neck"} else None
        x0, x1, y0, y1 = slice_bounds(vertices, z, max(height * 0.012, 0.0005), x_radius=x_radius)
        width = x1 - x0
        depth = y1 - y0
        slices[name] = {"z": z, "width": width * cm, "depth": depth * cm}

    torso_width = slices["bust"]["width"]
    measurements.update(
        {
            "bust": ellipse_circumference(slices["bust"]["width"], slices["bust"]["depth"]),
            "underbust": ellipse_circumference(slices["underbust"]["width"], slices["underbust"]["depth"]),
            "waist": ellipse_circumference(slices["waist"]["width"], slices["waist"]["depth"]),
            "hips": ellipse_circumference(slices["hips"]["width"], slices["hips"]["depth"]),
            "neck_w": torso_width * 0.56,
            "shoulder_w": torso_width * 1.05,
            "leg_circ": ellipse_circumference(slices["leg"]["width"], slices["leg"]["depth"]),
            "bust_line": (slices["bust"]["z"] - low.z) * cm,
            "waist_line": (slices["waist"]["z"] - low.z) * cm,
            "hips_line": (slices["hips"]["z"] - low.z) * cm,
            "vert_bust_line": (slices["neck"]["z"] - slices["bust"]["z"]) * cm,
            "waist_over_bust_line": (slices["neck"]["z"] - slices["waist"]["z"]) * cm,
            "crotch_hip_diff": (slices["hips"]["z"] - slices["leg"]["z"]) * cm,
            "head_l": (high.z - slices["neck"]["z"]) * cm,
            "back_width": torso_width * 0.46,
            "waist_back_width": slices["waist"]["width"] * 0.46,
            "hip_back_width": slices["hips"]["width"] * 0.46,
            "bust_points": slices["bust"]["depth"] * 0.5,
            "bum_points": slices["hips"]["depth"] * 0.5,
            "arm_length": (height * (0.84 - 0.25)) * cm,
            "arm_pose_angle": 45.0,
            "wrist": max(slices["wrist"]["width"], slices["wrist"]["depth"]) * math.pi,
            "armscye_depth": (slices["neck"]["z"] - slices["bust"]["z"]) * cm * 0.55,
            "shoulder_incl": 21.0,
            "hip_inclination": 9.0,
        }
    )

    shoulder = bone_world_point(armature, "CC_Base_L_Upperarm")
    hand = bone_world_point(armature, "CC_Base_L_Hand", tail=True)
    if shoulder is not None and hand is not None:
        measurements["arm_length"] = (shoulder - hand).length * cm

    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "assetslab_actor_garmentcode_measurements_v1",
        "source_actor": str(options.actor.resolve()),
        "source_object": actor.name,
        "frame": options.frame,
        "units": "centimetres",
        "method": "evaluated mesh horizontal slices with robust percentiles; design seed only",
        "world_bounds": {"min": list(low), "max": list(high)},
        "sections": slices,
        "body": measurements,
    }
    (output / "actor_v1_measurements.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_yaml_compatible_json(output / "actor_v1_body.yaml", measurements)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
