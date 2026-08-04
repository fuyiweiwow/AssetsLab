"""Assemble the Miku head onto the existing AccuRIG actor body for review.

This is a reversible test build.  It keeps the actor body and its AccuRIG
armature, removes the actor's original head faces, imports only Miku's head
skin/eyes/eyebrows, and parents the imported parts rigidly to CC_Base_Head.
Hair and mouth objects are deliberately excluded.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector


KEEP_NAMES = {
    "head_org_0_0_node",
    "head_back_2_0_node",
    "eye_007_22_0_node",
    "eyeball_1_0_node",
    "eyebrow_008_56_0_node",
}

LEGACY_MIKU_EXACT = {
    "head_org_0_0_node",
    "head_back_2_0_node",
    "eye_007_22_0_node",
    "eyeball_1_0_node",
    "eyebrow_008_56_0_node",
    "mouth_000_0_0_node",
    "MikuChibiEyeball",
}


def args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor-blend", required=True, type=Path)
    parser.add_argument("--miku-fbx", required=True, type=Path)
    parser.add_argument("--output-blend", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--head-split-z", type=float, default=2.08)
    parser.add_argument("--head-width-fit", type=float, default=0.98)
    return parser.parse_args(argv)


def world_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    low = Vector((float("inf"), float("inf"), float("inf")))
    high = Vector((float("-inf"), float("-inf"), float("-inf")))
    for obj in objects:
        for corner in obj.bound_box:
            point = obj.matrix_world @ Vector(corner)
            low.x, low.y, low.z = min(low.x, point.x), min(low.y, point.y), min(low.z, point.z)
            high.x, high.y, high.z = max(high.x, point.x), max(high.y, point.y), max(high.z, point.z)
    if not objects:
        raise RuntimeError("no objects available for bounds")
    return low, high


def remove_object(obj: bpy.types.Object) -> None:
    bpy.data.objects.remove(obj, do_unlink=True)


def clean_old_miku_objects() -> None:
    for obj in list(bpy.data.objects):
        if obj.name in LEGACY_MIKU_EXACT or obj.name.startswith("MikuEyeSocket"):
            remove_object(obj)
            continue
        if obj.type == "ARMATURE" and obj.name.startswith("Armature."):
            remove_object(obj)
            continue
        if obj.type == "MESH" and any(
            obj.name.startswith(prefix)
            for prefix in ("front_MZ_", "back_MZ_", "head_set_", "hair_tie_", "te_", "jacket_", "arm_", "body_hada_", "mouth_", "object_009_")
        ):
            remove_object(obj)


def remove_actor_head_faces(actor: bpy.types.Object, split_z: float) -> bpy.types.Object:
    """Copy the animated actor mesh and remove faces above world Z split_z."""
    body = actor.copy()
    body.data = actor.data.copy()
    body.name = "ChibiActorBody_MikuHeadReplacement"
    bpy.context.collection.objects.link(body)
    body.matrix_world = actor.matrix_world.copy()

    bm = bmesh.new()
    bm.from_mesh(body.data)
    delete_faces = []
    for face in bm.faces:
        center_world = body.matrix_world @ face.calc_center_median()
        if center_world.z >= split_z:
            delete_faces.append(face)
    if not delete_faces:
        bm.free()
        raise RuntimeError(f"no actor head faces found above split z={split_z}")
    bmesh.ops.delete(bm, geom=delete_faces, context="FACES")
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    return body


def detach_source_objects(objects: list[bpy.types.Object]) -> None:
    for obj in objects:
        world = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = world
        for modifier in list(obj.modifiers):
            obj.modifiers.remove(modifier)


def imported_keep_objects(before: set[bpy.types.Object]) -> list[bpy.types.Object]:
    imported = [obj for obj in bpy.context.scene.objects if obj not in before]
    found: list[bpy.types.Object] = []
    for expected in KEEP_NAMES:
        candidates = [obj for obj in imported if obj.name == expected or obj.name.startswith(expected + ".")]
        if not candidates:
            raise RuntimeError(f"Miku FBX is missing required object: {expected}")
        found.append(candidates[0])
    return found


def fit_miku_head(
    head_objects: list[bpy.types.Object],
    target_low: Vector,
    target_high: Vector,
    width_fit: float,
) -> dict[str, float]:
    source_low, source_high = world_bounds(head_objects)
    source_width = source_high.x - source_low.x
    target_width = (target_high.x - target_low.x) * width_fit
    scale = target_width / source_width

    # Align the top and the front plane.  This preserves the Miku head's
    # internal eye placement while fitting its silhouette to the actor body.
    target_top = target_high.z - 0.025
    target_front = target_low.y - 0.015
    translation = Vector(
        (
            -(source_low.x + source_high.x) * 0.5 * scale,
            target_front - source_low.y * scale,
            target_top - source_high.z * scale,
        )
    )
    transform = Matrix.Translation(translation) @ Matrix.Diagonal((scale, scale, scale, 1.0))
    for obj in head_objects:
        obj.matrix_world = transform @ obj.matrix_world
    return {
        "uniform_scale": scale,
        "target_top": target_top,
        "target_front": target_front,
        "source_width": source_width,
        "target_width": target_width,
    }


def parent_to_head(objects: list[bpy.types.Object], rig: bpy.types.Object) -> None:
    if rig.data.bones.get("CC_Base_Head") is None:
        raise RuntimeError("Armature is missing CC_Base_Head")
    for obj in objects:
        world = obj.matrix_world.copy()
        obj.parent = rig
        obj.parent_type = "BONE"
        obj.parent_bone = "CC_Base_Head"
        obj.matrix_world = world
        obj["assetslab_role"] = "miku_head_replacement"
        obj["assetslab_motion"] = "rigid_parent_CC_Base_Head"


def configure_render(scene: bpy.types.Scene) -> None:
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 320
    scene.render.resolution_y = 320
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"


def render_direction(scene: bpy.types.Scene, meshes: list[bpy.types.Object], output: Path, direction: str) -> None:
    low, high = world_bounds(meshes)
    target = (low + high) * 0.5
    height = high.z - low.z
    camera_data = bpy.data.cameras.new(f"MikuHeadReplacementCamera_{direction}")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = max(height * 1.14, 3.45)
    camera_data.clip_start = 0.01
    camera_data.clip_end = 100.0
    camera = bpy.data.objects.new(f"MikuHeadReplacementCamera_{direction}", camera_data)
    scene.collection.objects.link(camera)
    distance = max(height * 5.0, 12.0)
    if direction == "front":
        camera.location = target + Vector((0.0, -distance, 0.0))
    elif direction == "right":
        camera.location = target + Vector((distance, 0.0, 0.0))
    else:
        camera.location = target + Vector((0.0, distance, 0.0))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    remove_object(camera)


def main() -> int:
    options = args()
    actor_blend = options.actor_blend.resolve()
    miku_fbx = options.miku_fbx.resolve()
    output_blend = options.output_blend.resolve()
    output_dir = options.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.open_mainfile(filepath=str(actor_blend))
    clean_old_miku_objects()
    actor = bpy.data.objects.get("ChibiBaseMesh_AccuRIG_InputMesh")
    rig = bpy.data.objects.get("Armature")
    if actor is None or actor.type != "MESH":
        raise RuntimeError("actor mesh ChibiBaseMesh_AccuRIG_InputMesh not found")
    if rig is None or rig.type != "ARMATURE":
        raise RuntimeError("AccuRIG Armature not found")

    actor_low, actor_high = world_bounds([actor])
    body = remove_actor_head_faces(actor, options.head_split_z)
    body["assetslab_role"] = "actor_body_without_original_head"
    body["assetslab_head_split_world_z"] = options.head_split_z
    remove_object(actor)

    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=str(miku_fbx), automatic_bone_orientation=False)
    head_objects = imported_keep_objects(before)
    detach_source_objects(head_objects)
    fit_info = fit_miku_head(head_objects, actor_low, actor_high, options.head_width_fit)
    parent_to_head(head_objects, rig)

    # The imported FBX includes six source armatures and many accessory meshes.
    # They are no longer needed after the selected head meshes are detached.
    imported = [obj for obj in bpy.context.scene.objects if obj in before is False]
    for obj in list(bpy.context.scene.objects):
        if obj in head_objects or obj in {body, rig}:
            continue
        if obj not in before:
            remove_object(obj)

    scene = bpy.context.scene
    configure_render(scene)
    render_meshes = [body] + head_objects
    for direction in ("front", "right"):
        render_direction(scene, render_meshes, output_dir / f"{direction}.png", direction)

    manifest = {
        "schema": "assetslab_miku_head_replacement_test_v1",
        "actor_blend": str(actor_blend),
        "miku_fbx": str(miku_fbx),
        "output_blend": str(output_blend),
        "kept_miku_objects": [obj.name for obj in head_objects],
        "removed_categories": ["Miku hair", "Miku mouth", "Miku teeth", "Miku source armatures", "actor original head faces"],
        "parent_bone": "CC_Base_Head",
        "head_split_world_z": options.head_split_z,
        "fit": fit_info,
        "renders": {"front": str(output_dir / "front.png"), "right": str(output_dir / "right.png")},
        "status": "review_candidate",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    output_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))
    print(f"MIKU_HEAD_REPLACEMENT_PASS output={output_blend}")
    print(f"kept={','.join(obj.name for obj in head_objects)}")
    print(f"fit={json.dumps(fit_info)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
