"""Apply a symmetric local adjustment to the four open Pants hem edges."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-spec", required=True, type=Path)
    parser.add_argument("--output-spec", required=True, type=Path)
    parser.add_argument("--inset", type=float, default=2.0)
    options = parser.parse_args()
    if options.inset < 0:
        raise ValueError("--inset must be non-negative")

    result = copy.deepcopy(json.loads(options.input_spec.read_text(encoding="utf-8")))
    panels = result["pattern"]["panels"]
    # The endpoint listed is the outer-side end of each open hem. Moving it
    # toward the panel centre changes only the leg opening, not the waist,
    # crotch seam, or any stitched edge.
    edits = {
        "pant_f_r": {1: -options.inset},
        "pant_f_l": {6: options.inset},
        "pant_b_r": {12: -options.inset},
        "pant_b_l": {1: options.inset},
    }
    for panel_name, vertices in edits.items():
        for index, delta_x in vertices.items():
            panels[panel_name]["vertices"][index][0] += delta_x

    result["assetslab_local_adjustment"] = {
        "schema": "assetslab_pants_leg_opening_adjustment_v1",
        "source_spec": str(options.input_spec.resolve()),
        "inset_cm": options.inset,
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
