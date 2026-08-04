"""Audit the procedural anime eye's geometry and material construction."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.source.resolve()))
    records = []
    for name in ("EyeL", "EyeR"):
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        low = [min(v.co[i] for v in obj.data.vertices) for i in range(3)]
        high = [max(v.co[i] for v in obj.data.vertices) for i in range(3)]
        mats = []
        for material in obj.data.materials:
            if material is None:
                continue
            nodes = []
            for node in material.node_tree.nodes if material.use_nodes else []:
                nodes.append({
                    "name": node.name,
                    "type": node.bl_idname,
                    "inputs": [socket.name for socket in node.inputs],
                })
            mats.append({"name": material.name, "nodes": nodes})
        records.append({
            "object": name,
            "vertices": len(obj.data.vertices),
            "polygons": len(obj.data.polygons),
            "local_bounds": {"min": low, "max": high},
            "materials": mats,
        })
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps({"schema": "assetslab_procedural_eye_material_audit_v1", "source": str(options.source.resolve()), "eyes": records}, indent=2), encoding="utf-8")
    print(f"PROCEDURAL_EYE_MATERIAL_AUDIT_PASS output={options.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
