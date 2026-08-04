"""Build a texture-driven, shallow-curved anime EyePackage on the actor.

This is intentionally not a spherical eyeball transfer. The eye graphic is
carried by a shallow curved surface placed just in front of the actor's face,
with a small upper eyelid/eyeline strip and rigid head-bone parenting.
"""

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

from render_procedural_anime_eye_on_accurig import (  # noqa: E402
    annotation_world_point,
    bounds,
    load_calibration,
    make_camera,
    setup_render,
)


HEAD_BONE = "CC_Base_Head"


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--fbx", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--left-texture", type=Path, required=True)
    parser.add_argument("--right-texture", type=Path, required=True)
    parser.add_argument("--left-iris", type=Path)
    parser.add_argument("--right-iris", type=Path)
    parser.add_argument("--left-pupil", type=Path)
    parser.add_argument("--right-pupil", type=Path)
    parser.add_argument("--left-frame", type=Path)
    parser.add_argument("--right-frame", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--save-blend", type=Path, required=True)
    parser.add_argument("--width-scale", type=float, default=0.92)
    parser.add_argument("--spacing-scale", type=float, default=1.0)
    parser.add_argument("--height-scale", type=float, default=0.72)
    parser.add_argument("--front-clearance", type=float, default=0.012)
    parser.add_argument("--curvature", type=float, default=0.018)
    parser.add_argument("--upper-line-width", type=float, default=0.012)
    parser.add_argument("--no-upper-line", action="store_true")
    parser.add_argument("--shrinkwrap-offset", type=float, default=0.003)
    parser.add_argument("--eye-white-height-scale", type=float, default=0.80)
    parser.add_argument("--iris-width-scale", type=float, default=1.0)
    parser.add_argument("--iris-height-scale", type=float, default=1.0)
    parser.add_argument("--pupil-height-scale", type=float, default=1.0)
    return parser.parse_args(argv)


def parent_to_head(obj: bpy.types.Object, armature: bpy.types.Object) -> None:
    world = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = HEAD_BONE
    obj.matrix_world = world


def configure_alpha(material: bpy.types.Material) -> None:
    if hasattr(material, "surface_render_method"):
        try:
            material.surface_render_method = "DITHERED"
        except Exception:
            pass
    if hasattr(material, "blend_method"):
        try:
            material.blend_method = "HASHED"
        except Exception:
            pass
    if hasattr(material, "use_transparency_overlap"):
        material.use_transparency_overlap = False


def make_eye_material(name: str, texture_path: Path) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    configure_alpha(material)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = bpy.data.images.load(str(texture_path.resolve()), check_existing=True)
    texture.interpolation = "Closest"
    texture.extension = "CLIP"
    shader.inputs["Roughness"].default_value = 0.82
    if "Specular IOR Level" in shader.inputs:
        shader.inputs["Specular IOR Level"].default_value = 0.12
    links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    links.new(texture.outputs["Alpha"], shader.inputs["Alpha"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return material


def make_line_material() -> bpy.types.Material:
    material = bpy.data.materials.new("EyePackageV1_UpperLineMaterial")
    material.diffuse_color = (0.025, 0.012, 0.035, 1.0)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    if shader is not None:
        shader.inputs["Base Color"].default_value = (0.025, 0.012, 0.035, 1.0)
        shader.inputs["Roughness"].default_value = 0.88
    return material


def make_eye_white_material() -> bpy.types.Material:
    material = bpy.data.materials.new("EyePackageV1_EyeWhite")
    material.diffuse_color = (0.78, 0.88, 0.93, 1.0)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    if shader is not None:
        shader.inputs["Base Color"].default_value = (0.78, 0.88, 0.93, 1.0)
        shader.inputs["Roughness"].default_value = 0.78
    return material


def add_surface_fit(obj: bpy.types.Object, actor_mesh: bpy.types.Object, offset: float) -> None:
    shrink = obj.modifiers.new("EyePackageV1_FitToHeadSurface", "SHRINKWRAP")
    shrink.target = actor_mesh
    shrink.wrap_method = "PROJECT"
    shrink.wrap_mode = "ON_SURFACE"
    shrink.use_project_y = True
    shrink.use_positive_direction = True
    shrink.use_negative_direction = False
    shrink.offset = offset


def create_curved_lens(
    name: str,
    center: Vector,
    width: float,
    height: float,
    curvature: float,
    material: bpy.types.Material,
    armature: bpy.types.Object,
    actor_mesh: bpy.types.Object,
    side: str,
    shrinkwrap_offset: float,
) -> bpy.types.Object:
    cols, rows = 16, 10
    vertices = []
    faces = []
    uvs = []
    for row in range(rows + 1):
        v = row / rows
        z = (v - 0.5) * height
        for col in range(cols + 1):
            u = col / cols
            x = (u - 0.5) * width
            nx = (x / (width * 0.5)) if width else 0.0
            nz = (z / (height * 0.5)) if height else 0.0
            radius = min(1.0, nx * nx + nz * nz)
            # The rim stays slightly forward; the center retreats a little.
            y = center.y + curvature * (1.0 - radius)
            vertices.append((center.x + x, y, center.z + z))
            uvs.append((u, v))
    for row in range(rows):
        for col in range(cols):
            a = row * (cols + 1) + col
            b = a + 1
            d = (row + 1) * (cols + 1) + col
            c = d + 1
            faces.append((a, b, c, d))

    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        for loop_index in poly.loop_indices:
            uv_layer.data[loop_index].uv = uvs[mesh.loops[loop_index].vertex_index]
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj["assetslab_role"] = "eye_package_v1_lens"
    obj["assetslab_side"] = side
    add_surface_fit(obj, actor_mesh, shrinkwrap_offset)
    parent_to_head(obj, armature)
    return obj


def create_almond_frame(
    name: str,
    center: Vector,
    width: float,
    height: float,
    material: bpy.types.Material,
    armature: bpy.types.Object,
    actor_mesh: bpy.types.Object,
    side: str,
    shrinkwrap_offset: float,
) -> bpy.types.Object:
    vertices = []
    samples = 12
    # Filled almond behind the texture. It provides a crisp eye border while
    # the crop on top supplies the colored iris and white eye area.
    for index in range(samples):
        t = math.pi * index / (samples - 1)
        vertices.append((center.x - width * 0.5 + width * index / (samples - 1), center.y, center.z + height * 0.24 * math.sin(t)))
    for index in range(samples):
        t = math.pi * index / (samples - 1)
        vertices.append((center.x + width * 0.5 - width * index / (samples - 1), center.y, center.z - height * 0.18 * math.sin(t)))
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], [tuple(range(len(vertices)))])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj["assetslab_role"] = "eye_package_v1_almond_frame"
    obj["assetslab_side"] = side
    add_surface_fit(obj, actor_mesh, shrinkwrap_offset - 0.001)
    parent_to_head(obj, armature)
    return obj


def create_upper_line(
    name: str,
    center: Vector,
    width: float,
    height: float,
    line_width: float,
    material: bpy.types.Material,
    armature: bpy.types.Object,
    actor_mesh: bpy.types.Object,
    side: str,
    front_clearance: float,
    shrinkwrap_offset: float,
) -> bpy.types.Object:
    curve_data = bpy.data.curves.new(name + "Curve", type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 2
    curve_data.bevel_depth = line_width * 0.5
    curve_data.bevel_resolution = 1
    spline = curve_data.splines.new("POLY")
    points = 13
    spline.points.add(points - 1)
    for index in range(points):
        theta = math.pi * index / (points - 1)
        x = math.cos(theta) * width * 0.40
        # Keep the line just in front of the lens rim, not floating away from it.
        z = -height * 0.03 + math.sin(theta) * height * 0.23
        spline.points[index].co = (center.x + x, center.y - front_clearance * 0.65, center.z + z, 1.0)
    obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj["assetslab_role"] = "eye_package_v1_upper_line"
    obj["assetslab_side"] = side
    add_surface_fit(obj, actor_mesh, shrinkwrap_offset)
    parent_to_head(obj, armature)
    return obj


def main() -> int:
    options = cli_args()
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(options.fbx.resolve()), use_anim=True)
    actor_mesh = next(obj for obj in bpy.data.objects if obj.type == "MESH")
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    if HEAD_BONE not in armature.data.bones:
        raise RuntimeError(f"actor is missing {HEAD_BONE}")

    low, high = bounds(actor_mesh)
    actor_center = (low + high) * 0.5
    annotation_scale = max(4.0, (high.z - low.z) * 1.25)
    calibration = load_calibration(options.calibration)
    front = {item["key"]: item for item in calibration["views"]["front"]}
    side = {item["key"]: item for item in calibration["views"]["side"]}
    left_mark = annotation_world_point(front["screen_left_eye_center"], "front", actor_center.z, annotation_scale)
    right_mark = annotation_world_point(front["screen_right_eye_center"], "front", actor_center.z, annotation_scale)
    side_center = annotation_world_point(side["eye_center"], "side", actor_center.z, annotation_scale)
    face_surface = annotation_world_point(side["face_front_surface"], "side", actor_center.z, annotation_scale)
    eye_z = (left_mark.z + right_mark.z + side_center.z) / 3.0
    lens_y = face_surface.y - options.front_clearance
    base_gap = abs(right_mark.x - left_mark.x)
    eye_gap = base_gap * options.width_scale
    placement_gap = base_gap * options.width_scale * options.spacing_scale
    width = eye_gap * 0.68
    height = width * (0.78 * options.height_scale)
    midpoint_x = (left_mark.x + right_mark.x) * 0.5
    left_center = Vector((midpoint_x - placement_gap * 0.5, lens_y, eye_z))
    right_center = Vector((midpoint_x + placement_gap * 0.5, lens_y, eye_z))

    left_mat = make_eye_material("EyePackageV1_MikuLeft", options.left_texture)
    right_mat = make_eye_material("EyePackageV1_MikuRight", options.right_texture)
    line_mat = make_line_material()
    white_mat = make_eye_white_material()
    layered = options.left_iris is not None and options.right_iris is not None
    traced_frame = options.left_frame is not None and options.right_frame is not None
    left_iris_mat = make_eye_material("EyePackageV1_IrisLeft", options.left_iris) if layered else None
    right_iris_mat = make_eye_material("EyePackageV1_IrisRight", options.right_iris) if layered else None
    left_pupil_mat = make_eye_material("EyePackageV2_PupilLeft", options.left_pupil) if options.left_pupil else None
    right_pupil_mat = make_eye_material("EyePackageV2_PupilRight", options.right_pupil) if options.right_pupil else None
    left_frame_mat = make_eye_material("EyePackageV2_ConceptFrameLeft", options.left_frame) if traced_frame else None
    right_frame_mat = make_eye_material("EyePackageV2_ConceptFrameRight", options.right_frame) if traced_frame else None
    parts = []
    for label, center, material in (("L", left_center, left_mat), ("R", right_center, right_mat)):
        if traced_frame:
            frame_material = left_frame_mat if label == "L" else right_frame_mat
            frame_width = width * 1.08
            # The concept frame is intentionally taller than the source crop's
            # raw aspect ratio; this keeps the eye silhouette locked to the
            # actor's adjustable width/height profile.
            frame_height = height * 1.10
            parts.append(create_curved_lens(
                f"EyePackageV2_ConceptFrame_{label}", center, frame_width, frame_height,
                options.curvature * 0.5, frame_material, armature, actor_mesh, label,
                options.shrinkwrap_offset + 0.004,
            ))
        else:
            parts.append(create_almond_frame(
                f"EyePackageV1_AlmondFrame_{label}", center, width * 1.08, height * 1.12,
                line_mat, armature, actor_mesh, label, options.shrinkwrap_offset,
            ))
        if layered:
            parts.append(create_almond_frame(
                f"EyePackageV1_EyeWhite_{label}", center, width * 0.98,
                height * options.eye_white_height_scale,
                white_mat, armature, actor_mesh, label, options.shrinkwrap_offset + 0.001,
            ))
            iris_material = left_iris_mat if label == "L" else right_iris_mat
            parts.append(create_curved_lens(
                f"EyePackageV1_Iris_{label}",
                center + Vector((0.0, -0.002, -height * 0.03)),
                height * 0.56 * options.iris_width_scale,
                height * 0.56 * options.iris_height_scale,
                options.curvature * 0.35,
                iris_material, armature, actor_mesh, label, options.shrinkwrap_offset + 0.003,
            ))
            pupil_material = left_pupil_mat if label == "L" else right_pupil_mat
            if pupil_material is not None:
                parts.append(create_curved_lens(
                    f"EyePackageV2_ElongatedPupil_{label}",
                    center + Vector((0.0, -0.004, -height * 0.025)),
                    height * 0.30, height * 0.30 * options.pupil_height_scale,
                    options.curvature * 0.20,
                    pupil_material, armature, actor_mesh, label, options.shrinkwrap_offset + 0.005,
                ))
        else:
            parts.append(create_curved_lens(
                f"EyePackageV1_Lens_{label}", center, width, height, options.curvature,
                material, armature, actor_mesh, label, options.shrinkwrap_offset,
            ))
        if not traced_frame and not options.no_upper_line:
            parts.append(create_upper_line(
                f"EyePackageV1_UpperLine_{label}", center, width * 0.72, height, options.upper_line_width,
                line_mat, armature, actor_mesh, label, options.front_clearance, options.shrinkwrap_offset,
            ))

    scene = bpy.context.scene
    scene.frame_set(1)
    setup_render(scene, -1.0)
    scene.render.resolution_x = scene.render.resolution_y = 384
    scene.render.resolution_percentage = 100
    scene.render.image_settings.color_mode = "RGBA"
    camera_specs = {
        "front": (0.0, -12.0, actor_center.z),
        "threequarter": (8.5, -8.5, actor_center.z),
        "right": (12.0, 0.0, actor_center.z),
        "back": (0.0, 12.0, actor_center.z),
    }
    for direction, location in camera_specs.items():
        camera = make_camera(scene, actor_center, direction, location, max(4.0, high.z - low.z + 0.6))
        scene.camera = camera
        scene.render.filepath = str(output / f"{direction}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)

    face_target = Vector((actor_center.x, actor_center.y, eye_z))
    face_scale = max(1.35, (high.z - low.z) * 0.38)
    closeup_specs = {
        "front_face_closeup": (0.0, -12.0, eye_z),
        "threequarter_face_closeup": (8.5, -8.5, eye_z),
        "right_face_closeup": (12.0, 0.0, eye_z),
    }
    for direction, location in closeup_specs.items():
        camera = make_camera(scene, face_target, direction, location, face_scale)
        scene.camera = camera
        scene.render.filepath = str(output / f"{direction}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)

    bpy.ops.wm.save_as_mainfile(filepath=str(options.save_blend.resolve()))
    manifest = {
        "schema": "assetslab_eye_package_v1",
        "source_actor": str(options.fbx.resolve()),
        "source_eye_atlas": {
            "left": str(options.left_texture.resolve()),
            "right": str(options.right_texture.resolve()),
        },
        "style_bundle": {
            "id": "imagegen_blue_brows_v2",
            "randomization_unit": "eye_lash_brow_bundle",
            "components": ["eye_outline", "iris", "pupil", "highlights", "upper_lashes", "eyebrows"],
            "alpha_workflow": "magenta_chroma_key_to_rgba",
        },
        "parent_bone": HEAD_BONE,
        "parts": [obj.name for obj in parts],
        "placement": {
            "left_center": list(left_center),
            "right_center": list(right_center),
            "lens_y": lens_y,
            "width": width,
            "height": height,
            "width_scale": options.width_scale,
            "height_scale": options.height_scale,
            "spacing_scale": options.spacing_scale,
            "curvature": options.curvature,
            "front_clearance": options.front_clearance,
        },
        "directions": list(camera_specs) + list(closeup_specs),
        "status": "static_multiview_review_only",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"EYE_PACKAGE_V1_PASS output={output}")
    print(f"EYE_PACKAGE_V1_BLEND {options.save_blend.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
