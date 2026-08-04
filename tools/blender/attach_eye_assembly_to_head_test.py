"""Bind the experimental eye assembly rigidly to CC_Base_Head for animation testing."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy


def cli() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--eye", default="MikuChibiEyeball")
    parser.add_argument("--armature", default="Armature")
    return parser.parse_args(argv)


def main() -> None:
    options = cli()
    eye = bpy.data.objects.get(options.eye)
    armature = bpy.data.objects.get(options.armature)
    if eye is None or armature is None or eye.type != "MESH":
        raise RuntimeError("eye mesh or armature missing")
    for modifier in list(eye.modifiers):
        if modifier.type == "ARMATURE":
            eye.modifiers.remove(modifier)
    for group in list(eye.vertex_groups):
        eye.vertex_groups.remove(group)
    head_group = eye.vertex_groups.new(name="CC_Base_Head")
    head_group.add(list(range(len(eye.data.vertices))), 1.0, "REPLACE")
    arm_mod = eye.modifiers.new("EyeAssemblyHeadDeform", "ARMATURE")
    arm_mod.object = armature
    arm_mod.use_deform_preserve_volume = True
    options.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.output.resolve()), compress=True)
    print({"output": str(options.output), "eye": eye.name, "vertices": len(eye.data.vertices), "group": head_group.name})


if __name__ == "__main__":
    main()
