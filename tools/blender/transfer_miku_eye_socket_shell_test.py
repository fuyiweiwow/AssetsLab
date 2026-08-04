"""Transfer Miku's skin eye-shell candidate together with the actor eye assembly."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


def cli() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--actor", default="ChibiActor_MCP_PreciseEyeSocket_Test")
    parser.add_argument("--eye", default="MikuChibiEyeball")
    parser.add_argument("--shell", default="eye_007_22_0_node")
    parser.add_argument("--armature", default="Armature")
    return parser.parse_args(argv)


def bounds(points: list[Vector]) -> tuple[Vector, Vector]:
    return Vector((min(p[i] for p in points) for i in range(3))), Vector((max(p[i] for p in points) for i in range(3)))


def add_head_binding(obj: bpy.types.Object, armature: bpy.types.Object) -> None:
    for group in list(obj.vertex_groups):
        obj.vertex_groups.remove(group)
    group = obj.vertex_groups.new(name="CC_Base_Head")
    group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
    for modifier in list(obj.modifiers):
        if modifier.type == "ARMATURE":
            obj.modifiers.remove(modifier)
    arm_mod = obj.modifiers.new("MikuEyeShellHeadDeform", "ARMATURE")
    arm_mod.object = armature
    arm_mod.use_deform_preserve_volume = True


def main() -> None:
    options = cli()
    actor = bpy.data.objects.get(options.actor)
    eye = bpy.data.objects.get(options.eye)
    source = bpy.data.objects.get(options.shell)
    armature = bpy.data.objects.get(options.armature)
    if None in (actor, eye, source, armature):
        raise RuntimeError("actor, eye, shell, or armature missing")
    source_points = [source.matrix_world @ vertex.co for vertex in source.data.vertices]
    eye_points = [eye.matrix_world @ vertex.co for vertex in eye.data.vertices]
    src_low, src_high = bounds(source_points)
    eye_low, eye_high = bounds(eye_points)
    target_low = Vector((eye_low.x * 1.04, -0.70, eye_low.z - 0.045))
    target_high = Vector((eye_high.x * 1.04, -0.58, eye_high.z + 0.055))
    src_extent = src_high - src_low
    target_extent = target_high - target_low
    source_center = (src_low + src_high) * 0.5
    target_center = (target_low + target_high) * 0.5
    vertices = []
    for point in source_points:
        normalized = Vector(((point.x - source_center.x) / max(src_extent.x, 1e-6), (point.y - source_center.y) / max(src_extent.y, 1e-6), (point.z - source_center.z) / max(src_extent.z, 1e-6)))
        vertices.append(target_center + Vector((normalized.x * target_extent.x, normalized.y * target_extent.y, normalized.z * target_extent.z)))
    mesh = bpy.data.meshes.new("GEO_MikuEyeSocketShell_Mesh")
    mesh.from_pydata(vertices, [], [[v for v in polygon.vertices] for polygon in source.data.polygons])
    mesh.update()
    shell = bpy.data.objects.new("GEO_MikuEyeSocketShell", mesh)
    bpy.context.scene.collection.objects.link(shell)
    for material in source.data.materials:
        if material is not None:
            shell.data.materials.append(material)
    if not shell.data.materials and actor.data.materials:
        shell.data.materials.append(actor.data.materials[0])
    add_head_binding(shell, armature)
    source.hide_render = True
    source.hide_viewport = True
    source.hide_set(True)
    shell["source_object"] = options.shell
    shell["transfer_mode"] = "source_locked_xz_scaled_shallow_y"
    options.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.output.resolve()), compress=True)
    print({"output": str(options.output), "shell": shell.name, "source": options.shell, "vertices": len(vertices), "source_bounds": [list(src_low), list(src_high)], "target_bounds": [list(target_low), list(target_high)]})


if __name__ == "__main__":
    main()
