"""Create a real shallow eye recess on a duplicate of the actor head/body.

The cutter contour is derived from the imported Miku eyeball mesh projected to
the actor eye positions.  The actor mesh is duplicated, its Armature modifier
is temporarily removed, two manifold contour prisms are subtracted, and the
Armature modifier is restored.  The original actor is hidden and preserved.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.geometry import convex_hull_2d


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-blend", required=True, type=Path)
    parser.add_argument("--miku-fbx", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--save-blend", required=True, type=Path)
    parser.add_argument("--eye-scale", type=float, default=0.82)
    parser.add_argument("--eye-outward", type=float, default=0.05)
    parser.add_argument("--socket-scale", type=float, default=1.14)
    parser.add_argument("--front-depth", type=float, default=0.09)
    parser.add_argument("--back-depth", type=float, default=0.09)
    parser.add_argument("--eye-recess", type=float, default=0.07)
    return parser.parse_args(argv)


def bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    return Vector((min(p[i] for p in points) for i in range(3))), Vector((max(p[i] for p in points) for i in range(3)))


def remove_object(obj: bpy.types.Object) -> None:
    bpy.data.objects.remove(obj, do_unlink=True)


def clean_old_objects() -> None:
    prefixes = ("MikuEyeSocket", "MikuOpenEye", "eye_007_22_0_node", "eyeball_1_0_node", "EyeSocketCutter")
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefixes):
            remove_object(obj)
        elif obj.type == "ARMATURE" and obj.name.startswith("Armature."):
            remove_object(obj)


def raycast_face(actor: bpy.types.Object, x: float, z: float, fallback: float) -> float:
    inverse = actor.matrix_world.inverted()
    origin = inverse @ Vector((x, -10.0, z))
    direction = (inverse.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
    # The source actor is authored with a small object scale, so a world-space
    # 30-unit ray becomes roughly 3000 local units. Use a generous local ray
    # length to cover both normalized and centimeter-style Blender scenes.
    hit, location, _normal, _index = actor.ray_cast(origin, direction, distance=10000.0)
    print(f"RAY_DEBUG hit={hit} origin={tuple(round(v,4) for v in origin)} direction={tuple(round(v,4) for v in direction)} local_hit={tuple(round(v,4) for v in location)}")
    return (actor.matrix_world @ location).y if hit else fallback


def parent_to_head(obj: bpy.types.Object, rig: bpy.types.Object) -> None:
    world = obj.matrix_world.copy()
    obj.parent = rig
    obj.parent_type = "BONE"
    obj.parent_bone = "CC_Base_Head"
    obj.matrix_world = world


def import_reference_eye(source: Path) -> bpy.types.Object:
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=str(source.resolve()), automatic_bone_orientation=False)
    imported = [obj for obj in bpy.context.scene.objects if obj not in before]
    eye = next((obj for obj in imported if obj.name == "eyeball_1_0_node" or obj.name.startswith("eyeball_1_0_node.")), None)
    if eye is None:
        raise RuntimeError("Miku FBX is missing eyeball_1_0_node")
    world = eye.matrix_world.copy()
    eye.parent = None
    eye.matrix_world = world
    for modifier in list(eye.modifiers):
        eye.modifiers.remove(modifier)
    for obj in imported:
        if obj is not eye:
            remove_object(obj)
    eye.name = "MikuEyeballReferenceContour"
    return eye


def shrink_and_space_target_eye(eye: bpy.types.Object, scale: float, outward: float) -> None:
    points = [eye.matrix_world @ vertex.co for vertex in eye.data.vertices]
    center_z = sum(point.z for point in points) / len(points)
    left = [point for point in points if point.x < 0.0]
    right = [point for point in points if point.x >= 0.0]
    centers = {"L": sum(point.x for point in left) / len(left), "R": sum(point.x for point in right) / len(right)}
    inverse = eye.matrix_world.inverted()
    for vertex in eye.data.vertices:
        world = eye.matrix_world @ vertex.co
        side = "L" if world.x < 0.0 else "R"
        cx = centers[side]
        world.x = cx + (world.x - cx) * scale
        world.z = center_z + (world.z - center_z) * scale
        world.x += -outward if side == "L" else outward
        vertex.co = inverse @ world
    eye.data.update()


def contour_for_side(reference_eye: bpy.types.Object, side: str) -> list[Vector]:
    points = [reference_eye.matrix_world @ vertex.co for vertex in reference_eye.data.vertices if (reference_eye.matrix_world @ vertex.co).x < 0.0] if side == "L" else [reference_eye.matrix_world @ vertex.co for vertex in reference_eye.data.vertices if (reference_eye.matrix_world @ vertex.co).x >= 0.0]
    if len(points) < 3:
        raise RuntimeError(f"reference eye has too few points for side {side}")
    unique = []
    seen = set()
    for point in points:
        key = (round(point.x, 6), round(point.z, 6))
        if key not in seen:
            seen.add(key)
            unique.append(Vector((point.x, point.z)))
    hull = convex_hull_2d(unique)
    if len(hull) < 3:
        raise RuntimeError(f"convex hull failed for side {side}")
    # Blender 4.x returns indices into the input list; older versions may
    # return point-like values. Normalize both forms here.
    if isinstance(hull[0], int):
        return [unique[index].copy() for index in hull]
    return [Vector((point.x, point.y)) for point in hull]


def target_contour(reference_contour: list[Vector], target_eye: bpy.types.Object, side: str, socket_scale: float) -> list[Vector]:
    ref_low = Vector((min(point.x for point in reference_contour), min(point.y for point in reference_contour)))
    ref_high = Vector((max(point.x for point in reference_contour), max(point.y for point in reference_contour)))
    ref_center = (ref_low + ref_high) * 0.5
    points = [target_eye.matrix_world @ vertex.co for vertex in target_eye.data.vertices if (target_eye.matrix_world @ vertex.co).x < 0.0] if side == "L" else [target_eye.matrix_world @ vertex.co for vertex in target_eye.data.vertices if (target_eye.matrix_world @ vertex.co).x >= 0.0]
    low = Vector((min(point.x for point in points), min(point.z for point in points)))
    high = Vector((max(point.x for point in points), max(point.z for point in points)))
    center = (low + high) * 0.5
    sx = (high.x - low.x) / max(ref_high.x - ref_low.x, 1e-6) * socket_scale
    sz = (high.y - low.y) / max(ref_high.y - ref_low.y, 1e-6) * socket_scale
    return [Vector((center.x + (point.x - ref_center.x) * sx, center.y + (point.y - ref_center.y) * sz)) for point in reference_contour]


def create_prism(actor: bpy.types.Object, contour: list[Vector], name: str, front_depth: float, back_depth: float) -> bpy.types.Object:
    actor_low, _actor_high = bounds([actor])
    center = Vector((sum(point.x for point in contour) / len(contour), sum(point.y for point in contour) / len(contour)))
    face_y = raycast_face(actor, center.x, center.y, actor_low.y)
    front_y = face_y - front_depth
    back_y = face_y + back_depth
    print(f"CUTTER_DEBUG name={name} center_xz=({center.x:.4f},{center.y:.4f}) actor_y=({actor_low.y:.4f}) face_y={face_y:.4f} depth=({front_depth:.4f},{back_depth:.4f})")
    actor_inverse = actor.matrix_world.inverted()
    world_vertices = [(point.x, front_y, point.y) for point in contour] + [(point.x, back_y, point.y) for point in contour]
    vertices = [tuple(actor_inverse @ Vector(vertex)) for vertex in world_vertices]
    count = len(contour)
    front = tuple(reversed(range(count)))
    back = tuple(range(count, count * 2))
    faces = [front, back]
    for index in range(count):
        nxt = (index + 1) % count
        faces.append((index, nxt, count + nxt, count + index))
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    cutter = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(cutter)
    cutter.matrix_world = actor.matrix_world.copy()
    cutter["assetslab_role"] = "reference_derived_eye_socket_cutter"
    cutter["assetslab_front_y"] = front_y
    cutter["assetslab_back_y"] = back_y
    cutter_low, cutter_high = bounds([cutter])
    print(f"CUTTER_BOUNDS name={name} world=({tuple(round(v,4) for v in cutter_low)})..({tuple(round(v,4) for v in cutter_high)})")
    return cutter


def apply_boolean(body: bpy.types.Object, cutter: bpy.types.Object, index: int) -> int:
    armature_refs = [modifier.object for modifier in body.modifiers if modifier.type == "ARMATURE" and modifier.object]
    for modifier in list(body.modifiers):
        if modifier.type == "ARMATURE":
            body.modifiers.remove(modifier)
    before = len(body.data.polygons)
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    if index == 1:
        # The actor head is an open shell. Temporarily solidify only the test
        # duplicate so Boolean Difference has a closed volume to subtract from.
        solidify = body.modifiers.new("TrueEyeSocketTestSolidify", "SOLIDIFY")
        solidify.thickness = 0.12 / max(abs(body.scale.y), 1e-6)
        solidify.offset = 0.0
        bpy.ops.object.modifier_apply(modifier=solidify.name)
    modifier = body.modifiers.new(f"EyeSocketBoolean_{index}", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    after = len(body.data.polygons)
    for armature in armature_refs:
        restored = body.modifiers.new("Armature", "ARMATURE")
        restored.object = armature
    if after >= before:
        body[f"assetslab_boolean_failure_{index}"] = f"before={before} after={after}"
        print(f"BOOLEAN_FAIL cutter={cutter.name} before={before} after={after}")
        return 0
    return before - after


def remove_shape_keys_for_test(body: bpy.types.Object) -> int:
    """Remove shape keys only from the duplicated mesh before destructive booleans."""
    key_data = body.data.shape_keys
    if key_data is None:
        return 0
    count = len(key_data.key_blocks)
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.shape_key_remove(all=True)
    return count


def apply_armature_pose_for_test(body: bpy.types.Object) -> int:
    """Bake the actor's current armature pose into the test duplicate."""
    applied = 0
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    for modifier in list(body.modifiers):
        if modifier.type == "ARMATURE" and modifier.object:
            bpy.ops.object.modifier_apply(modifier=modifier.name)
            applied += 1
    return applied


def add_lights(scene: bpy.types.Scene) -> None:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("TrueEyeSocketWorld")
    scene.world.color = (0.035, 0.035, 0.05)
    for index, (location, energy, size) in enumerate((((0.0, -4.0, 5.0), 700.0, 4.0), ((-3.0, -2.0, 2.0), 350.0, 3.0))):
        data = bpy.data.lights.new(f"TrueEyeSocketLight{index}", "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(f"TrueEyeSocketLight{index}", data)
        scene.collection.objects.link(light)
        light.location = location


def render(scene: bpy.types.Scene, eye: bpy.types.Object, output: Path) -> None:
    add_lights(scene)
    low, high = bounds([eye])
    target = (low + high) * 0.5
    for direction, location in (("front", target + Vector((0.0, -10.0, 0.0))), ("right", target + Vector((10.0, 0.0, 0.0)))):
        data = bpy.data.cameras.new(f"TrueEyeSocketCamera_{direction}")
        data.type = "ORTHO"
        data.ortho_scale = 2.25
        camera = bpy.data.objects.new(f"TrueEyeSocketCamera_{direction}", data)
        bpy.context.collection.objects.link(camera)
        camera.location = location
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.camera = camera
        scene.render.filepath = str(output / f"{direction}.png")
        bpy.ops.render.render(write_still=True)
        remove_object(camera)


def main() -> int:
    options = cli_args()
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(options.base_blend.resolve()))
    clean_old_objects()
    actor = bpy.data.objects.get("ChibiBaseMesh_AccuRIG_InputMesh")
    eye = bpy.data.objects.get("MikuChibiEyeball")
    rig = bpy.data.objects.get("Armature")
    if actor is None or eye is None or rig is None:
        raise RuntimeError("base blend must contain actor, MikuChibiEyeball, and Armature")

    original_low, original_high = bounds([actor])
    body = actor.copy()
    body.data = actor.data.copy()
    body.name = "ChibiActor_TrueEyeSocket_Test"
    bpy.context.collection.objects.link(body)
    body.matrix_world = actor.matrix_world.copy()
    removed_shape_keys = remove_shape_keys_for_test(body)
    applied_armatures = apply_armature_pose_for_test(body)
    actor.hide_render = True
    actor.hide_viewport = True

    shrink_and_space_target_eye(eye, options.eye_scale, options.eye_outward)
    eye_low, eye_high = bounds([eye])
    body_low, body_high = bounds([body])
    print(f"TARGET_DEBUG body_bounds={tuple(round(v,4) for v in body_low)}..{tuple(round(v,4) for v in body_high)} eye_bounds={tuple(round(v,4) for v in eye_low)}..{tuple(round(v,4) for v in eye_high)}")
    reference_eye = import_reference_eye(options.miku_fbx)
    removed_polygons = 0
    cutters = []
    for index, side in enumerate(("L", "R"), 1):
        contour = target_contour(contour_for_side(reference_eye, side), eye, side, options.socket_scale)
        contour_low = Vector((min(point.x for point in contour), min(point.y for point in contour)))
        contour_high = Vector((max(point.x for point in contour), max(point.y for point in contour)))
        print(f"CONTOUR_DEBUG side={side} bounds=({contour_low.x:.4f},{contour_low.y:.4f})..({contour_high.x:.4f},{contour_high.y:.4f})")
        cutter = create_prism(body, contour, f"EyeSocketCutter.{side}", options.front_depth, options.back_depth)
        cutters.append(cutter)
        removed_polygons += apply_boolean(body, cutter, index)
        remove_object(cutter)
    remove_object(reference_eye)

    # Move the existing eye assembly into the new cavities and parent it to the head.
    eye.location.y += options.eye_recess
    parent_to_head(eye, rig)
    render(bpy.context.scene, eye, output)
    boolean_failures = {key: value for key, value in body.items() if key.startswith("assetslab_boolean_failure_")}
    manifest = {
        "schema": "assetslab_true_eye_socket_boolean_v1",
        "base_blend": str(options.base_blend.resolve()),
        "miku_fbx_reference": str(options.miku_fbx.resolve()),
        "body_object": body.name,
        "eye_object": eye.name,
        "parent_bone": "CC_Base_Head",
        "parameters": {
            "eye_scale": options.eye_scale,
            "eye_outward": options.eye_outward,
            "socket_scale": options.socket_scale,
            "front_depth": options.front_depth,
            "back_depth": options.back_depth,
            "eye_recess": options.eye_recess
        },
        "original_actor_preserved_hidden": True,
        "original_actor_bounds": {"low": list(original_low), "high": list(original_high)},
        "removed_polygon_count": removed_polygons,
        "removed_shape_key_count_on_test_duplicate": removed_shape_keys,
        "applied_armature_modifier_count_on_test_duplicate": applied_armatures,
        "status": "failed_boolean" if boolean_failures else "review_candidate",
        "boolean_failures": boolean_failures,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    options.save_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.save_blend.resolve()))
    print(f"TRUE_EYE_SOCKET_PASS output={output} removed_polygons={removed_polygons}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
