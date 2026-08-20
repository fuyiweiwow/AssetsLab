# Stage 10: AdventurerSetV1

## Goal

Build the first complete themed wearable set for `ChibiActorV1` using the V11 generated-wearable compiler contract. This is a clothing-system experiment, not a one-off inseparable character model.

## Planned slots

`head_hair`, `torso_outer`, `waist_accessory`, `legs_outer`, `feet_outer`, `wrist_accessory`, and `back_accessory`.

## Asset direction

Use a compact stylized fantasy-traveler silhouette with large reconstruction-friendly forms: chunky hair locks, short tunic/jacket, compact belt pouch, fitted legwear, ankle boots, short bracers, and a compact backpack. Avoid thin or dangling elements in V1.

## Execution order

1. Generate and approve one synchronized four-view master design tied to the current Actor proportions.
2. Produce per-slot synchronized transparent references while preserving the master design.
3. Generate one Hunyuan source mesh per slot.
4. Add or reuse a slot-specific semantic adapter and controlled bone whitelist.
5. Apply Actor body/scalp boundary masks and any required ActorProfile opening components.
6. Pass slot audit and front/right/back/left eight-frame review.
7. Assemble all accepted slots and render the complete 71-frame four-direction preview.

No slot enters the accepted set merely because the full dressed concept looks correct.

## Accepted checkpoint: complete seven-slot milestone

### V3 reproducible diagnostic checkpoint

`milestone/adventurer_set_workflow_v3.blend` preserves the current original-hair modular workflow after the V2MV footwear, waist-cinch, backpack-contact, and short-sleeve interface experiments. Its complete and upper-body reviews are `preview/preview_workflow_v3.gif` and `preview/preview_workflow_v3_upper.gif`.

V3 is deliberately recorded as a diagnostic checkpoint, not a final accepted wearable release. It establishes these reusable contracts:

- generated Hunyuan torso geometry remains the styled garment; a two-sided 80-face ActorProfile ring handles only the sleeve/skin boundary;
- equipping the rigid waist slot drives the reversible tunic shape key `AccessoryFit_AdventurerWaistV1`;
- both boots are rebuilt from the same generated source, use a percentile sole plane, and no longer retain a stale mirrored candidate;
- backpack depth is anchored from generated torso/back surface percentiles;
- hands are never masked, and bracers occupy only the wrist-side section of the forearm.

Two visual blockers remain open and must not be hidden by passing metadata: the generated sleeve/torso shell still self-interferes in motion, and rigid foot-bone boot binding makes the sole rotate like a hoof instead of preserving a believable planted contact. The exact files, audit distinctions, and known limitations are recorded in `WORKFLOW_V3_STATUS.md` and `MILESTONE_MANIFEST_V3.json`.

### V2 fit-fix and enclosing headwear checkpoint

The latest accepted file is `milestone/adventurer_set_fitfix_headscarf_v2.blend`. V1 remains in the package as the rollback baseline. V2 keeps the same seven gameplay slots and adds one compatible `head_hair_accessory` variant: a Hunyuan-generated close-fitting headscarf, leather band, rear knot, and short hair reconstructed as one asset from the current Actor's orthographic head calibration.

V2 records four reusable fit corrections:

- The outer shoulder mound is selectively lowered while the generated collar rim is preserved. Sleeve roots are narrowed and lowered without masking either hand.
- The lower tunic shell and generated belt are tightened around the Actor waist; the backpack is moved closer to the `Spine02` envelope.
- Each generated boot receives an ActorProfile skin bridge from inside the shorts to inside the boot cuff. The bridge uses controlled thigh/calf/foot weights and replaces the old segmented lower-leg exposure; it is fit support, not visible clothing authorship.
- Enclosing headwear is compiled as a hair-compatibility asset, not stacked blindly over arbitrary hair. The source mesh stays visible, binds rigidly to `CC_Base_Head`, and passes crown/rear/temple enclosure plus exposed-face contact gates.

All eight V2 reports under `reports/final_audit_*_v1.json` pass at frames 1, 11, 21, 31, 41, 51, 61, and 71. The visual review is `preview/preview_fitfix_headscarf_v2.gif`; the reproducibility inventory and hashes are in `MILESTONE_MANIFEST_V2.json`.

The headwear concept/reference images were generated with built-in ImageGen. Prompt intent: preserve the exact Chibi Actor head proportions and orthographic front/right/back/left alignment; create one compact teal cloth headscarf/cap with a brown leather band, integrated short brown hair, and a small rear knot; keep the face and neck unobstructed; use large reconstruction-friendly forms and a plain background. Hunyuan3D-2mv then reconstructed the isolated four-view asset with seed `20260820`, 30 steps, guidance `5.0`, and octree resolution `256`.

The accepted complete file is `milestone/adventurer_set_complete_v1.blend` (the curated copy of experiment candidate V5). It contains the generated visible assets for all seven planned slots plus Actor-specific fitting, masks, and controlled bindings.

| Slot | Generated source | Accepted adapter | Gate result |
| --- | --- | --- | --- |
| `torso_outer` | `assets/generated_sources/adventurer_torso_outer_2mv_v1.glb` | assembled from the accepted sleeve-fit V14 stage | eight frames, zero Actor contact; all six collar/shoulder bands pass |
| `head_hair` | `assets/generated_sources/adventurer_head_hair_actorfit_2mv_v2.glb` | assembled from accepted actor-fit V6 | rigid `CC_Base_Head`; four-region enclosure 100%; eight frames, zero exposed Actor contact |
| `waist_accessory` | `assets/generated_sources/adventurer_waist_accessory_2mv_v1.glb` | assembled as complete V5 | rigid `CC_Base_Waist`; eight frames, zero Actor and tunic contact |
| `legs_outer` | `assets/generated_sources/adventurer_legs_outer_2mv_v1.glb` | assembled from accepted legs V1 | pelvis/spine/thigh whitelist; eight frames, zero visible Actor contact and stable crotch bridge |
| `feet_outer` | `assets/generated_sources/adventurer_feet_outer_2mv_v1.glb` | assembled as complete V5 | mirrored single generated boot; rigid left/right foot binding; zero visible Actor vertices in the solid boot core across eight frames |
| `wrist_accessory` | `assets/generated_sources/adventurer_wrist_accessory_2mv_v1.glb` | assembled as complete V5 | independent generated bracers; rigid forearm binding; maximum center-to-arm-axis error below 0.006; hands never masked |
| `back_accessory` | `assets/generated_sources/adventurer_back_accessory_2mv_v1.glb` | assembled as complete V5 | compact generated backpack; rigid `Spine02` binding and stable topology across eight frames |

Accepted combined preview: `preview/preview.gif`. Checksums and the exact retained-file boundary are recorded in `MILESTONE_MANIFEST_V1.json`.

The Hunyuan inputs are built from four separate ImageGen views. ImageGen's requested transparent backgrounds were not reliable in this experiment, so source renders use plain white RGB and the official `hy3dgen.rembg.BackgroundRemover` produces the RGBA inputs. A failed montage or checkerboard-looking RGB image is never passed to 2mv.

### Adapter findings

- The short tunic reuses the V11 semantic compiler contract but has its own short-sleeve chain, lower-shell taper, shoulder-only lift, and body mask.
- The original `adventurer_head_hair_2mv_v1.glb` candidate is rejected: its normal-human ImageGen proportions passed the old no-visible-contact check but failed the later enclosure audit (crown 2.1%, rear 0.1%, both temples 0%). It must not be returned to the working set or preview gallery.
- Accepted hair V6 starts from orthographic renders of the current Actor's real unmasked head. ImageGen first adds the hairstyle to that exact skull in front/right/back/left views, then isolates only the fitted hair before official-rembg and local 30-step Hunyuan3D-2mv reconstruction. The adapter uses the generated mesh as visible geometry, applies Actor-head radial shell clearance, and binds it rigidly to `CC_Base_Head`.
- `audit_head_hair_enclosure_v2.py` is a mandatory gate. Crown, rear, and both above-ear temple bands must each have at least 94% radial enclosure with at least 0.008 clearance. V6 records 100% in all four bands. `audit_adventurer_head_hair_v1.py` separately rejects face/eye/cheek contacts while allowing only the invariant temple-scalp contacts hidden beneath the measured enclosing shell.
- The belt is a closed generated ring. Its outer silhouette remains inside the hand-swing envelope while a nonlinear radial correction increases only the inner clearance around the tunic.
- Short sleeves use `limb_transition_contract_v1.json` and `audit_sleeve_axis_alignment_v2.py`. The rejected skin-coloured patch was replaced by a garment-material ActorProfile terminal band. Its centerline is derived from the active Actor's upperarm-to-forearm rig segment, not fixed Chibi coordinates. The collar remains at least 0.008 above the sleeve shoulder and hands are never hidden.
- `legs_outer` uses the generated 2mv mesh as the visible shorts. The adapter maps it to the Actor hip envelope and assigns a controlled `Pelvis / Spine01 / L_Thigh / R_Thigh` whitelist. The center crotch bridge remains pelvis-owned while each lower leg follows its own thigh.

### Reuse checkpoint

`extract_actor_wearable_profile_v1.py` is the entry point for a replacement Actor. It resolves a semantic bone map, exports rest-bone anchors and weighted surface regions, and distinguishes animated from static-only compatibility. Full reuse steps and acceptance gates are recorded in `WORKFLOW_REUSE_V1.md`.
