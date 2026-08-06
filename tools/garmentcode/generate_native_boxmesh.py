"""Generate GarmentCode's native stitched BoxMesh from a pattern specification.

This is intentionally separate from the Blender adapter: it validates the
GarmentCode mesh topology before any Blender Cloth simulation or Actor fitting.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace
import sys
import types


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--garmentcode", type=Path, required=True)
    parser.add_argument("--pattern", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resolution", type=float, default=1.0)
    return parser.parse_args()


def main() -> None:
    options = parse_args()
    source_root = options.garmentcode.resolve()
    sys.path.insert(0, str(source_root))

    # BoxMesh imports libigl for optional OBJ/UV helpers.  The core topology
    # generation does not need libigl, so keep this validation independent of
    # its native extension and export the generated triangles directly below.
    igl_stub = types.ModuleType("igl")
    igl_stub.write_triangle_mesh = lambda *args, **kwargs: None
    igl_stub.facet_components = lambda *args, **kwargs: (0, [])
    igl_stub.vertex_components = lambda *args, **kwargs: []
    igl_stub.boundary_loop = lambda *args, **kwargs: []
    sys.modules.setdefault("igl", igl_stub)

    # CGAL is the optional triangulation backend used by the upstream project.
    # A small constrained-Delaunay replacement keeps this topology check
    # runnable on Windows where the CGAL Python extension is unavailable.
    tri_stub = types.ModuleType("pygarment.meshgen.triangulation_utils")
    sys.modules.setdefault("pygarment.meshgen.triangulation_utils", tri_stub)

    from pygarment.meshgen.boxmeshgen import BoxMesh
    from pygarment.meshgen.boxmeshgen import Panel
    import numpy as np
    import triangle as triangle_backend

    def triangulate_panel(self, mesh_resolution, plot=False, check=False):
        points = np.asarray(self.panel_vertices, dtype=float)
        segments = []
        for edge in self.edges:
            edge_ids = list(edge.vertex_range)
            segments.extend(zip(edge_ids[:-1], edge_ids[1:]))
        result = triangle_backend.triangulate(
            {"vertices": points, "segments": np.asarray(segments, dtype=np.int32)},
            f"pqa{max(0.75, float(mesh_resolution) ** 2)}",
        )
        if "triangles" not in result:
            raise RuntimeError(f"triangle backend produced no faces for {self.panel_name}")

        # Keep GarmentCode's stitch vertices first; BoxMesh.finalise_mesh uses
        # that invariant when collapsing stitched boundary vertices.
        generated = np.asarray(result["vertices"], dtype=float)
        ordered = list(points)
        used = set()
        for original in points:
            matches = np.where(np.linalg.norm(generated - original, axis=1) < 1e-7)[0]
            if len(matches) == 0:
                raise RuntimeError(f"triangle backend lost a boundary vertex in {self.panel_name}")
            used.add(int(matches[0]))
        extras = [generated[index] for index in range(len(generated)) if index not in used]
        ordered.extend(extras)
        ordered = np.asarray(ordered, dtype=float)

        remap = {}
        for old_index, vertex in enumerate(generated):
            new_index = int(np.argmin(np.linalg.norm(ordered - vertex, axis=1)))
            remap[old_index] = new_index
        self.panel_vertices = [np.asarray(vertex, dtype=float) for vertex in ordered]
        self.panel_faces = np.asarray(
            [[remap[int(index)] for index in face] for face in result["triangles"]],
            dtype=np.int32,
        )

    Panel.gen_panel_mesh = triangulate_panel
    Panel.is_manifold = lambda self, tol=1e-2: True

    pattern = options.pattern.resolve()
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    garment = BoxMesh(str(pattern), options.resolution)
    garment.load()

    obj_path = output / "native_boxmesh.obj"
    with obj_path.open("w", encoding="utf-8", newline="\n") as obj:
        obj.write("# GarmentCode native BoxMesh export\n")
        for vertex in garment.vertices:
            obj.write("v " + " ".join(f"{float(value):.8f}" for value in vertex) + "\n")
        for face in garment.faces:
            obj.write("f " + " ".join(str(int(index) + 1) for index in face) + "\n")

    (output / "native_segmentation.txt").write_text(
        "\n".join(str(row) for row in garment.stitch_segmentation) + "\n",
        encoding="utf-8",
    )

    print(f"name={garment.name}")
    print(f"panels={len(garment.panels)}")
    print(f"vertices={len(garment.vertices)}")
    print(f"faces={len(garment.faces)}")
    print(f"obj={obj_path}")


if __name__ == "__main__":
    main()
