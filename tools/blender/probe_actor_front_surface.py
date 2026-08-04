"""Probe the actor's front surface at eye-region x/z coordinates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--object", default="ChibiBaseMesh_AccuRIG_InputMesh")
    parser.add_argument("--x", nargs="+", type=float, default=[-0.3, 0.0, 0.3])
    parser.add_argument("--z", nargs="+", type=float, default=[2.0, 2.2, 2.4])
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    options = parser.parse_args(argv)
    bpy.ops.wm.open_mainfile(filepath=str(options.blend.resolve()))
    obj = bpy.data.objects.get(options.object)
    if obj is None:
        raise RuntimeError(f"missing object: {options.object}")
    for z in options.z:
        for x in options.x:
            inverse = obj.matrix_world.inverted()
            origin = inverse @ Vector((x, -2.0, z))
            direction = (inverse.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
            hit, location, normal, index = obj.ray_cast(origin, direction)
            world_location = obj.matrix_world @ location
            print("sample", x, z, "hit", hit, "point", tuple(round(v, 5) for v in world_location), "face", index)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
