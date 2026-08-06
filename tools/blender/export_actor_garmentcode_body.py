"""Export the evaluated Actor mesh as a GarmentCode collision-body OBJ.

GarmentCode body assets use centimetres while the AssetsLab Actor uses metres.
The exported mesh is therefore scaled by 100 and kept separate from the Actor
blend.  This is an authoring/research input, not a replacement Actor asset.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--object", default="ChibiBaseMesh_AccuRIG_InputMesh")
    parser.add_argument("--frame", type=int, default=1)
    parser.add_argument("--scale", type=float, default=100.0)
    parser.add_argument("--voxel-size", type=float, default=0.0, help="optional Blender-local voxel remesh size")
    return parser.parse_args(argv)


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.actor.resolve()))
    scene = bpy.context.scene
    scene.frame_set(options.frame)
    bpy.context.view_layer.update()
    actor = bpy.data.objects.get(options.object)
    if actor is None or actor.type != "MESH":
        raise RuntimeError(f"Actor mesh not found: {options.object}")

    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = actor.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
    body = bpy.data.objects.new("AssetsLabActorGarmentCodeBody", mesh)
    scene.collection.objects.link(body)
    # The Actor mesh datablock is already authored in centimetre-like units;
    # its 0.01 object matrix is only the Blender metre conversion.  Export the
    # evaluated local mesh directly and apply an optional explicit scale once.
    body.matrix_world.identity()
    body.scale = (options.scale / 100.0, options.scale / 100.0, options.scale / 100.0)

    if options.voxel_size > 0.0:
        remesh = body.modifiers.new("GarmentCodeClosedCollisionRemesh", "REMESH")
        remesh.mode = "VOXEL"
        remesh.voxel_size = options.voxel_size
        remesh.adaptivity = 0.0
        remesh.use_remove_disconnected = False
        bpy.context.view_layer.objects.active = body
        body.select_set(True)
        bpy.ops.object.modifier_apply(modifier=remesh.name)

    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    output = options.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.obj_export(
        filepath=str(output),
        export_materials=False,
        export_selected_objects=True,
        apply_modifiers=False,
    )
    print(f"ACTOR_GARMENTCODE_BODY_EXPORT_PASS path={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
