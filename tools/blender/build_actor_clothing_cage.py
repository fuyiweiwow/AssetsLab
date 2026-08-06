"""Build the first Actor Clothing Cage and armor hardpoint contract.

The cage is an authoring-time reference, not a runtime mesh.  It is derived
from the evaluated neutral Actor and carries region groups used by later
fit, occlusion, and weight-transfer scripts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--thickness", type=float, default=0.025)
    return parser.parse_args(argv)


def bone_point(armature: bpy.types.Object, name: str, tail: bool = False) -> Vector | None:
    bone = armature.data.bones.get(name) if armature else None
    if bone is None:
        return None
    return armature.matrix_world @ (bone.tail_local if tail else bone.head_local)


def duplicate_evaluated_mesh(actor: bpy.types.Object) -> tuple[bpy.types.Mesh, list[Vector]]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = actor.evaluated_get(depsgraph)
    source_mesh = evaluated.to_mesh()
    try:
        points = [evaluated.matrix_world @ vertex.co for vertex in source_mesh.vertices]
        faces = [tuple(polygon.vertices) for polygon in source_mesh.polygons]
    finally:
        evaluated.to_mesh_clear()
    mesh = bpy.data.meshes.new("ActorClothingCage_OuterMesh")
    mesh.from_pydata([tuple(point) for point in points], [], faces)
    mesh.update()
    return mesh, points


def add_region_groups(cage: bpy.types.Object, points: list[Vector], levels: dict[str, float]) -> dict[str, int]:
    low_z = min(point.z for point in points)
    pelvis_z = levels["pelvis"]
    waist_z = levels["waist"]
    neck_z = levels["neck"]
    groups = {
        "soft_garment_torso": cage.vertex_groups.new(name="Cage_SoftGarment_Torso"),
        "soft_garment_lower": cage.vertex_groups.new(name="Cage_SoftGarment_Lower"),
        "soft_garment_arms": cage.vertex_groups.new(name="Cage_SoftGarment_Arms"),
        "rigid_armor_chest": cage.vertex_groups.new(name="Cage_RigidArmor_Chest"),
        "rigid_armor_shoulders": cage.vertex_groups.new(name="Cage_RigidArmor_Shoulders"),
        "layered_accessory_waist": cage.vertex_groups.new(name="Cage_LayeredAccessory_Waist"),
    }
    counts = {name: 0 for name in groups}
    for index, point in enumerate(points):
        torso = waist_z - 0.18 <= point.z <= neck_z + 0.04 and abs(point.x) <= 0.58
        lower = low_z + 0.08 <= point.z <= pelvis_z + 0.16
        arms = waist_z + 0.02 <= point.z <= neck_z and abs(point.x) > 0.28
        chest = waist_z + 0.18 <= point.z <= neck_z - 0.10 and abs(point.x) <= 0.48
        shoulders = neck_z - 0.30 <= point.z <= neck_z + 0.02 and abs(point.x) > 0.28
        waist = waist_z - 0.12 <= point.z <= waist_z + 0.12
        membership = {
            "soft_garment_torso": torso,
            "soft_garment_lower": lower,
            "soft_garment_arms": arms,
            "rigid_armor_chest": chest,
            "rigid_armor_shoulders": shoulders,
            "layered_accessory_waist": waist,
        }
        for name, include in membership.items():
            if include:
                groups[name].add([index], 1.0, "REPLACE")
                counts[name] += 1
    return counts


def make_anchor(
    scene: bpy.types.Scene,
    armature: bpy.types.Object,
    name: str,
    bone_name: str,
    category: str,
) -> bpy.types.Object:
    anchor = bpy.data.objects.new(name, None)
    anchor.empty_display_type = "SPHERE"
    anchor.empty_display_size = 0.08
    anchor.parent = armature
    anchor.parent_type = "BONE"
    anchor.parent_bone = bone_name
    anchor.location = (0.0, 0.0, 0.0)
    anchor["assetslab_clothing_anchor"] = True
    anchor["assetslab_clothing_category"] = category
    anchor["assetslab_bone"] = bone_name
    scene.collection.objects.link(anchor)
    return anchor


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.actor.resolve()))
    scene = bpy.context.scene
    scene.frame_set(1)
    actor = bpy.data.objects.get("ChibiBaseMesh_AccuRIG_InputMesh")
    armature = bpy.data.objects.get("Armature")
    if actor is None or armature is None:
        raise RuntimeError("Actor mesh and Armature are required")

    cage_mesh, points = duplicate_evaluated_mesh(actor)
    cage = bpy.data.objects.new("ActorClothingCage_Outer", cage_mesh)
    scene.collection.objects.link(cage)
    cage.display_type = "WIRE"
    cage.show_in_front = True
    cage.hide_render = True
    cage["assetslab_clothing_cage_schema"] = "assetslab_actor_clothing_cage_v1"
    cage["assetslab_supports"] = ["soft_garment", "rigid_armor", "layered_accessory"]
    cage["assetslab_cage_thickness"] = options.thickness
    solidify = cage.modifiers.new("CageOuterClearance", "SOLIDIFY")
    solidify.thickness = options.thickness
    solidify.offset = 1.0

    levels = {
        "pelvis": (bone_point(armature, "CC_Base_Pelvis") or Vector((0, 0, 0.54))).z,
        "waist": (bone_point(armature, "CC_Base_Waist") or Vector((0, 0, 0.70))).z,
        "neck": (bone_point(armature, "CC_Base_NeckTwist01") or Vector((0, 0, 1.51))).z,
    }
    group_counts = add_region_groups(cage, points, levels)

    anchor_specs = {
        "ArmorAnchor_Chest": ("CC_Base_Spine02", "rigid_armor"),
        "ArmorAnchor_L_Shoulder": ("CC_Base_L_Clavicle", "rigid_armor"),
        "ArmorAnchor_R_Shoulder": ("CC_Base_R_Clavicle", "rigid_armor"),
        "ArmorAnchor_Waist": ("CC_Base_Waist", "layered_accessory"),
        "ArmorAnchor_L_Hand": ("CC_Base_L_Hand", "rigid_armor"),
        "ArmorAnchor_R_Hand": ("CC_Base_R_Hand", "rigid_armor"),
    }
    anchors = []
    for name, (bone_name, category) in anchor_specs.items():
        if armature.data.bones.get(bone_name):
            anchors.append(make_anchor(scene, armature, name, bone_name, category))

    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    scene["assetslab_clothing_cage_schema"] = "assetslab_actor_clothing_cage_v1"
    scene["assetslab_clothing_cage_status"] = "reference_ready_fit_not_yet_validated"
    report = {
        "schema": "assetslab_actor_clothing_cage_v1",
        "source_actor": str(options.actor.resolve()),
        "source_mesh": actor.name,
        "frame": 1,
        "thickness": options.thickness,
        "body_levels": levels,
        "vertex_count": len(points),
        "polygon_count": len(cage_mesh.polygons),
        "region_vertex_counts": group_counts,
        "anchors": [{"name": anchor.name, "bone": anchor["assetslab_bone"], "category": anchor["assetslab_clothing_category"]} for anchor in anchors],
        "supported_categories": ["soft_garment", "rigid_armor", "layered_accessory"],
        "status": "reference_ready_fit_not_yet_validated",
        "next_gate": "fit one simple T-shirt, then four-direction and 8-frame walk validation",
    }
    (output / "actor_clothing_cage_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "actor_clothing_cage_v1.blend"))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
