from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
BODY_ROOT = ROOT / "prototype/assets/characters/generated/female_adventurer_reference_mannequin_v1"
FEATURE_ATLAS = ROOT / "prototype/preview/assets/female_adventurer_reference_feature_atlas_v1.png"
OUTPUT = ROOT / "prototype/preview/assets/female_adventurer_reference_feature_composite_v1"
DIRECTIONS = ("front", "right", "back", "left")
CELL = 64


COMPONENT_BOXES = {
    "front": {
        "left_brow": (190, 290, 255, 311),
        "left_eye": (203, 342, 249, 411),
        "left_ear": (114, 367, 155, 429),
        "right_brow": (360, 289, 422, 311),
        "right_eye": (366, 342, 411, 411),
        "right_ear": (456, 367, 497, 430),
    },
    "right": {
        "eye": (215, 342, 258, 411),
        "brow": (209, 289, 271, 311),
        "ear": (361, 367, 403, 429),
    },
    "back": {
        "left_ear": (124, 367, 166, 429),
        "right_ear": (403, 367, 445, 430),
    },
    "left": {
        "eye": (208, 342, 251, 411),
        "brow": (194, 290, 257, 311),
        "ear": (105, 367, 147, 430),
    },
}

COMPONENT_POSITIONS = {
    "front": {
        "left_brow": (24, 14), "left_eye": (24, 17), "left_ear": (16, 19),
        "right_brow": (35, 14), "right_eye": (35, 17), "right_ear": (44, 19),
    },
    "right": {"brow": (36, 14), "eye": (36, 17), "ear": (16, 19)},
    "back": {"left_ear": (16, 21), "right_ear": (44, 21)},
    "left": {"brow": (18, 14), "eye": (18, 17), "ear": (44, 19)},
}


def prepare_overlay(panel: Image.Image, direction: str) -> Image.Image:
    overlay = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    for name, source_box in COMPONENT_BOXES[direction].items():
        component = panel.crop(source_box)
        scale = 0.10
        component = component.resize(
            (max(1, round(component.width * scale)), max(1, round(component.height * scale))),
            Image.Resampling.NEAREST,
        )
        overlay.alpha_composite(component, COMPONENT_POSITIONS[direction][name])
    return overlay


def main() -> int:
    atlas = Image.open(FEATURE_ATLAS).convert("RGBA")
    panel_width = atlas.width // 4
    overlays = {}
    manifest = {"schema": "reference_mannequin_feature_composite_v1", "directions": {}}
    for index, direction in enumerate(DIRECTIONS):
        panel = atlas.crop((index * panel_width, 0, (index + 1) * panel_width, atlas.height))
        overlays[direction] = prepare_overlay(panel, direction)
        manifest["directions"][direction] = {
            "panel_index": index,
            "overlay_size": list(overlays[direction].size),
            "component_boxes": COMPONENT_BOXES[direction],
            "component_positions": COMPONENT_POSITIONS[direction],
            "source": "prototype/preview/assets/female_adventurer_reference_feature_atlas_v1.png",
        }

    OUTPUT.mkdir(parents=True, exist_ok=True)
    all_frames = {}
    for direction in DIRECTIONS:
        frames = []
        for index in range(8):
            body = Image.open(BODY_ROOT / direction / f"frame{index}.png").convert("RGBA")
            body.alpha_composite(overlays[direction], (0, 0))
            body.save(OUTPUT / f"{direction}_frame{index}.png")
            frames.append(body)
        frames[0].save(
            OUTPUT / f"{direction}.gif",
            save_all=True,
            append_images=frames[1:],
            duration=100,
            loop=0,
            disposal=2,
        )
        all_frames[direction] = frames

    contact = Image.new("RGBA", (CELL * 8, CELL * 4), (22, 25, 39, 255))
    for row, direction in enumerate(DIRECTIONS):
        for index, frame in enumerate(all_frames[direction]):
            contact.alpha_composite(frame, (index * CELL, row * CELL))
    contact.resize((CELL * 8 * 4, CELL * 4 * 4), Image.Resampling.NEAREST).convert("RGB").save(
        OUTPUT / "contact.png"
    )
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("REFERENCE_MANNEQUIN_FEATURE_COMPOSITE_PASS directions=4 frames=32")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
