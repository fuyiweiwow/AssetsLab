"""Drape GarmentCode panels on the matching GarmentCode body.

This isolates garment construction from the later Actor fitting problem. The
standard body is used only as a static collision surface; the result is not
yet a runtime asset.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from render_eye_assembly_blink_walk import configure_lighting, visible_bounds  # noqa: E402
from render_procedural_anime_eye_on_accurig import make_camera  # noqa: E402
from simulate_garmentcode_pattern_cloth import DIRECTIONS, make_panel_geometry  # noqa: E402


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-blend", required=True, type=Path)
    parser.add_argument("--body-obj", required=True, type=Path)
    parser.add_argument("--pattern", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fit-scale", type=float, default=1.0)
    parser.add_argument("--settle-frame", type=int, default=120)
    parser.add_argument("--resolution", type=int, default=256)
    return parser.parse_args(argv)


def material(name: str, color: tuple[float, float, float, float], roughness: float = 0.86) -> bpy.types.Material:
    result = bpy.data.materials.new(name)
    result.diffuse_color = color
    result.use_nodes = True
    shader = result.node_tree.nodes.get("Principled BSDF")
    if shader:
        shader.inputs["Base Color"].default_value = color
        shader.inputs["Roughness"].default_value = roughness
    return result


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.base_blend.resolve()))
    scene = bpy.context.scene
    scene.frame_set(1)
    for obj in scene.objects:
        if obj.type == "MESH":
            obj.hide_render = True
            obj.hide_viewport = True

    bpy.ops.wm.obj_import(filepath=str(options.body_obj.resolve()))
    body = next((obj for obj in reversed(bpy.context.selected_objects) if obj.type == "MESH"), None)
    if body is None:
        raise RuntimeError("GarmentCode body OBJ did not import as a mesh")
    body.name = "GarmentCodeMatchedBody"
    body.hide_render = False
    body.hide_viewport = False
    body.data.materials.append(material("GarmentCodeMatchedBodyMaterial", (0.62, 0.65, 0.70, 1.0), 0.92))
    collision = body.modifiers.new("MatchedBodyCollision", "COLLISION")
    collision.settings.thickness_outer = 0.008
    collision.settings.thickness_inner = 0.008

    source = json.loads(options.pattern.resolve().read_text(encoding="utf-8"))["pattern"]
    panel_data = source["panels"]
    torso_panels = [panel for name, panel in panel_data.items() if "torso" in name]
    reference_panels = torso_panels or list(panel_data.values())
    pattern_bottom_y = min(float(panel["translation"][1]) for panel in reference_panels)
    scale = options.fit_scale * 0.01
    vertices: list[tuple[float, float, float]] = []
    faces: list[list[int]] = []
    panel_global_edges: dict[str, list[list[int]]] = {}
    panel_global_boundary: dict[str, list[int]] = {}
    for name, panel in panel_data.items():
        points, boundary, edge_sequences = make_panel_geometry(panel, scale, 0.70, pattern_bottom_y)
        base = len(vertices)
        vertices.extend(points)
        panel_global_boundary[name] = [base + index for index in boundary]
        panel_global_edges[name] = [[base + index for index in sequence] for sequence in edge_sequences]
        center = Vector((0.0, 0.0, 0.0))
        for index in panel_global_boundary[name]:
            center += Vector(vertices[index])
        center /= max(len(panel_global_boundary[name]), 1)
        center_index = len(vertices)
        vertices.append(tuple(center))
        boundary = panel_global_boundary[name]
        for index in range(len(boundary)):
            faces.append([boundary[index], boundary[(index + 1) % len(boundary)], center_index])

    sewing_edges: list[tuple[int, int]] = []
    for stitch in source["stitches"]:
        if len(stitch) != 2:
            continue
        first, second = stitch
        left = panel_global_edges[first["panel"]][int(first["edge"])]
        right = panel_global_edges[second["panel"]][int(second["edge"])]
        direct = sum((Vector(vertices[a]) - Vector(vertices[b])).length for a, b in zip(left, right))
        reverse = sum((Vector(vertices[a]) - Vector(vertices[b])).length for a, b in zip(left, reversed(right)))
        if reverse < direct:
            right = list(reversed(right))
        sewing_edges.extend(zip(left, right))

    mesh = bpy.data.meshes.new("GarmentCodeMatchedBodyTshirtMesh")
    mesh.from_pydata(vertices, sewing_edges, faces)
    mesh.update()
    clothing = bpy.data.objects.new("GarmentCodeMatchedBodyTshirt", mesh)
    scene.collection.objects.link(clothing)
    mesh.materials.append(material("GarmentCodeMatchedBodyCotton", (0.12, 0.36, 0.72, 1.0)))

    pin_group = clothing.vertex_groups.new(name="MatchedBodyShoulderPins")
    has_torso = any("torso" in name for name in panel_global_boundary)
    anchor_tokens = ("torso",) if has_torso else ("pant",)
    clothing_points = [Vector(point) for point in vertices]
    highest = max(point.z for point in clothing_points)
    for name, indices in panel_global_boundary.items():
        if not any(token in name for token in anchor_tokens):
            continue
        for index in indices:
            if vertices[index][2] >= highest - (0.10 if not has_torso else 0.25):
                pin_group.add([index], 1.0, "REPLACE")

    cloth = clothing.modifiers.new("MatchedBodyGarmentCloth", "CLOTH")
    cloth.settings.quality = 12
    cloth.settings.mass = 0.25
    cloth.settings.tension_stiffness = 50.0
    cloth.settings.compression_stiffness = 50.0
    cloth.settings.shear_stiffness = 20.0
    cloth.settings.bending_stiffness = 2.0
    cloth.settings.air_damping = 5.0
    cloth.settings.use_sewing_springs = True
    cloth.settings.sewing_force_max = 100.0
    cloth.settings.vertex_group_mass = pin_group.name
    cloth.settings.pin_stiffness = 100.0
    cloth.collision_settings.use_self_collision = True
    cloth.collision_settings.self_friction = 5.0

    scene.frame_start = 1
    scene.frame_end = options.settle_frame
    scene.frame_set(1)
    bpy.context.view_layer.update()
    scene.frame_set(options.settle_frame)
    bpy.context.view_layer.update()

    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    scene["assetslab_garmentcode_status"] = "matched_body_drape_baked"
    scene["assetslab_garmentcode_pattern"] = str(options.pattern.resolve())
    low, high = visible_bounds()
    center = (low + high) * 0.5
    configure_lighting(scene, center, "soft_flat")
    scene.view_settings.exposure = 0.25
    scene.render.resolution_x = options.resolution
    scene.render.resolution_y = options.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    ortho_scale = max(high.z - low.z, high.x - low.x, high.y - low.y) * 1.16
    frames = []
    for direction, (x, y) in DIRECTIONS.items():
        camera = make_camera(scene, center, f"MatchedBody_{direction}", (x, y, center.z), ortho_scale)
        scene.camera = camera
        frame_path = output / f"{direction}_00.png"
        scene.render.filepath = str(frame_path)
        bpy.ops.render.render(write_still=True)
        frames.append({"direction": direction, "sample_index": 0, "path": frame_path.name})
        bpy.data.objects.remove(camera, do_unlink=True)

    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = clothing.evaluated_get(depsgraph)
    baked_mesh = evaluated.to_mesh()
    baked = clothing.copy()
    baked.data = baked_mesh.copy()
    baked.name = "GarmentCodeMatchedBodyTshirt_BAKED"
    scene.collection.objects.link(baked)
    baked.modifiers.clear()
    baked["assetslab_requires_actor_cage_transfer"] = True
    clothing.hide_render = True
    clothing.hide_viewport = True
    evaluated.to_mesh_clear()
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "garmentcode_matched_body_tshirt.blend"))
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "assetslab_garmentcode_matched_body_review_v1",
                "generator": "GarmentCode_MIT_plus_Blender_Cloth",
                "body": str(options.body_obj.resolve()),
                "pattern": str(options.pattern.resolve()),
                "fit_scale": options.fit_scale,
                "settle_frame": options.settle_frame,
                "status": "matched_body_drape_baked",
                "next_stage": "transfer_baked_garment_to_actor_cage",
                "anchor_region": "torso" if has_torso else "pants_waist",
                "frames": frames,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "matched_body_drape_baked", "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
