"""Export manual vertex-group and bone annotations from the assistant blend."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


GROUPS = ("Bind_Head", "Bind_Neck", "Bind_Torso", "Bind_Arm_L", "Bind_Arm_R", "Bind_Leg_L", "Bind_Leg_R")
REQUIRED_GROUPS = ("Bind_Head", "Bind_Neck", "Bind_Torso")


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.blend.resolve()))
    mesh = bpy.data.objects.get("ChibiBaseMesh_ANNOTATE")
    rig = bpy.data.objects.get("ChibiManualBindingRig")
    if mesh is None or mesh.type != "MESH":
        raise SystemExit("CHIBI_BINDING_EXPORT_FAIL: annotation mesh not found")
    if rig is None or rig.type != "ARMATURE":
        raise SystemExit("CHIBI_BINDING_EXPORT_FAIL: annotation rig not found")
    groups = {}
    for name in GROUPS:
        group = mesh.vertex_groups.get(name)
        if group is None:
            groups[name] = []
            continue
        groups[name] = sorted(vertex.index for vertex in mesh.data.vertices if any(item.group == group.index for item in vertex.groups))
    bones = {}
    for bone in rig.data.bones:
        bones[bone.name] = {
            "head": [round(value, 6) for value in bone.head_local],
            "tail": [round(value, 6) for value in bone.tail_local],
            "parent": bone.parent.name if bone.parent else None,
        }
    missing_required = [name for name in REQUIRED_GROUPS if not groups[name]]
    missing_optional = [name for name in GROUPS if name not in REQUIRED_GROUPS and not groups[name]]
    annotation = {
        "schema": "assetslab_chibi_manual_binding_annotation_v1",
        "source_blend": str(options.blend.resolve()),
        "mesh": mesh.name,
        "armature": rig.name,
        "groups": {name: {"vertex_count": len(indices), "vertices": indices} for name, indices in groups.items()},
        "bones": bones,
        "missing_required_groups": missing_required,
        "missing_optional_groups": missing_optional,
        "status": "complete" if not missing_required else "incomplete",
    }
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(annotation, indent=2), encoding="utf-8")
    if missing_required:
        print("CHIBI_BINDING_EXPORT_INCOMPLETE missing_required=%s output=%s" % (",".join(missing_required), options.output))
    else:
        print("CHIBI_BINDING_EXPORT_PASS required_groups=3 optional_missing=%d bones=%d output=%s" % (len(missing_optional), len(bones), options.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
