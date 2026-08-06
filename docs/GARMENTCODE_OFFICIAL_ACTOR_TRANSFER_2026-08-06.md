# Official GarmentCode sim.obj -> Actor transfer (2026-08-06)

## Purpose

Verify whether the official GarmentCode Warp result can be rendered on the
project Actor without replacing the Actor body or walk action.

This is an isolated review candidate. It is not yet a clothing-library seed
and is not included in runtime randomization.

## Source and method

- Actor: `prototype/assets/characters/actor_v1/chibi_actor_mixamo_walk_v1.blend`
- Clothing cage: `prototype/test_output/actor_clothing_cage_v1/actor_clothing_cage_v1.blend`
- Official source: `third_party/GarmentCode/Logs/t-shirt__260805-19-14-57_260805-19-31-09/t-shirt__260805-19-14-57_sim.obj`
- Transfer candidate: `prototype/test_output/garmentcode_actor_official_neutral_v1/`
- OBJ scale: `0.01` (official GarmentCode output is in centimetres; Actor is in metres)
- Surface method: cage bounds fit followed by side-preserving ray projection with
  `0.018` Actor clearance
- Animation method: nearest Actor vertex weights plus the existing Actor armature
  and walk action

The transfer script now accepts either the existing fitted Blender source or an
official `sim.obj` through `--fitted-obj`. The original Actor blend is never
written in place.

## Result

The candidate rendered successfully as four directions x eight walk samples:

- front, right, back and left images were generated;
- all 32 renders completed;
- the official garment remained a complete shirt on the Actor;
- no previous nearest-surface front/back inversion was used;
- the walk action was preserved and rendered through frame samples 1..71.

The candidate remains `review_required`. The current checks are visual:
silhouette, sleeve/hem shape, back shading and whether the side view matches the
Actor's intended chibi proportions. It must not be promoted to a random pool
until those checks pass and a motion-specific deformation audit is completed.

## Gallery

The review page is published through the local preview service and Tailscale:

`http://100.72.203.81:8765/snapshots/20260806-082638-garmentcode-actor-official-neutral-20260806/index.html`

## Next gate

If the visual result is accepted, the next isolated test is a deformation audit
at additional walk frames and a comparison against the Actor Clothing Cage. If
it is rejected, adjust the Actor proxy/measurement mapping rather than editing
the official garment mesh by hand.

## Follow-up experiments

The first compressed-depth correction was rejected internally: reducing the
whole garment depth caused the Actor torso to occlude the back panel and made
the rear opening worse. Skipping projection on the sleeve edge also produced a
larger cuff gap, so that variant is not a baseline.

The official custom-body route was also tested. The raw automatic Actor
measurements were invalid for the GarmentCode t-shirt generator because the
stylised head and wrist entered the body slices. A constrained pattern preset
could be generated, but the raw Actor collision mesh was non-watertight and
had 29 disconnected components; Warp crashed around frame 104. A Blender
voxel remesh did not solve this and produced 1100 components. These outputs are
diagnostics only.

The current review candidate is v3:

- `prototype/test_output/garmentcode_actor_official_neutral_v3_surface_bias/`
- uses the verified official neutral `sim.obj`;
- keeps the original 1.0 depth fit and side-preserving projection;
- adds only small Actor-space corrections: front chest inward, back clearance
  outward and sleeve-edge outward compensation;
- remains `review_required` and is not in the random pool.

Gallery snapshot:

`http://100.72.203.81:8765/snapshots/20260806-084724-garmentcode-actor-surface-bias-v3-20260806/index.html`

## GarmentCode-compatible Actor proxy experiment

The raw Actor collision mesh must not be passed directly to GarmentCode: it
contains 29 disconnected components and is not watertight. The new proxy
builder fills the Actor volume with voxels and extracts one closed surface.
The proxy is exported in metres because GarmentCode multiplies body OBJ
coordinates by 100 internally; the measurement YAML remains in centimetres.

- Builder: `tools/garmentcode/build_actor_garmentcode_body_proxy.py`
- 4 cm proxy: `prototype/test_output/garmentcode_actor_body_proxy_v1/`
- 3 cm proxy: `prototype/test_output/garmentcode_actor_body_proxy_v2/`
- Both proxies: watertight, winding-consistent and one connected component.
- Segmentation: conservative mutually exclusive body/arm/leg vertex labels;
  no internal face geometry is present in the proxy.
- Custom simulation entry points now accept `--body-obj`,
  `--body-measurements` and `--body-segmentation` before `run_sim`.

The first proxy run exposed an invalid `head_l=47 cm` measurement: GarmentCode
computes the lower attachment as `height - head_l - waist_line`, placing the
shirt around the Actor head. The proxy-specific preset uses `head_l=152 cm`
based on the Actor neck/head transition around Y=155 cm. This moved the
simulated shirt into the torso range (Y about 73..149 cm).

The corrected 4 cm proxy completed 120 frames without a Warp crash, but failed
GarmentCode's quality gate with 368 body collisions and 826 self-collisions.
The 3 cm proxy also completed 120 frames and reached 415 body collisions and
593 self-collisions. These are diagnostic results, not Gallery candidates.
The next improvement must address body/garment dimensional fit and sleeve
clearance; increasing voxel resolution alone is not sufficient.

## First proxy physics baseline

The isolated torso experiment used the 3 cm proxy, `head_l=152 cm`, shirt
width `1.3`, and a sleeveless design. With a 500-frame simulation allowance,
GarmentCode stopped at frame 406 and reported `fails: {}`, 19 body collisions
and 0 self-collisions. The 405-frame boundary alone would have been recorded
as a static-equilibrium failure, so the larger allowance is part of the test
procedure.

The result was transferred to the original Actor and its walk action without
writing the source blend in place:

- Transfer output: `prototype/test_output/garmentcode_actor_proxy_v1_baseline/`
- Proxy and measurement inputs: `prototype/test_output/garmentcode_actor_body_proxy_v2/`
- Review status: `review_required`; this is a sleeveless torso baseline, not a
  finished short-sleeve garment or a randomization seed.

Previous Gallery snapshot:

`http://100.72.203.81:8765/snapshots/20260806-095956-garmentcode-actor-proxy-v1/`

## Current visual-fit experiment

The first Actor transfer exposed a second, separate problem: the Cage depth
range was much larger than the Actor torso (`-0.57..0.30 m` versus about
`-0.25..0.18 m`). The current experiment keeps the width and binding unchanged,
uses `depth_factor=0.55`, `depth_margin=0.02`, and adds `0.10 m` only to the
back side. This reduces the front chest inflation while keeping the back panel
visible. It remains `current`, not a passed milestone; visual review still
needs to check the back surface and four-direction motion.

- Current output: `prototype/test_output/garmentcode_actor_proxy_current/`
- Transfer script now records the GarmentCode OBJ orientation and uses the
  Actor/OBJ axis contract explicitly.
- Gallery policy: only the two official passed milestones and this current
  experiment are published. The next experiment overwrites `current`.

Current Gallery snapshot:

`http://100.72.203.81:8765/snapshots/20260806-110852-20260806-garmentcode-actor-sampled-torso-width-current/`

## Bone-constrained torso fit (2026-08-06)

The previous transfer still inherited the Cage's broad shoulder/hem profile. The
Actor armature was inspected at frame 1: `CC_Base_L/R_Upperarm` roots span about
`0.4985 m` at `z=1.3554 m`, while `CC_Base_L/R_Thigh` roots span about `0.3840 m`
at `z=0.5700 m`. The new transfer pass uses these two bone pairs as the lower and
upper references for a linear torso-width profile.

The shoulder band also compresses depth against Actor torso slices before the
side-preserving clearance raycast. This is a local shoulder/torso fit, not a
global garment scale. The current image is visibly less dress-like in front,
but the side collar transition and rear horizontal striping remain review issues.

- Transfer script: `tools/blender/transfer_garmentcode_fitted_to_actor.py`
- Current output: `prototype/test_output/garmentcode_actor_proxy_current/`
- Parameters: `depth_factor=0.55`, `depth_margin=0.02`, `back_clearance=0.10`,
  `shoulder_ease=0.055`
- Bone-fit report: `manifest.json -> bone_shoulder_fit`
- Status: `review_required`; not a milestone and not a randomization seed.

### Side-raycast correction

The first bone-width implementation still looked similar because the lateral
raycast hit the Actor arms/hands at lower torso heights and expanded the garment
back to approximately `x=±0.59 m`. For the sleeveless torso, the transfer now
keeps the bone-derived lateral profile and projects only front/back vertices;
`--project-side-x` remains opt-in for garments whose sleeves require side
projection. The corrected final garment range is approximately `x=±0.30 m`.

The result is visibly closer to a fitted short top in front. Rear source-panel
striping and the side collar transition remain review-required.

### Layered depth and deformation correction

The side-thickness issue required more than another global measurement. The
transfer now records a per-height torso front/back envelope with `0.018 m`
clearance, stops raycast projection at the upper-arm-root shoulder height, and
does not use the previous `back_clearance=0.10 m` compensation. The collar's
nearest-vertex `CC_Base_Head` weights are redistributed to
`CC_Base_NeckTwist01`/`CC_Base_Spine02`; otherwise the collar is pulled into the
face/neck during the armature evaluation.

The corrected render removes the side floating strip and keeps the rear panel
outside the torso. The horizontal source-panel folds remain a garment topology
quality issue, so the candidate stays `review_required`.

### Pelvis-bone hem constraint

The previous candidate's hem reached `z≈0.62 m` and intersected the thighs in
side view. The Actor armature places `CC_Base_Pelvis.tail` at `z≈0.73597 m` and
the thigh roots at `z≈0.57017 m`. The current sleeveless top uses a hem target of
`z=0.76597 m` (`pelvis tail + 0.03 m`); the evaluated garment minimum is about
`z=0.7552 m`. This shortens only the lower edge and leaves the accepted shoulder,
collar-weight and layered-depth corrections unchanged.

### Sampled torso-width interpolation

The bone-only shoulder-to-hip line was not sufficient: it matched the endpoints
but could pass through the Actor torso between them. The current transfer samples
the central Actor torso at `0.05 m` vertical intervals, excludes the detached
arm lobes, and linearly interpolates the sampled lateral envelope. The shoulder
bone remains an upper cap and the thigh/hip region remains the lower anchor.
The sampled curve is recorded in `manifest.json` under
`bone_shoulder_fit.width_fit`.

The hem remains above `CC_Base_Pelvis.tail`, and the depth/weight corrections are
unchanged. Four-direction motion samples were checked; the candidate remains
`review_required` because the source garment's horizontal panel folds still need
topology cleanup.

## Design-stage torso profile follow-up (2026-08-06)

The previous sampled curve was only applied during Actor transfer. That made the
runtime transfer responsible for correcting a pattern that had already been
designed too broadly. The new helper `tools/garmentcode/build_actor_design_body.py`
now records the same height-dependent torso profile and derives an auditable
GarmentCode body preset before pattern generation. The profile is kept beside the
scalar YAML because the official `tee.py` program consumes scalar measurements;
the full curve cannot be represented by four independent body fields.

The first direct scalarization was intentionally tested and rejected. It reduced
the generated design inputs to approximately `shoulder_w=60.85 cm`,
`back_width=83.16 cm`, `waist_back_width=59.88 cm`, and `hip_back_width=64.08 cm`.
The resulting sleeveless pattern crashed GarmentCode at frame 78 with the
official `mid_bending` material and at frame 120 with the default material. This
means the standard T-shirt's scalar body contract cannot safely carry this Q-style
Actor profile by simply narrowing shoulder/back measurements.

A second control kept the already stable proxy body preset and changed only the
shirt design `flare` from `1.0` to `0.92`. It also crashed at frame 200 with the
default material. Both candidates are diagnostics only and were not transferred
to Actor or published to Gallery. The existing passed physics source remains the
current source of truth.

Conclusion: torso sampling belongs in the design stage, but not as a late scalar
body override. The next implementation should feed the sampled curve into a
custom torso-panel boundary/side-edge construction, preserving the validated
body preset and sewing topology. Cloth stiffness must be evaluated separately
after that pattern is stable; `enable_body_smoothing` is not a garment smoothing
switch and remains disabled.

## Low-strength panel-profile preview (2026-08-06)

The first custom panel-boundary experiment uses
`tools/garmentcode/apply_actor_torso_profile.py` with `strength=0.30`. It leaves
the four torso panels, seams, and body YAML unchanged and only scales their
horizontal boundary coordinates against the sampled Actor curve. GarmentCode
completed 406 frames, but reported 74 body collisions and 1 self-collision, so
the physics gate failed. The complete sim OBJ was nevertheless transferred to
the Actor as the current visual diagnostic; it is not a milestone or random
seed. The Gallery labels these metrics explicitly.
