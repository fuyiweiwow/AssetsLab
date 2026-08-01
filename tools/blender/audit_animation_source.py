"""Audit a Blender file for a usable rig and animation source.

Run with Blender's bundled Python:
    blender --background model.blend --python audit_animation_source.py
"""

from __future__ import annotations

import bpy


def main() -> int:
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    actions = list(bpy.data.actions)
    nla_strips = []
    for obj in bpy.data.objects:
        animation = obj.animation_data
        if not animation or not animation.nla_tracks:
            continue
        for track in animation.nla_tracks:
            nla_strips.extend(strip.name for strip in track.strips)

    weighted_meshes = []
    for mesh in meshes:
        armature_modifiers = [modifier for modifier in mesh.modifiers if modifier.type == "ARMATURE"]
        weighted_meshes.append({
            "name": mesh.name,
            "vertex_groups": len(mesh.vertex_groups),
            "armature_modifiers": [modifier.object.name if modifier.object else None for modifier in armature_modifiers],
        })

    report = {
        "blend_file": bpy.data.filepath,
        "meshes": [{"name": mesh.name, "vertices": len(mesh.data.vertices), "polygons": len(mesh.data.polygons)} for mesh in meshes],
        "armatures": [{"name": armature.name, "bones": len(armature.data.bones)} for armature in armatures],
        "actions": [{"name": action.name, "frame_start": action.frame_range[0], "frame_end": action.frame_range[1]} for action in actions],
        "nla_strips": nla_strips,
        "weighted_meshes": weighted_meshes,
        "usable_rig_candidate": bool(armatures and any(item["vertex_groups"] and item["armature_modifiers"] for item in weighted_meshes)),
        "usable_animation_candidate": bool(actions or nla_strips),
    }
    print("ASSET_AUDIT_BEGIN")
    for key, value in report.items():
        print(f"{key}={value}")
    print("ASSET_AUDIT_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
