"""Build and render a physics-proxy/render-garment pair.

The input blend already contains the reviewed Actor-transfer garment with
nearest-Actor weights and an Armature modifier.  This pass keeps that mesh as
the animation/physics proxy, creates a separate render mesh, applies a small
render-only subdivision, and binds the render mesh with Surface Deform.

The important production boundary is intentional: only the proxy has the
Armature modifier.  The render garment follows the animated proxy through
Surface Deform, so a future high-resolution garment can replace the render
mesh without changing the physics or Actor-weight transfer stage.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from render_eye_assembly_blink_walk import (  # noqa: E402
    DIRECTIONS,
    configure_lighting,
    visible_bounds,
)
from render_procedural_anime_eye_on_accurig import make_camera  # noqa: E402


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--proxy-name", default="GarmentCodeShirt_ActorTransfer")
    parser.add_argument("--resolution", type=int, default=256)
    parser.add_argument("--subdivision-level", type=int, default=1)
    parser.add_argument("--clean-render-surface", action="store_true")
    parser.add_argument("--render-surface-clearance", type=float, default=0.035)
    parser.add_argument("--build-clean-render-garment", action="store_true")
    parser.add_argument("--proxy-weighted-render", action="store_true")
    parser.add_argument("--clean-animation-proxy", action="store_true")
    parser.add_argument("--animation-proxy-smooth-iterations", type=int, default=6)
    parser.add_argument("--animation-proxy-smooth-factor", type=float, default=0.35)
    parser.add_argument("--animation-proxy-decimate-ratio", type=float, default=0.30)
    return parser.parse_args(argv)


def apply_render_subdivision(obj: bpy.types.Object, level: int) -> dict[str, int]:
    if level < 1:
        raise RuntimeError("render subdivision level must be at least 1")
    before = len(obj.data.vertices)
    modifier = obj.modifiers.new("RenderGarmentSubdivision", "SUBSURF")
    modifier.subdivision_type = "CATMULL_CLARK"
    modifier.levels = level
    modifier.render_levels = level
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj.data.update()
    return {"before_vertices": before, "after_vertices": len(obj.data.vertices), "level": level}


def apply_animation_proxy_cleanup(
    obj: bpy.types.Object,
    armature: bpy.types.Object,
    smooth_iterations: int,
    smooth_factor: float,
    decimate_ratio: float,
) -> dict[str, object]:
    if smooth_iterations < 0 or not 0.0 < smooth_factor <= 1.0:
        raise RuntimeError("invalid animation proxy smoothing parameters")
    if not 0.0 < decimate_ratio <= 1.0:
        raise RuntimeError("animation proxy decimate ratio must be in (0, 1]")
    before = len(obj.data.vertices)
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
    if smooth_iterations > 0:
        smooth = obj.modifiers.new("AnimationProxySurfaceSmoothing", "SMOOTH")
        smooth.factor = smooth_factor
        smooth.iterations = smooth_iterations
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.modifier_apply(modifier=smooth.name)
        obj.select_set(False)
    decimate = obj.modifiers.new("AnimationProxyDecimate", "DECIMATE")
    decimate.decimate_type = "COLLAPSE"
    decimate.ratio = decimate_ratio
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=decimate.name)
    obj.select_set(False)
    armature_modifier = obj.modifiers.new("AnimationProxyArmatureDeform", "ARMATURE")
    armature_modifier.object = armature
    obj.data.update()
    return {
        "enabled": True,
        "before_vertices": before,
        "after_vertices": len(obj.data.vertices),
        "smooth_iterations": smooth_iterations,
        "smooth_factor": smooth_factor,
        "decimate_ratio": decimate_ratio,
        "armature_modifier": armature_modifier.name,
    }


def bind_surface_deform(render_garment: bpy.types.Object, proxy: bpy.types.Object) -> dict[str, object]:
    modifier = render_garment.modifiers.new("SurfaceDeformFromPhysicsProxy", "SURFACE_DEFORM")
    modifier.target = proxy
    modifier.strength = 1.0
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = render_garment
    render_garment.select_set(True)
    result = bpy.ops.object.surfacedeform_bind(modifier=modifier.name)
    render_garment.select_set(False)
    if "FINISHED" not in result:
        raise RuntimeError(f"Surface Deform bind did not finish: {result}")
    bpy.context.view_layer.update()
    return {
        "modifier": modifier.name,
        "target": proxy.name,
        "strength": modifier.strength,
        "bound": bool(modifier.is_bound),
    }


def bind_proxy_weighted_armature(
    render_garment: bpy.types.Object,
    source_proxy: bpy.types.Object,
    armature: bpy.types.Object,
) -> dict[str, object]:
    """Transfer the already validated garment weight schema to the clean mesh."""
    for source_group in source_proxy.vertex_groups:
        if render_garment.vertex_groups.get(source_group.name) is None:
            render_garment.vertex_groups.new(name=source_group.name)
    modifier = render_garment.modifiers.new("TransferGarmentProxyWeights", "DATA_TRANSFER")
    modifier.object = source_proxy
    modifier.use_vert_data = True
    modifier.data_types_verts = {"VGROUP_WEIGHTS"}
    modifier.vert_mapping = "POLYINTERP_NEAREST"
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = render_garment
    render_garment.select_set(True)
    result = bpy.ops.object.modifier_apply(modifier=modifier.name)
    render_garment.select_set(False)
    if "FINISHED" not in result:
        raise RuntimeError(f"Garment proxy vertex-weight transfer did not finish: {result}")
    armature_modifier = render_garment.modifiers.new("RenderGarmentProxyArmatureDeform", "ARMATURE")
    armature_modifier.object = armature
    bpy.context.view_layer.update()
    return {
        "method": "garment_proxy_vertex_group_transfer_plus_armature",
        "source": source_proxy.name,
        "armature": armature.name,
        "vertex_groups": len(render_garment.vertex_groups),
        "armature_modifier": armature_modifier.name,
    }


def evaluated_world_points(obj: bpy.types.Object) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def interpolation_samples(points: list[Vector], axis: str, step: float) -> list[tuple[float, float, float]]:
    if not points:
        raise RuntimeError("cannot build render surface envelope from an empty mesh")
    axis_index = {"x": 0, "y": 1, "z": 2}[axis]
    bins: dict[int, list[float]] = {}
    for point in points:
        key = round(float(point.z) / step)
        bins.setdefault(key, []).append(float(point[axis_index]))
    result = []
    for key in sorted(bins):
        values = sorted(bins[key])
        result.append((key * step, values[0], values[-1]))
    return result


def interpolate_envelope(samples: list[tuple[float, float, float]], z: float) -> tuple[float, float]:
    if z <= samples[0][0]:
        return samples[0][1], samples[0][2]
    if z >= samples[-1][0]:
        return samples[-1][1], samples[-1][2]
    for lower, upper in zip(samples, samples[1:]):
        if lower[0] <= z <= upper[0]:
            span = max(upper[0] - lower[0], 1e-6)
            t = (z - lower[0]) / span
            return (
                lower[1] + (upper[1] - lower[1]) * t,
                lower[2] + (upper[2] - lower[2]) * t,
            )
    return samples[-1][1], samples[-1][2]


def torso_depth_envelope(actor: bpy.types.Object, step: float = 0.025) -> list[tuple[float, float, float]]:
    points = evaluated_world_points(actor)
    if not points:
        raise RuntimeError("Actor has no evaluated points for render surface")
    low = min(point.z for point in points)
    high = max(point.z for point in points)
    samples: list[tuple[float, float, float]] = []
    for index in range(round((high - low) / step) + 1):
        z = low + index * step
        torso = [point for point in points if abs(point.z - z) <= step * 0.8 and abs(point.x) <= 0.21]
        if len(torso) < 8:
            torso = [point for point in points if abs(point.z - z) <= step * 1.2 and abs(point.x) <= 0.27]
        if torso:
            samples.append((z, min(point.y for point in torso), max(point.y for point in torso)))
    if len(samples) < 3:
        raise RuntimeError("Actor torso depth envelope has too few samples")
    return samples


def build_clean_render_surface(
    render_garment: bpy.types.Object,
    proxy: bpy.types.Object,
    actor: bpy.types.Object,
    clearance: float,
) -> dict[str, object]:
    source_points = evaluated_world_points(proxy)
    source_samples = interpolation_samples(source_points, "y", 0.025)
    actor_samples = torso_depth_envelope(actor)
    inverse = render_garment.matrix_world.inverted()
    changed = 0
    for vertex in render_garment.data.vertices:
        world = render_garment.matrix_world @ vertex.co
        source_front, source_back = interpolate_envelope(source_samples, world.z)
        source_half = max((source_back - source_front) * 0.5, 1e-4)
        source_mid = (source_front + source_back) * 0.5
        depth_ratio = max(-1.0, min(1.0, (world.y - source_mid) / source_half))
        actor_front, actor_back = interpolate_envelope(actor_samples, world.z)
        actor_half = max((actor_back - actor_front) * 0.5 + clearance, 1e-4)
        actor_mid = (actor_front + actor_back) * 0.5
        world.y = actor_mid + depth_ratio * actor_half
        vertex.co = inverse @ world
        changed += 1
    render_garment.data.update()
    return {
        "enabled": True,
        "changed_vertices": changed,
        "clearance": clearance,
        "method": "source_depth_ratio_to_actor_torso_envelope_preserving_xy_boundary_topology",
        "sample_step": 0.025,
    }


def build_clean_tank_render_mesh(
    render_garment: bpy.types.Object,
    actor: bpy.types.Object,
    proxy: bpy.types.Object,
    clearance: float,
) -> dict[str, object]:
    """Replace the sim-folded render copy with a clean quad tank-top shell."""
    samples = torso_depth_envelope(actor)
    z_rows = [0.766, 0.820, 0.950, 1.105, 1.190, 1.285, 1.355]
    half_widths = [0.270, 0.295, 0.315, 0.315, 0.300, 0.275, 0.240]
    x_profile = (-1.0, -0.68, -0.34, 0.34, 0.68, 1.0)
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int, int]] = []

    def depth_at(z: float) -> tuple[float, float]:
        front, back = interpolate_envelope(samples, z)
        return front - clearance, back + clearance

    def add_panel(back: bool) -> list[list[int]]:
        rows: list[list[int]] = []
        for row, (z, width) in enumerate(zip(z_rows, half_widths)):
            front, rear = depth_at(z)
            y = rear if back else front
            row_profile = x_profile
            if not back and row >= 4:
                opening_half = (0.34, 0.50, 0.60)[min(row - 4, 2)]
                row_profile = (-1.0, -0.68, -opening_half, opening_half, 0.68, 1.0)
            row_indices: list[int] = []
            for normalized_x in row_profile:
                local_z = z
                if back and row == len(z_rows) - 1:
                    # A shallow rear neckline keeps the back edge below the neck
                    # while preserving the shoulder strap endpoints.
                    local_z -= 0.035 * (1.0 - abs(normalized_x))
                row_indices.append(len(vertices))
                vertices.append((normalized_x * width, y, local_z))
            rows.append(row_indices)
        for row in range(len(rows) - 1):
            for column in range(len(x_profile) - 1):
                # Leave a real U-shaped front neckline between the two
                # shoulder straps above the chest row.
                if not back and column == 2 and row >= 3:
                    continue
                a, b = rows[row][column], rows[row][column + 1]
                c, d = rows[row + 1][column + 1], rows[row + 1][column]
                faces.append((a, b, c, d))
        return rows

    front_rows = add_panel(back=False)
    back_rows = add_panel(back=True)
    for row in range(len(z_rows) - 1):
        faces.append((front_rows[row][0], back_rows[row][0], back_rows[row + 1][0], front_rows[row + 1][0]))
        faces.append((front_rows[row][5], front_rows[row + 1][5], back_rows[row + 1][5], back_rows[row][5]))

    # Join the front/back top edges over the left and right shoulders.  The
    # previous render shell left these as two disconnected panels, which made
    # the garment read as a bandeau and let the side view expose a notch.
    top = len(z_rows) - 1
    for column in (0, 1, 4):
        faces.append((front_rows[top][column], front_rows[top][column + 1], back_rows[top][column + 1], back_rows[top][column]))

    # Close the lower hem with a shallow underside strip so the side silhouette
    # has a continuous lower edge instead of a semicircular opening.
    bottom = 0
    for column in range(len(x_profile) - 1):
        faces.append((front_rows[bottom][column], back_rows[bottom][column], back_rows[bottom][column + 1], front_rows[bottom][column + 1]))

    mesh = bpy.data.meshes.new("GarmentCodeCleanTankRenderMesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    old_mesh = render_garment.data
    render_garment.data = mesh
    if old_mesh.users == 0:
        bpy.data.meshes.remove(old_mesh)
    if proxy.data.materials:
        render_garment.data.materials.append(proxy.data.materials[0])
    # The generated vertices are already in Actor world coordinates.  Do not
    # inherit the imported OBJ's scale/rotation transform from the proxy.
    render_garment.matrix_world = Matrix.Identity(4)
    return {
        "enabled": True,
        "method": "procedural_clean_quad_tank_top_from_actor_torso_depth_envelope",
        "vertices": len(vertices),
        "faces": len(faces),
        "z_rows": z_rows,
        "half_widths": half_widths,
        "clearance": clearance,
        "neckline": "front_u_opening_back_shallow_scoop",
    }


def render_walk(scene: bpy.types.Scene, output: Path, resolution: int) -> list[dict[str, object]]:
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
    armature = bpy.data.objects.get("Armature")
    if armature is None or not armature.animation_data or armature.animation_data.action is None:
        raise RuntimeError("Actor armature has no active walk action")
    action = armature.animation_data.action
    start, end = int(action.frame_range[0]), int(action.frame_range[1])
    sample_frames = [round(start + (end - start) * index / 7.0) for index in range(8)]
    ortho_scale = max(high.z - low.z, high.x - low.x, high.y - low.y) * 1.16
    frames: list[dict[str, object]] = []
    for direction, (x, y) in DIRECTIONS.items():
        camera = make_camera(scene, center, f"GarmentProxyRender_{direction}", (x, y, center.z), ortho_scale)
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
    bpy.ops.wm.open_mainfile(filepath=str(options.input_blend.resolve()))
    scene = bpy.context.scene
    scene.frame_set(1)
    proxy = bpy.data.objects.get(options.proxy_name)
    if proxy is None or proxy.type != "MESH":
        raise RuntimeError(f"input blend is missing mesh proxy: {options.proxy_name}")
    if not any(modifier.type == "ARMATURE" for modifier in proxy.modifiers):
        raise RuntimeError("physics proxy must retain its Actor Armature modifier")

    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for child in output.iterdir():
        if child.is_file() and child.suffix.lower() in {".png", ".blend", ".json"}:
            child.unlink()

    proxy.name = "GarmentCodeShirt_PhysicsProxy"
    proxy["assetslab_role"] = "physics_proxy"
    proxy["assetslab_proxy_source"] = "official_garmentcode_sim_obj_transferred_to_actor"
    proxy.hide_render = True
    proxy.display_type = "WIRE"

    armature = bpy.data.objects.get("Armature")
    if armature is None:
        raise RuntimeError("input blend is missing Armature")

    animation_proxy = proxy.copy()
    animation_proxy.data = proxy.data.copy()
    animation_proxy.name = "GarmentCodeShirt_AnimationProxy"
    animation_proxy["assetslab_role"] = "animation_deform_proxy"
    animation_proxy["assetslab_source"] = proxy.name
    animation_proxy.parent = None
    animation_proxy.matrix_world = proxy.matrix_world.copy()
    animation_proxy.hide_render = True
    animation_proxy.hide_viewport = False
    animation_proxy.display_type = "WIRE"
    scene.collection.objects.link(animation_proxy)

    render_garment = proxy.copy()
    render_garment.data = proxy.data.copy()
    render_garment.name = "GarmentCodeShirt_RenderGarment"
    render_garment["assetslab_role"] = "render_garment"
    render_garment["assetslab_deformation_source"] = proxy.name
    render_garment.parent = None
    render_garment.matrix_world = proxy.matrix_world.copy()
    render_garment.hide_render = False
    render_garment.hide_viewport = False
    render_garment.display_type = "TEXTURED"
    scene.collection.objects.link(render_garment)
    for modifier in list(render_garment.modifiers):
        render_garment.modifiers.remove(modifier)

    actor = bpy.data.objects.get("ChibiBaseMesh_AccuRIG_InputMesh")
    if actor is None:
        raise RuntimeError("input blend is missing Actor mesh")
    clean_render_garment = (
        build_clean_tank_render_mesh(
            render_garment,
            actor,
            proxy,
            options.render_surface_clearance,
        )
        if options.build_clean_render_garment
        else {"enabled": False}
    )
    clean_surface = (
        build_clean_render_surface(
            render_garment,
            proxy,
            actor,
            options.render_surface_clearance,
        )
        if options.clean_render_surface
        else {"enabled": False}
    )
    animation_cleanup = (
        apply_animation_proxy_cleanup(
            animation_proxy,
            armature,
            options.animation_proxy_smooth_iterations,
            options.animation_proxy_smooth_factor,
            options.animation_proxy_decimate_ratio,
        )
        if options.clean_animation_proxy
        else {"enabled": False, "vertex_count": len(animation_proxy.data.vertices)}
    )
    subdivision = apply_render_subdivision(render_garment, options.subdivision_level)
    deformation = (
        bind_proxy_weighted_armature(render_garment, animation_proxy, armature)
        if options.proxy_weighted_render
        else bind_surface_deform(render_garment, animation_proxy)
    )
    bpy.context.view_layer.update()

    scene["assetslab_garment_proxy_render_pair_status"] = "review_required"
    scene["assetslab_garment_proxy_render_pair_method"] = "physics_proxy_armature_plus_render_subdivision_plus_surface_deform"
    frames = render_walk(scene, output, options.resolution)
    blend_path = output / "garmentcode_proxy_render_pair_candidate.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    report = {
        "schema": "assetslab_garmentcode_proxy_render_pair_review_v1",
        "input_blend": str(options.input_blend.resolve()),
        "physics_proxy": {
            "object": proxy.name,
            "vertex_count": len(proxy.data.vertices),
            "armature_modifier": next(modifier.name for modifier in proxy.modifiers if modifier.type == "ARMATURE"),
            "hide_render": proxy.hide_render,
        },
        "animation_proxy": {
            "object": animation_proxy.name,
            "cleanup": animation_cleanup,
            "hide_render": animation_proxy.hide_render,
        },
        "render_garment": {
            "object": render_garment.name,
            "vertex_count": len(render_garment.data.vertices),
            "clean_render_garment": clean_render_garment,
            "clean_surface": clean_surface,
            "subdivision": subdivision,
            "deformation": deformation,
            "armature_modifier": any(modifier.type == "ARMATURE" for modifier in render_garment.modifiers),
        },
        "animation": {
            "directions": list(DIRECTIONS),
            "frame_count": len(frames),
            "frames": frames,
        },
        "blend": str(blend_path),
        "status": "review_required",
    }
    (output / "manifest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
