"""Validate the static OpenGameArt anime eye candidate review output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def fail(message: str) -> None:
    raise SystemExit(f"OPENGAMEART_ANIME_EYE_VALIDATE_FAIL {message}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-dir", required=True, type=Path)
    args = parser.parse_args()
    root = args.render_dir.resolve()
    manifest_path = root / "attachment_manifest.json"
    if not manifest_path.is_file():
        fail(f"missing manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "assetslab_opengameart_anime_eyes_on_accurig_v1":
        fail("unexpected schema")
    if manifest.get("source_license") != "CC0":
        fail("source license is not recorded as CC0")
    if manifest.get("directions") != ["front", "right", "back", "left"]:
        fail(f"unexpected directions: {manifest.get('directions')}")
    required = {
        "OpenGameArtEye_Cornea",
        "OpenGameArtEye_Iris_L",
        "OpenGameArtEye_Iris_R",
        "OpenGameArtEye_Eyelash",
        "OpenGameArtEye_Pupil_L",
        "OpenGameArtEye_Pupil_R",
        "OpenGameArtEye_Highlight_L",
        "OpenGameArtEye_Highlight_R",
    }
    missing = sorted(required - set(manifest.get("features", [])))
    if missing:
        fail(f"missing feature objects: {missing}")
    for direction in manifest["directions"]:
        path = root / f"{direction}.png"
        if not path.is_file():
            fail(f"missing render: {path}")
        with Image.open(path) as image:
            if image.size != (256, 256) or image.mode not in ("RGBA", "RGB"):
                fail(f"invalid render: {path} size={image.size} mode={image.mode}")
    print("OPENGAMEART_ANIME_EYE_VALIDATE_PASS directions=4 features=8 size=256")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
