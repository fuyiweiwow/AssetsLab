"""Apply a small palette and silhouette outline to a pixel asset package."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter


PALETTE = {
    "outline": (31, 30, 43, 255),
    "shadow": (103, 98, 111, 255),
    "base": (169, 166, 174, 255),
    "light": (218, 214, 222, 255),
    "highlight": (242, 238, 245, 255),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--alpha-threshold", type=int, default=128)
    return parser.parse_args()


def style_frame(source: Image.Image, alpha_threshold: int) -> Image.Image:
    source = source.convert("RGBA")
    alpha = source.getchannel("A")
    solid_alpha = alpha.point(lambda value: 255 if value >= alpha_threshold else 0)
    expanded = solid_alpha.filter(ImageFilter.MaxFilter(3))
    outline_alpha = ImageChops.subtract(expanded, solid_alpha)

    output = Image.new("RGBA", source.size, (0, 0, 0, 0))
    outline = Image.new("RGBA", source.size, PALETTE["outline"])
    output.alpha_composite(Image.composite(outline, Image.new("RGBA", source.size), outline_alpha))

    pixels = source.load()
    styled = Image.new("RGBA", source.size, (0, 0, 0, 0))
    styled_pixels = styled.load()
    for y in range(source.height):
        for x in range(source.width):
            red, green, blue, original_alpha = pixels[x, y]
            if solid_alpha.getpixel((x, y)) == 0:
                continue
            luminance = (red * 299 + green * 587 + blue * 114) // 1000
            if luminance < 85:
                color = PALETTE["shadow"]
            elif luminance < 135:
                color = PALETTE["base"]
            elif luminance < 190:
                color = PALETTE["light"]
            else:
                color = PALETTE["highlight"]
            styled_pixels[x, y] = color
    output.alpha_composite(styled)
    return output


def main() -> int:
    options = parse_args()
    source_root = options.input_dir.resolve()
    output_root = options.output_dir.resolve()
    manifest = json.loads((source_root / "manifest.json").read_text(encoding="utf-8"))
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    sheets: dict[str, str] = {}
    styled_frames: list[dict[str, object]] = []
    for direction in manifest["directions"]:
        sheet = Image.new(
            "RGBA",
            (manifest["canvas_px"][0] * manifest["frame_count"], manifest["canvas_px"][1]),
            (0, 0, 0, 0),
        )
        gif_frames: list[Image.Image] = []
        for frame in range(manifest["frame_count"]):
            relative = Path(direction) / f"frame_{frame:02d}" / "pixel.png"
            image = style_frame(Image.open(source_root / relative), options.alpha_threshold)
            target = output_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            image.save(target)
            sheet.paste(image, (frame * manifest["canvas_px"][0], 0), image)
            gif_frames.append(image.copy())
            bbox = image.getchannel("A").getbbox()
            styled_frames.append(
                {
                    "direction": direction,
                    "frame": frame,
                    "path": str(relative),
                    "alpha_bbox": list(bbox) if bbox else None,
                }
            )
        sheet_path = output_root / f"{direction}_sheet.png"
        sheet.save(sheet_path)
        sheets[direction] = sheet_path.name
        gif_frames[0].save(
            output_root / f"{direction}.gif",
            save_all=True,
            append_images=gif_frames[1:],
            duration=140,
            loop=0,
            disposal=2,
        )

    result_manifest = {
        **manifest,
        "schema": "assetslab_pixel_style_test_v1",
        "style": {
            "palette": PALETTE,
            "levels": "shadow/base/light/highlight",
            "outline": "1px alpha silhouette dilation",
            "alpha_threshold": options.alpha_threshold,
            "edge_mode": "binary_opaque",
        },
        "sheets": sheets,
        "frames": styled_frames,
        "runtime_ready": False,
        "purpose": "palette_and_outline_diagnostic_only",
    }
    (output_root / "manifest.json").write_text(
        json.dumps(result_manifest, indent=2), encoding="utf-8"
    )
    print(f"PIXEL_STYLE_TEST_PASS frames={len(styled_frames)} output={output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
