from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from make_reference_mannequin_walk_previews import DIRECTIONS, INPUT, crop_strip


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "prototype/assets/characters/generated/female_adventurer_reference_mannequin_v1"
PREVIEW = ROOT / "prototype/preview/assets"
CELL_SIZE = 64
BASELINE_Y = 60
TARGET_HEIGHT = 54


def harden_alpha(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
    reduced = rgba.convert("RGB").quantize(colors=12, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGBA")
    reduced.putalpha(alpha)
    return reduced


def make_frame(image: Image.Image) -> Image.Image:
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("empty source frame")
    subject = image.crop(bbox)
    scale = TARGET_HEIGHT / subject.height
    if subject.width * scale > CELL_SIZE - 8:
        scale = (CELL_SIZE - 8) / subject.width
    size = (max(1, round(subject.width * scale)), max(1, round(subject.height * scale)))
    subject = subject.resize(size, Image.Resampling.NEAREST)
    subject = harden_alpha(subject)
    frame = Image.new("RGBA", (CELL_SIZE, CELL_SIZE), (0, 0, 0, 0))
    x = (CELL_SIZE - subject.width) // 2
    y = BASELINE_Y - subject.height
    frame.alpha_composite(subject, (x, y))
    return frame


def save_sheet(frames: list[Image.Image], direction: str) -> None:
    sheet = Image.new("RGBA", (CELL_SIZE * len(frames), CELL_SIZE), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        sheet.alpha_composite(frame, (index * CELL_SIZE, 0))
        frame.save(OUTPUT / direction / f"frame{index}.png")
    sheet.save(OUTPUT / f"{direction}.png")
    frames[0].save(
        PREVIEW / f"female_adventurer_reference_mannequin_v1_{direction}.gif",
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
        disposal=2,
    )


def save_contact(frames_by_direction: dict[str, list[Image.Image]]) -> None:
    sheet = Image.new("RGBA", (CELL_SIZE * 8, CELL_SIZE * 4), (22, 25, 39, 255))
    for row, direction in enumerate(DIRECTIONS):
        for index, frame in enumerate(frames_by_direction[direction]):
            sheet.alpha_composite(frame, (index * CELL_SIZE, row * CELL_SIZE))
    sheet.convert("RGB").resize((CELL_SIZE * 8 * 4, CELL_SIZE * 4 * 4), Image.Resampling.NEAREST).save(
        PREVIEW / "female_adventurer_reference_mannequin_v1_runtime_contact.png"
    )


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    frames_by_direction: dict[str, list[Image.Image]] = {}
    for direction in DIRECTIONS:
        (OUTPUT / direction).mkdir(parents=True, exist_ok=True)
        source_frames = crop_strip(INPUT / f"{direction}.png")
        frames = [make_frame(frame) for frame in source_frames]
        frames_by_direction[direction] = frames
        save_sheet(frames, direction)
    save_contact(frames_by_direction)
    manifest = {
        "schema": "reference_mannequin_runtime_v1",
        "cell_size": [CELL_SIZE, CELL_SIZE],
        "frame_count": 8,
        "directions": list(DIRECTIONS),
        "baseline_y": BASELINE_Y,
        "target_subject_height": TARGET_HEIGHT,
        "source": "prototype/preview/assets/female_adventurer_reference_mannequin_walk_v1",
        "status": "candidate_runtime_reference_not_final_art",
        "processing": ["alpha_bbox_registration", "nearest_neighbor_resize", "12_color_quantization", "hard_alpha_threshold"],
    }
    (OUTPUT / "runtime_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("REFERENCE_MANNEQUIN_RUNTIME_PASS directions=" + ",".join(DIRECTIONS) + " cells=32")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
