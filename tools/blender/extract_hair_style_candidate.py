"""Extract one hair tile from a grid OBJ and attach it to the chibi actor."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HEAD_BONE = "CC_Base_Head"


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--hair-obj", required=True, type=Path)
    parser.add_argument("--actor-blend", required=True, type=Path)
    parser.add_argument("--output-blend", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--group-name", type=str)
    parser.add_argument("--single-mesh", action="store_true")
    parser.add_argument("--row", type=int)
    parser.add_argument("--column", type=int)
    parser.add_argument("--rows", type=int, default=7)
    parser.add_argument("--columns", type=int, default=11)
    parser.add_argument("--color", nargs=4, type=float, default=(0.12, 0.045, 0.025, 1.0))
    parser.add_argument(
        "--q-height-ratio",
        type=float,
        default=1.35,
        help="maximum hair height as a multiple of the actor head width",
    )
    return parser.parse_args(argv)


def bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector((min(point[i] for point in points) for i in range(3))),
        Vector((max(point[i] for point in points) for i in range(3))),
    )


def make_material(color: tuple[float, float, float, float]) -> bpy.types.Material:
    material = bpy.data.materials.new("HairCandidatePreviewMaterial")
    material.diffuse_color = color
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 0.78
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.18
    return material


def import_tile(
    path: Path,
    row: int | None,
    column: int | None,
    rows: int,
    columns: int,
    group_name: str | None,
    single_mesh: bool,
) -> bpy.types.Object:
    before = {obj.as_pointer() for obj in bpy.data.objects}
    bpy.ops.wm.obj_import(filepath=str(path.resolve()), use_split_groups=bool(group_name))
    imported = [obj for obj in bpy.data.objects if obj.as_pointer() not in before and obj.type == "MESH"]
    if single_mesh:
        if len(imported) != 1:
            raise RuntimeError(f"expected one imported hair mesh, found {len(imported)}")
        tile = imported[0]
        tile.name = "HairCandidate_SingleMesh"
        return tile
    if group_name:
        matching = [obj for obj in imported if obj.name == group_name or obj.name.startswith(group_name + ".")]
        if len(matching) != 1:
            names = ", ".join(obj.name for obj in imported)
            raise RuntimeError(f"hair group not found: {group_name}; available={names}")
        tile = matching[0]
        for obj in imported:
            if obj is not tile:
                bpy.data.objects.remove(obj, do_unlink=True)
        tile.name = "HairCandidate_" + group_name
        return tile
    if len(imported) != 1:
        raise RuntimeError(f"expected one imported hair mesh, found {len(imported)}")
    if row is None or column is None:
        raise RuntimeError("row and column are required when group-name is not supplied")
    source = imported[0]
    low, high = bounds(source)
    # Centers estimated from the density of the downloaded collection. The
    # styles are not aligned to the outer bounding-box grid, so midpoint
    # boundaries keep each complete hairstyle together.
    x_centers = [-347.6, -273.3, -199.7, -124.1, -47.9, 2.7, 66.9, 136.6, 202.5, 265.2, 339.0]
    z_centers = [11.4, 79.9, 151.8, 218.8, 279.5, 339.0, 406.8]
    if columns != len(x_centers) or rows != len(z_centers):
        x_centers = [low.x + (high.x - low.x) * (index + 0.5) / columns for index in range(columns)]
        z_centers = [low.z + (high.z - low.z) * (index + 0.5) / rows for index in range(rows)]
    col_center = x_centers[column - 1]
    row_center = z_centers[rows - row]
    x_low = (x_centers[column - 2] + col_center) * 0.5 if column > 1 else low.x
    x_high = (col_center + x_centers[column]) * 0.5 if column < columns else high.x
    z_low = (z_centers[rows - row - 1] + row_center) * 0.5 if row < rows else low.z
    z_high = (row_center + z_centers[rows - row + 1]) * 0.5 if row > 1 else high.z
    if not (1 <= row <= rows and 1 <= column <= columns):
        raise ValueError(f"tile must be row 1..{rows}, column 1..{columns}")
    bpy.context.view_layer.objects.active = source
    bpy.ops.object.select_all(action="DESELECT")
    source.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(source.data)
    for vertex in bm.verts:
        vertex.select = False
    selected = 0
    for face in bm.faces:
        center = source.matrix_world @ face.calc_center_median()
        face.select = x_low <= center.x <= x_high and z_low <= center.z <= z_high
        if face.select:
            selected += 1
            for vertex in face.verts:
                vertex.select = True
    if selected == 0:
        bpy.ops.object.mode_set(mode="OBJECT")
        raise RuntimeError(f"no faces found in row={row} column={column}")
    bmesh.update_edit_mesh(source.data)
    bpy.ops.mesh.separate(type="SELECTED")
    bpy.ops.object.mode_set(mode="OBJECT")
    candidates = [obj for obj in bpy.data.objects if obj.as_pointer() not in before and obj.type == "MESH"]
    # The original object retains the unselected remainder; Blender creates a
    # smaller new object for the selected tile.
    tile = min(candidates, key=lambda obj: len(obj.data.polygons))
    for obj in candidates:
        if obj is not tile:
            bpy.data.objects.remove(obj, do_unlink=True)
    tile.name = f"HairCandidate_r{row:02d}_c{column:02d}"
    return tile


def head_target(armature: bpy.types.Object, body: bpy.types.Object) -> tuple[Vector, float, float]:
    head_bone = armature.data.bones[HEAD_BONE]
    head_world = armature.matrix_world @ head_bone.head_local
    head_vertices = [
        body.matrix_world @ vertex.co
        for vertex in body.data.vertices
        if (body.matrix_world @ vertex.co).z > head_world.z - 0.22
    ]
    if not head_vertices:
        raise RuntimeError("could not estimate actor head bounds")
    low = Vector((min(point[i] for point in head_vertices) for i in range(3)))
    high = Vector((max(point[i] for point in head_vertices) for i in range(3)))
    return (Vector(((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, high.z)), high.x - low.x, high.z)


def attach_and_fit(
    tile: bpy.types.Object,
    armature: bpy.types.Object,
    body: bpy.types.Object,
    q_height_ratio: float,
) -> dict[str, object]:
    tile.scale = (0.01, 0.01, 0.01)
    bpy.context.view_layer.objects.active = tile
    tile.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    # OBJ import converts the source from Y-up to Z-up by rotating the object.
    # Apply that conversion so the following Z-only Q-proportion fit is in
    # world space instead of accidentally scaling the source depth axis.
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    low, high = bounds(tile)
    head_center, head_width, head_top = head_target(armature, body)
    current_width = max(high.x - low.x, 0.001)
    fit_scale = (head_width * 1.08) / current_width
    tile.scale = (fit_scale, fit_scale, fit_scale)
    bpy.context.view_layer.update()
    low, high = bounds(tile)
    current_height = max(high.z - low.z, 0.001)
    max_height = max(head_width * q_height_ratio, 0.001)
    q_height_scale = min(1.0, max_height / current_height)
    tile.scale.z *= q_height_scale
    bpy.context.view_layer.update()
    low, high = bounds(tile)
    tile.location += Vector(
        (
            head_center.x - (low.x + high.x) * 0.5,
            head_center.y - (low.y + high.y) * 0.5,
            head_top + 0.06 - high.z,
        )
    )
    bpy.context.view_layer.update()
    world = tile.matrix_world.copy()
    tile.parent = armature
    tile.parent_type = "BONE"
    tile.parent_bone = HEAD_BONE
    tile.matrix_world = world
    tile.data.materials.clear()
    tile.data.materials.append(make_material((0.12, 0.045, 0.025, 1.0)))
    for polygon in tile.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True
    return {
        "scale_from_centimeters": 0.01,
        "fit_scale": fit_scale,
        "q_height_ratio": q_height_ratio,
        "q_height_scale": q_height_scale,
        "dimensions": [float(value) for value in tile.dimensions],
        "parent_bone": HEAD_BONE,
        "head_width": head_width,
        "head_top": head_top,
    }


def configure_render(scene: bpy.types.Scene) -> None:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    world = scene.world or bpy.data.worlds.new("HairCandidateWorld")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.018, 0.018, 0.024, 1.0)
        background.inputs["Strength"].default_value = 0.25
    for obj in list(bpy.data.objects):
        if obj.type == "LIGHT":
            bpy.data.objects.remove(obj, do_unlink=True)
    for name, location, energy, size in (
        ("HairKey", (-4.0, -5.0, 5.0), 700.0, 4.0),
        ("HairFill", (4.0, -2.0, 3.0), 350.0, 3.0),
    ):
        data = bpy.data.lights.new(name + "Data", "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = location
        light.rotation_euler = (Vector((0.0, 0.0, 1.6)) - light.location).to_track_quat("-Z", "Y").to_euler()


def render_views(scene: bpy.types.Scene, output_dir: Path, body: bpy.types.Object, tile: bpy.types.Object) -> dict[str, str]:
    low, high = bounds(body)
    hair_low, hair_high = bounds(tile)
    low.z = min(low.z, hair_low.z)
    high.z = max(high.z, hair_high.z)
    target = Vector(((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, (low.z + high.z) * 0.5))
    scale = max(3.8, (high.z - low.z) * 1.22)
    views = {
        "front": Vector((target.x, target.y - 12.0, target.z)),
        "right": Vector((target.x + 12.0, target.y, target.z)),
        "back": Vector((target.x, target.y + 12.0, target.z)),
        "left": Vector((target.x - 12.0, target.y, target.z)),
    }
    renders: dict[str, str] = {}
    for direction, location in views.items():
        camera_data = bpy.data.cameras.new("HairCandidateCameraData_" + direction)
        camera_data.type = "ORTHO"
        camera_data.ortho_scale = scale
        camera = bpy.data.objects.new("HairCandidateCamera_" + direction, camera_data)
        scene.collection.objects.link(camera)
        camera.location = location
        camera.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()
        scene.camera = camera
        path = output_dir / f"{direction}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        renders[direction] = str(path)
    return renders


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.actor_blend.resolve()))
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    body = next(obj for obj in bpy.data.objects if obj.type == "MESH" and obj.name.startswith("ChibiBase"))
    tile = import_tile(
        options.hair_obj,
        options.row,
        options.column,
        options.rows,
        options.columns,
        options.group_name,
        options.single_mesh,
    )
    fit = attach_and_fit(tile, armature, body, options.q_height_ratio)
    configure_render(bpy.context.scene)
    output_dir = options.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    renders = render_views(bpy.context.scene, output_dir, body, tile)
    options.output_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.output_blend.resolve()))
    manifest = {
        "schema": "assetslab_chibi_hair_candidate_v1",
        "source_obj": str(options.hair_obj.resolve()),
        "actor_blend": str(options.actor_blend.resolve()),
        "group_name": options.group_name,
        "row": options.row,
        "column": options.column,
        "tile_grid": [options.rows, options.columns],
        "object": tile.name,
        "vertices": len(tile.data.vertices),
        "polygons": len(tile.data.polygons),
        "fit": fit,
        "renders": renders,
        "status": "attached_candidate_review_required",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"CHIBI_HAIR_CANDIDATE_PASS row={options.row} column={options.column} vertices={len(tile.data.vertices)} output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
