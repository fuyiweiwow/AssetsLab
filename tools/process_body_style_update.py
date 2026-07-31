from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "prototype/assets/characters/generated/body_style_update_v1.png"
OUTPUT = ROOT / "prototype/assets/characters/generated/body_style_update_v1_runtime"
CELL_SIZE = 64
FRAME_COUNT = 8
TARGET_BASELINE_Y = 59
TARGET_BODY_HEIGHT = 30


def alpha_groups(image: Image.Image) -> list[tuple[int, int]]:
    alpha = image.getchannel("A")
    columns = [any(alpha.getpixel((x, y)) > 20 for y in range(image.height)) for x in range(image.width)]
    groups: list[tuple[int, int]] = []
    start: int | None = None
    for x, active in enumerate(columns + [False]):
        if active and start is None:
            start = x
        elif not active and start is not None:
            groups.append((start, x - 1))
            start = None
    return groups


def trim_alpha(image: Image.Image) -> Image.Image:
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("frame contains no visible pixels")
    return image.crop(bbox)


def normalize(frame: Image.Image) -> Image.Image:
    frame = trim_alpha(frame)
    scale = TARGET_BODY_HEIGHT / frame.height
    width = max(1, round(frame.width * scale))
    frame = frame.resize((width, TARGET_BODY_HEIGHT), Image.Resampling.NEAREST)
    result = Image.new("RGBA", (CELL_SIZE, CELL_SIZE))
    x = (CELL_SIZE - width) // 2
    y = TARGET_BASELINE_Y - TARGET_BODY_HEIGHT + 1
    result.alpha_composite(frame, (x, y))
    return result


def save_sheet(frames: list[Image.Image], path: Path) -> None:
    sheet = Image.new("RGBA", (CELL_SIZE * FRAME_COUNT, CELL_SIZE))
    for frame, image in enumerate(frames):
        sheet.alpha_composite(image, (frame * CELL_SIZE, 0))
    sheet.save(path)


def main() -> int:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    image = Image.open(SOURCE).convert("RGBA")
    groups = alpha_groups(image)
    if len(groups) != FRAME_COUNT:
        raise ValueError(f"expected {FRAME_COUNT} frame groups, found {len(groups)}")

    frame_dir = OUTPUT / "right_frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    frames: list[Image.Image] = []
    for frame, (left, right) in enumerate(groups):
        crop = image.crop((left, 0, right + 1, image.height))
        normalized = normalize(crop)
        normalized.save(frame_dir / f"frame{frame}.png")
        frames.append(normalized)
    sheet = OUTPUT / "right_walk_8.png"
    save_sheet(frames, sheet)
    manifest = {
        "schema": "body_style_update_runtime_v1",
        "status": "style_candidate_right_direction_only",
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "direction": "right",
        "frame_count": FRAME_COUNT,
        "cell_size": [CELL_SIZE, CELL_SIZE],
        "target_body_height": TARGET_BODY_HEIGHT,
        "baseline_y": TARGET_BASELINE_Y,
        "frame_directory": frame_dir.relative_to(ROOT).as_posix(),
        "sheet": sheet.relative_to(ROOT).as_posix(),
        "notes": "Generated from the original AssetsLab pixel language reference. This is a style candidate and must not replace the authoritative four-direction body until front/back/left are generated and the head seam is reviewed.",
    }
    (OUTPUT / "runtime_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"BODY_STYLE_UPDATE_PASS frames={FRAME_COUNT} size={CELL_SIZE}x{CELL_SIZE} baseline={TARGET_BASELINE_Y}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
