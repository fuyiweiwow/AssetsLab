"""Build the small, current-only AssetsLab preview asset set."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "prototype/preview/assets"
BODY_ROOT = ROOT / "prototype/assets/characters/generated/female_adventurer_reference_mannequin_v1_adapted/body_frames"
HEAD_ROOT = ROOT / "prototype/assets/characters/rebuild_atlas_v1_runtime/male"
VERTICAL_ROOT = ROOT / "prototype/assets/characters/generated/body_vertical_update_v1/runtime"
STYLE_ROOT = ROOT / "prototype/assets/characters/generated/skill_pixel_art_experiment_v1"
RECOMMENDED_FIX_ROOT = ROOT / "prototype/assets/characters/generated/recommended_base_horizontal_layer_fix_v1"
CAPTURE_GIF = ROOT / "prototype/test_output/movement_vertical_body_candidate.gif"
RIGHT_ONLY_CAPTURE_GIF = ROOT / "prototype/test_output/movement_rebuild_head_right_only.gif"
SKELETON_FRONT_CAPTURE = ROOT / "prototype/test_output/skeleton_pipeline/front_base.png"
SKELETON_LEG_CAPTURE_DIRECTORY = ROOT / "prototype/test_output/skeleton_pipeline/front_legs"
SKELETON_LEG_CAPTURE_GIF = ROOT / "prototype/test_output/skeleton_pipeline/front_legs.gif"
SKELETON_PELVIS_CAPTURE_DIRECTORY = ROOT / "prototype/test_output/skeleton_pipeline/front_pelvis_bob"
SKELETON_PELVIS_CAPTURE_GIF = ROOT / "prototype/test_output/skeleton_pipeline/front_pelvis_bob.gif"
SKELETON_ARM_CAPTURE_DIRECTORY = ROOT / "prototype/test_output/skeleton_pipeline/front_arm_swing"
SKELETON_ARM_CAPTURE_GIF = ROOT / "prototype/test_output/skeleton_pipeline/front_arm_swing.gif"
SKELETON_SIDE_BASE_CAPTURE = ROOT / "prototype/test_output/skeleton_pipeline/side_base.png"
SKELETON_SIDE_LEG_CAPTURE_DIRECTORY = ROOT / "prototype/test_output/skeleton_pipeline/side_legs"
SKELETON_SIDE_LEG_CAPTURE_GIF = ROOT / "prototype/test_output/skeleton_pipeline/side_legs.gif"
SKELETON_SIDE_PELVIS_CAPTURE_DIRECTORY = ROOT / "prototype/test_output/skeleton_pipeline/side_pelvis_bob"
SKELETON_SIDE_PELVIS_CAPTURE_GIF = ROOT / "prototype/test_output/skeleton_pipeline/side_pelvis_bob.gif"
SKELETON_SIDE_ARM_CAPTURE_DIRECTORY = ROOT / "prototype/test_output/skeleton_pipeline/side_arm_swing"
SKELETON_SIDE_ARM_CAPTURE_GIF = ROOT / "prototype/test_output/skeleton_pipeline/side_arm_swing.gif"
SKELETON_BACK_BASE_CAPTURE = ROOT / "prototype/test_output/skeleton_pipeline/back_base.png"
SKELETON_BACK_LEG_CAPTURE_DIRECTORY = ROOT / "prototype/test_output/skeleton_pipeline/back_legs"
SKELETON_BACK_LEG_CAPTURE_GIF = ROOT / "prototype/test_output/skeleton_pipeline/back_legs.gif"
STAGED_CAPTURE_GIF = OUTPUT / "movement_vertical_body_candidate.gif"
DIRECTIONS = ("front", "right", "back", "left")
CLOTHING_REVIEW_CANDIDATES = (
    {
        "slug": "actor_derived_tshirt_v10",
        "label": "Actor 派生基础 T 恤 v10",
        "root": ROOT / "prototype/test_output/actor_derived_tshirt_v10",
        "status": "待审查",
        "note": "躯干从 Actor 表面提取并外扩间隙，袖子改为完整独立袖筒并绑定上臂骨骼，肩部与躯干重叠；继承 Actor 权重，作为合身基准。",
    },
    {
        "slug": "garmentcode_cloth_v4",
        "label": "GarmentCode 裁片 + Blender Cloth v4",
        "root": ROOT / "prototype/test_output/garmentcode_cloth_v4",
        "status": "拟合失败",
        "note": "保留 GarmentCode 的裁片平移/旋转并提高缝合力与边界密度；默认人体版型与 Q 版 Actor 不匹配，肩部开口、袖片翻折和背部散开，不能进入随机池。",
    },
    {
        "slug": "garmentcode_native_boxmesh_preview_v7",
        "label": "GarmentCode native BoxMesh static v1",
        "root": ROOT / "prototype/test_output/garmentcode_native_boxmesh_preview_v7",
        "status": "待审核",
        "note": "原生 BoxMesh 已消除三角扇和散乱拓扑；这是匹配身体上的静态初始组装态，肩部开口和侧面叠层仍需物理或几何整理。",
    },
    {
        "slug": "garmentcode_native_boxmesh_cloth_v1",
        "label": "GarmentCode native BoxMesh + Blender Cloth v1",
        "root": ROOT / "prototype/test_output/garmentcode_native_boxmesh_cloth_v1",
        "status": "拟合失败",
        "note": "原生缝合网格直接进入 Blender Cloth 后发生严重自相交和尖刺爆炸；暂不进入随机池。",
    },
    {
        "slug": "garmentcode_native_boxmesh_fitted_v1",
        "label": "GarmentCode native BoxMesh body-surface fit v1",
        "root": ROOT / "prototype/test_output/garmentcode_native_boxmesh_fitted_v1",
        "status": "待审核",
        "note": "Shrinkwrap 到匹配身体后，四方向闭合且侧面不再出现横向叠层；领口、袖口和下摆的裁片形状仍需美术检查。",
    },
    {
        "slug": "garmentcode_fitted_boxmesh_cloth_v1",
        "label": "GarmentCode fitted BoxMesh + restrained Cloth v1",
        "root": ROOT / "prototype/test_output/garmentcode_fitted_boxmesh_cloth_v1",
        "status": "待审核",
        "note": "从身体表面拟合姿态开始，低强度 Cloth 稳定完成；关闭自碰撞以避免先前的尖刺爆炸，仍需确认褶皱是否适合像素化。",
    },
    {
        "slug": "proxy_collared_shirt_v5",
        "label": "OverScore Proxy / Collared Shirt v5",
        "root": ROOT / "prototype/test_output/clothes_proxy_collared_shirt_v5",
        "status": "拟合失败",
        "note": "只是包围盒缩放，未贴合身体；侧面外扩，不能视为已穿上。",
    },
    {
        "slug": "proxy_cropped_sweatshirt_v1",
        "label": "OverScore Proxy / Cropped Sweatshirt v1",
        "root": ROOT / "prototype/test_output/clothes_proxy_cropped_sweatshirt_v1",
        "status": "未通过",
        "note": "正面比例较好，侧面袖部块状外扩。",
    },
    {
        "slug": "garmentcode_official_neutral_v1",
        "label": "GarmentCode 官方 neutral body T-shirt v1",
        "root": ROOT / "third_party/GarmentCode/Logs/t-shirt__260805-19-14-57_260805-19-31-09",
        "source_frames": {
            "front": "t-shirt__260805-19-14-57_render_front.png",
            "back": "t-shirt__260805-19-14-57_render_back.png",
        },
        "status": "通过",
        "note": "官方裁片 + GarmentCode Warp 披挂；fails 为空，身体碰撞 0，自交 0，第 405 帧达到静态。该基线只有官方 front/back 视图，尚未进入 Actor。",
    },
    {
        "slug": "garmentcode_official_mean_male_v1",
        "label": "GarmentCode 官方 mean_male T-shirt v1",
        "root": ROOT / "third_party/GarmentCode/Logs/t-shirt__260805-19-36-01_260805-19-38-18",
        "source_frames": {
            "front": "t-shirt__260805-19-36-01_render_front.png",
            "back": "t-shirt__260805-19-36-01_render_back.png",
        },
        "status": "通过",
        "note": "官方 mean_male 身体参数复测；fails 为空，身体碰撞 0，自交 0，第 405 帧达到静态。该基线只有官方 front/back 视图，尚未进入 Actor。",
    },
    {
        "slug": "garmentcode_actor_official_neutral_v1",
        "label": "Official GarmentCode sim.obj -> Actor v1",
        "root": ROOT / "prototype/test_output/garmentcode_actor_official_neutral_v1",
        "status": "review_required",
        "note": "Official Warp CPU neutral-body sim.obj transferred to Actor with side-preserving projection, Actor weights, and the original walk action. Review only; not in the random pool.",
    },
    {
        "slug": "garmentcode_actor_official_neutral_v3_surface_bias",
        "label": "Official GarmentCode sim.obj -> Actor v3 surface bias",
        "root": ROOT / "prototype/test_output/garmentcode_actor_official_neutral_v3_surface_bias",
        "status": "review_required",
        "note": "Experimental millimetre-scale Actor-space correction: front chest flattened, back clearance added, sleeve edges offset outward. The official source mesh and Actor walk action remain unchanged.",
    },
    {
        "slug": "garmentcode_actor_proxy_v1_baseline",
        "label": "GarmentCode Actor proxy / sleeveless baseline v1",
        "root": ROOT / "prototype/test_output/garmentcode_actor_proxy_v1_baseline",
        "status": "review_required",
        "note": "First closed Actor proxy route: 3 cm voxel body, corrected head/neck measurement, GarmentCode Warp 406-frame equilibrium, 19 body collisions and 0 self-collisions. Sleeveless baseline only; not yet a finished random clothing seed.",
    },
)

# Gallery policy: keep only milestone passes and the single current experiment.
# Older diagnostic candidates remain in the worktree but are not republished.
CLOTHING_REVIEW_CANDIDATES = (
    {
        "slug": "garmentcode_official_neutral_v1",
        "label": "GarmentCode milestone / neutral T-shirt",
        "root": ROOT / "third_party/GarmentCode/Logs/t-shirt__260805-19-14-57_260805-19-31-09",
        "source_frames": {
            "front": "t-shirt__260805-19-14-57_render_front.png",
            "back": "t-shirt__260805-19-14-57_render_back.png",
        },
        "status": "通过",
        "note": "官方 neutral body 基线，作为 GarmentCode 物理通过里程碑保留。",
    },
    {
        "slug": "garmentcode_official_mean_male_v1",
        "label": "GarmentCode milestone / mean_male T-shirt",
        "root": ROOT / "third_party/GarmentCode/Logs/t-shirt__260805-19-36-01_260805-19-38-18",
        "source_frames": {
            "front": "t-shirt__260805-19-36-01_render_front.png",
            "back": "t-shirt__260805-19-36-01_render_back.png",
        },
        "status": "通过",
        "note": "官方 mean_male body 基线，作为第二个物理通过里程碑保留。",
    },
    {
        "slug": "garmentcode_actor_proxy_current",
        "label": "Current experiment / regenerated official short sleeve",
        "root": ROOT / "prototype/test_output/clothes_next_short_sleeve_official_transfer_v1",
        "status": "当前实验",
        "note": "保留 GarmentCode 物理代理，独立生成规则四边面无袖 Render Garment（放大 U 型领口、前后肩带连接、侧缝、闭合下摆），再通过 Surface Deform 跟随 5,369 顶点 Animation Proxy；条带和侧面缺口已消除，仍需审核肩带贴合和动作帧。下一次实验会覆盖它。",
    },
)


def rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def clear_output() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for child in OUTPUT.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def load_frames(root: Path, pattern: str) -> list[list[Image.Image]]:
    return [
        [rgba(root / pattern.format(row=row, frame=frame)) for frame in range(8)]
        for row in range(4)
    ]


def load_head_frames() -> dict[str, list[list[Image.Image]]]:
    return {
        layer: load_frames(HEAD_ROOT / f"{layer}_frames", "walk_row{row}_frame{frame}.png")
        for layer in ("face_base", "ears", "face")
    }


def compose(
    body: Image.Image,
    head_frames: dict[str, list[list[Image.Image]]],
    row: int,
    frame: int,
    offset: tuple[int, int],
) -> Image.Image:
    result = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    result.alpha_composite(body)
    for layer in ("face_base", "ears", "face"):
        result.alpha_composite(head_frames[layer][row][frame], dest=offset)
    return result


def sheet(frames: list[list[Image.Image]]) -> Image.Image:
    output = Image.new("RGBA", (512, 256), (0, 0, 0, 0))
    for row in range(4):
        for frame in range(8):
            output.alpha_composite(frames[row][frame], dest=(frame * 64, row * 64))
    return output


def strip(frames: list[Image.Image]) -> Image.Image:
    output = Image.new("RGBA", (len(frames) * 64, 64), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        output.alpha_composite(frame, dest=(index * 64, 0))
    return output


def gif(frames: list[Image.Image], path: Path) -> None:
    enlarged = [frame.resize((256, 256), Image.Resampling.NEAREST) for frame in frames]
    enlarged[0].save(path, save_all=True, append_images=enlarged[1:], duration=100, loop=0, disposal=2)


def skeleton_contact_sheet(paths: list[Path], path: Path) -> None:
	thumbnail_size = (240, 150)
	output = Image.new("RGB", (thumbnail_size[0] * 4, thumbnail_size[1] * 2), (17, 24, 39))
	draw = ImageDraw.Draw(output)
	for index, source_path in enumerate(paths):
		with Image.open(source_path) as source:
			thumbnail = source.convert("RGB").resize(thumbnail_size, Image.Resampling.LANCZOS)
			x = (index % 4) * thumbnail_size[0]
			y = (index // 4) * thumbnail_size[1]
			output.paste(thumbnail, (x, y))
			draw.text((x + 8, y + 8), "F%d" % index, fill=(255, 241, 168))
	output.save(path)


def clothing_contact_sheet(root: Path, path: Path) -> None:
    """Create a 4-direction x 8-frame review sheet for one candidate."""

    cell = 128
    output = Image.new("RGB", (cell * 8, cell * 4), (17, 24, 39))
    draw = ImageDraw.Draw(output)
    for row, direction in enumerate(DIRECTIONS):
        for frame in range(8):
            source = root / f"{direction}_{frame:02d}.png"
            if not source.exists():
                continue
            with Image.open(source) as image:
                thumbnail = image.convert("RGB").resize((cell, cell), Image.Resampling.LANCZOS)
                x = frame * cell
                y = row * cell
                output.paste(thumbnail, (x, y))
                draw.rectangle((x + 2, y + 2, x + 44, y + 18), fill=(8, 11, 19))
                draw.text((x + 5, y + 4), f"{direction[0].upper()}{frame}", fill=(255, 241, 168))
    output.save(path)


def clothing_pair_sheet(source_frames: dict[str, Path], path: Path) -> None:
    """Create a truthful front/back sheet for official static renders."""

    cell = 256
    output = Image.new("RGB", (cell * 2, cell), (17, 24, 39))
    draw = ImageDraw.Draw(output)
    for column, direction in enumerate(("front", "back")):
        source = source_frames.get(direction)
        if source is None or not source.exists():
            continue
        with Image.open(source) as image:
            thumbnail = image.convert("RGB")
            thumbnail.thumbnail((cell, cell), Image.Resampling.LANCZOS)
            x = column * cell + (cell - thumbnail.width) // 2
            y = (cell - thumbnail.height) // 2
            output.paste(thumbnail, (x, y))
            draw.rectangle((column * cell + 6, 6, column * cell + 70, 26), fill=(8, 11, 19))
            draw.text((column * cell + 12, 9), direction, fill=(255, 241, 168))
    output.save(path)


def copy_clothing_review_assets() -> list[dict[str, object]]:
    gallery_root = OUTPUT / "clothes_gallery"
    gallery_root.mkdir(parents=True, exist_ok=True)
    published: list[dict[str, object]] = []
    for candidate in CLOTHING_REVIEW_CANDIDATES:
        root = candidate["root"]
        source_frame_names = candidate.get("source_frames")
        if not isinstance(root, Path):
            continue
        if source_frame_names:
            source_frames = {
                direction: root / filename
                for direction, filename in source_frame_names.items()
            }
            if not all(path.exists() for path in source_frames.values()):
                continue
        elif not (root / "manifest.json").exists():
            continue
        slug = str(candidate["slug"])
        destination = gallery_root / slug
        destination.mkdir(parents=True, exist_ok=True)
        if source_frame_names:
            clothing_pair_sheet(source_frames, destination / "front_back.png")
        else:
            clothing_contact_sheet(root, destination / "4way_8frames.png")
        stills = []
        directions = source_frames.keys() if source_frame_names else DIRECTIONS
        for direction in directions:
            source = source_frames[direction] if source_frame_names else root / f"{direction}_00.png"
            target = destination / f"{direction}_00.png"
            shutil.copy2(source, target)
            stills.append(target.relative_to(OUTPUT).as_posix())
        contact_sheet = destination / ("front_back.png" if source_frame_names else "4way_8frames.png")
        if slug == "garmentcode_actor_proxy_current":
            candidate_label = "Current experiment / official milestone transferred to Actor"
            candidate_note = (
                "Current review candidate: a freshly regenerated official GarmentCode short-sleeve pattern with CircleNeckHalf, "
                "official Warp draping, then side-preserving Actor transfer and armature weights. It remains review_required "
                "because the Actor transfer still has sleeve/hem penetration; the sleeveless baseline and prior milestone transfer are preserved."
            )
        else:
            candidate_label = candidate["label"]
            candidate_note = candidate["note"]
        published.append(
            {
                "slug": slug,
                "label": candidate_label,
                "status": candidate["status"],
                "note": candidate_note,
                "contact_sheet": contact_sheet.relative_to(OUTPUT).as_posix(),
                "stills": stills,
            }
        )
    return published


def load_offsets() -> dict[str, tuple[int, int]]:
    payload = json.loads((HEAD_ROOT / "runtime_manifest.json").read_text(encoding="utf-8"))
    return {
        direction: tuple(payload.get("body_anchor_offsets", {}).get(direction, [0, 0]))
        for direction in DIRECTIONS
    }


def main() -> int:
    recommended_source = RECOMMENDED_FIX_ROOT / "right_source.png"
    recommended_runtime = RECOMMENDED_FIX_ROOT / "runtime"
    recommended_ready = recommended_source.exists() and (recommended_runtime / "right_walk_8.png").exists() and (recommended_runtime / "right_walk_8.gif").exists()
    if recommended_ready:
        subprocess.run(
            [sys.executable, str(ROOT / "tools/build_recommended_horizontal_fix.py")],
            cwd=ROOT,
            check=True,
        )
    clear_output()
    if not (BODY_ROOT / "walk_row0_frame0.png").exists():
        clothing_gallery = copy_clothing_review_assets()
        manifest = {
            "schema": "assetslab_clothing_preview_v1",
            "status": "clothing_review_only",
            "reason": "retired current-body source PNGs are not present in the checkout",
            "clothing_gallery": clothing_gallery,
            "files": sorted(path.name for path in OUTPUT.rglob("*") if path.is_file()),
        }
        (OUTPUT / "current_preview_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print("CURRENT_PREVIEW_ASSETS_PASS clothing_review_only")
        return 0
    body_frames = load_frames(BODY_ROOT, "walk_row{row}_frame{frame}.png")
    head_frames = load_head_frames()
    offsets = load_offsets()

    body_sheet = sheet(body_frames)
    character_frames = [
        [compose(body_frames[row][frame], head_frames, row, frame, offsets[DIRECTIONS[row]]) for frame in range(8)]
        for row in range(4)
    ]
    head_only_frames = [
        [compose(Image.new("RGBA", (64, 64), (0, 0, 0, 0)), head_frames, row, frame, (0, 0)) for frame in range(8)]
        for row in range(4)
    ]
    character_sheet = sheet(character_frames)
    head_sheet = sheet(head_only_frames)
    body_sheet.save(OUTPUT / "current_body_4way_8frames.png")
    character_sheet.save(OUTPUT / "current_character_4way_8frames.png")
    head_sheet.save(OUTPUT / "current_head_4way_8frames.png")
    gif([character_frames[row][frame] for row in range(4) for frame in range(8)], OUTPUT / "current_character_walk_4way.gif")

    for row, direction in enumerate(DIRECTIONS):
        character_frames[row][0].resize((512, 512), Image.Resampling.NEAREST).save(OUTPUT / f"current_{direction}.png")
        body_frames[row][0].resize((512, 512), Image.Resampling.NEAREST).save(OUTPUT / f"current_{direction}_body.png")

    vertical_front = [rgba(VERTICAL_ROOT / "front_frames" / f"frame{frame}.png") for frame in range(8)]
    vertical_back = [rgba(VERTICAL_ROOT / "back_frames" / f"frame{frame}.png") for frame in range(8)]
    vertical_front_character = [compose(frame, head_frames, 0, index, (0, 0)) for index, frame in enumerate(vertical_front)]
    vertical_back_character = [compose(frame, head_frames, 2, index, (0, 0)) for index, frame in enumerate(vertical_back)]
    strip(vertical_front_character).save(OUTPUT / "vertical_front_8frames.png")
    strip(vertical_back_character).save(OUTPUT / "vertical_back_8frames.png")
    gif(vertical_front_character + vertical_back_character, OUTPUT / "vertical_candidate_rebuilt.gif")
    if CAPTURE_GIF.exists():
        shutil.copy2(CAPTURE_GIF, OUTPUT / "movement_vertical_body_candidate.gif")
    elif STAGED_CAPTURE_GIF.exists():
        shutil.copy2(STAGED_CAPTURE_GIF, OUTPUT / "movement_vertical_body_candidate.gif")
    if RIGHT_ONLY_CAPTURE_GIF.exists():
        shutil.copy2(RIGHT_ONLY_CAPTURE_GIF, OUTPUT / "movement_rebuild_head_right_only.gif")
    if SKELETON_FRONT_CAPTURE.exists():
        shutil.copy2(SKELETON_FRONT_CAPTURE, OUTPUT / "skeleton_front_base.png")
    skeleton_leg_frames = [SKELETON_LEG_CAPTURE_DIRECTORY / f"frame_{index:02d}.png" for index in range(8)]
    if all(path.exists() for path in skeleton_leg_frames):
        skeleton_contact_sheet(skeleton_leg_frames, OUTPUT / "skeleton_front_legs_8frames.png")
    if SKELETON_LEG_CAPTURE_GIF.exists():
        shutil.copy2(SKELETON_LEG_CAPTURE_GIF, OUTPUT / "skeleton_front_legs.gif")
    skeleton_pelvis_frames = [SKELETON_PELVIS_CAPTURE_DIRECTORY / f"frame_{index:02d}.png" for index in range(8)]
    if all(path.exists() for path in skeleton_pelvis_frames):
        skeleton_contact_sheet(skeleton_pelvis_frames, OUTPUT / "skeleton_front_pelvis_bob_8frames.png")
    if SKELETON_PELVIS_CAPTURE_GIF.exists():
        shutil.copy2(SKELETON_PELVIS_CAPTURE_GIF, OUTPUT / "skeleton_front_pelvis_bob.gif")
    skeleton_arm_frames = [SKELETON_ARM_CAPTURE_DIRECTORY / f"frame_{index:02d}.png" for index in range(8)]
    if all(path.exists() for path in skeleton_arm_frames):
        skeleton_contact_sheet(skeleton_arm_frames, OUTPUT / "skeleton_front_arm_swing_8frames.png")
    if SKELETON_ARM_CAPTURE_GIF.exists():
        shutil.copy2(SKELETON_ARM_CAPTURE_GIF, OUTPUT / "skeleton_front_arm_swing.gif")
    if SKELETON_SIDE_BASE_CAPTURE.exists():
        shutil.copy2(SKELETON_SIDE_BASE_CAPTURE, OUTPUT / "skeleton_side_base.png")
    skeleton_side_leg_frames = [SKELETON_SIDE_LEG_CAPTURE_DIRECTORY / f"frame_{index:02d}.png" for index in range(8)]
    if all(path.exists() for path in skeleton_side_leg_frames):
        skeleton_contact_sheet(skeleton_side_leg_frames, OUTPUT / "skeleton_side_legs_8frames.png")
    if SKELETON_SIDE_LEG_CAPTURE_GIF.exists():
        shutil.copy2(SKELETON_SIDE_LEG_CAPTURE_GIF, OUTPUT / "skeleton_side_legs.gif")
    skeleton_side_pelvis_frames = [SKELETON_SIDE_PELVIS_CAPTURE_DIRECTORY / f"frame_{index:02d}.png" for index in range(8)]
    if all(path.exists() for path in skeleton_side_pelvis_frames):
        skeleton_contact_sheet(skeleton_side_pelvis_frames, OUTPUT / "skeleton_side_pelvis_bob_8frames.png")
    if SKELETON_SIDE_PELVIS_CAPTURE_GIF.exists():
        shutil.copy2(SKELETON_SIDE_PELVIS_CAPTURE_GIF, OUTPUT / "skeleton_side_pelvis_bob.gif")
    skeleton_side_arm_frames = [SKELETON_SIDE_ARM_CAPTURE_DIRECTORY / f"frame_{index:02d}.png" for index in range(8)]
    if all(path.exists() for path in skeleton_side_arm_frames): skeleton_contact_sheet(skeleton_side_arm_frames, OUTPUT / "skeleton_side_arm_swing_8frames.png")
    if SKELETON_SIDE_ARM_CAPTURE_GIF.exists(): shutil.copy2(SKELETON_SIDE_ARM_CAPTURE_GIF, OUTPUT / "skeleton_side_arm_swing.gif")
    if SKELETON_BACK_BASE_CAPTURE.exists(): shutil.copy2(SKELETON_BACK_BASE_CAPTURE, OUTPUT / "skeleton_back_base.png")
    skeleton_back_leg_frames = [SKELETON_BACK_LEG_CAPTURE_DIRECTORY / f"frame_{index:02d}.png" for index in range(8)]
    if all(path.exists() for path in skeleton_back_leg_frames): skeleton_contact_sheet(skeleton_back_leg_frames, OUTPUT / "skeleton_back_legs_8frames.png")
    if SKELETON_BACK_LEG_CAPTURE_GIF.exists(): shutil.copy2(SKELETON_BACK_LEG_CAPTURE_GIF, OUTPUT / "skeleton_back_legs.gif")

    style_image = STYLE_ROOT / "turnaround_db16_transparent.png"
    if style_image.exists():
        shutil.copy2(style_image, OUTPUT / "style_experiment_db16.png")

    if recommended_ready:
        shutil.copy2(recommended_source, OUTPUT / "recommended_horizontal_layer_fix_source.png")
        shutil.copy2(recommended_runtime / "right_walk_8.png", OUTPUT / "recommended_horizontal_layer_fix_8frames.png")
        shutil.copy2(recommended_runtime / "right_walk_8.gif", OUTPUT / "recommended_horizontal_layer_fix.gif")
    clothing_gallery = copy_clothing_review_assets()

    manifest = {
        "schema": "assetslab_current_preview_v2",
        "status": "current_test_base_only",
        "test_base": {
            "body": "prototype/assets/characters/generated/female_adventurer_reference_mannequin_v1_adapted/body_frames",
            "head": "prototype/assets/characters/rebuild_atlas_v1_runtime/male",
            "body_registration": "runtime_manifest.json body_anchor_offsets",
            "directions": list(DIRECTIONS),
            "frames_per_direction": 8,
        },
        "vertical_candidate": {
            "source": "prototype/assets/characters/generated/body_vertical_update_v1/runtime",
            "head_anchor_offsets": {"front": [0, 0], "back": [0, 0]},
            "status": "candidate_for_visual_review",
        },
        "recommended_horizontal_layer_fix": {
            "source": "prototype/assets/characters/generated/recommended_base_horizontal_layer_fix_v1/right_source.png",
            "runtime": "prototype/assets/characters/generated/recommended_base_horizontal_layer_fix_v1/runtime",
            "foot_occlusion_policy": ["right_front", "right_front", "right_front", "left_front", "left_front", "left_front", "left_front", "right_front"],
            "status": "candidate_for_visual_review" if recommended_ready else "source_removed",
        },
        "clothing_gallery": clothing_gallery,
        "skeleton_walk_pipeline": {
            "source": "prototype/assets/characters/generated/skeleton_walk_pipeline_v1/back_base_manifest.json",
            "stage": "back_base",
            "status": "active_review",
            "next_stage": "back_legs_8_frames",
        },
        "excluded": "legacy bodies, RGS proxies, skeleton tests, old generated walk GIFs, and retired preview pages",
        "files": sorted(path.name for path in OUTPUT.iterdir() if path.is_file()),
    }
    (OUTPUT / "current_preview_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("CURRENT_PREVIEW_ASSETS_PASS base=4x8 vertical=2x8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
