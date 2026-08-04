"""Render a bound actor's real action from four orthographic directions."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

# Blender executes a script with its own file directory as the first import
# location only in some launch modes. Make the sibling renderer explicit so
# this tool is reproducible from PowerShell and CI.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from render_accurig_chibi_walk_test import (
    apply_face_style,
    bounds,
    configure_soft_toon_lighting,
    make_camera,
)


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--frame-count", type=int, default=8)
    parser.add_argument("--face-style", type=int, choices=range(4), default=0)
    parser.add_argument("--soft-toon-lighting", action="store_true")
    return parser.parse_args(argv)


def main() -> int:
    options = cli_args()
    if options.frame_count < 2:
        raise RuntimeError("frame count must be at least two")
    bpy.ops.wm.open_mainfile(filepath=str(options.input_blend.resolve()))
    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one actor armature, found {[obj.name for obj in armatures]}")
    armature = armatures[0]
    mesh = next((obj for obj in bpy.data.objects if obj.type == "MESH" and obj.name.startswith("ChibiBase")), None)
    if mesh is None:
        raise RuntimeError("actor mesh not found")
    if not armature.animation_data or not armature.animation_data.action:
        raise RuntimeError("bound actor has no action")
    action = armature.animation_data.action
    frame_start, frame_end = action.frame_range

    low, high = bounds(mesh)
    target = Vector(((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, (low.z + high.z) * 0.5))
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = scene.render.resolution_y = 256
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = True
    if options.soft_toon_lighting:
        configure_soft_toon_lighting(scene)

    output_dir = options.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    face_variant = apply_face_style(armature, options.face_style)
    cameras = {
        name: make_camera(scene, target, low, high, name, location)
        for name, location in {
            "front": (0.0, -12.0, target.z),
            "right": (12.0, 0.0, target.z),
            "back": (0.0, 12.0, target.z),
            "left": (-12.0, 0.0, target.z),
        }.items()
    }
    frame_values = [
        round(frame_start + (frame_end - frame_start) * index / (options.frame_count - 1))
        for index in range(options.frame_count)
    ]
    for direction, camera in cameras.items():
        scene.camera = camera
        for index, frame in enumerate(frame_values):
            scene.frame_set(frame)
            scene.render.filepath = str(output_dir / f"{direction}_{index:02d}.png")
            bpy.ops.render.render(write_still=True)

    manifest = {
        "schema": "assetslab_bound_fourway_test_v1",
        "input_blend": str(options.input_blend.resolve()),
        "action": action.name,
        "action_frame_range": [frame_start, frame_end],
        "directions": ["front", "right", "back", "left"],
        "frames_per_direction": options.frame_count,
        "face_style": face_variant,
        "feature_objects": {
            "eyes": "EyePackageV1_*",
            "brows": "FaceVariantBrowL/R",
            "ears": "CartoonEar_L/R_Downloaded",
        },
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        "BOUND_FOURWAY_RENDER_PASS "
        f"directions=4 frames={options.frame_count} action={action.name} output={output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
