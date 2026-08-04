"""Audit Miku eye geometry, UVs, materials, and source renders."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--fbx", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def object_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector((min(point[i] for point in points) for i in range(3))),
        Vector((max(point[i] for point in points) for i in range(3))),
    )


def material_info(obj: bpy.types.Object) -> list[dict]:
    result = []
    for slot in obj.material_slots:
        material = slot.material
        item = {"name": material.name if material else None, "images": []}
        if material and material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image:
                    item["images"].append(node.image.filepath)
        result.append(item)
    return result


def geometry_info(obj: bpy.types.Object) -> dict:
    mesh = obj.data
    local_points = [vertex.co.copy() for vertex in mesh.vertices]
    low = Vector((min(point[i] for point in local_points) for i in range(3)))
    high = Vector((max(point[i] for point in local_points) for i in range(3)))
    uv_info = {}
    for layer in mesh.uv_layers:
        values = [item.uv.copy() for item in layer.data]
        uv_info[layer.name] = {
            "min": [min(value[i] for value in values) for i in range(2)],
            "max": [max(value[i] for value in values) for i in range(2)],
            "samples": [[round(value.x, 4), round(value.y, 4)] for value in values[:12]],
        }
    components = []
    adjacency = [[] for _ in mesh.vertices]
    for polygon in mesh.polygons:
        indices = list(polygon.vertices)
        for index in indices:
            adjacency[index].extend(other for other in indices if other != index)
    seen = set()
    for start in range(len(mesh.vertices)):
        if start in seen:
            continue
        stack = [start]
        component = set()
        while stack:
            index = stack.pop()
            if index in seen:
                continue
            seen.add(index)
            component.add(index)
            stack.extend(adjacency[index])
        points = [mesh.vertices[index].co for index in component]
        item = {
            "vertices": len(component),
            "local_bounds": [
                [min(point[i] for point in points) for i in range(3)],
                [max(point[i] for point in points) for i in range(3)],
            ],
        }
        if mesh.uv_layers:
            layer = mesh.uv_layers.active
            component_loops = [loop_index for polygon in mesh.polygons for loop_index in polygon.loop_indices if mesh.loops[loop_index].vertex_index in component]
            uv_values = [layer.data[index].uv for index in component_loops]
            if uv_values:
                item["uv_bounds"] = [
                    [min(value[i] for value in uv_values) for i in range(2)],
                    [max(value[i] for value in uv_values) for i in range(2)],
                ]
        components.append(item)
    return {
        "vertices": len(mesh.vertices),
        "polygons": len(mesh.polygons),
        "local_bounds": [list(low), list(high)],
        "world_bounds": [list(object_bounds(obj)[0]), list(object_bounds(obj)[1])],
        "object_location": list(obj.location),
        "object_rotation": list(obj.rotation_euler),
        "object_scale": list(obj.scale),
        "uv": uv_info,
        "materials": material_info(obj),
        "connected_components": components,
    }


def render_source_objects(out: Path, names: list[str]) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world = scene.world or bpy.data.worlds.new("MikuEyeAuditWorld")
    scene.world.color = (0.035, 0.04, 0.06)
    for index, (location, energy, size) in enumerate((((0.0, -500.0, 300.0), 900.0, 250.0), ((-200.0, -300.0, 100.0), 300.0, 150.0))):
        data = bpy.data.lights.new(f"MikuEyeAuditLight{index}", "AREA")
        data.energy = energy
        data.size = size
        light = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(light)
        light.location = location
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.hide_render = obj.name not in names
    shown = [bpy.data.objects[name] for name in names if bpy.data.objects.get(name)]
    low, high = object_bounds(shown[0])
    for obj in shown[1:]:
        obj_low, obj_high = object_bounds(obj)
        low = Vector((min(low[i], obj_low[i]) for i in range(3)))
        high = Vector((max(high[i], obj_high[i]) for i in range(3)))
    target = (low + high) * 0.5
    extent = max(high.x - low.x, high.z - low.z) * 1.35
    for label, location in (("front_minus_y", (target.x, target.y - 600.0, target.z)), ("right_plus_x", (target.x + 600.0, target.y, target.z))):
        data = bpy.data.cameras.new(f"MikuEyeAuditCamera_{label}")
        data.type = "ORTHO"
        data.ortho_scale = extent
        camera = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(camera)
        camera.location = location
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.camera = camera
        scene.render.filepath = str(out / f"{'_'.join(names)}_{label}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)


def main() -> int:
    options = cli_args()
    out = options.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(options.fbx.resolve()), use_anim=True)
    names = ["eyeball_1_0_node", "eye_007_22_0_node"]
    audit = {name: geometry_info(bpy.data.objects[name]) for name in names if bpy.data.objects.get(name)}
    render_source_objects(out, ["eyeball_1_0_node"])
    render_source_objects(out, ["eye_007_22_0_node"])
    (out / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
