"""Sew and drape a GarmentCode pattern with Blender's offline Cloth solver.

The GarmentCode JSON contains 2D panel boundaries and stitch pairs.  This
adapter makes a low-resolution triangle fan for each panel, adds Blender
sewing-spring edges for every stitch pair, pins the shoulder/neck boundary,
and bakes one static 3D result.  It is a production-input experiment, not an
animation-ready clothing asset until the later weight-transfer gate passes.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from render_eye_assembly_blink_walk import configure_lighting, visible_bounds  # noqa: E402
from render_procedural_anime_eye_on_accurig import make_camera  # noqa: E402


DIRECTIONS = {"front": (0.0, -12.0), "right": (12.0, 0.0), "back": (0.0, 12.0), "left": (-12.0, 0.0)}


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor", required=True, type=Path)
    parser.add_argument("--pattern", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fit-scale", type=float, default=1.55)
    parser.add_argument("--settle-frame", type=int, default=60)
    parser.add_argument("--resolution", type=int, default=256)
    return parser.parse_args(argv)


def make_panel_geometry(
    panel: dict,
    scale: float,
    waist_z: float,
    pattern_bottom_y: float,
    edge_segments: int = 12,
) -> tuple[list[tuple[float, float, float]], list[int], list[list[int]]]:
    """Map GarmentCode's supplied 3D panel placement onto the Actor.

    The pattern already contains mirrored sleeve rotations and front/back
    depth translations.  Reusing those placements is more reliable than
    separately guessing sleeve anchors.
    """

    rotation_z = math.radians(float(panel.get("rotation", [0.0, 0.0, 0.0])[2]))
    cos_z, sin_z = math.cos(rotation_z), math.sin(rotation_z)
    tx, ty, tz = [float(value) for value in panel.get("translation", [0.0, 0.0, 0.0])]

    def map_point(u: float, v: float) -> tuple[float, float, float]:
        rotated_x = cos_z * u - sin_z * v
        rotated_y = sin_z * u + cos_z * v
        world_x = (rotated_x + tx) * scale
        # GarmentCode's z translation is the panel depth around the body.
        # Preserve it; the old adapter collapsed every sleeve/front/back panel
        # onto two hard-coded planes, which broke the sewing geometry.
        world_y = -tz * scale
        world_z = waist_z + (rotated_y + ty - pattern_bottom_y) * scale
        return world_x, world_y, world_z

    original_points = [map_point(float(u), float(v)) for u, v in panel["vertices"]]
    points = list(original_points)
    boundary_indices: list[int] = []
    edge_sequences: list[list[int]] = []
    for edge in panel["edges"]:
        start, end = [int(index) for index in edge["endpoints"]]
        sequence = [start]
        start_point = Vector(original_points[start])
        end_point = Vector(original_points[end])
        for step in range(1, edge_segments):
            point = start_point.lerp(end_point, step / edge_segments)
            sequence.append(len(points))
            points.append(tuple(point))
        sequence.append(end)
        edge_sequences.append(sequence)
        boundary_indices.extend(sequence[:-1])

    # Convert panel-local indices to the caller's global mesh index later.
    return points, boundary_indices, edge_sequences


def add_material(obj: bpy.types.Object) -> None:
    material = bpy.data.materials.new("GarmentCodeDrapedCotton")
    material.diffuse_color = (0.12, 0.36, 0.72, 1.0)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    if shader is not None:
        shader.inputs["Base Color"].default_value = material.diffuse_color
        shader.inputs["Roughness"].default_value = 0.86
    obj.data.materials.append(material)


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.actor.resolve()))
    scene = bpy.context.scene
    scene.frame_set(1)
    source = json.loads(options.pattern.resolve().read_text(encoding="utf-8"))["pattern"]
    panel_data = source["panels"]
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    vertices: list[tuple[float, float, float]] = []
    faces: list[list[int]] = []
    panel_global_vertices: dict[str, list[int]] = {}
    panel_global_edges: dict[str, list[list[int]]] = {}
    scale = options.fit_scale * 0.01
    pattern_bottom_y = min(float(panel["translation"][1]) for name, panel in panel_data.items() if "torso" in name)
    for name, panel in panel_data.items():
        local_points, boundary_indices, edge_sequences = make_panel_geometry(panel, scale, 0.70, pattern_bottom_y)
        base = len(vertices)
        vertices.extend(local_points)
        global_boundary = [base + index for index in boundary_indices]
        global_edges = [[base + index for index in sequence] for sequence in edge_sequences]
        panel_global_vertices[name] = global_boundary
        panel_global_edges[name] = global_edges
        # Add a center point and a triangle fan: the source is deliberately
        # low-resolution, but it must have interior cloth vertices to bend.
        center = Vector((0.0, 0.0, 0.0))
        for index in global_boundary:
            center += Vector(vertices[index])
        center /= len(global_boundary)
        center_index = len(vertices)
        vertices.append(tuple(center))
        for index in range(len(global_boundary)):
            faces.append([global_boundary[index], global_boundary[(index + 1) % len(global_boundary)], center_index])

    sewing_edges: list[tuple[int, int]] = []
    for stitch in source["stitches"]:
        if len(stitch) != 2:
            continue
        first, second = stitch
        a_sequence = panel_global_edges[first["panel"]][int(first["edge"])]
        b_sequence = panel_global_edges[second["panel"]][int(second["edge"])]
        direct = sum((Vector(vertices[a]) - Vector(vertices[b])).length for a, b in zip(a_sequence, b_sequence))
        reverse = sum((Vector(vertices[a]) - Vector(vertices[b])).length for a, b in zip(a_sequence, reversed(b_sequence)))
        if reverse < direct:
            b_sequence = list(reversed(b_sequence))
        sewing_edges.extend(zip(a_sequence, b_sequence))

    mesh = bpy.data.meshes.new("GarmentCodeDrapedTshirtMesh")
    mesh.from_pydata(vertices, sewing_edges, faces)
    mesh.update()
    clothing = bpy.data.objects.new("GarmentCodeDrapedTshirt", mesh)
    scene.collection.objects.link(clothing)
    add_material(clothing)

    # Extra edges are sewing springs, not surface edges.  Explicitly mark
    # them for clarity; Blender identifies them as the edges not in faces.
    surface_pairs = {tuple(sorted(edge_key)) for polygon in mesh.polygons for edge_key in polygon.edge_keys}
    sewing_indices = []
    for edge in mesh.edges:
        if tuple(sorted(edge.vertices)) not in surface_pairs:
            edge.use_seam = True
            sewing_indices.append(edge.index)

    pin_group = clothing.vertex_groups.new(name="GarmentShoulderPins")
    for name, panel in panel_data.items():
        if "torso" not in name:
            continue
        global_ids = panel_global_vertices[name]
        for global_id in global_ids:
            if vertices[global_id][2] >= 1.28:
                pin_group.add([global_id], 1.0, "REPLACE")

    cloth = clothing.modifiers.new("GarmentClothSewAndDrape", "CLOTH")
    cloth.settings.quality = 12
    cloth.settings.mass = 0.25
    cloth.settings.tension_stiffness = 50.0
    cloth.settings.compression_stiffness = 50.0
    cloth.settings.shear_stiffness = 20.0
    cloth.settings.bending_stiffness = 2.0
    cloth.settings.air_damping = 5.0
    cloth.settings.use_sewing_springs = True
    cloth.settings.sewing_force_max = 100.0
    cloth.collision_settings.use_self_collision = True
    cloth.collision_settings.self_friction = 5.0
    cloth.settings.vertex_group_mass = pin_group.name
    cloth.settings.pin_stiffness = 100.0

    actor = bpy.data.objects.get("ChibiBaseMesh_AccuRIG_InputMesh")
    if actor is None:
        raise RuntimeError("Actor mesh is missing")
    collision = actor.modifiers.new("GarmentBodyCollision", "COLLISION")
    collision.settings.thickness_outer = 0.015
    collision.settings.thickness_inner = 0.015

    scene.frame_start = 1
    scene.frame_end = options.settle_frame
    scene.frame_set(1)
    bpy.context.view_layer.update()
    scene.frame_set(options.settle_frame)
    bpy.context.view_layer.update()

    scene["assetslab_garmentcode_status"] = "blender_cloth_sewn_static_bake"
    scene["assetslab_garmentcode_sewing_spring_edges"] = len(sewing_indices)
    scene["assetslab_garmentcode_pattern"] = str(options.pattern.resolve())
    scene.render.resolution_x = options.resolution
    scene.render.resolution_y = options.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    low, high = visible_bounds()
    center = (low + high) * 0.5
    configure_lighting(scene, center, "soft_flat")
    scene.view_settings.exposure = 0.25
    ortho_scale = max(high.z - low.z, high.x - low.x, high.y - low.y) * 1.16
    frames = []
    for direction, (x, y) in DIRECTIONS.items():
        camera = make_camera(scene, center, f"GarmentCodeDraped_{direction}", (x, y, center.z), ortho_scale)
        scene.camera = camera
        frame_path = output / f"{direction}_00.png"
        scene.render.filepath = str(frame_path)
        bpy.ops.render.render(write_still=True)
        frames.append({"direction": direction, "sample_index": 0, "source_frame": options.settle_frame, "path": frame_path.name})

    # Freeze the simulated frame as a separate mesh.  Keep the source scene
    # with modifiers too, so failed results remain diagnosable.
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = clothing.evaluated_get(depsgraph)
    baked_mesh = evaluated.to_mesh()
    baked = clothing.copy()
    baked.data = baked_mesh.copy()
    baked.name = "GarmentCodeDrapedTshirt_BAKED"
    scene.collection.objects.link(baked)
    baked.modifiers.clear()
    baked["assetslab_baked_from_frame"] = options.settle_frame
    baked["assetslab_requires_weight_transfer"] = True
    clothing.hide_render = True
    clothing.hide_viewport = True
    evaluated.to_mesh_clear()
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "garmentcode_draped_tshirt.blend"))
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "assetslab_garmentcode_cloth_review_v1",
                "generator": "GarmentCode_MIT_plus_Blender_Cloth",
                "pattern": str(options.pattern.resolve()),
                "fit_scale": options.fit_scale,
                "settle_frame": options.settle_frame,
                "sewing_spring_edges": len(sewing_indices),
                "direction_count": len(DIRECTIONS),
                "frame_count_per_direction": 1,
                "status": "review_required_failed_fit",
                "failure_reason": "default GarmentCode body/panel proportions do not fit the Q-version Actor; shoulder and sleeve seams remain unstable",
                "frames": frames,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": scene["assetslab_garmentcode_status"], "sewing_spring_edges": len(sewing_indices), "baked_blend": str(output / "garmentcode_draped_tshirt.blend")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
