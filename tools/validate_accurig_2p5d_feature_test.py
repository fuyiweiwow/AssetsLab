"""Validate the static 2.5D feature placement contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_DIRECTIONS = ["front", "right", "back", "left"]


def fail(message: str) -> None:
    raise SystemExit(f"ACCURIG_2P5D_FEATURE_VALIDATE_FAIL {message}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    manifest_path = output / "feature_manifest.json"
    if not manifest_path.is_file():
        fail(f"missing manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "assetslab_accurig_2p5d_feature_test_v1":
        fail("unexpected manifest schema")
    if manifest.get("parent_bone") != "CC_Base_Head":
        fail("features are not parented to CC_Base_Head")
    if manifest.get("directions") != EXPECTED_DIRECTIONS:
        fail(f"unexpected directions: {manifest.get('directions')}")
    if manifest.get("status") != "static_four_direction_review_only":
        fail("test output is not marked review-only")
    for direction in EXPECTED_DIRECTIONS:
        image_path = output / f"{direction}.png"
        if not image_path.is_file() or image_path.stat().st_size <= 0:
            fail(f"missing render: {image_path}")
    placement = manifest.get("placement", {})
    eye_scale = placement.get("eye_outer_scale", [])
    if len(eye_scale) != 3 or float(eye_scale[0]) > 0.13 or float(eye_scale[2]) > 0.11:
        fail(f"eye profile is too large for the compact actor: {eye_scale}")
    print(
        "ACCURIG_2P5D_FEATURE_VALIDATE_PASS profile=%s directions=%d"
        % (manifest.get("profile"), len(EXPECTED_DIRECTIONS))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
