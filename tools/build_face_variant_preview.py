"""Build a contact sheet for the currently integrated face variants."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
VARIANT_COUNT = 8
CELL_SIZE = 64
PREVIEW_SIZE = 192
FACE_MAX_SIZE = (20, 8)
EAR_MAX_SIZE = (32, 12)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gender", choices=("male", "female"), default="male")
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def load_rgba(path: Path) -> Image.Image:
    if not path.is_file():
        raise SystemExit(f"FACE_VARIANT_PREVIEW_FAIL: missing asset: {path}")
    image = Image.open(path).convert("RGBA")
    if image.size != (CELL_SIZE, CELL_SIZE):
        raise SystemExit(f"FACE_VARIANT_PREVIEW_FAIL: unexpected size {image.size}: {path}")
    return image


def main() -> int:
    options = parse_args()
    output = options.output.resolve()
    head_root = ROOT / "prototype" / "assets" / "characters" / "chibi" / f"head_{options.gender}_frames"
    face_root = ROOT / "prototype" / "assets" / "characters" / "faces"
    output.mkdir(parents=True, exist_ok=True)
    head = load_rgba(head_root / "walk_row0_frame0.png")
    previews: list[Image.Image] = []
    for variant_id in range(VARIANT_COUNT):
        canvas = head.copy()
        ear = load_rgba(face_root / f"ear_{variant_id:02d}" / "frames" / "walk_row0_frame0.png")
        face = load_rgba(face_root / f"face_{variant_id:02d}" / "frames" / "walk_row0_frame0.png")
        face_bbox = face.getchannel("A").getbbox()
        ear_bbox = ear.getchannel("A").getbbox()
        if face_bbox is None or ear_bbox is None:
            raise SystemExit(f"FACE_VARIANT_PREVIEW_FAIL: empty overlay variant {variant_id}")
        face_size = (face_bbox[2] - face_bbox[0], face_bbox[3] - face_bbox[1])
        ear_size = (ear_bbox[2] - ear_bbox[0], ear_bbox[3] - ear_bbox[1])
        if face_size[0] > FACE_MAX_SIZE[0] or face_size[1] > FACE_MAX_SIZE[1]:
            raise SystemExit(f"FACE_VARIANT_PREVIEW_FAIL: face variant {variant_id} exceeds {FACE_MAX_SIZE}: {face_size}")
        if ear_size[0] > EAR_MAX_SIZE[0] or ear_size[1] > EAR_MAX_SIZE[1]:
            raise SystemExit(f"FACE_VARIANT_PREVIEW_FAIL: ear variant {variant_id} exceeds {EAR_MAX_SIZE}: {ear_size}")
        canvas.alpha_composite(ear)
        canvas.alpha_composite(face)
        frame_path = output / f"variant_{variant_id:02d}_front.png"
        canvas.save(frame_path)
        previews.append(ImageOps.contain(canvas, (PREVIEW_SIZE, PREVIEW_SIZE), Image.Resampling.NEAREST))

    sheet = Image.new("RGBA", (PREVIEW_SIZE * 4, (PREVIEW_SIZE + 28) * 2), (28, 31, 46, 255))
    draw = ImageDraw.Draw(sheet)
    for variant_id, preview in enumerate(previews):
        x = (variant_id % 4) * PREVIEW_SIZE
        y = (variant_id // 4) * (PREVIEW_SIZE + 28)
        sheet.alpha_composite(preview, (x, y))
        draw.text((x + 8, y + PREVIEW_SIZE + 5), f"variant {variant_id:02d}", fill=(240, 242, 248, 255))
    sheet.save(output / "face_variants_contact_sheet.png")
    print(f"FACE_VARIANT_PREVIEW_PASS variants={VARIANT_COUNT} gender={options.gender} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
