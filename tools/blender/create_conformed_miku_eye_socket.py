"""Conform Miku's original eye-socket mesh to the actor's head surface.

This test keeps the actor head and body intact.  It imports only Miku's
eye_007 eyelid/socket mesh, projects its front boundary onto the actor head,
and parents it to the actor head bone.  The existing Miku eyeballs remain as
the eye volume behind the socket.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-blend", required=True, type=Path)
    parser.add_argument("--miku-fbx", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--save-blend", required=True, type=Path)
    parser.add_argument("--socket-scale", type=float, default=1.08)
    parser.add_argument("--front-offset", type=float, default=0.012)
    parser.add_argument("--eye-recess", type=float, default=0.025)
    parser.add_argument("--keep-source-material", action="store_true")
    parser.add_argument("--eevee", action="store_true")
    return parser.parse_args(argv)


def bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    return (
        Vector((min(point[i] for point in points) for i in range(3))),
        Vector((max(point[i] for point in points) for i in range(3))),
    )


def remove_object(obj: bpy.types.Object) -> None:
    bpy.data.objects.remove(obj, do_unlink=True)


def clean_previous_socket_objects() -> None:
    prefixes = (
        "MikuEyeSocket",
        "eye_007_22_0_node",
    )
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefixes):
            remove_object(obj)
        elif obj.type == "ARMATURE" and obj.name.startswith("Armature."):
            remove_object(obj)


def actor_face_y(actor: bpy.types.Object, x: float, z: float, fallback: float) -> float:
    """Raycast only against the actor mesh, avoiding eye-object occlusion."""
    inverse = actor.matrix_world.inverted()
    origin_world = Vector((x, -10.0, z))
    direction_world = Vector((0.0, 1.0, 0.0))
    origin_local = inverse @ origin_world
    direction_local = (inverse.to_3x3() @ direction_world).normalized()
    hit, location, _normal, _face_index = actor.ray_cast(origin_local, direction_local, distance=30.0)
    if hit:
        return (actor.matrix_world @ location).y
    return fallback


def parent_to_head(obj: bpy.types.Object, rig: bpy.types.Object) -> None:
    world = obj.matrix_world.copy()
    obj.parent = rig
    obj.parent_type = "BONE"
    obj.parent_bone = "CC_Base_Head"
    obj.matrix_world = world


def import_socket(source: Path) -> bpy.types.Object:
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=str(source.resolve()), automatic_bone_orientation=False)
    imported = [obj for obj in bpy.context.scene.objects if obj not in before]
    socket = next((obj for obj in imported if obj.name == "eye_007_22_0_node"), None)
    if socket is None:
        socket = next((obj for obj in imported if obj.name.startswith("eye_007_22_0_node")), None)
    if socket is None:
        raise RuntimeError("Miku FBX does not contain eye_007_22_0_node")

    # Detach from the source armature and preserve its rest-pose world matrix.
    world = socket.matrix_world.copy()
    socket.parent = None
    socket.matrix_world = world
    for modifier in list(socket.modifiers):
        socket.modifiers.remove(modifier)
    for obj in imported:
        if obj is not socket:
            remove_object(obj)
    socket.name = "MikuEyeSocket_Conformed"
    return socket


def transform_and_project(socket: bpy.types.Object, actor: bpy.types.Object, eye: bpy.types.Object, scale_factor: float, front_offset: float) -> dict[str, float]:
    source_low, source_high = bounds([socket])
    eye_low, eye_high = bounds([eye])
    source_center = (source_low + source_high) * 0.5
    target_center = (eye_low + eye_high) * 0.5
    source_width = source_high.x - source_low.x
    target_width = (eye_high.x - eye_low.x) * scale_factor
    scale = target_width / source_width
    transform = Matrix.Translation(target_center) @ Matrix.Scale(scale, 4) @ Matrix.Translation(-source_center)
    socket.matrix_world = transform @ socket.matrix_world

    projected_points: list[Vector] = []
    projected_low_y = bounds([socket])[0].y
    actor_low, _actor_high = bounds([actor])
    for vertex in socket.data.vertices:
        world = socket.matrix_world @ vertex.co
        face_y = actor_face_y(actor, world.x, world.z, actor_low.y)
        # Preserve the source mesh's shallow depth.  Its front boundary lies
        # on the actor face, while the rear portion goes inward (+Y), creating
        # an occluding eyelid volume rather than a flat decal.
        depth = max(0.0, world.y - projected_low_y)
        world.y = face_y - front_offset + depth
        projected_points.append(socket.matrix_world.inverted() @ world)
    for vertex, point in zip(socket.data.vertices, projected_points):
        vertex.co = point
    socket.data.update()
    return {
        "uniform_scale": scale,
        "source_width": source_width,
        "target_width": target_width,
        "front_offset": front_offset,
    }


def set_skin_material(socket: bpy.types.Object, actor: bpy.types.Object, keep_source_material: bool) -> None:
    if keep_source_material and socket.data.materials:
        return
    skin = next((material for material in actor.data.materials if material), None)
    if skin is None:
        skin = bpy.data.materials.new("ActorSkinForMikuEyeSocket")
        skin.diffuse_color = (0.72, 0.42, 0.32, 1.0)
    socket.data.materials.clear()
    socket.data.materials.append(skin)
    socket["assetslab_role"] = "conformed_miku_eye_socket"
    socket["assetslab_source"] = "Miku eye_007_22_0_node"
    socket["assetslab_method"] = "actor_surface_projection_with_preserved_depth"


def render(scene: bpy.types.Scene, eye: bpy.types.Object, output: Path, eevee: bool) -> None:
    scene.render.engine = "BLENDER_EEVEE_NEXT" if eevee else "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    if not eevee:
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "MATERIAL"
        scene.display.shading.show_shadows = True
        scene.display.shading.show_cavity = True
        scene.display.shading.cavity_type = "BOTH"
    else:
        scene.render.film_transparent = False
        if scene.world is None:
            scene.world = bpy.data.worlds.new("ConformedMikuEyeWorld")
        scene.world.color = (0.035, 0.035, 0.05)
        for index, (location, energy, size) in enumerate(
            (((0.0, -4.0, 5.0), 700.0, 4.0), ((-3.0, -2.0, 2.0), 350.0, 3.0))
        ):
            light_data = bpy.data.lights.new(f"ConformedMikuEyeLight{index}", "AREA")
            light_data.energy = energy
            light_data.shape = "DISK"
            light_data.size = size
            light = bpy.data.objects.new(f"ConformedMikuEyeLight{index}", light_data)
            bpy.context.collection.objects.link(light)
            light.location = location
    eye_low, eye_high = bounds([eye])
    target = (eye_low + eye_high) * 0.5
    for direction, position in (
        ("front", target + Vector((0.0, -10.0, 0.0))),
        ("right", target + Vector((10.0, 0.0, 0.0))),
    ):
        camera_data = bpy.data.cameras.new(f"ConformedMikuEyeCamera_{direction}")
        camera_data.type = "ORTHO"
        camera_data.ortho_scale = 2.15
        camera = bpy.data.objects.new(f"ConformedMikuEyeCamera_{direction}", camera_data)
        bpy.context.collection.objects.link(camera)
        camera.location = position
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
    clean_previous_socket_objects()
    actor = bpy.data.objects.get("ChibiBaseMesh_AccuRIG_InputMesh")
    eye = bpy.data.objects.get("MikuChibiEyeball")
    rig = bpy.data.objects.get("Armature")
    if actor is None or eye is None or rig is None:
        raise RuntimeError("base blend must contain actor, MikuChibiEyeball, and Armature")

    socket = import_socket(options.miku_fbx)
    fit = transform_and_project(socket, actor, eye, options.socket_scale, options.front_offset)
    set_skin_material(socket, actor, options.keep_source_material)
    parent_to_head(socket, rig)
    parent_to_head(eye, rig)

    render(bpy.context.scene, eye, output, options.eevee)
    manifest = {
        "schema": "assetslab_conformed_miku_eye_socket_v1",
        "base_blend": str(options.base_blend.resolve()),
        "miku_fbx": str(options.miku_fbx.resolve()),
        "socket_object": socket.name,
        "eye_object": eye.name,
        "parent_bone": "CC_Base_Head",
        "fit": fit,
        "removed": ["previous Miku socket tests", "Miku source armatures and accessory meshes"],
        "status": "conformed_socket_review_candidate",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    options.save_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.save_blend.resolve()))
    print(f"CONFORMED_MIKU_SOCKET_PASS output={output}")
    print(json.dumps(fit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
