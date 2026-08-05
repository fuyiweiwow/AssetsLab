"""Append the validated eye-anime candidate to the tracked movement gallery."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from PIL import Image


DIRECTIONS = ("front", "right", "back", "left")
MARKER = "<!-- ASSETSLAB_EYE_ANIME_V6 -->"


def make_gif(source_dir: Path, output: Path, stem: str, size: int) -> None:
    frames = []
    for index in range(8):
        source = source_dir / f"{stem}_{index:02d}.png"
        if not source.is_file():
            raise RuntimeError(f"missing source frame: {source}")
        frame = Image.open(source).convert("RGBA")
        if frame.size != (size, size):
            frame = frame.resize((size, size), Image.Resampling.NEAREST)
        frames.append(frame)
    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=125,
        loop=0,
        disposal=2,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--render-dir", type=Path, required=True)
    parser.add_argument("--gallery", type=Path, default=Path("prototype/preview/animation_gallery"))
    return parser.parse_args()


def main() -> int:
    options = parse_args()
    root = options.project_root.resolve()
    render_dir = (root / options.render_dir).resolve()
    gallery = (root / options.gallery).resolve()
    target = gallery / "eye-anime-v6"
    target.mkdir(parents=True, exist_ok=True)
    source_manifest = render_dir / "manifest.json"
    manifest = json.loads(source_manifest.read_text(encoding="utf-8"))

    directions: dict[str, dict[str, str]] = {}
    for direction in DIRECTIONS:
        render_gif = target / f"{direction}.gif"
        make_gif(render_dir, render_gif, direction, 256)
        pixel_gif = target / "pixel" / f"{direction}.gif"
        make_gif(render_dir, pixel_gif, direction, 64)
        directions[direction] = {
            "render": render_gif.name,
            "pixel": str(pixel_gif.relative_to(target)).replace("\\", "/"),
        }

    gallery_manifest = {
        "schema": "assetslab_eye_anime_gallery_candidate_v1",
        "id": "eye-anime-v6",
        "label": "Eye Anime v6 · image_gen 眉眼组合层",
        "action": "Walk + deterministic blink",
        "source_manifest": manifest,
        "directions": directions,
        "review_status": "WIP_validated_render_reference",
        "pixel_art_status": "preview_only_nearest_neighbor",
    }
    (target / "manifest.json").write_text(
        json.dumps(gallery_manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    index = gallery / "gallery.html"
    text = index.read_text(encoding="utf-8")
    if MARKER not in text:
        figures = []
        pixels = []
        label = html.escape(gallery_manifest["label"])
        for direction in DIRECTIONS:
            item = directions[direction]
            figures.append(
                f'<figure><img src="eye-anime-v6/{item["render"]}" alt="{label} {direction} render">'
                f"<figcaption>{direction} · 256px 3D渲染参考 GIF</figcaption></figure>"
            )
            pixels.append(
                f'<figure><img class="pixel" src="eye-anime-v6/{item["pixel"]}" alt="{label} {direction} preview">'
                f"<figcaption>{direction} · 64px 最近邻预览（非最终像素资产）</figcaption></figure>"
            )
        card = (
            f"{MARKER}\n<section class=\"panel\"><h2>{label}</h2>"
            '<p class="warning">WIP：眉毛与眼睛由 image_gen 作为同一组合层生成；此处用于验证 3D→2D 参考渲染和眨眼节奏，不代表最终像素画。</p>'
            '<h3>四向 3D 渲染</h3><div class="grid">'
            + "".join(figures)
            + '</div><h3>四向 64px 预览</h3><div class="grid">'
            + "".join(pixels)
            + "</div></section>"
        )
        text = text.replace("</main>", card + "\n</main>", 1)
        index.write_text(text, encoding="utf-8")
    print(f"EYE_ANIME_GALLERY_PASS output={index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
