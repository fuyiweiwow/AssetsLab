"""Build the reproducible G0 Blender mannequin and its four static references.

Run only through Blender's bundled Python.  The scene is intentionally plain:
it establishes proportions, orthographic registration, and real depth before
pixel art, animation, facial features, or clothing are attempted.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--render-dir", required=True, type=Path)
    return parser.parse_args(argv)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.armatures, bpy.data.lights):
        for datablock in list(datablocks):
            datablocks.remove(datablock)


def material(name: str, rgba: tuple[float, float, float, float]) -> bpy.types.Material:
    item = bpy.data.materials.new(name)
    item.diffuse_color = rgba
    item.use_nodes = True
    principled = item.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = rgba
    principled.inputs["Roughness"].default_value = 0.82
    return item


def assign_material(obj: bpy.types.Object, item: bpy.types.Material) -> None:
    obj.data.materials.append(item)


def smooth(obj: bpy.types.Object) -> None:
    for polygon in obj.data.polygons:
        polygon.use_smooth = True


def sphere(name: str, location: Vector, scale: Vector, item: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth(obj)
    assign_material(obj, item)
    return obj


def rounded_box(name: str, location: Vector, scale: Vector, item: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = obj.modifiers.new("soft_block_edges", "BEVEL")
    bevel.width = 0.14
    bevel.segments = 3
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    smooth(obj)
    assign_material(obj, item)
    return obj


def capsule(name: str, start: Vector, end: Vector, radius: float, item: bpy.types.Material) -> bpy.types.Object:
    direction = end - start
    midpoint = (start + end) * 0.5
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=radius, depth=direction.length, location=midpoint)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(direction.normalized())
    smooth(obj)
    assign_material(obj, item)
    sphere(name + "_start", start, Vector((radius, radius, radius)), item)
    sphere(name + "_end", end, Vector((radius, radius, radius)), item)
    return obj


def create_armature() -> bpy.types.Object:
    bpy.ops.object.armature_add(enter_editmode=True, location=(0.0, 0.0, 0.0))
    rig = bpy.context.object
    rig.name = "GuideRig"
    rig.data.name = "GuideRigData"
    edit_bones = rig.data.edit_bones
    edit_bones.remove(edit_bones[0])

    def bone(name: str, head: tuple[float, float, float], tail: tuple[float, float, float], parent=None):
        item = edit_bones.new(name)
        item.head = head
        item.tail = tail
        item.parent = parent
        return item

    root = bone("root", (0, 0, 0), (0, 0, 1.2))
    pelvis = bone("pelvis", (0, 0, 2.45), (0, 0, 3.1), root)
    spine = bone("spine", (0, 0, 3.1), (0, 0, 3.84), pelvis)
    neck = bone("neck", (0, 0, 3.84), (0, 0, 4.12), spine)
    bone("head", (0, 0, 4.12), (0, 0, 5.05), neck)
    for side, sign in (("L", -1.0), ("R", 1.0)):
        hip = bone("thigh." + side, (0.34 * sign, 0, 2.5), (0.34 * sign, 0.05, 1.3), pelvis)
        shin = bone("shin." + side, (0.34 * sign, 0.05, 1.3), (0.34 * sign, -0.12, 0.3), hip)
        shoulder = bone("upper_arm." + side, (0.72 * sign, 0, 3.65), (0.98 * sign, -0.04 * sign, 2.96), spine)
        bone("lower_arm." + side, (0.98 * sign, -0.04 * sign, 2.96), (0.9 * sign, -0.1 * sign, 2.38), shoulder)
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.hide_render = True
    rig.display_type = "WIRE"
    rig["purpose"] = "G0 rig definition; meshes remain unbound until G1 pose transfer."
    return rig


def point_camera(camera: bpy.types.Object, location: Vector, target: Vector) -> None:
    camera.location = location
    camera.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()


def create_scene(contract: dict) -> tuple[bpy.types.Scene, bpy.types.Object]:
    clear_scene()
    scene = bpy.context.scene
    scene.name = "AssetsLab_G0_3D_Guide"
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x, scene.render.resolution_y = contract["guide_canvas_px"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.render.image_settings.color_depth = "8"
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.fps = 8
    try:
        scene.view_settings.look = "None"
    except TypeError:
        pass

    colors = {
        "head": material("M_Head", (0.92, 0.94, 0.97, 1.0)),
        "torso": material("M_Torso", (0.55, 0.64, 0.75, 1.0)),
        "arm": material("M_Arms", (0.72, 0.81, 0.89, 1.0)),
        "leg": material("M_Legs", (0.62, 0.69, 0.77, 1.0)),
        "foot": material("M_Feet", (0.82, 0.87, 0.93, 1.0)),
    }
    sphere("Head", Vector((0, -0.04, 4.8)), Vector((0.78, 0.62, 0.78)), colors["head"])
    rounded_box("Torso", Vector((0, 0, 3.17)), Vector((0.64, 0.34, 0.65)), colors["torso"])
    sphere("Pelvis", Vector((0, 0, 2.5)), Vector((0.57, 0.3, 0.25)), colors["torso"])
    for side, sign in (("Left", -1.0), ("Right", 1.0)):
        shoulder = Vector((0.72 * sign, 0, 3.65))
        elbow = Vector((0.98 * sign, -0.04 * sign, 2.96))
        hand = Vector((0.9 * sign, -0.1 * sign, 2.38))
        capsule("%s_UpperArm" % side, shoulder, elbow, 0.17, colors["arm"])
        capsule("%s_LowerArm" % side, elbow, hand, 0.16, colors["arm"])
        sphere("%s_Hand" % side, hand, Vector((0.2, 0.16, 0.22)), colors["arm"])
        hip = Vector((0.34 * sign, 0.02 * sign, 2.5))
        knee = Vector((0.34 * sign, 0.08 * sign, 1.3))
        ankle = Vector((0.34 * sign, -0.12 * sign, 0.28))
        capsule("%s_Thigh" % side, hip, knee, 0.22, colors["leg"])
        capsule("%s_Shin" % side, knee, ankle, 0.2, colors["leg"])
        sphere("%s_Foot" % side, Vector((0.34 * sign, -0.28 * sign, 0.17)), Vector((0.29, 0.46, 0.17)), colors["foot"])
    create_armature()

    light_data = bpy.data.lights.new("KeyLight", "AREA")
    light_data.energy = 550.0
    light_data.shape = "DISK"
    light_data.size = 5.0
    light = bpy.data.objects.new("KeyLight", light_data)
    bpy.context.collection.objects.link(light)
    light.location = (3.0, -4.0, 7.0)
    point_camera(light, light.location, Vector((0, 0, 3.0)))

    camera_data = bpy.data.cameras.new("GuideCamera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = contract["world_contract"]["orthographic_scale"]
    camera = bpy.data.objects.new("GuideCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    scene["camera_contract"] = contract["schema"]
    scene["runtime_anchors_px"] = json.dumps(contract["runtime_anchors_px"], sort_keys=True)
    return scene, camera


def main() -> int:
    args = cli_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    if contract["guide_canvas_px"] != [256, 256] or contract["runtime_canvas_px"] != [64, 64]:
        raise ValueError("G0 currently requires the locked 256px guide and 64px runtime contract")
    args.blend.parent.mkdir(parents=True, exist_ok=True)
    args.render_dir.mkdir(parents=True, exist_ok=True)
    scene, camera = create_scene(contract)
    target_z = contract["world_contract"]["camera_target_z"]
    target = Vector((0.0, 0.0, target_z))
    for direction, payload in contract["directions"].items():
        point_camera(camera, Vector(payload["camera_position"]), target)
        scene.render.filepath = str(args.render_dir / (direction + ".png"))
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.blend))
    print("G0_BLEND_BUILD_PASS blend=%s renders=%s" % (args.blend, args.render_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
