"""Attach the downloaded ear using normalized front/right anchor annotations."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from attach_cartoon_ear_candidate import (  # noqa: E402
    HEAD_BONE,
    append_source_part,
    bounds,
    center_mesh,
    configure_render,
    duplicate_ear,
    make_skin_material,
)
from render_procedural_anime_eye_on_accurig import make_camera  # noqa: E402


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-blend", required=True, type=Path)
    parser.add_argument("--source-blend", required=True, type=Path)
    parser.add_argument("--calibration", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--save-blend", required=True, type=Path)
    parser.add_argument("--part", default="CartoonEarPart_01")
    parser.add_argument("--rotation-x", type=float, default=90.0, help="Base rotation that makes the source ear upright")
    parser.add_argument("--size-multiplier", type=float, default=1.0, help="Uniform multiplier applied to the calibration-derived ear size")
    parser.add_argument("--eye-height-scale", type=float, default=1.0, help="Vertical scale for the verified eye meshes, around each eye centre")
    parser.add_argument("--root-inset", type=float, default=0.0, help="Positive distance to push the narrow root into the head")
    parser.add_argument("--back-tilt-degrees", type=float, default=0.0, help="Positive amount to tuck each pinna toward the back of the head")
    parser.add_argument("--top-back-tilt-degrees", type=float, default=0.0, help="Positive amount to move the upper pinna back and the lower stalk forward")
    parser.add_argument("--outward-offset", type=float, default=0.0, help="Legacy: positive value pulls the root outward")
    return parser.parse_args(argv)


def image_point_to_world(point: dict, center: Vector, ortho_scale: float, side: str) -> Vector:
    screen_x = float(point["x"])
    screen_y = float(point["y"])
    world_x = center.x + (screen_x - 0.5) * ortho_scale if side == "front" else center.y + (screen_x - 0.5) * ortho_scale
    world_z = center.z + (0.5 - screen_y) * ortho_scale
    if side == "front":
        return Vector((world_x, center.y, world_z))
    return Vector((center.x, world_x, world_z))


def narrow_root_center(source: bpy.types.Object) -> Vector:
    """Return the centroid of the source ear's narrow attachment end.

    The downloaded part has its attachment at the local +X extreme.  Using
    that actual geometry (instead of the bounding-box centre) makes the
    calibration annotation refer to the contact point on the ear.
    """
    vertices = [vertex.co.copy() for vertex in source.data.vertices]
    max_x = max(point.x for point in vertices)
    min_x = min(point.x for point in vertices)
    band = (max_x - min_x) * 0.05
    root_vertices = [point for point in vertices if point.x >= max_x - band]
    return sum(root_vertices, Vector()) / len(root_vertices)


def transformed_root(local_root: Vector, scale: float, mirror_x: bool, rotation_x: float) -> Vector:
    point = local_root.copy()
    point.x *= -1.0 if mirror_x else 1.0
    point *= scale
    return Matrix.Rotation(math.radians(rotation_x), 3, "X") @ point


def rotate_about_world_point(obj: bpy.types.Object, point: Vector, degrees: float) -> None:
    if not degrees:
        return
    rotation = Matrix.Rotation(math.radians(degrees), 4, "Z")
    obj.matrix_world = Matrix.Translation(point) @ rotation @ Matrix.Translation(-point) @ obj.matrix_world


def restore_eye_textures() -> None:
    """Repair and pack the verified imagegen eye textures when present.

    Older eye-package Blends stored a relative path that becomes invalid once
    a prepared actor is saved under ``assets/characters/generated``.  Packing
    the restored images keeps the final actor portable and prevents Blender's
    missing-texture magenta fallback in the pixel-render pipeline.
    """
    texture_root = TOOLS_DIR.parents[1] / "prototype" / "assets" / "generated" / "eye_package_v5" / "imagegen_eye_v5_auto_crops"
    for material_name, texture_name in (
        ("EyePackageV1_MikuLeft", "imagegen_eye_L.png"),
        ("EyePackageV1_MikuRight", "imagegen_eye_R.png"),
    ):
        material = bpy.data.materials.get(material_name)
        texture_path = texture_root / texture_name
        if material is None or not material.use_nodes or not texture_path.is_file():
            continue
        image_nodes = [node for node in material.node_tree.nodes if node.type == "TEX_IMAGE"]
        for node in image_nodes:
            image = bpy.data.images.load(str(texture_path), check_existing=False)
            node.image = image
            image.pack()


def scale_eye_height(scale: float) -> None:
    """Increase eye readability for the big-head pixel actor without shifting it."""
    if abs(scale - 1.0) < 1e-6:
        return
    for obj in bpy.data.objects:
        if not obj.name.startswith("EyePackageV1_") or obj.type != "MESH":
            continue
        coordinates = [vertex.co.z for vertex in obj.data.vertices]
        if not coordinates:
            continue
        center_z = (min(coordinates) + max(coordinates)) * 0.5
        for vertex in obj.data.vertices:
            vertex.co.z = center_z + (vertex.co.z - center_z) * scale


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.input_blend.resolve()))
    output = options.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    actor = next(obj for obj in bpy.data.objects if obj.type == "MESH" and obj.name.startswith("ChibiBase"))
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    if HEAD_BONE not in armature.data.bones:
        raise RuntimeError(f"actor is missing {HEAD_BONE}")
    calibration = json.loads(options.calibration.resolve().read_text(encoding="utf-8"))
    if calibration.get("schema") != "assetslab_chibi_ear_anchor_calibration_v1":
        raise RuntimeError("unsupported ear calibration schema")
    restore_eye_textures()
    scale_eye_height(options.eye_height_scale)

    low, high = bounds(actor)
    center = (low + high) * 0.5
    ortho_scale = max(4.0, high.z - low.z + 0.6)
    front = calibration["views"]["front"]
    side = calibration["views"]["side"]["R"]
    root_l = image_point_to_world(front["L"]["root"], center, ortho_scale, "front")
    root_r = image_point_to_world(front["R"]["root"], center, ortho_scale, "front")
    depth_r = image_point_to_world(side["root"], center, ortho_scale, "side")
    root_l.y = depth_r.y
    root_r.y = depth_r.y
    height_l = abs(float(front["L"]["bottom"]["y"]) - float(front["L"]["top"]["y"])) * ortho_scale
    height_r = abs(float(front["R"]["bottom"]["y"]) - float(front["R"]["top"]["y"])) * ortho_scale

    source = append_source_part(options.source_blend, options.part)
    center_mesh(source)
    root_local = narrow_root_center(source)
    source_height = source.dimensions.z
    scale = max(0.05, ((height_l + height_r) * 0.5) / source_height * options.size_multiplier)
    skin = make_skin_material()
    # The source ear's narrow attachment end points along its local +X axis.
    # Keep that end toward the head: right ears are mirrored and left ears use
    # the original orientation. The previous polarity attached the pinna to
    # the face and left the root pointing outward.
    # The legacy outward option is retained for old command lines.  Positive
    # root_inset moves both roots toward the head centre.
    effective_inset = options.root_inset - options.outward_offset
    left_contact = root_l + Vector((effective_inset, 0.0, 0.0))
    right_contact = root_r - Vector((effective_inset, 0.0, 0.0))
    left_location = left_contact - transformed_root(root_local, scale, False, options.rotation_x)
    right_location = right_contact - transformed_root(root_local, scale, True, options.rotation_x)
    left = duplicate_ear(source, "L", *left_location, scale, 0.0, 0.0, False, armature, skin, options.rotation_x)
    right = duplicate_ear(source, "R", *right_location, scale, 0.0, 0.0, True, armature, skin, options.rotation_x)
    # Pivot at the actual contact point so back-tilt cannot pull the connector
    # away from the face.  In this actor's coordinate frame, these signs move
    # both outer pinnae toward the back of the head rather than the face.
    rotate_about_world_point(left, left_contact, -options.back_tilt_degrees)
    rotate_about_world_point(right, right_contact, options.back_tilt_degrees)
    # A negative X rotation moves the upper portion toward +Y (back) while
    # bringing the lower attachment/stalk toward -Y (front).
    for ear, contact in ((left, left_contact), (right, right_contact)):
        if options.top_back_tilt_degrees:
            rotation = Matrix.Rotation(math.radians(-options.top_back_tilt_degrees), 4, "X")
            ear.matrix_world = Matrix.Translation(contact) @ rotation @ Matrix.Translation(-contact) @ ear.matrix_world
    bpy.data.objects.remove(source, do_unlink=True)

    configure_render(bpy.context.scene)
    scene = bpy.context.scene
    specs = {
        "front": ((0.0, -12.0, center.z), ortho_scale),
        "right": ((12.0, 0.0, center.z), ortho_scale),
        "front_face_closeup": ((0.0, -12.0, (root_l.z + root_r.z) * 0.5), max(1.85, (high.z - low.z) * 0.52)),
        "right_face_closeup": ((12.0, 0.0, depth_r.z), max(1.35, (high.z - low.z) * 0.38)),
    }
    for name, (location, camera_scale) in specs.items():
        target = Vector((center.x, center.y, depth_r.z if "closeup" in name else center.z))
        camera = make_camera(scene, target, name, location, camera_scale)
        scene.camera = camera
        scene.render.filepath = str(output / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)

    options.save_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.save_blend.resolve()))
    manifest = {
        "schema": "assetslab_calibrated_cartoon_ear_attachment_v1",
        "calibration": str(options.calibration.resolve()),
        "source_part": options.part,
        "parent_bone": HEAD_BONE,
        "computed": {
            "left_root": list(root_l),
            "right_root": list(root_r),
            "right_side_depth": depth_r.y,
            "ortho_scale": ortho_scale,
            "scale": scale,
            "size_multiplier": options.size_multiplier,
            "root_local": list(root_local),
            "rotation_x_degrees": options.rotation_x,
            "root_inset": options.root_inset,
            "back_tilt_degrees": options.back_tilt_degrees,
            "top_back_tilt_degrees": options.top_back_tilt_degrees,
            "eye_height_scale": options.eye_height_scale,
            "outward_offset": options.outward_offset,
        },
        "renders": {name: str(output / f"{name}.png") for name in specs},
        "status": "calibrated_attachment_review_pending",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"CALIBRATED_CARTOON_EAR_PASS output={output} blend={options.save_blend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
