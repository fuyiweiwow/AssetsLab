"""Build a derived 3D eye-blink experiment from the Actor V1 blend.

The actor already contains imagegen-derived open-eye textures on shallow eye
lenses. This experiment adds head-bone-parented eyelid covers and bakes a
deterministic blink sequence into the derived Blend. It deliberately does not
write pixel frames or modify the retained Actor V1 baseline.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector


HEAD_BONE = "CC_Base_Head"
LENS_NAMES = ("EyePackageV1_Lens_L", "EyePackageV1_Lens_R")


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-blend", type=Path, required=True)
    parser.add_argument("--output-blend", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--closed-left-texture", type=Path, required=True)
    parser.add_argument("--closed-right-texture", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260805)
    parser.add_argument("--interval-min", type=float, default=2.5)
    parser.add_argument("--interval-max", type=float, default=5.0)
    parser.add_argument("--closed-frames", type=int, default=2)
    parser.add_argument("--half-frames", type=int, default=1)
    parser.add_argument("--preview-frames", type=int, default=0)
    return parser.parse_args(argv)


def set_constant_interpolation(obj: bpy.types.Object) -> None:
    if obj.animation_data is None or obj.animation_data.action is None:
        return
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = "CONSTANT"


def key_state(obj: bpy.types.Object, frame: int, visible: bool, scale_z: float) -> None:
    obj.hide_render = not visible
    obj.hide_viewport = not visible
    obj.keyframe_insert(data_path="hide_render", frame=frame)
    obj.keyframe_insert(data_path="hide_viewport", frame=frame)


def duplicate_lid(source: bpy.types.Object, material: bpy.types.Material) -> bpy.types.Object:
    lid = source.copy()
    lid.data = source.data.copy()
    lid.name = source.name.replace("EyePackageV1_Lens_", "EyeBlinkV1_ClosedTexture_")
    lid.data.name = lid.name + "Mesh"
    lid.data.materials.clear()
    lid.data.materials.append(material)
    bpy.context.collection.objects.link(lid)

    # The source eye is already parented to the head bone. Keep that contract
    # and move the closed texture a few millimetres toward the front camera.
    # Object.copy() retains the source's armature parent and local transform.
    # Offset the object in parent-local space so the source Shrinkwrap can
    # continue to follow the animated head surface.
    offset_local = source.matrix_world.to_3x3().inverted() @ Vector((0.0, -0.090, 0.0))
    lid.location += offset_local
    lid["assetslab_layer"] = "Face/Eyes"
    lid["assetslab_role"] = "eye_blink_3d_closed_texture"
    lid["assetslab_source"] = source.name
    return lid


def make_texture_material(name: str, texture_path: Path) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    if hasattr(material, "surface_render_method"):
        material.surface_render_method = "DITHERED"
    if hasattr(material, "blend_method"):
        material.blend_method = "HASHED"
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = bpy.data.images.load(str(texture_path.resolve()), check_existing=True)
    texture.interpolation = "Linear"
    texture.extension = "CLIP"
    shader.inputs["Roughness"].default_value = 0.82
    if "Specular IOR Level" in shader.inputs:
        shader.inputs["Specular IOR Level"].default_value = 0.12
    links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    links.new(texture.outputs["Alpha"], shader.inputs["Alpha"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return material


def bake_schedule(
    scene: bpy.types.Scene,
    seed: int,
    interval_min: float,
    interval_max: float,
    half_frames: int,
    closed_frames: int,
    start_frame: int,
    end_frame: int,
) -> list[dict[str, int | float]]:
    if interval_min <= 0 or interval_max < interval_min:
        raise ValueError("blink interval range is invalid")
    rng = random.Random(seed)
    fps = float(scene.render.fps)
    cursor = float(start_frame)
    schedule: list[dict[str, int | float]] = []
    while True:
        wait_seconds = rng.uniform(interval_min, interval_max)
        blink_start = int(round(cursor + wait_seconds * fps))
        blink_end = blink_start + half_frames * 2 + closed_frames
        if blink_end > end_frame:
            break
        schedule.append(
            {
                "start_frame": blink_start,
                "half_in": half_frames,
                "closed": closed_frames,
                "half_out": half_frames,
                "wait_seconds": round(wait_seconds, 4),
            }
        )
        cursor = float(blink_end)
    return schedule


def bake_blinks(
    open_eyes: list[bpy.types.Object],
    closed_eyes: list[bpy.types.Object],
    schedule: list[dict[str, int | float]],
    start_frame: int,
    end_frame: int,
    half_frames: int,
    closed_frames: int,
) -> None:
    for open_eye, closed_eye in zip(open_eyes, closed_eyes):
        key_state(open_eye, start_frame, True, 1.0)
        key_state(closed_eye, start_frame, False, 1.0)
        for event in schedule:
            blink_start = int(event["start_frame"])
            closed_start = blink_start + half_frames
            closed_end = closed_start + closed_frames
            # The first 3D pass keeps the half timing in the deterministic
            # schedule, while the actual visual switch uses the imagegen
            # open/closed texture states.
            key_state(open_eye, blink_start, False, 1.0)
            key_state(closed_eye, blink_start, True, 1.0)
            key_state(open_eye, closed_end + half_frames, True, 1.0)
            key_state(closed_eye, closed_end + half_frames, False, 1.0)
        key_state(open_eye, end_frame, True, 1.0)
        key_state(closed_eye, end_frame, False, 1.0)
        set_constant_interpolation(open_eye)
        set_constant_interpolation(closed_eye)


def main() -> int:
    options = cli_args()
    input_blend = options.input_blend.resolve()
    output_blend = options.output_blend.resolve()
    manifest_path = options.manifest.resolve()
    bpy.ops.wm.open_mainfile(filepath=str(input_blend))

    armature = next((obj for obj in bpy.data.objects if obj.type == "ARMATURE"), None)
    if armature is None or HEAD_BONE not in armature.data.bones:
        raise RuntimeError(f"Actor is missing {HEAD_BONE}")

    lenses = [bpy.data.objects.get(name) for name in LENS_NAMES]
    if any(obj is None for obj in lenses):
        raise RuntimeError("Actor V1 eye package is incomplete")
    closed_materials = [
        make_texture_material("EyeBlinkV1_Closed_L", options.closed_left_texture),
        make_texture_material("EyeBlinkV1_Closed_R", options.closed_right_texture),
    ]

    collection = bpy.data.collections.get("Face_Eyes_Blink_V1")
    if collection is None:
        collection = bpy.data.collections.new("Face_Eyes_Blink_V1")
        bpy.context.scene.collection.children.link(collection)

    closed_eyes = [
        duplicate_lid(obj, material)
        for obj, material in zip(lenses, closed_materials)
    ]
    for obj in closed_eyes:
        for parent in list(obj.users_collection):
            parent.objects.unlink(obj)
        collection.objects.link(obj)

    scene = bpy.context.scene
    if options.preview_frames > 0:
        scene.frame_end = max(scene.frame_start + 1, options.preview_frames)
    schedule = bake_schedule(
        scene,
        options.seed,
        options.interval_min,
        options.interval_max,
        options.half_frames,
        options.closed_frames,
        scene.frame_start,
        scene.frame_end,
    )
    bake_blinks(
        lenses,
        closed_eyes,
        schedule,
        scene.frame_start,
        scene.frame_end,
        options.half_frames,
        options.closed_frames,
    )

    scene["assetslab_eye_anime"] = "eye_blink_3d_v1"
    scene["assetslab_eye_anime_seed"] = options.seed
    scene["assetslab_eye_anime_back_policy"] = "transparent_no_eye_geometry"
    scene["assetslab_eye_anime_layer"] = "Face/Eyes"

    output_blend.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))
    manifest = {
        "schema": "assetslab_eye_blink_3d_experiment_v1",
        "status": "derived_blend_review_only",
        "source_blend": str(input_blend),
        "output_blend": str(output_blend),
        "layer": "Face/Eyes",
        "source_open_eye_materials": ["EyePackageV1_MikuLeft", "EyePackageV1_MikuRight"],
        "blink_geometry": {
            "closed_texture_lenses": [obj.name for obj in closed_eyes],
            "parent_bone": HEAD_BONE,
            "back_policy": "transparent_no_eye_geometry",
        },
        "imagegen_closed_eye_textures": [
            str(options.closed_left_texture.resolve()),
            str(options.closed_right_texture.resolve()),
        ],
        "timeline": {
            "fps": scene.render.fps,
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
            "seed": options.seed,
            "interval_min_seconds": options.interval_min,
            "interval_max_seconds": options.interval_max,
            "half_frames": options.half_frames,
            "closed_frames": options.closed_frames,
            "schedule": schedule,
        },
        "randomization": {
            "unit": "eye_style_bundle_before_render",
            "runtime_generation": False,
            "note": "The 3D scene is baked before 2D rendering; Godot does not render or generate 3D eyes.",
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"EYE_BLINK_3D_PASS schedule={len(schedule)} blend={output_blend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
