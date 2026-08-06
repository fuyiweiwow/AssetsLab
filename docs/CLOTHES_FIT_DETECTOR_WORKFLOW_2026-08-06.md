# Clothing fit detector and clean garment workflow

Date: 2026-08-06

This note records the workflow used to recover the sleeveless Actor clothing
experiment after repeated shoulder, hem, and motion failures.

## Findings

1. The clean garment must be authored in the same pose used for the Surface
   Deform bind. For the demo route this is walk frame 1. Building in rest pose
   and binding against frame 1 gives the garment and proxy different initial
   coordinate spaces, which pulls the shoulder and hem out of alignment.
   Rest-pose authoring is only valid for the explicit Armature comparison route.
2. A front-to-back horizontal cap at the hem is not a valid clothing closure.
   It crosses the body by construction and, after subdivision, produces
   interior vertices that look like thigh penetration or a semicircular notch.
   The sleeveless prototype therefore keeps a continuous open hem boundary.
3. Catmull-Clark is acceptable once the demo topology is restored: continuous
   side seams and shoulder bridges, with only the hem intentionally open. The
   previous internal-vertex problem came from disconnected bridge/cap topology.
4. For the motion stage, Surface Deform to the Animation Proxy is currently
   more stable than a small hand-authored height/side weight schema. The
   explicit bone weights remain useful as a comparison, but are not the active
   current candidate.

## Detector

`tools/blender/check_garment_actor_fit.py` now emits schema
`assetslab_garment_actor_fit_check_v2` and samples frames 1, 11, 21, 31, 41,
51, 61, and 71. It reports:

- shoulder height and lateral placement against the clavicle/upperarm bones;
- interior back boundary edges, separate from intentional hem and armhole
  boundaries;
- lower-hem penetration using Actor torso depth samples;
- front/back torso clearance during movement;
- non-manifold edges and worst sample coordinates.

Shoulder bridge midpoints and outer armhole points are excluded from torso
depth checks because they are intentional clothing geometry, not body-facing
surfaces. The detector remains a regression gate, not a replacement for visual
review.

## Current candidate

The candidate promoted to Gallery current uses:

- Actor frame-1 bind-pose measurements;
- `--render-surface-clearance 0.050`;
- Catmull-Clark subdivision level 2;
- open hem;
- Surface Deform to the Animation Proxy;
- headless 4-direction × 8-frame rendering.

The detector passes shoulder placement, back integrity, hem penetration, body
clearance, and manifold checks. It remains `review_required`: this is a stable
sleeveless prototype, not yet a general random-clothing generator or a
milestone for sleeves, trousers, armor, or clothing randomization.

The current proportions are intentionally taken from the striped demo review:
the lower edge remains approximately `z=0.775 m`; lower support rows use
half-widths `0.370/0.375/0.365 m` to cover the upper-thigh envelope, middle
rows taper to `0.325/0.300/0.290 m`, and the upper shoulder envelope remains
approximately +/-0.31 m. These are clothing bounds, not global Actor scaling
parameters.

## Parameter provenance and tools

All dimensions are meters after the Actor import scale has been applied.
Record the source of each value instead of treating the clothing mesh as a
freehand drawing:

| Parameter | Source region or object | Current value / rule |
|---|---|---|
| shoulder joint height | `Armature`, `CC_Base_L_Upperarm.head` left/right | mean z ≈ 1.391 m in bind frame |
| shoulder surface top | `Armature`, `CC_Base_L/R_Clavicle.tail` plus shoulder margin | max(clavicle tail, upperarm head) + 0.080 m |
| hem anchor | `Armature`, `CC_Base_Waist.tail` | waist tail - 0.015 m, z ≈ 0.775 m |
| torso front/back depth | `ChibiBaseMesh_AccuRIG_InputMesh`, torso-weighted vertices in local x/z slices | robust 5th/95th percentile y + 0.050 m clearance |
| lower and shoulder width | last accepted striped demo render envelope plus lower support rows | lower support half-widths 0.370/0.375/0.365 m; shoulder envelope approximately +/-0.31 m |
| vertical interpolation | hem-to-shoulder span | normalized rows 0.00, 0.09, 0.31, 0.575, 0.72, 0.88, 1.00 |
| neckline and shoulders | clean shell topology | x profile `(-0.92,-0.68,-0.34,0.34,0.68,0.92)`; front opening `(0.34,0.50,0.60)`; top bridges columns `0,1,4` |

The torso depth sample includes vertices weighted to `CC_Base_Pelvis`,
`CC_Base_Waist`, `CC_Base_Spine01`, `CC_Base_Spine02`, both clavicles, and both
upper arms. Head and face vertices are excluded. Shoulder width is taken from
the shoulder bones, while the lower clothing width is taken from the accepted
striped clothing envelope; these two measurements must not be replaced by a
single whole-body bounding box.

The record is maintained at two levels:

1. `tools/blender/build_garment_proxy_render_pair.py` writes the reproducible
   geometry, deformation, and render parameters to `manifest.json`.
2. `tools/blender/check_garment_actor_fit.py` writes the sampled regression
   result to `garment_actor_fit_report.json`; Gallery publication is performed
   by `tools/build_preview_assets.py` and `tools/serve_preview.ps1`.

The current render chain is therefore:

`Actor bones + torso slices -> demo-style clean shell -> Catmull-Clark 2 -> Surface Deform -> Animation Proxy -> 4 directions x 8 frames -> fit detector -> Gallery`

## Front-to-side transition rule

The front/side discontinuity is corrected using the same principle visible in
the official GarmentCode demo: a continuous cloth surface with a gradual
normal change, not a separate sewn-on side strip. The accepted shoulder and
hem landmarks remain unchanged. The front and back panels use an outer
normalized x value of +/-0.92. Between them, each row uses three lateral
samples at x factors `0.94/0.97/0.94` and depth fractions `0.30/0.50/0.70`,
making four faces per side and row:

`front panel -> three lateral samples -> back panel`

This replaces the old single vertical front-to-back wall, which created a hard
90-degree fold even after Catmull-Clark smoothing. The lower support rows and
0.050 m torso clearance are fit guards for the open hem; they do not change the
shoulder, neckline, or overall Actor scale. Render-only smoothing is disabled
for this candidate because it pulled the open hem inward during walking. The
geometry, transition samples, and smoothing switches are written to
`manifest.json` and validated by the same eight-frame fit detector.

## Reproduction

```powershell
& blender.exe --background --python tools/blender/build_garment_proxy_render_pair.py -- `
  --input-blend prototype/test_output/garmentcode_actor_proxy_current/garmentcode_actor_transfer_candidate.blend `
  --output prototype/test_output/garmentcode_proxy_render_pair_current `
  --subdivision-level 2 --build-clean-render-garment `
  --render-surface-clearance 0.050 --clean-animation-proxy `
  --animation-proxy-smooth-iterations 6 --animation-proxy-smooth-factor 0.35 `
  --animation-proxy-decimate-ratio 0.30 `
  --render-surface-smoothing-iterations 0 --post-deform-smooth-iterations 0 `
  --resolution 256

& blender.exe --background --python tools/blender/check_garment_actor_fit.py -- `
  --blend prototype/test_output/garmentcode_proxy_render_pair_current/garmentcode_proxy_render_pair_candidate.blend `
  --output prototype/test_output/garmentcode_proxy_render_pair_current/garment_actor_fit_report.json
```
