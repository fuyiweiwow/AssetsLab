"""Export a browser-friendly actor + procedural-eye calibration asset."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from render_procedural_anime_eye_on_accurig import (  # noqa: E402
    HEAD_BONE,
    append_eyes,
    apply_safe_edit_materials,
    bounds,
    load_calibration,
    place_eyes_from_calibration,
)


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--fbx", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--calibration", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scale", type=float, default=1.4)
    parser.add_argument("--left-yaw-deg", type=float, default=0.0)
    parser.add_argument("--right-yaw-deg", type=float, default=0.0)
    parser.add_argument("--pitch-deg", type=float, default=0.0)
    return parser.parse_args(argv)


def make_web_material(name: str, color: tuple[float, float, float, float], roughness: float = 0.75) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    if shader is not None:
        shader.inputs["Base Color"].default_value = color
        shader.inputs["Roughness"].default_value = roughness
    return material


def make_eye_web_materials(eyes: list[bpy.types.Object]) -> None:
    white = make_web_material("WebCalibratorEyeWhite", (0.96, 0.96, 0.98, 1.0))
    for eye in eyes:
        eye.data.materials.clear()
        eye.data.materials.append(white)
        eye["assetslab_role"] = "calibration_eye"
        eye["assetslab_forward_axis"] = "-Y"
        eye["assetslab_source_name"] = eye.name.rsplit("_", 1)[-1]


def add_scene_metadata(scene: bpy.types.Scene, actor_bounds: tuple[Vector, Vector]) -> None:
    low, high = actor_bounds
    scene["assetslab_web_calibrator_schema"] = "assetslab_chibi_eye_web_calibrator_v1"
    scene["assetslab_actor_bounds_min"] = list(low)
    scene["assetslab_actor_bounds_max"] = list(high)


def main() -> int:
    options = cli_args()
    output = options.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(options.fbx.resolve()), use_anim=True)
    mesh = next(obj for obj in bpy.data.objects if obj.type == "MESH")
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    if HEAD_BONE not in armature.data.bones:
        raise RuntimeError(f"actor is missing required head bone: {HEAD_BONE}")

    low, high = bounds(mesh)
    actor_center = (low + high) * 0.5
    eyes = append_eyes(options.source)
    calibration = load_calibration(options.calibration)
    annotation_scale = max(4.0, (high.z - low.z) * 1.25)
    placement = place_eyes_from_calibration(
        eyes,
        calibration,
        actor_center.z,
        annotation_scale,
        options.scale,
        options.left_yaw_deg,
        options.right_yaw_deg,
        options.pitch_deg,
    )
    make_eye_web_materials(eyes)
    add_scene_metadata(bpy.context.scene, (low, high))

    # The browser editor is for static placement review. Keep the armature in
    # the GLB for reference, but do not bake animation into this calibration asset.
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    for obj in bpy.context.view_layer.objects:
        if obj.type in {"MESH", "ARMATURE"}:
            obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh

    bpy.ops.export_scene.gltf(
        filepath=str(output),
        export_format="GLB",
        use_selection=True,
        export_apply=False,
        export_animations=False,
        export_skins=True,
        export_morph=False,
        export_materials="EXPORT",
    )
    print(f"WEB_EYE_CALIBRATOR_ASSET_PASS output={output}")
    print(f"WEB_EYE_CALIBRATOR_PLACEMENT {placement}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
