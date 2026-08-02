"""Reweight only the Boolean socket neighborhood to the head bone for a test."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target", default="ChibiActor_MCP_PreciseEyeSocket_Test")
    parser.add_argument("--armature", default="Armature")
    return parser.parse_args(argv)


def main() -> None:
    options = cli()
    target = bpy.data.objects.get(options.target)
    armature = bpy.data.objects.get(options.armature)
    if target is None or armature is None:
        raise RuntimeError("target or armature missing")
    head_group = target.vertex_groups.get("CC_Base_Head")
    if head_group is None:
        head_group = target.vertex_groups.new(name="CC_Base_Head")
    changed = []
    for vertex in target.data.vertices:
        point = target.matrix_world @ vertex.co
        in_socket_band = abs(point.x) <= 0.82 and 1.62 <= point.z <= 2.58 and point.y <= -0.12
        if not in_socket_band:
            continue
        for assignment in list(vertex.groups):
            group = target.vertex_groups[assignment.group]
            group.remove([vertex.index])
        head_group.add([vertex.index], 1.0, "REPLACE")
        changed.append(vertex.index)
    bpy.context.scene["TEST_socket_reweighted_vertex_count"] = len(changed)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.output.resolve()), compress=True)
    print({"output": str(options.output), "reweighted_vertices": len(changed), "group": head_group.name})


if __name__ == "__main__":
    main()
