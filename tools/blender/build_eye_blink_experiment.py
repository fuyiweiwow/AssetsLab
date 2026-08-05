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
from mathutils import Matrix, Vector


HEAD_BONE = "CC_Base_Head"
LENS_NAMES = ("EyePackageV1_Lens_L", "EyePackageV1_Lens_R")
SIDE_EYE_WIDTH = 0.68
SIDE_EYE_HEIGHT = 0.64


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-blend", type=Path, required=True)
    parser.add_argument("--output-blend", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--closed-left-texture", type=Path, required=True)
    parser.add_argument("--closed-right-texture", type=Path, required=True)
    parser.add_argument("--open-left-texture", type=Path, required=True)
    parser.add_argument("--open-right-texture", type=Path, required=True)
    parser.add_argument("--half-left-texture", type=Path, required=True)
    parser.add_argument("--half-right-texture", type=Path, required=True)
    parser.add_argument("--side-left-texture", type=Path, required=True)
    parser.add_argument("--side-right-texture", type=Path, required=True)
    parser.add_argument("--side-half-left-texture", type=Path, required=True)
    parser.add_argument("--side-half-right-texture", type=Path, required=True)
    parser.add_argument("--side-closed-left-texture", type=Path, required=True)
    parser.add_argument("--side-closed-right-texture", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260805)
    parser.add_argument("--interval-min", type=float, default=2.5)
    parser.add_argument("--interval-max", type=float, default=5.0)
    parser.add_argument("--closed-frames", type=int, default=2)
    parser.add_argument("--half-frames", type=int, default=3)
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


def duplicate_state(
    source: bpy.types.Object,
    material: bpy.types.Material,
    state: str,
    armature: bpy.types.Object,
    eye_bone_name: str,
) -> bpy.types.Object:
    lid = source.copy()
    lid.data = source.data.copy()
    lid.name = source.name.replace("EyePackageV1_Lens_", f"EyeBlinkV1_{state}Texture_")
    lid.data.name = lid.name + "Mesh"
    lid.data.materials.clear()
    lid.data.materials.append(material)
    bpy.context.collection.objects.link(lid)

    # Keep the standard bundle at the Actor V1 lens size. Move it a few
    # millimetres toward the front camera before rebinding it to the eye bone.
    # The eye bone is a child of the facial/head chain, so it follows both
    # walking head motion and any later facial/eye animation.
    offset_local = source.matrix_world.to_3x3().inverted() @ Vector((0.0, -0.090, 0.0))
    lid.location += offset_local
    world_matrix = lid.matrix_world.copy()
    lid.parent = armature
    lid.parent_type = "BONE"
    lid.parent_bone = eye_bone_name
    lid.matrix_parent_inverse = Matrix.Identity(4)
    eye_bone_world = armature.matrix_world @ armature.pose.bones[eye_bone_name].matrix
    lid.matrix_basis = eye_bone_world.inverted() @ world_matrix
    lid["assetslab_layer"] = "Face/Eyes"
    lid["assetslab_role"] = f"eye_blink_3d_{state.lower()}_texture"
    lid["assetslab_source"] = source.name
    lid["assetslab_parent_bone"] = eye_bone_name
    return lid


def make_texture_material(
    name: str, texture_path: Path, *, unlit: bool = False
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    if hasattr(material, "surface_render_method"):
        # Dithered/hashed alpha produces frame-dependent holes on these shallow
        # eye layers, which looks like a small window opening in the face.
        material.surface_render_method = "BLENDED"
    if hasattr(material, "blend_method"):
        material.blend_method = "BLEND"
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
    if unlit and "Emission Color" in shader.inputs:
        links.new(texture.outputs["Color"], shader.inputs["Emission Color"])
        if "Emission Strength" in shader.inputs:
            shader.inputs["Emission Strength"].default_value = 1.0
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return material


def create_side_plane(
    name: str,
    location: Vector,
    normal_sign: float,
    material: bpy.types.Material,
    armature: bpy.types.Object,
    eye_bone_name: str,
) -> bpy.types.Object:
    # The side source is a profile eye inside a transparent 496x609 canvas.
    # Its non-transparent content occupies less of that canvas than the front
    # bundle, so the native v18 plane made the eye unreadable at 256px.
    width = SIDE_EYE_WIDTH
    height = SIDE_EYE_HEIGHT
    vertices = [
        (-width * 0.5, -height * 0.5, 0.0),
        (width * 0.5, -height * 0.5, 0.0),
        (width * 0.5, height * 0.5, 0.0),
        (-width * 0.5, height * 0.5, 0.0),
    ]
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], [(0, 1, 2, 3)])
    mesh.uv_layers.new(name="UVMap")
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            vertex = mesh.loops[loop_index].vertex_index
            mesh.uv_layers[0].data[loop_index].uv = ((1.0, 0.0), (0.0, 0.0), (0.0, 1.0), (1.0, 1.0))[vertex]
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    # Local X follows head Y, local Y follows head Z, and local Z faces +/-X.
    basis = Matrix(((0.0, 0.0, normal_sign), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))).to_4x4()
    desired_world = Matrix.Translation(location) @ basis
    bone_world = armature.matrix_world @ armature.pose.bones[eye_bone_name].matrix
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = eye_bone_name
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_basis = bone_world.inverted() @ desired_world
    obj["assetslab_layer"] = "Face/Eyes"
    obj["assetslab_role"] = "eye_blink_3d_side_texture"
    obj["assetslab_side_normal"] = normal_sign
    obj["assetslab_side_plane_size"] = (width, height)
    obj["assetslab_parent_bone"] = eye_bone_name
    # Keep the profile plane rigid. The imagegen side canvas is already
    # camera-oriented; a shrinkwrap projection would deform the plane across
    # the rounded head and make the eye collapse into a tiny sliver. The eye
    # bone parent supplies the required facial/head motion.
    return obj


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
    half_eyes: list[bpy.types.Object],
    closed_eyes: list[bpy.types.Object],
    schedule: list[dict[str, int | float]],
    start_frame: int,
    end_frame: int,
    half_frames: int,
    closed_frames: int,
) -> None:
    for open_eye, half_eye, closed_eye in zip(open_eyes, half_eyes, closed_eyes):
        key_state(open_eye, start_frame, True, 1.0)
        key_state(half_eye, start_frame, False, 1.0)
        key_state(closed_eye, start_frame, False, 1.0)
        for event in schedule:
            blink_start = int(event["start_frame"])
            closed_start = blink_start + half_frames
            half_out_start = closed_start + closed_frames
            open_start = half_out_start + half_frames
            # Use actual imagegen half-open textures for both sides of the
            # transition; the schedule and the visual state now agree.
            key_state(open_eye, blink_start, False, 1.0)
            key_state(half_eye, blink_start, True, 1.0)
            key_state(closed_eye, blink_start, False, 1.0)
            key_state(half_eye, closed_start, False, 1.0)
            key_state(closed_eye, closed_start, True, 1.0)
            key_state(closed_eye, half_out_start, False, 1.0)
            key_state(half_eye, half_out_start, True, 1.0)
            key_state(half_eye, open_start, False, 1.0)
            key_state(open_eye, open_start, True, 1.0)
        key_state(open_eye, end_frame, True, 1.0)
        key_state(half_eye, end_frame, False, 1.0)
        key_state(closed_eye, end_frame, False, 1.0)
        set_constant_interpolation(open_eye)
        set_constant_interpolation(half_eye)
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
    eye_bones = ("CC_Base_L_Eye", "CC_Base_R_Eye")
    if any(name not in armature.pose.bones for name in eye_bones):
        raise RuntimeError("Actor V1 eye bones are incomplete")
    open_materials = [
        make_texture_material("EyeBlinkV1_Open_L", options.open_left_texture),
        make_texture_material("EyeBlinkV1_Open_R", options.open_right_texture),
    ]
    closed_materials = [
        make_texture_material("EyeBlinkV1_Closed_L", options.closed_left_texture),
        make_texture_material("EyeBlinkV1_Closed_R", options.closed_right_texture),
    ]
    half_materials = [
        make_texture_material("EyeBlinkV1_Half_L", options.half_left_texture),
        make_texture_material("EyeBlinkV1_Half_R", options.half_right_texture),
    ]
    side_open_materials = [
        make_texture_material("EyeBlinkV1_SideOpen_L", options.side_left_texture, unlit=True),
        make_texture_material("EyeBlinkV1_SideOpen_R", options.side_right_texture, unlit=True),
    ]
    side_closed_materials = [
        make_texture_material("EyeBlinkV1_SideClosed_L", options.side_closed_left_texture, unlit=True),
        make_texture_material("EyeBlinkV1_SideClosed_R", options.side_closed_right_texture, unlit=True),
    ]
    side_half_materials = [
        make_texture_material("EyeBlinkV1_SideHalf_L", options.side_half_left_texture, unlit=True),
        make_texture_material("EyeBlinkV1_SideHalf_R", options.side_half_right_texture, unlit=True),
    ]

    collection = bpy.data.collections.get("Face_Eyes_Blink_V1")
    if collection is None:
        collection = bpy.data.collections.new("Face_Eyes_Blink_V1")
        bpy.context.scene.collection.children.link(collection)

    open_eyes = [
        duplicate_state(obj, material, "Open", armature, eye_bone)
        for obj, material, eye_bone in zip(lenses, open_materials, eye_bones)
    ]
    closed_eyes = [
        duplicate_state(obj, material, "Closed", armature, eye_bone)
        for obj, material, eye_bone in zip(lenses, closed_materials, eye_bones)
    ]
    half_eyes = [
        duplicate_state(obj, material, "Half", armature, eye_bone)
        for obj, material, eye_bone in zip(lenses, half_materials, eye_bones)
    ]
    side_open_eyes = [
        create_side_plane(
            name,
            location,
            normal_sign,
            material,
            armature,
            eye_bone,
        )
        for name, location, normal_sign, material, eye_bone in (
            ("EyeBlinkV1_SideOpen_L", Vector((-0.66, -0.07, 2.07)), 1.0, side_open_materials[0], eye_bones[0]),
            ("EyeBlinkV1_SideOpen_R", Vector((0.66, -0.07, 2.07)), -1.0, side_open_materials[1], eye_bones[1]),
        )
    ]
    side_closed_eyes = [
        create_side_plane(
            name,
            location,
            normal_sign,
            material,
            armature,
            eye_bone,
        )
        for name, location, normal_sign, material, eye_bone in (
            ("EyeBlinkV1_SideClosed_L", Vector((-0.665, -0.07, 2.07)), 1.0, side_closed_materials[0], eye_bones[0]),
            ("EyeBlinkV1_SideClosed_R", Vector((0.665, -0.07, 2.07)), -1.0, side_closed_materials[1], eye_bones[1]),
        )
    ]
    side_half_eyes = [
        create_side_plane(
            name,
            location,
            normal_sign,
            material,
            armature,
            eye_bone,
        )
        for name, location, normal_sign, material, eye_bone in (
            ("EyeBlinkV1_SideHalf_L", Vector((-0.662, -0.07, 2.07)), 1.0, side_half_materials[0], eye_bones[0]),
            ("EyeBlinkV1_SideHalf_R", Vector((0.662, -0.07, 2.07)), -1.0, side_half_materials[1], eye_bones[1]),
        )
    ]
    for obj in side_open_eyes + side_half_eyes + side_closed_eyes:
        obj["assetslab_view"] = "left" if "_L" in obj.name else "right"
    for obj in open_eyes + half_eyes + closed_eyes:
        for parent in list(obj.users_collection):
            parent.objects.unlink(obj)
        collection.objects.link(obj)
    for obj in side_open_eyes + side_half_eyes + side_closed_eyes:
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
    for obj in bpy.data.objects:
        if obj.name.startswith("EyePackageV1_"):
            obj.hide_render = True
            obj.hide_viewport = True

    bake_blinks(
        open_eyes + side_open_eyes,
        half_eyes + side_half_eyes,
        closed_eyes + side_closed_eyes,
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
        "source_open_eye_materials": ["EyeBlinkV1_Open_L", "EyeBlinkV1_Open_R"],
        "standard_reference": {
            "actor_eye_texture": "prototype/assets/characters/actor_v1/eye_textures/eye_right.png",
            "runtime_canvas_px": [64, 64],
            "runtime_front_head_alpha_bbox_px": [18, 7, 46, 57],
            "reference_eye_alpha_bbox_px": [13, 12, 488, 597],
            "policy": "preserve_standard_bbox_and_eye_brow_spacing",
        },
        "blink_geometry": {
            "open_texture_lenses": [obj.name for obj in open_eyes],
            "half_texture_lenses": [obj.name for obj in half_eyes],
            "closed_texture_lenses": [obj.name for obj in closed_eyes],
            "side_open_texture_planes": [obj.name for obj in side_open_eyes],
            "side_half_texture_planes": [obj.name for obj in side_half_eyes],
            "side_closed_texture_planes": [obj.name for obj in side_closed_eyes],
            "parent_bone": {
                "left": eye_bones[0],
                "right": eye_bones[1],
                "chain": "CC_Base_L/R_Eye -> CC_Base_FacialBone -> CC_Base_Head",
            },
            "back_policy": "transparent_no_eye_geometry",
        },
        "imagegen_closed_eye_textures": [
            str(options.closed_left_texture.resolve()),
            str(options.closed_right_texture.resolve()),
        ],
        "imagegen_open_eye_textures": (
            [str(options.open_left_texture.resolve()), str(options.open_right_texture.resolve())]
            if options.open_left_texture and options.open_right_texture
            else None
        ),
        "imagegen_side_eye_textures": [
            str(options.side_left_texture.resolve()),
            str(options.side_right_texture.resolve()),
        ],
        "imagegen_side_closed_eye_textures": [
            str(options.side_closed_left_texture.resolve()),
            str(options.side_closed_right_texture.resolve()),
        ],
        "imagegen_half_eye_textures": [
            str(options.half_left_texture.resolve()),
            str(options.half_right_texture.resolve()),
        ],
        "imagegen_side_half_eye_textures": [
            str(options.side_half_left_texture.resolve()),
            str(options.side_half_right_texture.resolve()),
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
