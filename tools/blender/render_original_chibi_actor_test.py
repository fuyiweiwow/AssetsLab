"""Bind the original static chibi mesh to the KIIRA walk rig and render a test."""

from __future__ import annotations

import argparse
import io
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-blend", required=True, type=Path)
    parser.add_argument("--walk-fbx", required=True, type=Path)
    parser.add_argument("--render-dir", required=True, type=Path)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--camera-contract", type=Path, default=None)
    parser.add_argument("--head-scale", type=float, default=1.18)
    parser.add_argument("--body-scale", type=float, default=0.86)
    parser.add_argument("--preserve-source-transform", action="store_true")
    parser.add_argument("--rigid-head", action="store_true")
    parser.add_argument("--head-split-z", type=float, default=1.3)
    return parser.parse_args(argv)


def bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points))), Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))


def apply_source_display_modifiers(mesh: bpy.types.Object) -> list[dict[str, str]]:
    """Apply visible source modifiers without mirroring an already bilateral mesh."""
    records: list[dict[str, str]] = []
    x_values = [vertex.co.x for vertex in mesh.data.vertices]
    already_bilateral = bool(x_values) and min(x_values) < -0.001 and max(x_values) > 0.001
    bpy.context.view_layer.objects.active = mesh
    mesh.select_set(True)
    for modifier in list(mesh.modifiers):
        modifier_name = str(modifier.name)
        modifier_type = str(modifier.type)
        if modifier_type == "MIRROR" and already_bilateral:
            records.append({"name": modifier_name, "type": "MIRROR", "action": "skipped_already_bilateral"})
            mesh.modifiers.remove(modifier)
        elif modifier_type in {"MIRROR", "SUBSURF"}:
            bpy.ops.object.modifier_apply(modifier=modifier_name)
            records.append({"name": modifier_name, "type": modifier_type, "action": "applied"})
        else:
            records.append({"name": modifier_name, "type": modifier_type, "action": "removed_unsupported"})
            mesh.modifiers.remove(modifier)
    return records


def rigid_bind_chibi(mesh: bpy.types.Object, rig: bpy.types.Object) -> None:
    """Assign each vertex to the closest compatible rest-pose bone segment."""
    for group in list(mesh.vertex_groups):
        mesh.vertex_groups.remove(group)
    bone_names = [
        "Bone.002", "Bone.003", "Bone.004", "Bone.006", "Bone.007", "Bone.008",
        "Bone.009", "Bone.010", "Bone.012", "Bone.013", "Bone.014", "Bone.016",
        "Bone.017", "Bone.018",
    ]
    groups = {name: mesh.vertex_groups.new(name=name) for name in bone_names}

    def segment_distance(point: Vector, start: Vector, end: Vector) -> float:
        direction = end - start
        length_squared = direction.length_squared
        if length_squared <= 1e-8:
            return (point - start).length
        factor = max(0.0, min(1.0, (point - start).dot(direction) / length_squared))
        return (point - (start + factor * direction)).length

    segments = {}
    for name in bone_names:
        bone = rig.data.bones[name]
        segments[name] = (
            rig.matrix_world @ bone.head_local,
            rig.matrix_world @ bone.tail_local,
        )

    for vertex in mesh.data.vertices:
        world_point = mesh.matrix_world @ vertex.co
        if vertex.co.z >= 2.12:
            bone = "Bone.010"
        elif abs(vertex.co.x) < 0.16 and vertex.co.z > 0.25:
            bone = "Bone.009"
        else:
            bone = min(
                (name for name in bone_names if name not in {"Bone.009", "Bone.010"}),
                key=lambda name: segment_distance(world_point, *segments[name]),
            )
        groups[bone].add([vertex.index], 1.0, "REPLACE")
    modifier = mesh.modifiers.new("KIIRA_Walk_Armature", "ARMATURE")
    modifier.object = rig


def split_rigid_head(mesh: bpy.types.Object, split_z: float) -> bpy.types.Object:
    """Separate the upper head into a rigid object before body binding.

    The source is one connected mesh. Applying its display modifiers and
    splitting by the neck height gives the head a rigid transform, preventing
    face vertices near the neck from being assigned to arm/torso bones.
    """
    apply_source_display_modifiers(mesh)
    head_faces = []
    body_faces = []
    for polygon in mesh.data.polygons:
        touches_head = any(mesh.data.vertices[index].co.z >= split_z for index in polygon.vertices)
        (head_faces if touches_head else body_faces).append(polygon)

    def make_part(name: str, polygons: list[bpy.types.MeshPolygon]) -> bpy.types.Object:
        vertex_map = {}
        vertices = []
        faces = []
        smooth = []
        for polygon in polygons:
            face = []
            for index in polygon.vertices:
                if index not in vertex_map:
                    vertex_map[index] = len(vertices)
                    vertices.append(tuple(mesh.data.vertices[index].co))
                face.append(vertex_map[index])
            faces.append(face)
            smooth.append(polygon.use_smooth)
        data = bpy.data.meshes.new(name + "Mesh")
        data.from_pydata(vertices, [], faces)
        data.update()
        for polygon, is_smooth in zip(data.polygons, smooth):
            polygon.use_smooth = is_smooth
        part = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(part)
        part.matrix_world = mesh.matrix_world.copy()
        return part

    if not head_faces or not body_faces:
        raise RuntimeError("rigid head split did not produce both head and body parts")
    head = make_part("OriginalChibiHead", head_faces)
    body = make_part("OriginalChibiBody", body_faces)
    for material in mesh.data.materials:
        head.data.materials.append(material)
        body.data.materials.append(material)
    bpy.data.objects.remove(mesh, do_unlink=True)
    return body


def scale_head_region(mesh: bpy.types.Object, scale: float) -> None:
    """Scale the source head around the neck seam before fitting to the rig."""
    if scale <= 0.0:
        raise ValueError("head-scale must be positive")
    neck_z = 2.12
    for vertex in mesh.data.vertices:
        if vertex.co.z < neck_z:
            continue
        vertex.co.x *= scale
        vertex.co.y *= scale
        vertex.co.z = neck_z + (vertex.co.z - neck_z) * scale
    mesh.data.update()


def evaluated_bounds(scene: bpy.types.Scene, mesh: bpy.types.Object, frames: list[int]) -> tuple[Vector, Vector]:
    low = Vector((float("inf"), float("inf"), float("inf")))
    high = Vector((float("-inf"), float("-inf"), float("-inf")))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for frame in frames:
        scene.frame_set(frame)
        evaluated = mesh.evaluated_get(depsgraph)
        for vertex in evaluated.data.vertices:
            point = evaluated.matrix_world @ vertex.co
            low.x, low.y, low.z = min(low.x, point.x), min(low.y, point.y), min(low.z, point.z)
            high.x, high.y, high.z = max(high.x, point.x), max(high.y, point.y), max(high.z, point.z)
    if low.x == float("inf"):
        raise RuntimeError("animated mesh has no evaluated vertices")
    return low, high


def resolve_source_blend(path: Path) -> tuple[Path, Path | None]:
    """Return a .blend path and an optional temporary extraction directory.

    The downloaded source is a ZIP containing another ZIP. Supporting that
    layout here keeps the actor build reproducible without copying vendor files
    into the repository or requiring a manual extraction step.
    """
    path = path.resolve()
    if path.suffix.lower() == ".blend":
        return path, None
    if path.suffix.lower() != ".zip":
        raise RuntimeError(f"source-blend must be .blend or .zip, got {path}")

    temp_root = Path(tempfile.mkdtemp(prefix="assetslab-chibi-source-"))
    try:
        with zipfile.ZipFile(path) as outer:
            nested_name = next(
                (name for name in outer.namelist() if name.lower().endswith("chibi base mesh_blender.zip")),
                None,
            )
            if nested_name is None:
                raise RuntimeError("source ZIP does not contain the nested chibi base mesh archive")
            nested_bytes = outer.read(nested_name)
        with zipfile.ZipFile(io.BytesIO(nested_bytes)) as inner:
            blend_name = next(
                (name for name in inner.namelist() if name.lower().endswith("chibi base mesh.blend")),
                None,
            )
            if blend_name is None:
                raise RuntimeError("nested source ZIP does not contain chibi base mesh.blend")
            blend_path = temp_root / "chibi base mesh.blend"
            blend_path.write_bytes(inner.read(blend_name))
        return blend_path, temp_root
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise


def load_source_mesh(path: Path, center_source: bool = True) -> bpy.types.Object:
    blend_path, temp_root = resolve_source_blend(path)
    try:
        with bpy.data.libraries.load(str(blend_path), link=False) as (data_from, data_to):
            mesh_names = [name for name in data_from.objects if name == "Cube"]
            if not mesh_names:
                raise RuntimeError("source blend has no Cube mesh")
            data_to.objects = mesh_names
        mesh = next(obj for obj in data_to.objects if obj is not None)
        bpy.context.collection.objects.link(mesh)
        mesh.name = "OriginalChibiActor"
        mesh.hide_render = False
        mesh.hide_viewport = False
        bpy.context.view_layer.objects.active = mesh
        mesh.select_set(True)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        if center_source:
            local_x = [vertex.co.x for vertex in mesh.data.vertices]
            local_y = [vertex.co.y for vertex in mesh.data.vertices]
            local_z = [vertex.co.z for vertex in mesh.data.vertices]
            center = Vector(((min(local_x) + max(local_x)) * 0.5, (min(local_y) + max(local_y)) * 0.5, min(local_z)))
            mesh.data.transform(Matrix.Translation(-center))
            mesh.data.update()
        low, high = bounds(mesh)
        height = high.z - low.z
        if height <= 0.01:
            raise RuntimeError("source mesh has no height")
        return mesh
    finally:
        if temp_root is not None:
            shutil.rmtree(temp_root, ignore_errors=True)


def setup_scene(options: argparse.Namespace):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 256
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    bpy.ops.import_scene.fbx(filepath=str(options.walk_fbx), use_anim=True)
    rig = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    # The FBX meshes are only needed long enough to import the action. Keeping
    # them in the saved actor would duplicate the source character and its
    # broken external texture paths, so remove them before loading our mesh.
    for obj in [obj for obj in bpy.data.objects if obj.type == "MESH"]:
        bpy.data.objects.remove(obj, do_unlink=True)
    mesh = load_source_mesh(options.source_blend, center_source=not options.preserve_source_transform)
    scale_head_region(mesh, options.head_scale)
    low, high = bounds(mesh)
    mesh_low, mesh_high = bounds(mesh)
    rig_z = [value for bone in rig.data.bones for value in (bone.head_local.z, bone.tail_local.z)]
    rig_height = max(rig_z) - min(rig_z)
    mesh_height = mesh_high.z - mesh_low.z
    fit_scale = (rig_height / mesh_height) * options.body_scale
    mesh.scale = (fit_scale, fit_scale, fit_scale)
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    low, high = bounds(mesh)
    if options.rigid_head:
        mesh = split_rigid_head(mesh, options.head_split_z * fit_scale)
    foot_z = min((rig.matrix_world @ bone.head_local).z for bone in rig.data.bones if bone.name in {"Bone.014", "Bone.018"})
    mesh.location.z += foot_z - low.z
    mesh.location.x = rig.location.x
    mesh.location.y = rig.location.y
    if options.rigid_head:
        head = bpy.data.objects.get("OriginalChibiHead")
        if head is None:
            raise RuntimeError("rigid head split did not create head object")
        head.matrix_world = mesh.matrix_world.copy()
        head.parent = rig
        head.parent_type = "BONE"
        # Bone.010 belongs to the external character's head/upper chain and
        # moves the downloaded mesh's face seam sideways. Bone.009 is the
        # torso anchor; the whole head follows it rigidly without facial shear.
        head.parent_bone = "Bone.009"
        head.matrix_world = mesh.matrix_world.copy()
    rigid_bind_chibi(mesh, rig)
    face = bpy.data.objects.get("FACE")
    if face:
        face.hide_render = True
    root = bpy.data.objects.new("ActorRoot", None)
    scene.collection.objects.link(root)
    for obj in (rig, mesh):
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix
    camera_data = bpy.data.cameras.new("OriginalChibiTestCamera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 6.2
    camera = bpy.data.objects.new("OriginalChibiTestCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    # The pose can move the feet well below the rest-pose bounds. The final
    # camera is fitted to the union of all sampled poses, not the rest mesh.
    camera.location = (0.0, -12.0, 0.0)
    return scene, rig, mesh, root


def configure_camera(scene: bpy.types.Scene, camera: bpy.types.Object, contract_path: Path | None, low: Vector, high: Vector) -> str:
    if contract_path is None:
        camera_z = (low.z + high.z) * 0.5
        camera.data.ortho_scale = max(4.5, (high.z - low.z) * 1.18)
        camera.location = (0.0, -12.0, camera_z)
        target = Vector((0.0, 0.0, camera_z))
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        return "animated_union_bounds_review_camera"

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    camera.data.ortho_scale = contract["world_contract"]["orthographic_scale"]
    target = Vector((0.0, 0.0, contract["world_contract"]["camera_target_z"]))
    position = Vector(contract["directions"]["front"]["camera_position"])
    camera.location = position
    camera.rotation_euler = (target - position).to_track_quat("-Z", "Y").to_euler()
    return "G0_camera_contract_front"


def normalize_actor_floor(scene: bpy.types.Scene, root: bpy.types.Object, mesh: bpy.types.Object, frames: list[int]) -> tuple[Vector, Vector, float]:
    """Move the complete actor so the lowest sampled foot point is world Z=0."""
    low, high = evaluated_bounds(scene, mesh, frames)
    offset = -low.z
    root.location.z += offset
    bpy.context.view_layer.update()
    low, high = evaluated_bounds(scene, mesh, frames)
    if abs(low.z) > 0.01:
        raise RuntimeError(f"floor normalization failed: animated minimum z={low.z:.4f}")
    return low, high, offset


def main() -> int:
    options = cli_args()
    scene, rig, mesh, root = setup_scene(options)
    action = rig.animation_data.action if rig.animation_data else None
    if action is None:
        raise RuntimeError("Walk FBX has no active action")
    start, end = action.frame_range
    samples = [round(start + (end - start) * i / 8.0) for i in range(8)]
    low, high, floor_offset = normalize_actor_floor(scene, root, mesh, samples)
    camera = scene.camera
    camera_registration = configure_camera(scene, camera, options.camera_contract, low, high)
    frames = []
    for index, source_frame in enumerate(samples):
        scene.frame_set(source_frame)
        target = options.render_dir / f"frame_{index:02d}" / "beauty.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        frames.append({"frame": index, "source_frame": source_frame, "path": str(target)})
    options.blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(options.blend))
    options.render_dir.mkdir(parents=True, exist_ok=True)
    (options.render_dir / "manifest.json").write_text(json.dumps({
        "schema": "assetslab_original_chibi_actor_test_v2",
        "stage": "actor_v1_front_walk_8_frame_binding_test",
        "source_blend": str(options.source_blend),
        "walk_fbx": str(options.walk_fbx),
        "source_input_support": [".blend", ".zip_with_nested_blend"],
        "binding_policy": "rigid_body_regions_to_KIIRA_bones",
        "fbx_source_meshes_removed": True,
        "camera_contract": str(options.camera_contract) if options.camera_contract else None,
        "camera_registration": camera_registration,
        "floor_normalized": True,
        "actor_root": root.name,
        "floor_offset_z": round(floor_offset, 4),
        "animated_bounds_after_floor": {
            "min_z": round(low.z, 4),
            "max_z": round(high.z, 4),
        },
        "head_scale": options.head_scale,
        "body_scale": options.body_scale,
        "preserve_source_transform": options.preserve_source_transform,
        "face_hidden": True,
        "frames": frames,
        "runtime_ready": False,
    }, indent=2), encoding="utf-8")
    print(f"ORIGINAL_CHIBI_ACTOR_TEST_PASS frames={len(frames)} output={options.render_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
