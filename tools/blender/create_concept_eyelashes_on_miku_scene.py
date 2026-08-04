"""Create thick, long concept-art upper eyelashes from the Miku eye proportions."""

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

from render_easy_anime_eye_on_accurig import flat_material, make_camera, world_bounds  # noqa: E402


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--inner-margin", type=float, default=0.10, help="Margin from the eye center-side inner corner")
    parser.add_argument("--outer-margin", type=float, default=0.025, help="Margin from the eye outer contour")
    parser.add_argument("--base-z", type=float, default=2.18)
    parser.add_argument("--arch-height", type=float, default=0.035)
    parser.add_argument("--outer-drop", type=float, default=0.025)
    parser.add_argument("--thickness", type=float, default=0.050)
    parser.add_argument("--front-offset", type=float, default=0.012)
    parser.add_argument("--save-blend", action="store_true")
    return parser.parse_args(argv)


def actor_surface_y(actor: bpy.types.Object, x: float, z: float, fallback: float) -> float:
    inverse = actor.matrix_world.inverted()
    origin = inverse @ Vector((x, -2.0, z))
    direction = (inverse.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
    hit, location, _normal, _face = actor.ray_cast(origin, direction)
    if not hit:
        return fallback
    return (actor.matrix_world @ location).y


def make_lash(
    name: str,
    side: float,
    inner_x: float,
    outer_x: float,
    base_z: float,
    arch_height: float,
    outer_drop: float,
    thickness: float,
    actor: bpy.types.Object,
    front_offset: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    # Start at the inner corner and travel toward the outward facial contour.
    fractions = (0.0, 0.20, 0.45, 0.70, 1.0)
    widths = (thickness * 0.34, thickness * 0.50, thickness * 0.56, thickness * 0.48, thickness * 0.16)
    vertices: list[tuple[float, float, float]] = []
    for fraction, width in zip(fractions, widths):
        x = inner_x + (outer_x - inner_x) * fraction
        z = base_z + arch_height * (1.0 - (2.0 * fraction - 0.68) ** 2) - outer_drop * fraction
        for vertical in (-width * 0.5, width * 0.5):
            vertex_z = z + vertical
            y = actor_surface_y(actor, x, vertex_z, -0.70) - front_offset
            vertices.append((x, y, vertex_z))

    faces = []
    for index in range(len(fractions) - 1):
        left = index * 2
        right = (index + 1) * 2
        faces.append((left, right, right + 1, left + 1))
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj["assetslab_role"] = "concept_eyelash_candidate"
    obj["source_reference"] = "front-character-anchor.png"
    obj["direction"] = "outer_contour"
    return obj


def parent_to_head(obj: bpy.types.Object, armature: bpy.types.Object) -> None:
    matrix = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = "CC_Base_Head"
    obj.matrix_world = matrix


def add_lights(scene: bpy.types.Scene, target: Vector) -> None:
    for location, energy, size in (((0.0, -4.0, 5.0), 900.0, 4.0), ((-3.0, -2.0, 3.0), 350.0, 3.0)):
        data = bpy.data.lights.new("ConceptEyelashArea", "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new("ConceptEyelashArea", data)
        scene.collection.objects.link(light)
        light.location = location
        light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()


def main() -> int:
    options = cli_args()
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(options.base_blend.resolve()))
    actor = bpy.data.objects.get("ChibiBaseMesh_AccuRIG_InputMesh")
    armature = bpy.data.objects.get("Armature")
    eye = bpy.data.objects.get("MikuChibiEyeball")
    if actor is None or armature is None or eye is None:
        raise RuntimeError("base scene is missing actor, Armature, or MikuChibiEyeball")

    eye_low, eye_high = world_bounds([eye])
    eye_width = eye_high.x - eye_low.x
    single_eye_width = eye_width * 0.5
    inner_distance = options.inner_margin
    outer_distance = single_eye_width - options.outer_margin
    material = flat_material("ConceptEyelashDark", (0.012, 0.003, 0.002, 1.0), 0.75)
    lashes = [
        make_lash("ConceptEyelash.L", -1.0, -inner_distance, -outer_distance, options.base_z, options.arch_height, options.outer_drop, options.thickness, actor, options.front_offset, material),
        make_lash("ConceptEyelash.R", 1.0, inner_distance, outer_distance, options.base_z, options.arch_height, options.outer_drop, options.thickness, actor, options.front_offset, material),
    ]
    for lash in lashes:
        parent_to_head(lash, armature)

    actor_low, actor_high = world_bounds([actor])
    actor_center = (actor_low + actor_high) * 0.5
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = scene.render.resolution_y = 256
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("ConceptEyelashWorld")
    scene.world.color = (0.06, 0.06, 0.08)
    add_lights(scene, actor_center)
    cameras = {
        "front": (0.0, -12.0, actor_center.z),
        "right": (12.0, 0.0, actor_center.z),
        "back": (0.0, 12.0, actor_center.z),
        "left": (-12.0, 0.0, actor_center.z),
    }
    for direction, location in cameras.items():
        camera = make_camera(scene, actor_center, direction, location, max(4.0, actor_high.z - actor_low.z + 0.6))
        scene.camera = camera
        scene.render.filepath = str(output / f"{direction}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)

    lash_width = outer_distance - inner_distance
    manifest = {
        "schema": "assetslab_concept_eyelashes_on_miku_scene_v1",
        "base_blend": str(options.base_blend.resolve()),
        "reference_image": "front-character-anchor.png",
        "objects": [lash.name for lash in lashes],
        "proportion_analysis": {
            "miku_eye_pair_width": eye_width,
            "estimated_single_eye_width": single_eye_width,
            "custom_lash_width": lash_width,
            "lash_to_single_eye_ratio": lash_width / single_eye_width,
        },
        "parameters": {
            "inner_margin": options.inner_margin,
            "outer_margin": options.outer_margin,
            "base_z": options.base_z,
            "arch_height": options.arch_height,
            "outer_drop": options.outer_drop,
            "thickness": options.thickness,
            "front_offset": options.front_offset,
        },
        "directions": list(cameras),
        "status": "static_four_direction_review_only",
    }
    (output / "feature_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if options.save_blend:
        blend_path = output / "concept_eyelashes_on_miku_scene.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
        print(f"BLEND_SAVED {blend_path}")
    print(f"CONCEPT_EYELASHES_PASS output={output} ratio={lash_width / single_eye_width:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
