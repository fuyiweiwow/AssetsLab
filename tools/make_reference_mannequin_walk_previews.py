from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "prototype/preview/assets/female_adventurer_reference_mannequin_walk_v1"
OUTPUT = INPUT
DIRECTIONS = ("front", "right", "back", "left")


def crop_strip(path: Path) -> list[Image.Image]:
    image = Image.open(path).convert("RGBA")
    alpha = image.getchannel("A")
    occupied = [any(alpha.getpixel((x, y)) > 0 for y in range(image.height)) for x in range(image.width)]
    groups: list[list[int]] = []
    start = None
    gap_start = None
    for x, has_pixels in enumerate(occupied + [False]):
        if has_pixels and start is None:
            start = x if gap_start is None else gap_start
            gap_start = None
        elif not has_pixels and start is not None and gap_start is None:
            gap_start = x
        elif has_pixels and gap_start is not None:
            if x - gap_start >= 20:
                groups.append([start, gap_start])
                start = x
            gap_start = None
    if start is not None and gap_start is not None:
        groups.append([start, gap_start])
    if len(groups) != 8:
        raise ValueError(f"expected 8 visible frame groups in {path}, found {len(groups)}")

    raw_frames = []
    for left, right in groups:
        bbox = alpha.crop((left, 0, right, image.height)).getbbox()
        if bbox is None:
            raise ValueError(f"empty frame group in {path}")
        raw_frames.append(image.crop((left + bbox[0], bbox[1], left + bbox[2], bbox[3])))

    pad = 24
    canvas_width = max(frame.width for frame in raw_frames) + pad * 2
    canvas_height = max(frame.height for frame in raw_frames) + pad * 2
    frames = []
    for frame in raw_frames:
        canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        canvas.alpha_composite(frame, ((canvas_width - frame.width) // 2, canvas_height - pad - frame.height))
        frames.append(canvas)
    return frames


def save_gif(direction: str, frames: list[Image.Image]) -> None:
    frames[0].save(
        OUTPUT / f"{direction}.gif",
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
        disposal=2,
    )


def save_contact(all_frames: dict[str, list[Image.Image]]) -> None:
    cell_width = max(frame.width for frames in all_frames.values() for frame in frames)
    cell_height = max(frame.height for frames in all_frames.values() for frame in frames)
    label_height = 32
    sheet = Image.new("RGBA", (cell_width * 8, (cell_height + label_height) * 4), (22, 25, 39, 255))
    draw = ImageDraw.Draw(sheet)
    for row, direction in enumerate(DIRECTIONS):
        top = row * (cell_height + label_height)
        draw.text((8, top + 8), direction, fill=(240, 240, 240, 255))
        for index, frame in enumerate(all_frames[direction]):
            sheet.alpha_composite(frame, (index * cell_width, top + label_height))
            draw.text((index * cell_width + 8, top + label_height + 8), str(index + 1), fill=(240, 240, 240, 255))
    sheet.convert("RGB").save(OUTPUT / "walk_contact.png")


def main() -> int:
    all_frames = {}
    for direction in DIRECTIONS:
        frames = crop_strip(INPUT / f"{direction}.png")
        all_frames[direction] = frames
        save_gif(direction, frames)
    save_contact(all_frames)
    print("REFERENCE_MANNEQUIN_WALK_PREVIEWS_PASS directions=" + ",".join(DIRECTIONS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
