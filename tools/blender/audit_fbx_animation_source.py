"""Import and audit an FBX animation source with Blender."""
from __future__ import annotations
import bpy
import sys

def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        raise SystemExit("usage: audit_fbx_animation_source.py -- file.fbx")
    path = argv[0]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path, use_anim=True)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    armatures = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    print("FBX_AUDIT_BEGIN")
    print("source=" + path)
    print("meshes=" + str([(o.name, len(o.data.vertices), len(o.vertex_groups)) for o in meshes]))
    print("armatures=" + str([(o.name, len(o.data.bones)) for o in armatures]))
    print("actions=" + str([(a.name, tuple(a.frame_range), len(a.fcurves)) for a in bpy.data.actions]))
    print("FBX_AUDIT_END")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
