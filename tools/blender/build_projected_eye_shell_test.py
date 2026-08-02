"""Build the clean projected Miku eye-shell recipe on the stable actor baseline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


def cli() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target", default="ChibiActor_MCP_PreciseEyeSocket_Test")
    parser.add_argument("--armature", default="Armature")
    return parser.parse_args(argv)


def main() -> None:
    options = cli()
    recipe = json.loads(options.recipe.read_text(encoding="utf-8"))
    target = bpy.data.objects.get(options.target)
    armature = bpy.data.objects.get(options.armature)
    if target is None or armature is None:
        raise RuntimeError("target or armature missing")
    mesh = bpy.data.meshes.new("GEO_MikuProjectedEyeShell_Mesh")
    mesh.from_pydata(recipe["vertices"], [], recipe["faces"])
    mesh.update()
    shell = bpy.data.objects.new("GEO_MikuProjectedEyeShell", mesh)
    bpy.context.scene.collection.objects.link(shell)
    if target.data.materials:
        shell.data.materials.append(target.data.materials[0])
    shrink = shell.modifiers.new("ProjectedShellShrinkwrap", "SHRINKWRAP")
    shrink.target = target
    shrink.wrap_method = "PROJECT"
    shrink.wrap_mode = "ON_SURFACE"
    shrink.use_project_y = True
    shrink.use_positive_direction = True
    shrink.use_negative_direction = False
    shrink.offset = 0.002
    bpy.context.view_layer.objects.active = shell
    shell.select_set(True)
    bpy.ops.object.modifier_apply(modifier=shrink.name)
    shell.select_set(False)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    group = shell.vertex_groups.new(name="CC_Base_Head")
    group.add(list(range(len(mesh.vertices))), 1.0, "REPLACE")
    arm_mod = shell.modifiers.new("ProjectedShellHeadDeform", "ARMATURE")
    arm_mod.object = armature
    arm_mod.use_deform_preserve_volume = True
    shell["source"] = recipe["source"]
    shell["construction"] = "projected_contour_triangulated_shrinkwrapped"
    options.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.output.resolve()), compress=True)
    print({"output": str(options.output), "object": shell.name, "vertices": len(mesh.vertices), "faces": len(mesh.polygons), "source": recipe["source"]})


if __name__ == "__main__":
    main()
