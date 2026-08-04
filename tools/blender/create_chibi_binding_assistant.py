"""Create a Blender scene for manual annotation of the downloaded chibi mesh."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_original_chibi_actor_test import load_source_mesh  # noqa: E402


GROUPS = (
    "Bind_Head",
    "Bind_Neck",
    "Bind_Torso",
    "Bind_Arm_L",
    "Bind_Arm_R",
    "Bind_Leg_L",
    "Bind_Leg_R",
)


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--safe", action="store_true", help="apply source display modifiers before saving")
    return parser.parse_args(argv)


def bounds(mesh: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [mesh.matrix_world @ Vector(corner) for corner in mesh.bound_box]
    low = Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points)))
    high = Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)))
    return low, high


def make_rig(mesh: bpy.types.Object, low: Vector, high: Vector) -> bpy.types.Object:
    data = bpy.data.armatures.new("ChibiManualBindingRigData")
    rig = bpy.data.objects.new("ChibiManualBindingRig", data)
    bpy.context.collection.objects.link(rig)
    rig.show_in_front = True
    rig.display_type = "WIRE"
    z0 = low.z
    z1 = high.z
    x = (low.x + high.x) * 0.5
    y = (low.y + high.y) * 0.5
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    bones = {
            "BindRoot": (z0, z0 + 0.2, None),
            "BindSpine": (z0 + (z1 - z0) * 0.32, z0 + (z1 - z0) * 0.58, "BindRoot"),
            "BindNeck": (z0 + (z1 - z0) * 0.57, z0 + (z1 - z0) * 0.64, "BindSpine"),
            "BindHead": (z0 + (z1 - z0) * 0.64, z0 + (z1 - z0) * 0.92, "BindNeck"),
            "BindArm_L": (z0 + (z1 - z0) * 0.56, z0 + (z1 - z0) * 0.38, "BindSpine"),
            "BindArm_R": (z0 + (z1 - z0) * 0.56, z0 + (z1 - z0) * 0.38, "BindSpine"),
            "BindLeg_L": (z0 + (z1 - z0) * 0.34, z0 + (z1 - z0) * 0.04, "BindRoot"),
            "BindLeg_R": (z0 + (z1 - z0) * 0.34, z0 + (z1 - z0) * 0.04, "BindRoot"),
    }
    for name, (head_z, tail_z, parent_name) in bones.items():
        bone = data.edit_bones.new(name)
        lateral = 0.0
        if name.endswith("_L"):
            lateral = (high.x - low.x) * 0.22
        elif name.endswith("_R"):
            lateral = -(high.x - low.x) * 0.22
        bone.head = (x + lateral, y, head_z)
        bone.tail = (x + lateral, y, tail_z)
        if parent_name:
            bone.parent = data.edit_bones.get(parent_name)
    bpy.ops.object.mode_set(mode="OBJECT")
    return rig


def make_cameras(mesh: bpy.types.Object, low: Vector, high: Vector) -> None:
    target_z = (low.z + high.z) * 0.5
    for name, position in {
        "GuideFront": (0.0, -12.0, target_z),
        "GuideRight": (12.0, 0.0, target_z),
        "GuideBack": (0.0, 12.0, target_z),
        "GuideLeft": (-12.0, 0.0, target_z),
    }.items():
        camera_data = bpy.data.cameras.new(name + "Data")
        camera_data.type = "ORTHO"
        camera_data.ortho_scale = max(4.0, (high.z - low.z) * 1.25)
        camera = bpy.data.objects.new(name, camera_data)
        bpy.context.collection.objects.link(camera)
        camera.location = position
        camera.rotation_euler = (Vector((0.0, 0.0, target_z)) - camera.location).to_track_quat("-Z", "Y").to_euler()


def main() -> int:
    options = cli_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh = load_source_mesh(options.source, center_source=False)
    mesh.name = "ChibiBaseMesh_ANNOTATE"
    if options.safe:
        bpy.ops.object.select_all(action="DESELECT")
        mesh.select_set(True)
        bpy.context.view_layer.objects.active = mesh
        for modifier in list(mesh.modifiers):
            bpy.ops.object.modifier_apply(modifier=modifier.name)
    low, high = bounds(mesh)
    for name in GROUPS:
        mesh.vertex_groups.new(name=name)
    rig = make_rig(mesh, low, high)
    make_cameras(mesh, low, high)
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    scene = bpy.context.scene
    scene["AssetsLabBindingInstructions"] = "Select mesh vertices, assign Bind_* groups, move Bind* bones in Edit Mode, then save and export annotation JSON."
    scene["AssetsLabSource"] = str(options.source.resolve())
    options.blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.blend))
    manifest = {
        "schema": "assetslab_chibi_manual_binding_assistant_v1",
        "source": str(options.source.resolve()),
        "blend": str(options.blend.resolve()),
        "mesh": mesh.name,
        "armature": rig.name,
        "vertex_groups": list(GROUPS),
        "instruction": "Manually assign selected vertices to Bind_* groups and reposition Bind* bones, then run export_chibi_binding_annotation.py.",
        "safe_mode": options.safe,
        "status": "awaiting_manual_annotation",
    }
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("CHIBI_BINDING_ASSISTANT_PASS blend=%s manifest=%s" % (options.blend, options.manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
