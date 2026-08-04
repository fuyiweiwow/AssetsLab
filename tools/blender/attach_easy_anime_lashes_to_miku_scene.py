"""Attach only Easy Anime Eye eyelashes to the accepted Miku-eye actor scene."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from render_easy_anime_eye_on_accurig import (  # noqa: E402
    LASH_FEATURE_NAMES,
    append_features,
    flat_material,
    make_camera,
    world_bounds,
)


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-blend", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target-object", default="MikuChibiEyeball")
    parser.add_argument("--lash-scale", type=float, default=0.92)
    parser.add_argument("--thickness-scale", type=float, default=1.0, help="Scale the lash band thickness along Z")
    parser.add_argument("--front-margin", type=float, default=0.012, help="Small clearance in front of the target eye surface")
    parser.add_argument("--top-margin", type=float, default=0.010, help="Small clearance below the target eye top edge")
    parser.add_argument("--vertical-offset", type=float, default=0.0, help="Move the aligned lash band along Z")
    parser.add_argument("--shrinkwrap", action="store_true", help="Project lashes onto the actor face along +Y")
    parser.add_argument("--shrinkwrap-offset", type=float, default=0.008)
    parser.add_argument("--raycast-conform", action="store_true", help="Conform every lash vertex to the actor front surface")
    parser.add_argument("--save-blend", action="store_true")
    return parser.parse_args(argv)


def parent_to_head_bone(obj: bpy.types.Object, armature: bpy.types.Object) -> None:
    matrix = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = "CC_Base_Head"
    obj.matrix_world = matrix


def adapt_lash_materials(objects: list[bpy.types.Object]) -> None:
    material = flat_material("EasyAnimeLashDark", (0.045, 0.008, 0.004, 1.0), 0.75)
    for obj in objects:
        obj.data.materials.clear()
        obj.data.materials.append(material)


def add_lights(scene: bpy.types.Scene, target: Vector) -> None:
    for location, energy, size in (
        ((0.0, -4.0, 5.0), 900.0, 4.0),
        ((-3.0, -2.0, 3.0), 350.0, 3.0),
    ):
        data = bpy.data.lights.new("EasyAnimeLashTestArea", "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new("EasyAnimeLashTestArea", data)
        scene.collection.objects.link(light)
        light.location = location
        light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()


def conform_to_actor_face(obj: bpy.types.Object, actor: bpy.types.Object, offset: float) -> None:
    modifier = obj.modifiers.new("EasyAnimeLashFaceConform", "SHRINKWRAP")
    modifier.target = actor
    modifier.wrap_method = "PROJECT"
    modifier.use_project_y = True
    modifier.use_positive_direction = True
    modifier.use_negative_direction = False
    modifier.offset = offset
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)


def conform_vertices_to_actor_face(obj: bpy.types.Object, actor: bpy.types.Object, offset: float) -> None:
    """Place each lash vertex just in front of the actor surface at its x/z."""
    actor_inverse = actor.matrix_world.inverted()
    object_inverse = obj.matrix_world.inverted()
    for vertex in obj.data.vertices:
        world = obj.matrix_world @ vertex.co
        origin_local = actor_inverse @ Vector((world.x, -2.0, world.z))
        direction_local = (actor_inverse.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
        hit, location, _normal, _face = actor.ray_cast(origin_local, direction_local)
        if not hit:
            continue
        surface = actor.matrix_world @ location
        world.y = surface.y - offset
        vertex.co = object_inverse @ world
    obj.data.update()


def main() -> int:
    options = cli_args()
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.open_mainfile(filepath=str(options.base_blend.resolve()))
    target = bpy.data.objects.get(options.target_object)
    actor = bpy.data.objects.get("ChibiBaseMesh_AccuRIG_InputMesh")
    armature = bpy.data.objects.get("Armature")
    if target is None or actor is None or armature is None:
        raise RuntimeError("base scene is missing MikuChibiEyeball, actor mesh, or Armature")

    lash_objects = append_features(options.source, LASH_FEATURE_NAMES)
    bpy.context.view_layer.update()
    original_matrices = {obj: obj.matrix_world.copy() for obj in lash_objects}
    for obj in lash_objects:
        obj.parent = None
        obj.matrix_world = original_matrices[obj]

    source_low, source_high = world_bounds(lash_objects)
    source_center = (source_low + source_high) * 0.5
    source_width = max(source_high.x - source_low.x, 1e-6)
    target_low, target_high = world_bounds([target])
    target_width = target_high.x - target_low.x
    scale = target_width / source_width * options.lash_scale
    # Align the two meaningful contact edges instead of matching bounding-box
    # centers: the source lash top belongs on the target eye's upper rim, and
    # the source lash front should sit just in front of the target eye surface.
    target_center = Vector(
        (
            (target_low.x + target_high.x) * 0.5,
            (target_low.y - options.front_margin) - (source_low.y - source_center.y) * scale,
            (target_high.z - options.top_margin)
            - (source_high.z - source_center.z) * scale * options.thickness_scale,
        )
    )
    target_center.z += options.vertical_offset
    transform = (
        Matrix.Translation(target_center)
        @ Matrix.Scale(scale, 4)
        @ Matrix.Scale(options.thickness_scale, 4, (0.0, 0.0, 1.0))
        @ Matrix.Translation(-source_center)
    )
    for obj in lash_objects:
        obj.matrix_world = transform @ original_matrices[obj]
        adapt_lash_materials([obj])
        if options.shrinkwrap:
            conform_to_actor_face(obj, actor, options.shrinkwrap_offset)
        if options.raycast_conform:
            conform_vertices_to_actor_face(obj, actor, options.shrinkwrap_offset)
        parent_to_head_bone(obj, armature)
        obj["assetslab_role"] = "easy_anime_lash_candidate"
        obj["source_object"] = obj.name

    actor_low, actor_high = world_bounds([actor])
    actor_center = (actor_low + actor_high) * 0.5
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = scene.render.resolution_y = 256
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("EasyAnimeLashTestWorld")
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
        "schema": "assetslab_easy_anime_lashes_on_miku_scene_v1",
        "base_blend": str(options.base_blend.resolve()),
        "source_blend": str(options.source.resolve()),
        "source_objects": list(LASH_FEATURE_NAMES),
        "target_object": options.target_object,
        "placement": {
            "lash_scale": options.lash_scale,
            "thickness_scale": options.thickness_scale,
            "front_margin": options.front_margin,
            "top_margin": options.top_margin,
            "vertical_offset": options.vertical_offset,
            "shrinkwrap": options.shrinkwrap,
            "shrinkwrap_offset": options.shrinkwrap_offset,
            "raycast_conform": options.raycast_conform,
            "derived_uniform_scale": scale,
        },
        "directions": list(cameras),
        "status": "static_four_direction_review_only",
    }
    (output / "feature_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if options.save_blend:
        blend_path = output / "easy_anime_lashes_on_miku_scene.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
        print(f"BLEND_SAVED {blend_path}")
    print(f"EASY_ANIME_LASHES_ON_MIKU_PASS output={output} scale={scale:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
