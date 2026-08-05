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
            red, green, blue, alpha = pixels[x, y]
            energy = red + blue - 2 * green
            # Remove the chroma background and its purple anti-aliased fringe.
            # Keeping fringe pixels opaque is what creates the visible magenta
            # halo after Eevee filters the texture on a shallow face layer.
            if red > 70 and blue > 50 and green < 170 and energy > 40:
                pixels[x, y] = (0, 0, 0, 0)
            else:
                # Preserve transparency when the source already carries an
                # alpha channel (the Actor standard texture does).
                pixels[x, y] = (red, green, blue, alpha)
    return rgba


def fit_texture(
    image: Image.Image,
    size: tuple[int, int],
    max_height_fraction: float,
    reference: Image.Image | None = None,
) -> Image.Image:
    keyed = key_magenta(image)
    bbox = keyed.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("imagegen source has no non-background pixels")
    cropped = keyed.crop(bbox)
    if reference is not None:
        reference_keyed = key_magenta(reference)
        reference_bbox = reference_keyed.getchannel("A").getbbox()
        if reference_bbox is None:
            raise ValueError("reference texture has no non-background pixels")
        target_x, target_y = reference_bbox[:2]
        max_width = reference_bbox[2] - reference_bbox[0]
        max_height = reference_bbox[3] - reference_bbox[1]
    else:
        target_x, target_y = 0, 0
        max_width = round(size[0] * 0.86)
        max_height = round(size[1] * max_height_fraction)
    scale = min(max_width / cropped.width, max_height / cropped.height)
    resized = cropped.resize(
        (max(1, round(cropped.width * scale)), max(1, round(cropped.height * scale))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(
        resized,
        (
            target_x + (max_width - resized.width) // 2 if reference is not None else (size[0] - resized.width) // 2,
            target_y + (max_height - resized.height) // 2 if reference is not None else (size[1] - resized.height) // 2,
        ),
    )
    # Lanczos introduces partially transparent edge pixels after compositing;
    # key them once more so Blender cannot display a purple/magenta halo.
    pixels = canvas.load()
    for y in range(canvas.height):
        for x in range(canvas.width):
            red, green, blue, alpha = pixels[x, y]
            energy = red + blue - 2 * green
            if alpha and red > 70 and blue > 50 and green < 170 and energy > 40:
                pixels[x, y] = (0, 0, 0, 0)
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--width", type=int, default=496)
    parser.add_argument("--height", type=int, default=609)
    parser.add_argument("--prefix", default="eye_closed_imagegen_v1")
    parser.add_argument("--max-height-fraction", type=float, default=0.28)
    parser.add_argument("--reference-texture", type=Path)
    options = parser.parse_args()
    output_dir = options.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    reference = Image.open(options.reference_texture) if options.reference_texture else None
    base = fit_texture(
        Image.open(options.source),
        (options.width, options.height),
        options.max_height_fraction,
        reference=reference,
    )
    base.save(output_dir / f"{options.prefix}_R.png")
    ImageOps.mirror(base).save(output_dir / f"{options.prefix}_L.png")
    print(f"IMAGEGEN_EYE_TEXTURE_PASS output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
