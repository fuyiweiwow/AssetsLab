"""Build a tracked, dependency-free gallery for Mixamo retarget experiments.

The Blender render directories normally live below the ignored test-output
folder. This tool copies only the review GIFs and metadata into the tracked
preview tree, so a fresh checkout can inspect the experiment without carrying
all intermediate blends and PNGs.
"""
from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path

from PIL import Image


DIRECTIONS = ("front", "right", "back", "left")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("prototype/preview/animation_gallery"))
    parser.add_argument(
        "--candidate",
        action="append",
        nargs=4,
        metavar=("ID", "LABEL", "ACTION", "RENDER_DIR"),
        required=True,
        help="repeat for each candidate; RENDER_DIR is relative to project root",
    )
    return parser.parse_args()


def make_gif(source_dir: Path, output: Path, size: int, fps: float = 8.0) -> None:
    frames = []
    for index in range(8):
        source = source_dir / f"{output.stem}_{index:02d}.png"
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
        duration=round(1000.0 / fps),
        loop=0,
        disposal=2,
    )


def build_candidate(root: Path, output: Path, candidate: list[str]) -> dict[str, object]:
    candidate_id, label, action, render_dir_arg = candidate
    render_dir = (root / render_dir_arg).resolve()
    if not render_dir.is_dir():
        raise RuntimeError(f"render directory does not exist: {render_dir}")
    target = output / candidate_id
    target.mkdir(parents=True, exist_ok=True)
    source_manifest = render_dir / "manifest.json"
    manifest = json.loads(source_manifest.read_text(encoding="utf-8")) if source_manifest.is_file() else {}
    directions: dict[str, dict[str, str]] = {}
    for direction in DIRECTIONS:
        directions[direction] = {}
        render_gif = target / f"{direction}.gif"
        make_gif(render_dir, render_gif, size=256, fps=8.0)
        directions[direction]["render"] = render_gif.name
        pixel_dir = target / "pixel"
        pixel_dir.mkdir(parents=True, exist_ok=True)
        pixel_gif = pixel_dir / f"{direction}.gif"
        make_gif(render_dir, pixel_gif, size=64, fps=8.0)
        directions[direction]["pixel"] = str(pixel_gif.relative_to(target)).replace("\\", "/")
    output_manifest = {
        "schema": "assetslab_mixamo_animation_gallery_candidate_v1",
        "id": candidate_id,
        "label": label,
        "action": action,
        "source_render_dir": str(render_dir),
        "source_manifest": manifest,
        "directions": directions,
        "review_status": "WIP_candidate",
    }
    (target / "manifest.json").write_text(json.dumps(output_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_manifest


def render_card(output: Path, candidate: dict[str, object]) -> str:
    cid = html.escape(str(candidate["id"]))
    label = html.escape(str(candidate["label"]))
    action = html.escape(str(candidate["action"]))
    directions = candidate["directions"]
    figures = []
    for direction in DIRECTIONS:
        item = directions[direction]
        figures.append(
            f'<figure><img src="{cid}/{html.escape(item["render"])}" alt="{label} {direction} render">'
            f'<figcaption>{direction} · 256px 渲染 GIF</figcaption></figure>'
        )
    pixel_figures = []
    for direction in DIRECTIONS:
        item = directions[direction]
        pixel_figures.append(
            f'<figure><img class="pixel" src="{cid}/{html.escape(item["pixel"])}" alt="{label} {direction} pixel">'
            f'<figcaption>{direction} · 64px 像素 GIF</figcaption></figure>'
        )
    return (
        f'<section class="panel"><h2>{label}</h2>'
        '<p class="warning">WIP 候选：用于观察骨骼重定向，不代表最终动作。</p>'
        '<h3>四向 3D 渲染</h3><div class="grid">' + "".join(figures) + '</div>'
        '<h3>四向像素化预览</h3><div class="grid">' + "".join(pixel_figures) + '</div></section>'
    )


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    output = (root / args.output).resolve() if not args.output.is_absolute() else args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    candidates = [build_candidate(root, output, item) for item in args.candidate]
    cards = "\n".join(render_card(output, candidate) for candidate in candidates)
    index = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AssetsLab Mixamo 骨骼动画实验 Gallery</title>
<style>
:root {{ color-scheme: dark; --bg:#101522; --panel:#1b2233; --line:#35415d; --text:#f4f5f7; --muted:#aeb9cc; --accent:#8fd3ff; --warn:#ffd18a; }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:linear-gradient(150deg,#101522,#1d2639); color:var(--text); font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }}
main {{ width:min(1180px,100%); margin:auto; padding:20px 14px 48px; }} h1 {{ margin:0 0 6px; }} h2 {{ margin:0 0 8px; }} h3 {{ margin:18px 0 8px; font-size:16px; color:var(--accent); }} p {{ color:var(--muted); }} .warning {{ color:var(--warn); }}
.panel {{ margin:16px 0; padding:16px; border:1px solid var(--line); border-radius:16px; background:rgba(27,34,51,.92); }} .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:10px; }} figure {{ margin:0; padding:8px; border:1px solid var(--line); border-radius:12px; background:#0c101b; }} img {{ display:block; width:100%; max-height:330px; object-fit:contain; background:#080b13; border-radius:8px; }} img.pixel {{ image-rendering:pixelated; image-rendering:crisp-edges; }} figcaption {{ padding-top:6px; color:var(--muted); font-size:13px; }} code {{ color:#d9f2ff; }}
</style></head><body><main><h1>Mixamo 骨骼动画实验</h1>
<p>本页由 <code>tools/build_mixamo_animation_gallery.py</code> 生成。四向 GIF 同时展示 3D 渲染和 64×64 像素化结果；所有条目都标记为 WIP 候选，最终动作需继续检查膝盖、腿根和手臂摆动方向。</p>
{cards}
</main></body></html>'''
    (output / "gallery.html").write_text(index, encoding="utf-8")
    print(f"MIXAMO_GALLERY_PASS candidates={len(candidates)} output={output / 'gallery.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
