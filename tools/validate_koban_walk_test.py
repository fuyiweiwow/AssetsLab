"""Validate Koban's four-direction walk render package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def fail(message: str) -> None:
    raise SystemExit(f"KOBAN_WALK_VALIDATE_FAIL {message}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-dir", required=True, type=Path)
    args = parser.parse_args()
    root = args.render_dir.resolve()
    manifest_path = root / "walk_manifest.json"
    if not manifest_path.is_file():
        fail(f"missing manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "assetslab_koban_walk_test_v1":
        fail("unexpected schema")
    if manifest.get("directions") != ["front", "right", "back", "left"]:
        fail(f"unexpected directions: {manifest.get('directions')}")
    if manifest.get("frame_count") != 8:
        fail("expected eight frames per direction")
    for direction in manifest["directions"]:
        for frame in range(8):
            path = root / f"{direction}_{frame:02d}.png"
            if not path.is_file():
                fail(f"missing render: {path}")
            with Image.open(path) as image:
                if image.size != (256, 256) or image.mode not in ("RGBA", "RGB"):
                    fail(f"invalid render: {path} size={image.size} mode={image.mode}")
    print("KOBAN_WALK_VALIDATE_PASS directions=4 frames=32 size=256")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
