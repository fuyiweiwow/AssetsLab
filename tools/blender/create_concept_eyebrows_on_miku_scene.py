"""Create simple concept-art eyebrows and attach them to the Miku-eye actor scene."""

from __future__ import annotations

import argparse
import json
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
    parser.add_argument("--brow-width", type=float, default=0.34)
    parser.add_argument("--brow-separation", type=float, default=0.62)
    parser.add_argument("--brow-z", type=float, default=2.22)
    parser.add_argument("--arc-height", type=float, default=0.040)
    parser.add_argument("--thickness", type=float, default=0.018)
    parser.add_argument("--front-offset", type=float, default=0.012)
    parser.add_argument("--save-blend", action="store_true")
    return parser.parse_args(argv)


def actor_surface_y(actor: bpy.types.Object, x: float, z: float, fallback: float) -> float:
    inverse = actor.matrix_world.inverted()
    origin = inverse @ Vector((x, -2.0, z))
    direction = (inverse.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
    hit, location, _normal, _face = actor.ray_cast(origin, direction)
    if not hit:
        return fallback
    return (actor.matrix_world @ location).y


def make_brow(
    name: str,
    center_x: float,
    z: float,
    width: float,
    arc_height: float,
    thickness: float,
    actor: bpy.types.Object,
    front_offset: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    curve = bpy.data.curves.new(name + "Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = thickness
    curve.bevel_resolution = 0
    curve.resolution_v = 0
    curve.fill_mode = "FULL"
    spline = curve.splines.new("POLY")
    points = (-0.5, -0.28, 0.0, 0.28, 0.5)
    heights = (0.0, arc_height * 0.65, arc_height, arc_height * 0.72, arc_height * 0.12)
    spline.points.add(len(points) - 1)
    face_fallback = -0.70
    for spline_point, position, height in zip(spline.points, points, heights):
        x = center_x + position * width
        spline_point.co = (x, actor_surface_y(actor, x, z + height, face_fallback) - front_offset, z + height, 1.0)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj["assetslab_role"] = "concept_eyebrow_candidate"
    obj["source_reference"] = "front-character-anchor.png"
    return obj


def parent_to_head(obj: bpy.types.Object, armature: bpy.types.Object) -> None:
    matrix = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = "CC_Base_Head"
    obj.matrix_world = matrix


def add_lights(scene: bpy.types.Scene, target: Vector) -> None:
    for location, energy, size in (((0.0, -4.0, 5.0), 900.0, 4.0), ((-3.0, -2.0, 3.0), 350.0, 3.0)):
        data = bpy.data.lights.new("ConceptEyebrowArea", "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new("ConceptEyebrowArea", data)
        scene.collection.objects.link(light)
        light.location = location
        light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()


def main() -> int:
    options = cli_args()
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(options.base_blend.resolve()))
    actor = bpy.data.objects.get("ChibiBaseMesh_AccuRIG_InputMesh")
    armature = bpy.data.objects.get("Armature")
    if actor is None or armature is None:
        raise RuntimeError("base scene is missing actor or Armature")

    material = flat_material("ConceptEyebrowDark", (0.018, 0.006, 0.004, 1.0), 0.8)
    brows = [
        make_brow("ConceptEyebrow.L", -options.brow_separation * 0.5, options.brow_z, options.brow_width, options.arc_height, options.thickness, actor, options.front_offset, material),
        make_brow("ConceptEyebrow.R", options.brow_separation * 0.5, options.brow_z, options.brow_width, options.arc_height, options.thickness, actor, options.front_offset, material),
    ]
    for brow in brows:
        parent_to_head(brow, armature)

    actor_low, actor_high = world_bounds([actor])
    actor_center = (actor_low + actor_high) * 0.5
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = scene.render.resolution_y = 256
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("ConceptEyebrowWorld")
    scene.world.color = (0.06, 0.06, 0.08)
    add_lights(scene, actor_center)
    cameras = {
        "front": (0.0, -12.0, actor_center.z),
        "right": (12.0, 0.0, actor_center.z),
        "back": (0.0, 12.0, actor_center.z),
        "left": (-12.0, 0.0, actor_center.z),
    }
    for direction, location in cameras.items():
        camera = make_camera(scene, actor_center, direction, location, max(4.0, actor_high.z - actor_low.z + 0.6))
        scene.camera = camera
        scene.render.filepath = str(output / f"{direction}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)

    manifest = {
        "schema": "assetslab_concept_eyebrows_on_miku_scene_v1",
        "base_blend": str(options.base_blend.resolve()),
        "reference_image": "front-character-anchor.png",
        "objects": [brow.name for brow in brows],
        "parameters": {
            "brow_width": options.brow_width,
            "brow_separation": options.brow_separation,
            "brow_z": options.brow_z,
            "arc_height": options.arc_height,
            "thickness": options.thickness,
            "front_offset": options.front_offset,
        },
        "directions": list(cameras),
        "status": "static_four_direction_review_only",
    }
    (output / "feature_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if options.save_blend:
        blend_path = output / "concept_eyebrows_on_miku_scene.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
        print(f"BLEND_SAVED {blend_path}")
    print(f"CONCEPT_EYEBROWS_PASS output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
