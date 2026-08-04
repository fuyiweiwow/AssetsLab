"""Create an open almond-style eye socket on the original actor head.

Unlike a closed ring, this test only creates the upper lid, a short lower lid,
and a tapered outer-corner extension.  The strips are projected to the actor
head surface and parented to CC_Base_Head.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--save-blend", required=True, type=Path)
    parser.add_argument("--eye-scale", type=float, default=0.86)
    parser.add_argument("--eye-outward", type=float, default=0.035)
    parser.add_argument("--upper-width", type=float, default=0.052)
    parser.add_argument("--lower-width", type=float, default=0.022)
    parser.add_argument("--front-offset", type=float, default=0.018)
    return parser.parse_args(argv)


def bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    return Vector((min(p[i] for p in points) for i in range(3))), Vector((max(p[i] for p in points) for i in range(3)))


def remove_object(obj: bpy.types.Object) -> None:
    bpy.data.objects.remove(obj, do_unlink=True)


def clean_old_socket_objects() -> None:
    prefixes = ("MikuEyeSocket", "MikuOpenEye", "eye_007_22_0_node")
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefixes):
            remove_object(obj)
        elif obj.type == "ARMATURE" and obj.name.startswith("Armature."):
            remove_object(obj)


def raycast_face(actor: bpy.types.Object, x: float, z: float, fallback: float) -> float:
    inverse = actor.matrix_world.inverted()
    origin = inverse @ Vector((x, -10.0, z))
    direction = (inverse.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
    hit, location, _normal, _index = actor.ray_cast(origin, direction, distance=30.0)
    return (actor.matrix_world @ location).y if hit else fallback


def make_material(name: str, color: tuple[float, float, float, float], roughness: float = 0.75) -> bpy.types.Material:
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    if shader:
        shader.inputs["Base Color"].default_value = color
        shader.inputs["Roughness"].default_value = roughness
    return mat


def parent_to_head(obj: bpy.types.Object, rig: bpy.types.Object) -> None:
    world = obj.matrix_world.copy()
    obj.parent = rig
    obj.parent_type = "BONE"
    obj.parent_bone = "CC_Base_Head"
    obj.matrix_world = world


def shrink_and_space_eyes(eye: bpy.types.Object, scale: float, outward: float) -> None:
    points = [eye.matrix_world @ vertex.co for vertex in eye.data.vertices]
    center_z = sum(point.z for point in points) / len(points)
    left = [point for point in points if point.x < 0.0]
    right = [point for point in points if point.x >= 0.0]
    centers = {
        "L": sum(point.x for point in left) / len(left),
        "R": sum(point.x for point in right) / len(right),
    }
    inverse = eye.matrix_world.inverted()
    for vertex in eye.data.vertices:
        world = eye.matrix_world @ vertex.co
        side = "L" if world.x < 0.0 else "R"
        cx = centers[side]
        world.x = cx + (world.x - cx) * scale
        world.z = center_z + (world.z - center_z) * scale
        world.x += -outward if side == "L" else outward
        vertex.co = inverse @ world
    eye.data.update()


def make_strip(
    actor: bpy.types.Object,
    rig: bpy.types.Object,
    side: str,
    name: str,
    points: list[tuple[float, float, float]],
    width: float,
    material: bpy.types.Material,
    front_offset: float,
    fallback_y: float,
) -> bpy.types.Object:
    vertices: list[tuple[float, float, float]] = []
    for x, z, offset in points:
        y = raycast_face(actor, x, z, fallback_y) - front_offset
        vertices.append((x, y, z + width * 0.5 + offset))
        vertices.append((x, y - 0.004, z - width * 0.5 + offset))
    faces = [(i * 2, i * 2 + 1, (i + 1) * 2 + 1, (i + 1) * 2) for i in range(len(points) - 1)]
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    parent_to_head(obj, rig)
    obj["assetslab_role"] = "open_anime_eye_socket_lid"
    obj["assetslab_side"] = side
    return obj


def create_eye_parts(actor: bpy.types.Object, eye: bpy.types.Object, rig: bpy.types.Object, side: str, upper_width: float, lower_width: float, front_offset: float, dark: bpy.types.Material) -> list[bpy.types.Object]:
    points = [eye.matrix_world @ vertex.co for vertex in eye.data.vertices if (eye.matrix_world @ vertex.co).x < 0.0] if side == "L" else [eye.matrix_world @ vertex.co for vertex in eye.data.vertices if (eye.matrix_world @ vertex.co).x >= 0.0]
    low = Vector((min(p[i] for p in points) for i in range(3)))
    high = Vector((max(p[i] for p in points) for i in range(3)))
    cx = (low.x + high.x) * 0.5
    cz = (low.z + high.z) * 0.5
    rx = (high.x - low.x) * 0.5 + 0.035
    top = (high.z - low.z) * 0.5 + 0.025
    bottom = (high.z - low.z) * 0.5 * 0.64
    inner_is_left = side == "R"
    fallback_y = raycast_face(actor, cx, cz, bounds([actor])[0].y)
    samples = 18
    upper: list[tuple[float, float, float]] = []
    lower: list[tuple[float, float, float]] = []
    for index in range(samples):
        u = index / (samples - 1)
        x = cx - rx + 2.0 * rx * u
        if inner_is_left:
            x = cx + rx - 2.0 * rx * u
        arch = max(0.0, math.sin(math.pi * u)) ** 0.62
        outer_drop = 0.035 * (1.0 - u if not inner_is_left else u)
        z_upper = cz + top * arch - outer_drop
        upper.append((x, z_upper, 0.0))
        if u <= 0.68:
            lower_arch = max(0.0, math.sin(math.pi * (u / 0.68))) ** 0.75
            z_lower = cz - bottom * lower_arch - 0.015
            lower.append((x, z_lower, 0.0))
    parts = [make_strip(actor, rig, side, f"MikuOpenEyeUpper.{side}", upper, upper_width, dark, front_offset, fallback_y)]
    parts.append(make_strip(actor, rig, side, f"MikuOpenEyeLower.{side}", lower, lower_width, dark, front_offset + 0.003, fallback_y))
    return parts


def render(scene: bpy.types.Scene, eye: bpy.types.Object, output: Path) -> None:
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    low, high = bounds([eye])
    target = (low + high) * 0.5
    for direction, location in (("front", target + Vector((0, -10, 0))), ("right", target + Vector((10, 0, 0)))):
        data = bpy.data.cameras.new(f"MikuOpenEyeCamera_{direction}")
        data.type = "ORTHO"
        data.ortho_scale = 2.05
        camera = bpy.data.objects.new(f"MikuOpenEyeCamera_{direction}", data)
        bpy.context.collection.objects.link(camera)
        camera.location = location
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.camera = camera
        scene.render.filepath = str(output / f"{direction}.png")
        bpy.ops.render.render(write_still=True)
        remove_object(camera)


def main() -> int:
    options = cli_args()
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(options.base_blend.resolve()))
    clean_old_socket_objects()
    actor = bpy.data.objects.get("ChibiBaseMesh_AccuRIG_InputMesh")
    eye = bpy.data.objects.get("MikuChibiEyeball")
    rig = bpy.data.objects.get("Armature")
    if actor is None or eye is None or rig is None:
        raise RuntimeError("base blend must contain actor, MikuChibiEyeball, and Armature")
    shrink_and_space_eyes(eye, options.eye_scale, options.eye_outward)
    dark = make_material("MikuOpenEyeLidDark", (0.035, 0.012, 0.018, 1.0), 0.65)
    parts = []
    for side in ("L", "R"):
        parts.extend(create_eye_parts(actor, eye, rig, side, options.upper_width, options.lower_width, options.front_offset, dark))
    parent_to_head(eye, rig)
    render(bpy.context.scene, eye, output)
    manifest = {
        "schema": "assetslab_open_anime_eye_socket_v1",
        "base_blend": str(options.base_blend.resolve()),
        "parts": [part.name for part in parts],
        "parent_bone": "CC_Base_Head",
        "parameters": {"eye_scale": options.eye_scale, "eye_outward": options.eye_outward, "upper_width": options.upper_width, "lower_width": options.lower_width, "front_offset": options.front_offset},
        "status": "review_candidate",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    options.save_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.save_blend.resolve()))
    print(f"OPEN_ANIME_SOCKET_PASS output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
