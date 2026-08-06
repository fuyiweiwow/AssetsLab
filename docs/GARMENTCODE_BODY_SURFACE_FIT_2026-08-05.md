# GarmentCode body-surface fit gate (2026-08-05)

## Experiment

The native GarmentCode BoxMesh was shrinkwrapped to the matching GarmentCode
body with a 0.025 m surface offset. This was tested before Actor transfer and
before using Cloth, so geometry quality and physics quality remained separate
gates.

## Result

The static fitted result is substantially more stable than the assembled native
pose:

- four directions are closed;
- the side view no longer shows the previous horizontal panel layering;
- the garment stays on the body surface instead of floating away.

Remaining visual issues are concentrated in the neckline, sleeve openings and
hem shape. These are now garment-design issues rather than topology or body
matching failures.

A restrained Cloth pass was then run from this fitted pose. It completed without
the previous spike explosion. Self-collision was disabled because the fitted
starting pose is already on the collision body and self-collision destabilised
the earlier test. The result has visible horizontal wrinkles and remains a
review candidate, not a runtime-approved garment.

Outputs:

- `prototype/test_output/garmentcode_native_boxmesh_fitted_v1/`
- `prototype/test_output/garmentcode_fitted_boxmesh_cloth_v1/`

Next gate: visually approve the fitted silhouette and decide whether the Cloth
wrinkles survive the intended pixel-render resolution. Only then should the
mesh be transferred through the Actor Clothing Cage.
