"""Generate a deterministic GarmentCode sewing-pattern candidate.

Run this with the isolated Python 3.9 environment described in the clothing
pipeline document.  The script only uses GarmentCode's MIT core; simulation
and Blender fitting remain separate review stages.
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from pathlib import Path

import yaml


def cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--garmentcode", type=Path, required=True)
    parser.add_argument("--body", type=Path, required=True)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--name", default="actor_v1_tshirt")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--length", type=float, default=1.15)
    parser.add_argument("--width", type=float, default=1.05)
    parser.add_argument("--flare", type=float, default=1.03)
    parser.add_argument("--sleeveless", action="store_true")
    return parser.parse_args()


def main() -> int:
    options = cli_args()
    source_root = options.garmentcode.resolve()
    sys.path.insert(0, str(source_root))

    from assets.bodies.body_params import BodyParameters
    from assets.garment_programs.meta_garment import MetaGarment

    random.seed(options.seed)
    body = BodyParameters(str(options.body.resolve()))
    design = yaml.safe_load(options.design.read_text(encoding="utf-8"))["design"]
    design["meta"]["upper"]["v"] = "Shirt"
    design["meta"]["bottom"]["v"] = None
    design["meta"]["wb"]["v"] = None
    design["shirt"]["length"]["v"] = options.length
    design["shirt"]["width"]["v"] = options.width
    design["shirt"]["flare"]["v"] = options.flare
    if options.sleeveless:
        design["sleeve"]["sleeveless"]["v"] = True
        design["left"]["sleeve"]["sleeveless"]["v"] = True

    garment = MetaGarment(options.name, body, design)
    pattern = garment.assembly()
    if garment.is_self_intersecting():
        raise RuntimeError("GarmentCode generated a self-intersecting garment")

    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    destination = pattern.serialize(
        str(output),
        tag=f"seed_{options.seed}",
        with_3d=False,
        with_text=False,
        view_ids=False,
        with_printable=False,
    )
    body.save(destination)
    shutil.copy2(options.design.resolve(), Path(destination) / "design_source.yaml")
    manifest = {
        "schema": "assetslab_garmentcode_candidate_v1",
        "generator": "GarmentCode/PyGarment",
        "license_boundary": "GarmentCode core MIT; no GPL measurement dependency",
        "name": options.name,
        "seed": options.seed,
        "body_source": str(options.body.resolve()),
        "design_source": str(options.design.resolve()),
        "design_overrides": {
            "upper": "Shirt",
            "length": options.length,
            "width": options.width,
            "flare": options.flare,
            "sleeveless": options.sleeveless,
        },
        "output": str(Path(destination).resolve()),
        "panels": sorted(pattern.pattern["panels"]),
        "stitches": len(pattern.pattern["stitches"]),
        "next_stage": "drape or import pattern mesh, then Actor Clothing Cage and four-direction walk review",
    }
    Path(destination, "assetslab_candidate_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
