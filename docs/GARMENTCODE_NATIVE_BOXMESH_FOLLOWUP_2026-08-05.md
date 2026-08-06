# GarmentCode native BoxMesh follow-up (2026-08-05)

## Purpose

Validate GarmentCode's native stitched mesh before using Blender Cloth or
transferring the result to the Q-style Actor.

## Findings

The earlier Blender adapter created a triangle fan per panel. Both the matched
body and Actor tests failed; that adapter is not a valid garment topology.

The native BoxMesh path was then tested. The upstream CGAL extension was not
available in the local Blender Python, so the validation script used the
compatible `triangle` constrained-Delaunay backend only for panel triangulation.
GarmentCode's stitch-collapse and mesh finalisation logic remained unchanged.

The static native result is materially better:

- no triangle-fan spikes;
- no scattered panel fragments;
- front/back panels form one coherent garment topology.

It is still only an assembled starting pose: shoulder openings and side overlap
are visible.

Directly sending this mesh into Blender Cloth failed. The solver produced
severe self-intersection and spike explosions. This candidate is rejected for
runtime use.

## Outputs

- `prototype/test_output/garmentcode_native_boxmesh_v1/native_boxmesh.obj`
- `prototype/test_output/garmentcode_native_boxmesh_preview_v7/`
- `prototype/test_output/garmentcode_native_boxmesh_cloth_v1/`

## Next gate

Before any Actor transfer, remove self-intersections and establish a clean
body-fitted initial pose. If that cannot be made stable, skip runtime Cloth and
transfer a controlled, body-fitted garment mesh instead.
