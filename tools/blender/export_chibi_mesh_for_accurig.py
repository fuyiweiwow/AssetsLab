"""Export the downloaded chibi mesh as a clean neutral FBX for AccuRIG."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_original_chibi_actor_test as binding  # noqa: E402


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-fbx", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    return parser.parse_args(argv)


def apply_display_modifiers(mesh: bpy.types.Object) -> list[dict[str, str]]:
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    return binding.apply_source_display_modifiers(mesh)


def main() -> int:
    options = cli_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # The vendor mesh is a right-half mesh whose Mirror plane is at the
    # original object origin. Apply that modifier before centering; centering
    # the half mesh first moves the mirror plane into the wrong place.
    mesh = binding.load_source_mesh(options.source, center_source=False)
    applied = apply_display_modifiers(mesh)
    mesh.name = "ChibiBaseMesh_AccuRIG_Input"
    mesh.data.name = "ChibiBaseMesh_AccuRIG_InputMesh"
    low_before, high_before = binding.bounds(mesh)
    center = Vector(((low_before.x + high_before.x) * 0.5, (low_before.y + high_before.y) * 0.5, low_before.z))
    mesh.data.transform(Matrix.Translation(-center))
    mesh.data.update()
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    options.output_fbx.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.fbx(
        filepath=str(options.output_fbx),
        use_selection=True,
        object_types={"MESH"},
        add_leaf_bones=False,
        bake_anim=False,
        apply_scale_options="FBX_SCALE_ALL",
        path_mode="AUTO",
    )

    low, high = binding.bounds(mesh)
    manifest = {
        "schema": "assetslab_chibi_accurig_input_v1",
        "source": str(options.source),
        "output_fbx": str(options.output_fbx),
        "mesh_name": mesh.name,
        "vertex_count": len(mesh.data.vertices),
        "polygon_count": len(mesh.data.polygons),
        "source_modifier_actions": applied,
        "centered_on_xy": True,
        "bottom_at_z": round(low.z, 6),
        "bounds_min": list(low),
        "bounds_max": list(high),
        "armature_included": False,
        "camera_included": False,
        "neutral_pose": True,
    }
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"CHIBI_ACCURIG_EXPORT_PASS fbx={options.output_fbx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
