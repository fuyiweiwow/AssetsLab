"""Create a thin anime-style upper/lower eye socket arc for comparison."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from render_easy_anime_eye_on_accurig import flat_material, make_camera, world_bounds  # noqa: E402


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--eye-scale", type=float, default=0.9)
    parser.add_argument("--upper-width", type=float, default=0.026)
    parser.add_argument("--lower-width", type=float, default=0.009)
    parser.add_argument("--front-offset", type=float, default=0.008)
    parser.add_argument("--eye-inset", type=float, default=0.004)
    parser.add_argument("--save-blend", type=Path)
    return parser.parse_args(argv)


def face_y(actor: bpy.types.Object, x: float, z: float) -> float:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    hit, location, _normal, _index, _obj, _matrix = bpy.context.scene.ray_cast(
        depsgraph, Vector((x, -5.0, z)), Vector((0.0, 1.0, 0.0)), distance=15.0
    )
    return location.y if hit else -0.66


def eye_measurements(eye: bpy.types.Object, negative_x: bool, scale: float) -> tuple[float, float, float, float]:
    points = [eye.matrix_world @ vertex.co for vertex in eye.data.vertices]
    points = [point for point in points if (point.x < 0.0) == negative_x]
    low = Vector((min(point[i] for point in points) for i in range(3)))
    high = Vector((max(point[i] for point in points) for i in range(3)))
    return (low.x + high.x) * 0.5, (low.z + high.z) * 0.5, (high.x - low.x) * 0.5 * scale, (high.z - low.z) * 0.5 * scale


def make_arc(
    actor: bpy.types.Object,
    name: str,
    cx: float,
    cz: float,
    rx: float,
    rz: float,
    outer_sign: float,
    upper: bool,
    bevel: float,
    front_offset: float,
) -> bpy.types.Object:
    curve = bpy.data.curves.new(name + "Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = bevel
    curve.bevel_resolution = 0
    spline = curve.splines.new("POLY")
    count = 13
    spline.points.add(count - 1)
    for index, point in enumerate(spline.points):
        u = index / (count - 1)
        x = cx - outer_sign * (1.0 - u) * rx * 0.88 + outer_sign * u * rx
        if upper:
            z = cz + rz * (0.07 + 0.93 * math.sin(math.pi * u) ** 0.72)
        else:
            z = cz - rz * (0.03 + 0.62 * math.sin(math.pi * u) ** 0.82)
        point.co = (x, face_y(actor, x, z) - front_offset, z, 1.0)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(bpy.data.materials["MikuEyeSocketArcDark"])
    obj["assetslab_role"] = "miku_inspired_eye_socket_arc"
    obj["assetslab_upper"] = upper
    return obj


def main() -> int:
    options = cli_args()
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(options.base_blend.resolve()))
    actor = bpy.data.objects.get("ChibiBaseMesh_AccuRIG_InputMesh")
    eye = bpy.data.objects.get("MikuChibiEyeball")
    if actor is None or eye is None:
        raise RuntimeError("base blend is missing actor or MikuChibiEyeball")
    material = flat_material("MikuEyeSocketArcDark", (0.015, 0.008, 0.012, 1.0), 0.65)
    del material
    for name, negative_x, outer_sign in (("L", True, -1.0), ("R", False, 1.0)):
        cx, cz, rx, rz = eye_measurements(eye, negative_x, options.eye_scale)
        make_arc(actor, f"MikuEyeSocketArc.{name}.Upper", cx, cz, rx, rz, outer_sign, True, options.upper_width, options.front_offset)
        make_arc(actor, f"MikuEyeSocketArc.{name}.Lower", cx, cz, rx, rz, outer_sign, False, options.lower_width, options.front_offset)
    eye.location.y += options.eye_inset

    low, high = world_bounds([actor])
    target = Vector(((low.x + high.x) * 0.5, 0.0, 2.05))
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("MikuEyeSocketArcWorld")
    scene.world.color = (0.055, 0.055, 0.07)
    scene.view_settings.look = "None"
    camera_scale = max(2.9, high.z - low.z + 0.35)
    for direction, location in {"front": (0.0, -12.0, target.z), "right": (12.0, 0.0, target.z), "back": (0.0, 12.0, target.z), "left": (-12.0, 0.0, target.z)}.items():
        camera = make_camera(scene, target, f"MikuEyeSocketArcCamera.{direction}", location, camera_scale)
        scene.camera = camera
        scene.render.filepath = str(output / f"{direction}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)
    if options.save_blend:
        options.save_blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(options.save_blend.resolve()))
    (output / "manifest.json").write_text(json.dumps({"schema":"assetslab_miku_eye_socket_arc_on_accurig_v1","base_blend":str(options.base_blend.resolve()),"eye_scale":options.eye_scale,"upper_width":options.upper_width,"lower_width":options.lower_width,"front_offset":options.front_offset,"eye_inset":options.eye_inset,"status":"visual_layer_proof_only"}, indent=2), encoding="utf-8")
    print(f"MIKU_EYE_SOCKET_ARC_PASS output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
