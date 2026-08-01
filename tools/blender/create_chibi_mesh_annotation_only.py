"""Create the smallest possible Blender file for manual mesh annotation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_original_chibi_actor_test import load_source_mesh  # noqa: E402


GROUPS = ("Bind_Head", "Bind_Neck", "Bind_Torso")


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    options = parser.parse_args(argv)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh = load_source_mesh(options.source, center_source=False)
    mesh.name = "ChibiBaseMesh_ANNOTATE_ONLY"
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    # Apply only Mirror to make the control cage symmetric, then remove the
    # heavy Subsurf modifier. The user only needs a stable low-complexity mesh
    # for selecting regions; the final render keeps the original modifiers.
    for modifier in list(mesh.modifiers):
        if modifier.type == "MIRROR":
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        else:
            mesh.modifiers.remove(modifier)
    for name in GROUPS:
        mesh.vertex_groups.new(name=name)
    scene = bpy.context.scene
    scene["AssetsLabBindingInstructions"] = "Assign Bind_Head, Bind_Neck, and Bind_Torso only. Do not edit geometry."
    scene["AssetsLabSource"] = str(options.source.resolve())
    options.blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.blend))
    manifest = {
        "schema": "assetslab_chibi_mesh_annotation_only_v1",
        "source": str(options.source.resolve()),
        "blend": str(options.blend.resolve()),
        "mesh": mesh.name,
        "vertex_groups": list(GROUPS),
        "modifiers_in_saved_scene": [],
        "status": "awaiting_manual_annotation",
    }
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("CHIBI_MESH_ANNOTATION_ONLY_PASS blend=%s manifest=%s" % (options.blend, options.manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
