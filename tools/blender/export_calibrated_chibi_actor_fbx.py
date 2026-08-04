"""Export the calibrated actor rig from the accepted Blend as a clean FBX."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy


ARMATURE_NAME = "Armature"
BODY_NAME = "ChibiBaseMesh_AccuRIG_InputMesh"


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-blend", required=True, type=Path)
    parser.add_argument("--output-fbx", required=True, type=Path)
    return parser.parse_args(argv)


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.input_blend.resolve()))
    armature = bpy.data.objects.get(ARMATURE_NAME)
    body = bpy.data.objects.get(BODY_NAME)
    if armature is None or armature.type != "ARMATURE":
        raise RuntimeError(f"missing calibrated armature {ARMATURE_NAME}")
    if body is None or body.type != "MESH":
        raise RuntimeError(f"missing calibrated body mesh {BODY_NAME}")
    if body.parent != armature or len(armature.data.bones) != 101:
        raise RuntimeError("source is not the expected 101-bone calibrated actor")

    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = armature
    options.output_fbx.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.fbx(
        filepath=str(options.output_fbx.resolve()),
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        use_mesh_modifiers=True,
        add_leaf_bones=False,
        bake_anim=False,
        path_mode="AUTO",
        apply_scale_options="FBX_SCALE_UNITS",
    )
    print(
        "CALIBRATED_CHIBI_FBX_EXPORT_PASS "
        f"mesh={BODY_NAME} bones={len(armature.data.bones)} output={options.output_fbx.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
