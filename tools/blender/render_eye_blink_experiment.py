"""Render a few frames of the derived 3D eye-blink experiment headlessly."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frames", type=int, nargs="+", default=[1, 30, 40])
    parser.add_argument(
        "--body-frames",
        type=int,
        nargs="+",
        help="optional body-pose frames; must have the same count as --frames",
    )
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--gallery", action="store_true")
    return parser.parse_args(argv)


def bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector((min(point[i] for point in points) for i in range(3))),
        Vector((max(point[i] for point in points) for i in range(3))),
    )


def make_camera(scene: bpy.types.Scene, target: Vector, location: Vector, scale: float) -> bpy.types.Object:
    camera_data = bpy.data.cameras.new("EyeBlinkReviewCameraData")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = scale
    camera = bpy.data.objects.new("EyeBlinkReviewCamera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = location
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    return camera


def apply_direction_face_pass(view_name: str) -> None:
    allowed: set[str]
    if view_name in ("front", "threequarter"):
        allowed = {"front"}
    elif view_name == "right":
        allowed = {"right"}
    elif view_name == "left":
        allowed = {"left"}
    else:
        allowed = set()

    for obj in bpy.data.objects:
        if not obj.name.startswith(("EyePackageV1_Lens_", "EyePackageV1_AlmondFrame_", "EyeBlinkV1_")):
            continue
        if obj.name.startswith("EyePackageV1_Lens_") or (
            "Texture" in obj.name and "Side" not in obj.name
        ):
            role = "front"
        elif obj.name.endswith("_L"):
            role = "left"
        elif obj.name.endswith("_R"):
            role = "right"
        else:
            role = "none"
        if role not in allowed:
            obj.hide_render = True
            obj.hide_viewport = True


def normalize_review_materials() -> None:
    """Avoid hashed alpha dithering on opaque character materials in review renders."""
    for material in bpy.data.materials:
        if material.name.startswith(("EyeBlinkV1_", "EyePackageV1_")):
            continue
        if not material.use_nodes:
            continue
        shader = next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
        if shader is None or "Alpha" not in shader.inputs or shader.inputs["Alpha"].default_value >= 0.999:
            if hasattr(material, "surface_render_method"):
                material.surface_render_method = "BLENDED"


def capture_pose(armature: bpy.types.Object) -> dict[str, object]:
    return {bone.name: bone.matrix_basis.copy() for bone in armature.pose.bones}


def restore_pose(armature: bpy.types.Object, pose: dict[str, object]) -> None:
    for bone in armature.pose.bones:
        matrix_basis = pose.get(bone.name)
        if matrix_basis is not None:
            bone.matrix_basis = matrix_basis
    bpy.context.view_layer.update()


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.blend.resolve()))
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    actor = next(obj for obj in bpy.data.objects if obj.type == "MESH" and obj.name.startswith("ChibiBaseMesh"))
    low, high = bounds(actor)
    center = (low + high) * 0.5
    scene = bpy.context.scene
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    if options.body_frames is not None and len(options.body_frames) != len(options.frames):
        raise ValueError("--body-frames must have the same number of values as --frames")
    # The Actor V1 open eyes are imagegen-derived texture materials. Workbench
    # ignores their node-based alpha/color path, so the review must use Eevee.
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = scene.render.resolution_y = options.size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.render.film_transparent = False
    # Keep the review render clean enough to judge texture edges and shadows.
    scene.eevee.taa_render_samples = 128
    scene.eevee.shadow_ray_count = 4
    normalize_review_materials()

    camera_specs = {
        "front": Vector((0.0, -12.0, center.z)),
        "threequarter": Vector((8.5, -8.5, center.z)),
        "right": Vector((12.0, 0.0, center.z)),
        "left": Vector((-12.0, 0.0, center.z)),
        "back": Vector((0.0, 12.0, center.z)),
    }
    for view_name, location in camera_specs.items():
        camera = make_camera(scene, center, location, max(4.0, high.z - low.z + 0.6))
        scene.camera = camera
        for index, frame in enumerate(options.frames):
            if options.body_frames is None:
                scene.frame_set(frame)
            else:
                scene.frame_set(options.body_frames[index])
                body_pose = capture_pose(armature)
                scene.frame_set(frame)
                restore_pose(armature, body_pose)
            apply_direction_face_pass(view_name)
            filename = f"{view_name}_{index:02d}.png" if options.gallery else f"{view_name}_frame{frame:03d}.png"
            scene.render.filepath = str(output / filename)
            bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)
    print(f"EYE_BLINK_RENDER_PASS output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
