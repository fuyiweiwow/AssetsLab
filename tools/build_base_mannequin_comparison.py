"""Build a four-direction silhouette comparison board."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


DIRECTIONS = ["front", "right", "back", "left"]
CARD_SIZE = (360, 440)
MARGIN = 16


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def fit_on_card(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = image.convert("RGB")
    return ImageOps.contain(image, size, Image.Resampling.LANCZOS)


def main() -> int:
    options = parse_args()
    reference = Image.open(options.reference).convert("RGB")
    if reference.size != (1536, 1024):
        raise SystemExit(f"unexpected reference size: {reference.size}")

    board_width = CARD_SIZE[0] * 4 + MARGIN * 5
    board_height = CARD_SIZE[1] * 2 + MARGIN * 3
    board = Image.new("RGB", (board_width, board_height), "#20232e")
    draw = ImageDraw.Draw(board)
    draw.text((MARGIN, 4), "BASE MANNEQUIN SILHOUETTE REVIEW", fill="#f1f3f8")

    for row, title in enumerate(("REFERENCE", "CURRENT 3D CANDIDATE")):
        y = MARGIN + row * (CARD_SIZE[1] + MARGIN)
        for index, direction in enumerate(DIRECTIONS):
            x = MARGIN + index * (CARD_SIZE[0] + MARGIN)
            draw.rectangle((x, y, x + CARD_SIZE[0], y + CARD_SIZE[1]), fill="#e4e4e4", outline="#8990a0", width=2)
            draw.text((x + 10, y + 8), f"{title} / {direction}", fill="#20232e")
            if row == 0:
                source = reference.crop((index * 384, 0, (index + 1) * 384, 576))
            else:
                source_path = options.candidate_dir / direction / "frame_00" / "beauty.png"
                if not source_path.is_file():
                    raise SystemExit(f"missing candidate render: {source_path}")
                source = Image.open(source_path)
            preview = fit_on_card(source, (CARD_SIZE[0] - 20, CARD_SIZE[1] - 48))
            paste_x = x + (CARD_SIZE[0] - preview.width) // 2
            paste_y = y + 36 + (CARD_SIZE[1] - 48 - preview.height) // 2
            board.paste(preview, (paste_x, paste_y))

    options.output.parent.mkdir(parents=True, exist_ok=True)
    board.save(options.output)
    print(f"BASE_MANNEQUIN_COMPARISON_PASS output={options.output.resolve()} size={board.size[0]}x{board.size[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
