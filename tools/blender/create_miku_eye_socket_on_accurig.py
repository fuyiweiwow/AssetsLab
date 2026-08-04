"""Create a Miku-inspired eye socket ring on the actor for visual testing."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

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
    parser.add_argument("--socket-width", type=float, default=1.08)
    parser.add_argument("--socket-height", type=float, default=1.05)
    parser.add_argument("--rim-width", type=float, default=0.055)
    parser.add_argument("--front-offset", type=float, default=0.018)
    parser.add_argument("--eye-inset", type=float, default=0.012)
    parser.add_argument("--save-blend", type=Path)
    return parser.parse_args(argv)


def raycast_face(actor: bpy.types.Object, x: float, z: float, front_y: float = -5.0) -> float:
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    hit, location, _normal, _index, obj, _matrix = scene.ray_cast(
        depsgraph, Vector((x, front_y, z)), Vector((0.0, 1.0, 0.0)), distance=15.0
    )
    if hit:
        return location.y
    # Fallback for a very small missed ray at the eye edge.
    return -0.66


def create_ring(
    actor: bpy.types.Object,
    eye: bpy.types.Object,
    side_name: str,
    side_negative_x: bool,
    socket_width: float,
    socket_height: float,
    rim_width: float,
    front_offset: float,
) -> bpy.types.Object:
    points = [eye.matrix_world @ vertex.co for vertex in eye.data.vertices]
    points = [point for point in points if (point.x < 0.0) == side_negative_x]
    if not points:
        raise RuntimeError(f"could not find {side_name} eye vertices")
    low = Vector((min(point[i] for point in points) for i in range(3)))
    high = Vector((max(point[i] for point in points) for i in range(3)))
    center_x = (low.x + high.x) * 0.5
    center_z = (low.z + high.z) * 0.5
    rx = (high.x - low.x) * 0.5 * socket_width
    rz = (high.z - low.z) * 0.5 * socket_height
    inner_rx = max(rx - rim_width, rx * 0.72)
    inner_rz = max(rz - rim_width, rz * 0.72)

    vertices: list[tuple[float, float, float]] = []
    segments = 40
    for radius_x, radius_z in ((rx, rz), (inner_rx, inner_rz)):
        for index in range(segments):
            angle = 2.0 * math.pi * index / segments
            x = center_x + math.cos(angle) * radius_x
            z = center_z + math.sin(angle) * radius_z
            y = raycast_face(actor, x, z) - front_offset
            vertices.append((x, y, z))

    faces = []
    for index in range(segments):
        next_index = (index + 1) % segments
        faces.append((index, next_index, segments + next_index, segments + index))
    mesh = bpy.data.meshes.new(f"MikuEyeSocket_{side_name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(f"MikuEyeSocket.{side_name}", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(flat_material("MikuEyeSocketDarkRim", (0.015, 0.008, 0.012, 1.0), 0.65))
    obj["assetslab_role"] = "miku_inspired_eye_socket_ring"
    obj["assetslab_source"] = "Miku eye_007_22_0_node silhouette"
    obj["assetslab_side"] = side_name
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

    rings = [
        create_ring(actor, eye, "L", True, options.socket_width, options.socket_height, options.rim_width, options.front_offset),
        create_ring(actor, eye, "R", False, options.socket_width, options.socket_height, options.rim_width, options.front_offset),
    ]

    # Move the eye layer a small amount inward (+Y). The ring stays in front and hides the outer rim.
    eye.location.y += options.eye_inset
    actor_low, actor_high = world_bounds([actor])
    target = Vector(((actor_low.x + actor_high.x) * 0.5, 0.0, 2.05))
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("MikuEyeSocketWorld")
    scene.world.color = (0.055, 0.055, 0.07)
    scene.view_settings.look = "None"
    camera_specs = {
        "front": (0.0, -12.0, target.z),
        "right": (12.0, 0.0, target.z),
        "back": (0.0, 12.0, target.z),
        "left": (-12.0, 0.0, target.z),
    }
    camera_scale = max(2.9, actor_high.z - actor_low.z + 0.35)
    for direction, location in camera_specs.items():
        camera = make_camera(scene, target, f"MikuEyeSocketCamera.{direction}", location, camera_scale)
        scene.camera = camera
        scene.render.filepath = str(output / f"{direction}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)

    if options.save_blend:
        options.save_blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(options.save_blend.resolve()))
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "assetslab_miku_eye_socket_on_accurig_v1",
                "base_blend": str(options.base_blend.resolve()),
                "socket_width": options.socket_width,
                "socket_height": options.socket_height,
                "rim_width": options.rim_width,
                "front_offset": options.front_offset,
                "eye_inset": options.eye_inset,
                "status": "visual_layer_proof_only",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"MIKU_EYE_SOCKET_PASS output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
