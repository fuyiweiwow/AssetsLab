"""Export the three required vertex groups from the mesh-only annotation file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy

GROUPS = ("Bind_Head", "Bind_Neck", "Bind_Torso")


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args(argv)
    bpy.ops.wm.open_mainfile(filepath=str(options.blend.resolve()))
    mesh = bpy.data.objects.get("ChibiBaseMesh_ANNOTATE_ONLY")
    if mesh is None or mesh.type != "MESH":
        raise SystemExit("CHIBI_MESH_GROUP_EXPORT_FAIL: annotation mesh not found")
    groups = {}
    for name in GROUPS:
        group = mesh.vertex_groups.get(name)
        if group is None:
            groups[name] = []
        else:
            groups[name] = sorted(vertex.index for vertex in mesh.data.vertices if any(item.group == group.index for item in vertex.groups))
    missing = [name for name, indices in groups.items() if not indices]
    data = {
        "schema": "assetslab_chibi_mesh_groups_v1",
        "source_blend": str(options.blend.resolve()),
        "mesh": mesh.name,
        "groups": {name: {"vertex_count": len(indices), "vertices": indices} for name, indices in groups.items()},
        "missing_groups": missing,
        "status": "complete" if not missing else "incomplete",
    }
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(data, indent=2), encoding="utf-8")
    if missing:
        print("CHIBI_MESH_GROUP_EXPORT_INCOMPLETE missing=%s output=%s" % (",".join(missing), options.output))
    else:
        print("CHIBI_MESH_GROUP_EXPORT_PASS groups=3 output=%s" % options.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
