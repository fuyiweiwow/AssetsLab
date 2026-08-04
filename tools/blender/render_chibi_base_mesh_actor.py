"""Render the downloaded chibi mesh with the external Walk action in 4 views."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_original_chibi_actor_test as binding  # noqa: E402


DIRECTIONS = {
    "front": (0.0, -12.0),
    "right": (12.0, 0.0),
    "back": (0.0, 12.0),
    "left": (-12.0, 0.0),
}


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-blend", required=True, type=Path)
    parser.add_argument("--walk-fbx", required=True, type=Path)
    parser.add_argument("--render-dir", required=True, type=Path)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--head-scale", type=float, default=1.18)
    parser.add_argument("--body-scale", type=float, default=0.86)
    parser.add_argument("--body-width-scale", type=float, default=1.0)
    parser.add_argument("--body-depth-scale", type=float, default=1.0)
    parser.add_argument("--preserve-source-transform", action="store_true")
    parser.add_argument("--rigid-head", action="store_true")
    parser.add_argument("--head-split-z", type=float, default=1.3)
    parser.add_argument("--binding-lines", type=Path, default=None)
    return parser.parse_args(argv)


def set_camera(camera: bpy.types.Object, position: tuple[float, float], target_z: float, ortho_scale: float) -> None:
    camera.data.ortho_scale = ortho_scale
    camera.location = (position[0], position[1], target_z)
    target = Vector((0.0, 0.0, target_z))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def derive_head_split_z(source: Path, lines_path: Path) -> tuple[float, dict]:
    """Convert browser image coordinates into the source mesh Z threshold."""
    lines = json.loads(lines_path.read_text(encoding="utf-8"))
    probe = binding.load_source_mesh(source, center_source=False)
    bpy.ops.object.select_all(action="DESELECT")
    probe.select_set(True)
    bpy.context.view_layer.objects.active = probe
    binding.apply_source_display_modifiers(probe)
    low, high = binding.bounds(probe)
    target_z = (low.z + high.z) * 0.5
    ortho_scale = max(4.0, (high.z - low.z) * 1.25)
    front = lines["views"]["front"]
    side = lines["views"]["side"]
    head_y = (float(front[0]) + float(side[0])) * 0.5
    neck_y = (float(front[1]) + float(side[1])) * 0.5
    torso_y = (float(front[2]) + float(side[2])) * 0.5
    minimum_gap = 6.0
    neck_adjusted = False
    if neck_y < head_y + minimum_gap:
        neck_y = head_y + minimum_gap
        neck_adjusted = True
    def pixel_to_z(pixel_y: float) -> float:
        return target_z + ortho_scale * 0.5 - pixel_y / 512.0 * ortho_scale
    calibration = {
        "head_bottom_px": head_y,
        "neck_bottom_px": neck_y,
        "torso_bottom_px": torso_y,
        "neck_gap_adjusted": neck_adjusted,
        "head_split_z": pixel_to_z(head_y),
        "neck_split_z": pixel_to_z(neck_y),
        "torso_split_z": pixel_to_z(torso_y),
        "source_bounds_min": list(low),
        "source_bounds_max": list(high),
        "annotation_image_px": [512, 512],
    }
    bpy.data.objects.remove(probe, do_unlink=True)
    return calibration["head_split_z"], calibration


def main() -> int:
    options = cli_args()
    line_calibration = None
    if options.binding_lines is not None:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        options.head_split_z, line_calibration = derive_head_split_z(options.source_blend, options.binding_lines)
    scene_options = SimpleNamespace(
        source_blend=options.source_blend,
        walk_fbx=options.walk_fbx,
        render_dir=options.render_dir,
        blend=options.blend,
        camera_contract=None,
        head_scale=options.head_scale,
        body_scale=options.body_scale,
        body_width_scale=options.body_width_scale,
        body_depth_scale=options.body_depth_scale,
        preserve_source_transform=options.preserve_source_transform,
        rigid_head=True if options.binding_lines is not None else options.rigid_head,
        head_split_z=options.head_split_z,
    )
    scene, rig, mesh, root = binding.setup_scene(scene_options)
    action = rig.animation_data.action if rig.animation_data else None
    if action is None:
        raise RuntimeError("Walk FBX has no active action")
    start, end = action.frame_range
    samples = [round(start + (end - start) * index / 8.0) for index in range(8)]
    low, high, floor_offset = binding.normalize_actor_floor(scene, root, mesh, samples)
    target_z = (low.z + high.z) * 0.5
    ortho_scale = max(4.5, (high.z - low.z) * 1.18)
    frames = []
    for direction, position in DIRECTIONS.items():
        set_camera(scene.camera, position, target_z, ortho_scale)
        for index, source_frame in enumerate(samples):
            scene.frame_set(source_frame)
            target = options.render_dir / direction / f"frame_{index:02d}" / "beauty.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            scene.render.filepath = str(target)
            bpy.ops.render.render(write_still=True)
            frames.append({"direction": direction, "frame": index, "source_frame": source_frame, "path": str(target)})
    options.blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.blend))
    options.render_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "assetslab_chibi_base_mesh_actor_v1",
        "stage": "downloaded_chibi_base_mesh_four_direction_walk_review",
        "source_blend": str(options.source_blend),
        "walk_fbx": str(options.walk_fbx),
        "source_input_support": [".blend", ".zip_with_nested_blend"],
        "binding_policy": "experimental_rigid_head_bone_parent_plus_body_regions_to_KIIRA_bones",
        "rigid_head": options.rigid_head,
        "head_split_z": options.head_split_z,
        "binding_lines": str(options.binding_lines) if options.binding_lines else None,
        "binding_line_calibration": line_calibration,
        "model_is_downloaded_chibi_base_mesh": True,
        "source_meshes_removed_after_action_import": True,
        "preserve_source_transform": options.preserve_source_transform,
        "camera_registration": "fixed_four_direction_review_camera_not_G0_locked",
        "floor_normalized": True,
        "actor_root": root.name,
        "floor_offset_z": round(floor_offset, 4),
        "animated_bounds_after_floor": {"min_z": round(low.z, 4), "max_z": round(high.z, 4)},
        "head_scale": options.head_scale,
        "body_scale": options.body_scale,
        "directions": list(DIRECTIONS),
        "frame_count": 8,
        "frames": frames,
        "runtime_ready": False,
        "visual_review_required": True,
    }
    (options.render_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("CHIBI_BASE_MESH_ACTOR_RENDER_PASS directions=4 frames=8 renders=32 output=%s" % options.render_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
