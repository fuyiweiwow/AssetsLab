"""Validate the static four-view Koban feature attachment review output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def fail(message: str) -> None:
    raise SystemExit(f"KOBAN_FEATURE_ATTACHMENT_VALIDATE_FAIL {message}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-dir", required=True, type=Path)
    args = parser.parse_args()
    root = args.render_dir.resolve()
    manifest_path = root / "attachment_manifest.json"
    if not manifest_path.is_file():
        fail(f"missing manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "assetslab_koban_features_on_accurig_v1":
        fail("unexpected schema")
    if manifest.get("directions") != ["front", "right", "back", "left"]:
        fail(f"unexpected directions: {manifest.get('directions')}")
    if manifest.get("eye_style") == "anime_plate_v2":
        names = manifest.get("features", [])
        for side in ("L", "R"):
            required = [f"AnimeEye_{side}_{part}" for part in ("Outline", "Sclera", "IrisOutline", "Iris", "Pupil", "Highlight")]
            if any(name not in names for name in required):
                fail(f"missing generated eye components for side {side}")
    for direction in manifest["directions"]:
        path = root / f"{direction}.png"
        if not path.is_file():
            fail(f"missing render: {path}")
        with Image.open(path) as image:
            if image.size != (256, 256) or image.mode not in ("RGBA", "RGB"):
                fail(f"invalid render: {path} size={image.size} mode={image.mode}")
    print(f"KOBAN_FEATURE_ATTACHMENT_VALIDATE_PASS directions=4 eye_style={manifest.get('eye_style')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
