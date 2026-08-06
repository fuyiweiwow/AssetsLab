"""Project-owned GarmentCode simulation entry point.

The upstream checkout is a local dependency. Keeping this small wrapper in the
AssetsLab repository preserves the custom body/proxy CLI without vendoring the
upstream source or its Python/Warp environments.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GARMENTCODE_ROOT = ROOT / "third_party" / "GarmentCode"
sys.path.insert(0, str(GARMENTCODE_ROOT))

from pygarment.meshgen.boxmeshgen import BoxMesh  # noqa: E402
from pygarment.meshgen.simulation import run_sim  # noqa: E402
import pygarment.data_config as data_config  # noqa: E402
from pygarment.meshgen.sim_config import PathCofig  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern-spec", required=True, type=Path)
    parser.add_argument("--sim-config", type=Path, default=GARMENTCODE_ROOT / "assets/Sim_props/default_sim_props.yaml")
    parser.add_argument("--body-name", default="mean_all")
    parser.add_argument("--body-obj", type=Path)
    parser.add_argument("--body-measurements", type=Path)
    parser.add_argument("--body-segmentation", type=Path)
    parser.add_argument("--max-sim-steps", type=int)
    parser.add_argument("--resolution-scale", type=float)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pattern_spec = args.pattern_spec.resolve()
    sim_config = args.sim_config.resolve()
    body_obj = args.body_obj.resolve() if args.body_obj else None
    body_measurements = args.body_measurements.resolve() if args.body_measurements else None
    body_segmentation = args.body_segmentation.resolve() if args.body_segmentation else None
    if not pattern_spec.is_file():
        raise FileNotFoundError(pattern_spec)
    if not sim_config.is_file():
        raise FileNotFoundError(sim_config)

    original_cwd = Path.cwd()
    os.chdir(GARMENTCODE_ROOT)
    try:
        props = data_config.Properties(str(sim_config))
        if args.max_sim_steps is not None:
            props["sim"]["config"]["max_sim_steps"] = args.max_sim_steps
        if args.resolution_scale is not None:
            props["sim"]["config"]["resolution_scale"] = args.resolution_scale
        props.set_section_stats(
            "sim", fails={}, sim_time={}, spf={}, fin_frame={},
            body_collisions={}, self_collisions={}
        )
        props.set_section_stats("render", render_time={})

        garment_name = pattern_spec.stem.rpartition("_specification")[0]
        sys_props = data_config.Properties(str(GARMENTCODE_ROOT / "system.json"))
        paths = PathCofig(
            in_element_path=pattern_spec.parent,
            out_path=sys_props["output"],
            in_name=garment_name,
            body_name=args.body_name,
            smpl_body=False,
            add_timestamp=True,
        )
        if body_obj:
            paths.in_body_obj = body_obj
        if body_measurements:
            paths.in_body_mes = body_measurements
        if body_segmentation:
            paths.body_seg = body_segmentation

        garment_box_mesh = BoxMesh(
            paths.in_g_spec, props["sim"]["config"]["resolution_scale"]
        )
        garment_box_mesh.load()
        garment_box_mesh.serialize(
            paths, store_panels=False, uv_config=props["render"]["config"]["uv_texture"]
        )
        props.serialize(paths.element_sim_props)
        run_sim(
            garment_box_mesh.name,
            props,
            paths,
            save_v_norms=False,
            store_usd=False,
            optimize_storage=False,
            verbose=args.verbose,
        )
        props.serialize(paths.element_sim_props)
        return 0
    finally:
        os.chdir(original_cwd)


if __name__ == "__main__":
    raise SystemExit(main())
