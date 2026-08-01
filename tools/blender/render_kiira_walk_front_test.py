"""Render a front-only, featureless KIIRA Walk.fbx test strip."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--fbx", required=True, type=Path)
    parser.add_argument("--render-dir", required=True, type=Path)
    parser.add_argument("--blend", required=True, type=Path)
    return parser.parse_args(argv)


def setup_scene() -> tuple[bpy.types.Object, bpy.types.Object, list[bpy.types.Object]]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    # The downloaded FBX references the author's original absolute texture
    # paths. Workbench keeps this motion test independent of those textures.
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 256
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True

    bpy.ops.import_scene.fbx(filepath=str(cli.fbx), use_anim=True)
    rig = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    for obj in meshes:
        obj.hide_render = obj.name.upper() == "FACE"
        obj.hide_viewport = obj.name.upper() == "FACE"

    # Reuse the imported materials but remove the FBX default world/background.
    scene.world = bpy.data.worlds.new("KIIRA_Test_World")
    scene.world.color = (0.02, 0.02, 0.02)
    light_data = bpy.data.lights.new("KIIRA_Test_Key", "AREA")
    light_data.energy = 500
    light_data.size = 5
    light = bpy.data.objects.new("KIIRA_Test_Key", light_data)
    light.location = (-4, -6, 8)
    scene.collection.objects.link(light)

    camera_data = bpy.data.cameras.new("KIIRA_Test_Camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 6.2
    camera = bpy.data.objects.new("KIIRA_Test_Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return scene, rig, meshes


def configure_camera(scene: bpy.types.Scene, camera: bpy.types.Object, meshes: list[bpy.types.Object]) -> dict:
    points = []
    for obj in meshes:
        if obj.hide_render:
            continue
        points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    if not points:
        raise RuntimeError("no visible KIIRA mesh")
    min_z = min(point.z for point in points)
    max_z = max(point.z for point in points)
    center_z = (min_z + max_z) * 0.5
    camera = scene.camera
    camera.location = (0.0, -12.0, center_z)
    camera.rotation_euler = (Vector((0.0, 0.0, center_z)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    return {"min_z": min_z, "max_z": max_z, "center_z": center_z}


def main() -> int:
    options = cli_args()
    # Keep the imported FBX object available to the helper without global path state.
    global cli
    cli = options
    scene, rig, meshes = setup_scene()
    bounds = configure_camera(scene, scene.camera, meshes)
    action = rig.animation_data.action if rig.animation_data else None
    if action is None:
        raise RuntimeError("Walk.fbx has no active action")
    start, end = action.frame_range
    sample_frames = [round(start + (end - start) * index / 8.0) for index in range(8)]
    frame_files = []
    for index, frame in enumerate(sample_frames):
        scene.frame_set(frame)
        target = options.render_dir / f"frame_{index:02d}" / "beauty.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        frame_files.append({"frame": index, "source_frame": frame, "path": str(target)})
    options.blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.blend))
    manifest = {
        "schema": "assetslab_kiira_walk_front_test_v1",
        "purpose": "Featureless KIIRA actor front walk test before pixel redraw.",
        "source_fbx": str(options.fbx),
        "canvas_px": [256, 256],
        "sample_frames": frame_files,
        "camera": {"projection": "orthographic", "ortho_scale": scene.camera.data.ortho_scale, **bounds},
        "face_hidden": True,
        "runtime_ready": False,
    }
    options.render_dir.mkdir(parents=True, exist_ok=True)
    (options.render_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"KIIRA_FRONT_TEST_PASS frames={len(frame_files)} output={options.render_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
