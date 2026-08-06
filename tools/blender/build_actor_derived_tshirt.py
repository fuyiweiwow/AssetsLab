"""Build a first fitted T-shirt directly from the Actor surface.

This is intentionally an actor-derived acceptance garment, not a general
clothing generator.  It keeps the Actor topology and weights, extracts a
torso/upper-arm band, offsets it by a measured clearance, and then renders
the same four-direction/action review used by the rest of AssetsLab.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from fit_clothing_to_actor_cage import DIRECTIONS  # noqa: E402
from render_eye_assembly_blink_walk import configure_lighting, visible_bounds  # noqa: E402
from render_procedural_anime_eye_on_accurig import make_camera  # noqa: E402


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor-blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bottom-z", type=float, default=0.70)
    parser.add_argument("--top-z", type=float, default=1.48)
    parser.add_argument("--max-abs-x", type=float, default=0.82)
    parser.add_argument("--sleeve-fraction", type=float, default=0.68)
    parser.add_argument("--clearance", type=float, default=0.025)
    parser.add_argument("--resolution", type=int, default=256)
    return parser.parse_args(argv)


def make_material() -> bpy.types.Material:
    material = bpy.data.materials.new("ActorDerivedTshirt_Material")
    material.diffuse_color = (0.12, 0.38, 0.82, 1.0)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    if shader:
        shader.inputs["Base Color"].default_value = (0.12, 0.38, 0.82, 1.0)
        shader.inputs["Roughness"].default_value = 0.86
    return material


def create_bone_sleeves(
    actor: bpy.types.Object,
    collection: bpy.types.Collection,
    material: bpy.types.Material,
    armature: bpy.types.Object,
    sleeve_fraction: float,
    clearance: float,
) -> None:
    """Create two complete, capped sleeve tubes driven by the upper-arm bones."""
    inverse = actor.matrix_world.inverted()
    fraction = max(0.45, min(sleeve_fraction, 0.9))
    sides = ("L", "R")
    for side in sides:
        upper = armature.data.bones.get(f"CC_Base_{side}_Upperarm")
        twist = armature.data.bones.get(f"CC_Base_{side}_UpperarmTwist02")
        if not upper or not twist:
            continue
        shoulder = armature.matrix_world @ upper.head_local
        elbow = armature.matrix_world @ twist.tail_local
        axis = elbow - shoulder
        if axis.length < 0.001:
            continue
        axis.normalize()
        start = shoulder - axis * 0.09
        end = shoulder + (elbow - shoulder) * fraction
        end_axis = (end - start).normalized()
        reference = Vector((0.0, 1.0, 0.0))
        if abs(end_axis.dot(reference)) > 0.95:
            reference = Vector((1.0, 0.0, 0.0))
        radial_a = end_axis.cross(reference).normalized()
        radial_b = end_axis.cross(radial_a).normalized()
        radius_start = 0.125 + clearance
        radius_end = 0.115 + clearance
        segments = 12
        world_vertices = []
        for center, radius in ((start, radius_start), (end, radius_end)):
            for index in range(segments):
                angle = 2.0 * math.pi * index / segments
                offset = radial_a * math.cos(angle) * radius + radial_b * math.sin(angle) * radius
                world_vertices.append(center + offset)
        world_vertices.extend((start, end))
        vertices = [tuple(inverse @ vertex) for vertex in world_vertices]
        faces = []
        for index in range(segments):
            next_index = (index + 1) % segments
            faces.append((index, next_index, segments + next_index, segments + index))
        end_center = segments * 2
        # Leave the shoulder side open and overlapped by the torso garment;
        # only the cuff side is capped, so the sleeve reads as one sewn piece.
        faces.append(tuple([end_center, *range(segments, segments * 2)]))

        mesh = bpy.data.meshes.new(f"ActorDerivedSleeve_{side}_Mesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.materials.append(material)
        mesh.update()
        sleeve = bpy.data.objects.new(f"ActorDerivedSleeve_{side}", mesh)
        sleeve.matrix_world = actor.matrix_world.copy()
        collection.objects.link(sleeve)
        upper_group = sleeve.vertex_groups.new(name=upper.name)
        clavicle = armature.data.bones.get(f"CC_Base_{side}_Clavicle")
        clavicle_group = sleeve.vertex_groups.new(name=clavicle.name) if clavicle else None
        start_indices = list(range(segments))
        end_indices = list(range(segments, segments * 2)) + [end_center]
        upper_group.add(start_indices, 0.72, "REPLACE")
        upper_group.add(end_indices, 1.0, "REPLACE")
        if clavicle_group:
            clavicle_group.add(start_indices, 0.28, "REPLACE")
        modifier = sleeve.modifiers.new("Armature", "ARMATURE")
        modifier.object = armature
        sleeve["assetslab_clothing_type"] = "complete_bone_sleeve"
        sleeve["assetslab_sleeve_fraction"] = fraction


def extract_surface_shirt(
    actor: bpy.types.Object,
    collection: bpy.types.Collection,
    bottom_z: float,
    top_z: float,
    max_abs_x: float,
    sleeve_fraction: float,
    clearance: float,
) -> tuple[bpy.types.Object, int, int]:
    shirt = actor.copy()
    shirt.data = actor.data.copy()
    shirt.name = "ActorDerivedTshirt_v1"
    shirt.parent = None
    shirt.matrix_world = actor.matrix_world.copy()
    collection.objects.link(shirt)

    mesh = shirt.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    matrix = actor.matrix_world
    group_indices = {group.name: group.index for group in actor.vertex_groups}
    upper_groups = {
        index
        for name, index in group_indices.items()
        if any(token in name for token in ("Clavicle", "Upperarm"))
    }
    lower_groups = {
        index
        for name, index in group_indices.items()
        if any(token in name for token in ("Forearm", "Hand"))
    }

    def group_weight(face: bmesh.types.BMFace, groups: set[int]) -> float:
        if not groups:
            return 0.0
        return sum(
            sum(assignment.weight for assignment in actor.data.vertices[vertex.index].groups if assignment.group in groups)
            for vertex in face.verts
        ) / max(len(face.verts), 1)

    selected = []
    for face in bm.faces:
        center = matrix @ face.calc_center_median()
        # Include the shoulder cap in the torso garment so the independent
        # sleeve tube can overlap it cleanly instead of exposing an opening.
        torso_face = abs(center.x) <= 0.72
        upper_arm_face = (
            abs(center.x) <= max_abs_x
            and group_weight(face, upper_groups) >= group_weight(face, lower_groups)
            and group_weight(face, upper_groups) > 0.20
        )
        if bottom_z <= center.z <= top_z and torso_face:
            selected.append(face)
    selected_count = len(selected)
    bmesh.ops.delete(bm, geom=[face for face in bm.faces if face not in selected], context="FACES")
    loose = [vertex for vertex in bm.verts if not vertex.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")

    # Cut the hem and shoulder line with planes after the region selection so
    # the boundary is a clean ring instead of an irregular source topology.
    scale = max(matrix.to_scale().x, 0.000001)
    for plane_z in (bottom_z, top_z):
        bmesh.ops.bisect_plane(
            bm,
            geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
            plane_co=Vector((0.0, 0.0, plane_z / scale)),
            plane_no=Vector((0.0, 0.0, 1.0)),
            clear_inner=False,
            clear_outer=False,
        )
        outside = [
            face
            for face in bm.faces
            if ((matrix @ face.calc_center_median()).z < bottom_z - 0.00001)
            or ((matrix @ face.calc_center_median()).z > top_z + 0.00001)
        ]
        if outside:
            bmesh.ops.delete(bm, geom=outside, context="FACES")
        loose = [vertex for vertex in bm.verts if not vertex.link_faces]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context="VERTS")

    armature_modifier = next((modifier for modifier in shirt.modifiers if modifier.type == "ARMATURE"), None)
    armature_object = armature_modifier.object if armature_modifier else None
    bm.normal_update()
    local_clearance = clearance / scale
    for vertex in bm.verts:
        normal = vertex.normal.normalized()
        vertex.co += normal * local_clearance
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    # The duplicate already owns Actor vertex groups and its Armature modifier.
    # Replace the body material with a visible review material.
    mesh.materials.clear()
    mesh.materials.append(make_material())
    if armature_modifier:
        shirt.modifiers.remove(armature_modifier)
    solidify = shirt.modifiers.new("GarmentThickness", "SOLIDIFY")
    solidify.thickness = 0.8
    solidify.offset = -1.0
    solidify.use_rim = True
    if armature_object:
        armature = shirt.modifiers.new("Armature", "ARMATURE")
        armature.object = armature_object
        create_bone_sleeves(actor, collection, mesh.materials[0], armature_object, sleeve_fraction, clearance)
    shirt["assetslab_clothing_type"] = "soft_garment"
    shirt["assetslab_clothing_source"] = "actor_surface_extraction"
    shirt["assetslab_fit_status"] = "review_required"
    shirt["assetslab_clearance_world"] = clearance
    shirt["assetslab_region_contract"] = "torso_upper_arm_surface_band"
    return shirt, selected_count, len(mesh.polygons)


def render_review(scene: bpy.types.Scene, output: Path, actor: bpy.types.Object, shirt: bpy.types.Object, resolution: int) -> list[dict[str, object]]:
    low, high = visible_bounds()
    center = (low + high) * 0.5
    configure_lighting(scene, center, "soft_flat")
    scene.view_settings.exposure = 0.35
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    action = bpy.data.objects["Armature"].animation_data.action
    start, end = int(action.frame_range[0]), int(action.frame_range[1])
    sample_frames = [round(start + (end - start) * index / 7.0) for index in range(8)]
    ortho_scale = max(high.z - low.z, high.x - low.x, high.y - low.y) * 1.16
    frames = []
    for direction, (x, y) in DIRECTIONS.items():
        camera = make_camera(scene, center, f"ActorDerivedTshirt_{direction}", (x, y, center.z), ortho_scale)
        scene.camera = camera
        for index, source_frame in enumerate(sample_frames):
            scene.frame_set(source_frame)
            bpy.context.view_layer.update()
            path = output / f"{direction}_{index:02d}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            frames.append({"direction": direction, "sample_index": index, "source_frame": source_frame, "path": path.name})
        bpy.data.objects.remove(camera, do_unlink=True)
    return frames


def main() -> int:
    options = cli_args()
    bpy.ops.wm.open_mainfile(filepath=str(options.actor_blend.resolve()))
    scene = bpy.context.scene
    actor = bpy.data.objects.get("ChibiBaseMesh_AccuRIG_InputMesh")
    armature = bpy.data.objects.get("Armature")
    if actor is None or armature is None:
        raise RuntimeError("actor blend must contain Actor mesh and Armature")

    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    collection = bpy.data.collections.new("ActorDerivedClothing")
    scene.collection.children.link(collection)
    shirt, selected_faces, final_faces = extract_surface_shirt(
        actor, collection, options.bottom_z, options.top_z, options.max_abs_x, options.sleeve_fraction, options.clearance
    )
    frames = render_review(scene, output, actor, shirt, options.resolution)
    candidate_blend = output / "actor_derived_tshirt_candidate.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(candidate_blend))
    report = {
        "schema": "assetslab_actor_derived_tshirt_review_v1",
        "actor_blend": str(options.actor_blend.resolve()),
        "candidate": "ActorDerivedTshirt_v1",
        "source_method": "actor_surface_face_extraction_plus_normal_clearance",
        "region": {
            "bottom_z": options.bottom_z,
            "top_z": options.top_z,
            "max_abs_x": options.max_abs_x,
        },
        "clearance": options.clearance,
        "selected_faces_before_cleanup": selected_faces,
        "final_faces": final_faces,
        "rig_status": "actor_vertex_groups_and_armature_modifier_inherited",
        "direction_count": 4,
        "frame_count_per_direction": 8,
        "lighting_profile": "soft_flat_v1",
        "status": "review_required",
        "frames": frames,
    }
    (output / "manifest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
