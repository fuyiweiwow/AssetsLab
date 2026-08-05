"""Chroma-key an imagegen eye asset into a Blender-ready RGBA texture.

This only removes the requested chroma background and normalizes placement; it
does not draw, trace, or synthesize any eye pixels locally.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps


def key_magenta(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            red, green, blue, _ = pixels[x, y]
            energy = red + blue - 2 * green
            if red > 170 and blue > 95 and green < 125 and energy > 180:
                pixels[x, y] = (0, 0, 0, 0)
            else:
                pixels[x, y] = (red, green, blue, 255)
    return rgba


def fit_texture(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    keyed = key_magenta(image)
    bbox = keyed.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("imagegen source has no non-background pixels")
    cropped = keyed.crop(bbox)
    max_width = round(size[0] * 0.86)
    max_height = round(size[1] * 0.28)
    scale = min(max_width / cropped.width, max_height / cropped.height)
    resized = cropped.resize(
        (max(1, round(cropped.width * scale)), max(1, round(cropped.height * scale))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(
        resized,
        ((size[0] - resized.width) // 2, (size[1] - resized.height) // 2),
    )
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--width", type=int, default=496)
    parser.add_argument("--height", type=int, default=609)
    options = parser.parse_args()
    output_dir = options.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    base = fit_texture(Image.open(options.source), (options.width, options.height))
    base.save(output_dir / "eye_closed_imagegen_v1_R.png")
    ImageOps.mirror(base).save(output_dir / "eye_closed_imagegen_v1_L.png")
    print(f"IMAGEGEN_EYE_TEXTURE_PASS output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
