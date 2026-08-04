"""Build an almond-shaped, shallow eye-socket shell on the actor head.

The socket is a small conforming shell rather than a black decal or a full
elliptical ring.  The outer/inner loops follow the actor head by raycast, the
front rim uses skin material, and the inner wall uses a subdued socket-shadow
material.  The eye opening remains visible through the shell.
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
    parser.add_argument("--rim-front", type=float, default=0.035)
    parser.add_argument("--inner-depth", type=float, default=0.022)
    return parser.parse_args(argv)


def bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    return Vector((min(p[i] for p in points) for i in range(3))), Vector((max(p[i] for p in points) for i in range(3)))


def remove_object(obj: bpy.types.Object) -> None:
    bpy.data.objects.remove(obj, do_unlink=True)


def clean_old_objects() -> None:
    prefixes = ("MikuEyeSocket", "eye_007_22_0_node")
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefixes):
            remove_object(obj)
        elif obj.type == "ARMATURE" and obj.name.startswith("Armature."):
            remove_object(obj)


def face_y(actor: bpy.types.Object, x: float, z: float, fallback: float) -> float:
    inv = actor.matrix_world.inverted()
    origin = inv @ Vector((x, -10.0, z))
    direction = (inv.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
    hit, location, _normal, _index = actor.ray_cast(origin, direction, distance=30.0)
    return (actor.matrix_world @ location).y if hit else fallback


def material(name: str, color: tuple[float, float, float, float], roughness: float = 0.8) -> bpy.types.Material:
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


def shrink_eyes(eye: bpy.types.Object, scale: float, outward: float) -> None:
    low, high = bounds([eye])
    center_z = (low.z + high.z) * 0.5
    left_points = [eye.matrix_world @ v.co for v in eye.data.vertices if (eye.matrix_world @ v.co).x < 0.0]
    right_points = [eye.matrix_world @ v.co for v in eye.data.vertices if (eye.matrix_world @ v.co).x >= 0.0]
    centers = {
        "L": sum((p.x for p in left_points), 0.0) / len(left_points),
        "R": sum((p.x for p in right_points), 0.0) / len(right_points),
    }
    inv = eye.matrix_world.inverted()
    for vertex in eye.data.vertices:
        world = eye.matrix_world @ vertex.co
        side = "L" if world.x < 0.0 else "R"
        cx = centers[side]
        world.x = cx + (world.x - cx) * scale
        world.z = center_z + (world.z - center_z) * scale
        world.x += -outward if side == "L" else outward
        world.y += 0.018
        vertex.co = inv @ world
    eye.data.update()


def create_socket(
    actor: bpy.types.Object,
    eye: bpy.types.Object,
    rig: bpy.types.Object,
    side: str,
    rim_front: float,
    inner_depth: float,
    skin: bpy.types.Material,
    shadow: bpy.types.Material,
) -> bpy.types.Object:
    points = [eye.matrix_world @ v.co for v in eye.data.vertices if (eye.matrix_world @ v.co).x < 0.0] if side == "L" else [eye.matrix_world @ v.co for v in eye.data.vertices if (eye.matrix_world @ v.co).x >= 0.0]
    low = Vector((min(p[i] for p in points) for i in range(3)))
    high = Vector((max(p[i] for p in points) for i in range(3)))
    cx = (low.x + high.x) * 0.5
    cz = (low.z + high.z) * 0.5
    rx = (high.x - low.x) * 0.5 + 0.055
    rz_top = (high.z - low.z) * 0.5 + 0.035
    rz_bottom = (high.z - low.z) * 0.5 * 0.72 + 0.025
    inner_rx = max(rx - 0.052, rx * 0.82)
    inner_top = max(rz_top - 0.055, rz_top * 0.80)
    inner_bottom = max(rz_bottom - 0.042, rz_bottom * 0.75)
    fallback = bounds([actor])[0].y
    segments = 28
    vertices: list[tuple[float, float, float]] = []
    # outer front, inner front, inner rear; the hole stays open for the eye.
    for ring in range(3):
        for i in range(segments):
            t = 2.0 * math.pi * i / segments
            c = math.cos(t)
            s = math.sin(t)
            if ring == 0:
                r_x, r_top, r_bottom, y_offset = rx, rz_top, rz_bottom, -rim_front
            elif ring == 1:
                r_x, r_top, r_bottom, y_offset = inner_rx, inner_top, inner_bottom, -rim_front * 0.48
            else:
                r_x, r_top, r_bottom, y_offset = inner_rx, inner_top, inner_bottom, inner_depth
            z_radius = r_top if s >= 0.0 else r_bottom
            x = cx + c * r_x
            z = cz + s * z_radius
            y = face_y(actor, x, z, fallback) + y_offset
            vertices.append((x, y, z))
    faces: list[tuple[int, ...]] = []
    mats: list[int] = []
    for i in range(segments):
        n = (i + 1) % segments
        faces.append((i, n, segments + n, segments + i))
        mats.append(0)
        faces.append((segments + i, segments + n, 2 * segments + n, 2 * segments + i))
        mats.append(1)
    mesh = bpy.data.meshes.new(f"MikuStyleEyeSocket_{side}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(f"MikuEyeSocket.{side}", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(skin)
    obj.data.materials.append(shadow)
    for poly, index in zip(mesh.polygons, mats):
        poly.material_index = index
        poly.use_smooth = True
    parent_to_head(obj, rig)
    obj["assetslab_role"] = "anime_eye_socket_shell"
    obj["assetslab_method"] = "almond_open_shell_conformed_to_actor_head"
    return obj


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
        data = bpy.data.cameras.new(f"MikuStyleSocketCamera_{direction}")
        data.type = "ORTHO"
        data.ortho_scale = 2.05
        camera = bpy.data.objects.new(f"MikuStyleSocketCamera_{direction}", data)
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
    clean_old_objects()
    actor = bpy.data.objects.get("ChibiBaseMesh_AccuRIG_InputMesh")
    eye = bpy.data.objects.get("MikuChibiEyeball")
    rig = bpy.data.objects.get("Armature")
    if actor is None or eye is None or rig is None:
        raise RuntimeError("base blend must contain actor, MikuChibiEyeball, and Armature")
    shrink_eyes(eye, options.eye_scale, options.eye_outward)
    skin = next((m for m in actor.data.materials if m), material("ActorSkinForSocket", (0.72, 0.42, 0.32, 1.0)))
    shadow = material("AnimeEyeSocketInnerShadow", (0.16, 0.035, 0.04, 1.0), 0.9)
    sockets = [
        create_socket(actor, eye, rig, "L", options.rim_front, options.inner_depth, skin, shadow),
        create_socket(actor, eye, rig, "R", options.rim_front, options.inner_depth, skin, shadow),
    ]
    parent_to_head(eye, rig)
    render(bpy.context.scene, eye, output)
    manifest = {
        "schema": "assetslab_anime_eye_socket_shell_v1",
        "base_blend": str(options.base_blend.resolve()),
        "objects": [obj.name for obj in sockets],
        "parent_bone": "CC_Base_Head",
        "parameters": {"eye_scale": options.eye_scale, "eye_outward": options.eye_outward, "rim_front": options.rim_front, "inner_depth": options.inner_depth},
        "status": "review_candidate",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    options.save_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.save_blend.resolve()))
    print(f"ANIME_SOCKET_SHELL_PASS output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
