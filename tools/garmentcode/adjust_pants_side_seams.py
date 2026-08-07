"""Apply a symmetric, tapered inset to lower outer side-seam vertices."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


def tapered_delta(y: float, max_y: float, inset: float) -> float:
    # Full correction at the hem, fading to zero by the lower hip/side seam.
    t = max(0.0, min(1.0, y / max_y))
    return inset * (1.0 - t) ** 1.2


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
    # Outer-side lower vertices, ordered hem -> hip for each half-panel.
    right = {
        "pant_f_r": [1, 2, 3],
        "pant_b_r": [12, 11, 10],
    }
    left = {
        "pant_f_l": [6, 5, 4],
        "pant_b_l": [1, 2, 3],
    }
    edits: dict[str, list[int]] = {**right, **left}
    for panel_name, indices in edits.items():
        vertices = panels[panel_name]["vertices"]
        max_y = max(float(vertices[index][1]) for index in indices)
        sign = -1.0 if panel_name.endswith("_r") else 1.0
        for index in indices:
            delta = sign * tapered_delta(float(vertices[index][1]), max_y, options.inset)
            vertices[index][0] += delta

    result["assetslab_local_adjustment"] = {
        "schema": "assetslab_pants_side_seam_adjustment_v1",
        "source_spec": str(options.input_spec.resolve()),
        "max_inset_cm": options.inset,
        "changed_vertices": edits,
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
