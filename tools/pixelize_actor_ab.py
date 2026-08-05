"""Build reproducible A/B pixelization outputs from 3D actor renders.

Candidate A is the existing direct nearest-neighbour reduction. Candidate B
uses a shared global palette and a two-stage reduction before quantization.
Neither candidate crops frames or changes the 3D render registration.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


DIRECTIONS = ("front", "right", "back", "left")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--size", type=int, default=64)
    parser.add_argument("--palette-colors", type=int, default=32)
    parser.add_argument("--fps", type=float, default=8.0)
    return parser.parse_args()


def load_sources(render_dir: Path) -> dict[str, list[Image.Image]]:
    sources: dict[str, list[Image.Image]] = {}
    for direction in DIRECTIONS:
        frames = []
        for frame in range(8):
            path = render_dir / f"{direction}_{frame:02d}.png"
            if not path.is_file():
                raise RuntimeError(f"missing source render: {path}")
            image = Image.open(path).convert("RGBA")
            if image.size != (256, 256):
                raise RuntimeError(f"expected 256x256 source render: {path}")
            frames.append(image)
        sources[direction] = frames
    return sources


def derive_global_palette(sources: dict[str, list[Image.Image]], colors: int) -> list[str]:
    if colors < 2 or colors > 256:
        raise ValueError("palette-colors must be between 2 and 256")
    samples: list[tuple[int, int, int]] = []
    for direction in DIRECTIONS:
        for image in sources[direction]:
            rgb = image.convert("RGB")
            corners = [rgb.getpixel(point) for point in ((0, 0), (255, 0), (0, 255), (255, 255))]
            background = tuple(sum(pixel[index] for pixel in corners) // len(corners) for index in range(3))
            for y in range(0, 256, 3):
                for x in range(0, 256, 3):
                    pixel = rgb.getpixel((x, y))
                    distance = sum(abs(pixel[index] - background[index]) for index in range(3))
                    if distance > 24 or (x % 12 == 0 and y % 12 == 0):
                        samples.append(pixel)
    sample_image = Image.new("RGB", (max(len(samples), 1), 1))
    sample_image.putdata(samples or [(0, 0, 0)])
    quantized = sample_image.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    palette = quantized.getpalette()[: colors * 3]
    return ["#%02x%02x%02x" % tuple(palette[index : index + 3]) for index in range(0, len(palette), 3)]


def palette_image(colors: list[str]) -> Image.Image:
    image = Image.new("P", (1, 1))
    flat: list[int] = []
    for value in colors:
        flat.extend(int(value[index : index + 2], 16) for index in (1, 3, 5))
    pad = tuple(int(colors[0][index : index + 2], 16) for index in (1, 3, 5))
    flat.extend(list(pad) * (256 - len(colors)))
    image.putpalette(flat)
    return image


def quantize_with_palette(image: Image.Image, colors: list[str]) -> Image.Image:
    palette = palette_image(colors)
    rgb = image.convert("RGB")
    quantized = rgb.quantize(palette=palette, dither=Image.Dither.NONE).convert("RGB")
    alpha = image.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
    output = quantized.convert("RGBA")
    output.putalpha(alpha)
    return output


def write_gif(frames: list[Image.Image], path: Path, duration: int) -> None:
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=duration, loop=0, disposal=2)


def write_candidate(
    name: str,
    sources: dict[str, list[Image.Image]],
    output_dir: Path,
    size: int,
    duration: int,
    colors: list[str] | None,
) -> dict[str, object]:
    candidate_dir = output_dir / name
    candidate_dir.mkdir(parents=True, exist_ok=True)
    sheets: dict[str, str] = {}
    frame_records: list[dict[str, object]] = []
    for direction in DIRECTIONS:
        frames = []
        sheet = Image.new("RGBA", (size * 8, size), (0, 0, 0, 0))
        for index, source in enumerate(sources[direction]):
            if colors is None:
                pixel = source.resize((size, size), Image.Resampling.NEAREST)
            else:
                intermediate = source.resize((size * 2, size * 2), Image.Resampling.LANCZOS)
                pixel = quantize_with_palette(intermediate.resize((size, size), Image.Resampling.NEAREST), colors)
            frame_dir = candidate_dir / direction / f"frame_{index:02d}"
            frame_dir.mkdir(parents=True, exist_ok=True)
            frame_path = frame_dir / "pixel.png"
            pixel.save(frame_path)
            sheet.paste(pixel, (index * size, 0), pixel)
            frames.append(pixel)
            bbox = pixel.getchannel("A").getbbox()
            frame_records.append(
                {
                    "direction": direction,
                    "frame": index,
                    "path": str(frame_path.relative_to(candidate_dir)).replace("\\", "/"),
                    "alpha_bbox": list(bbox) if bbox else None,
                    "color_count": len(pixel.getcolors(maxcolors=1_000_000) or []),
                }
            )
        sheet_path = candidate_dir / f"{direction}_sheet.png"
        sheet.save(sheet_path)
        sheets[direction] = sheet_path.name
        write_gif(frames, candidate_dir / f"{direction}.gif", duration)
    manifest = {
        "schema": "assetslab_pixelization_ab_candidate_v1",
        "candidate": name,
        "canvas_px": [size, size],
        "directions": list(DIRECTIONS),
        "frame_count": 8,
        "sheets": sheets,
        "frames": frame_records,
        "method": {
            "resize": "nearest" if colors is None else "lanczos_to_2x_then_nearest",
            "palette": "source_colors" if colors is None else "global_fixed_palette",
            "alpha": "threshold_128",
            "per_frame_crop": False,
        },
        "palette": colors,
        "runtime_ready": False,
        "purpose": "pixelization_review_only",
    }
    (candidate_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    options = parse_args()
    if options.size <= 0 or options.fps <= 0.0:
        raise ValueError("size and fps must be positive")
    render_dir = options.render_dir.resolve()
    output_dir = options.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    sources = load_sources(render_dir)
    colors = derive_global_palette(sources, options.palette_colors)
    duration = round(1000.0 / options.fps)
    manifests = {
        "nearest": write_candidate("nearest", sources, output_dir, options.size, duration, None),
        "palette32": write_candidate("palette32", sources, output_dir, options.size, duration, colors),
    }
    result = {
        "schema": "assetslab_pixelization_ab_v1",
        "source_render_dir": str(options.render_dir),
        "canvas_px": [options.size, options.size],
        "directions": list(DIRECTIONS),
        "frame_count": 8,
        "shared_body_and_eye_sampling": True,
        "candidates": manifests,
        "status": "review_only",
    }
    (output_dir / "manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"PIXELIZATION_AB_PASS candidates=2 directions=4 frames=8 output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
