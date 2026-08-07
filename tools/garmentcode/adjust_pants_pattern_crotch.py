"""Apply a small, topology-preserving local crotch adjustment to a Pants spec."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-spec", required=True, type=Path)
    parser.add_argument("--output-spec", required=True, type=Path)
    parser.add_argument("--shift", type=float, default=2.0)
    return parser.parse_args()


def main() -> int:
    options = parse_args()
    if abs(options.shift) < 1e-6:
        raise ValueError("--shift must be non-zero")
    source = json.loads(options.input_spec.read_text(encoding="utf-8"))
    result = copy.deepcopy(source)
    panels = result["pattern"]["panels"]

    # These are the shared crotch-bottom vertices in the official Pants
    # topology. Move both sides of each stitched seam together so no stitch
    # relationship or panel boundary count changes.
    edits = {
        "pant_f_r": {6: options.shift},
        "pant_b_r": {1: options.shift},
        "pant_f_l": {1: -options.shift},
        "pant_b_l": {12: -options.shift},
    }
    for panel_name, vertices in edits.items():
        for index, delta_x in vertices.items():
            panels[panel_name]["vertices"][index][0] += delta_x

    result["assetslab_local_adjustment"] = {
        "schema": "assetslab_pants_crotch_adjustment_v1",
        "source_spec": str(options.input_spec.resolve()),
        "shift_cm": options.shift,
        "changed_vertices": {name: sorted(values) for name, values in edits.items()},
        "topology_changed": False,
        "stitches_changed": False,
        "next_stage": "GarmentCode physics gate",
    }
    output = options.output_spec.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["assetslab_local_adjustment"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
