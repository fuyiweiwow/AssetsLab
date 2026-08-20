# Generated wearable workflow reuse contract V1

## Scope

This milestone proves one reusable workflow for one Actor class and a complete seven-slot adventurer set. The visible clothes, hair, boots, bracers, belt, shorts, and backpack are Hunyuan3D-2mv generated meshes. Script-built geometry is limited to ActorProfile fit transitions, masks, placement coordinates, and binding support; it is not the authored garment design.

The result is reusable for a replacement Actor, but not as a blind one-click transfer. A new Actor first becomes a new Actor class and must pass the same profile, fit, binding, and motion gates.

## Replacement Actor requirements

- Static preview: one clean Actor surface is sufficient for envelopes and rigid accessory placement.
- Animated clothing: the Actor needs a usable skeleton, skin weights, a stable bind/rest pose, and semantic bones for pelvis, waist, spine, head, arms, hands, legs, and feet.
- Different bone names are supported through the alias resolver or an explicit semantic remap. Missing animated semantics produce `static_only`, never a false animated pass.
- A different head/body proportion requires regenerated Actor calibration views. Hair and close-fitting clothes must not reuse the old Actor's isolated images.

## Rebuild sequence

1. Run `extract_actor_wearable_profile_v1.py` on the replacement Actor and resolve every missing animated semantic.
2. Render orthographic Actor calibration views for the slot boundary being authored: head, torso/arms, waist/hips, or feet.
3. Use ImageGen to place the desired design on those exact Actor proportions. For close-fitting slots, remove the Actor only after the dressed multiview is consistent.
4. Split synchronized front/right/back/left views, then run `prepare_multiview_rgba_v1.py` with the official Hunyuan background remover.
5. Run `run_hunyuan2mv_slot_v1.py`. Never generate a complete inseparable dressed Actor when the target is a modular slot.
6. Compile the generated mesh through its slot adapter. Fit coordinates, masks, and small transition bands come from the new Actor profile; the generated mesh remains the visible authored asset.
7. Bind with the smallest controlled bone whitelist. Rigid parts use one semantic bone; deforming garments use explicit regional weights.
8. Run slot geometry audits and front/right/back/left eight-frame action review. Failed candidates do not enter the accepted working blend or preview.

The current online ImageGen stage may later be replaced by a local multi-image editor. The RTX 3060 deployment candidates, separation experiment, and acceptance gates are recorded in `docs/OFFLINE_IMAGE_AI_RTX3060_RESEARCH_2026-08-20.md`. Replacing the image model does not relax any ActorProfile, binding, collision, or motion gate.

Set `HUNYUAN3D_SOURCE` to the local Hunyuan3D-2 checkout and
`HUNYUAN3D_2MV_MODEL` to the local 2mv model directory when they are not stored
next to this workflow. The model and runtime are intentionally not duplicated in
the milestone package.

## Mandatory gates

- `head_hair`: crown, rear, and both temple enclosure bands plus exposed-contact animation audit.
- `torso_outer`: generated-source/weight audit, collar coverage, zero visible Actor contact, sleeve shoulder below collar, sleeve terminal center aligned to the Actor arm ring, and zero masked hand vertices.
- `waist_accessory`: closed generated ring, tunic clearance, and hand-swing clearance.
- `legs_outer`: pelvis/thigh whitelist, stable crotch bridge, and zero visible Actor contact.
- `feet_outer`: rigid left/right foot ownership and zero visible Actor vertices inside the solid boot core; the top cuff remains an intentional ankle transition.
- `wrist_accessory`: forearm-axis centering, stable topology, visible forearm through generated recesses, and zero masked hand vertices.
- `back_accessory`: rigid spine ownership, stable topology, four-direction clearance review, and no substitution with a rule-built backpack.

## Boundary continuity contracts added in V2

- Sleeve and boot openings are explicit Actor-class contracts. A generated garment or shoe is allowed to overlap a small ActorProfile transition surface whose geometry is derived from the Actor envelope and whose weights interpolate only across the adjacent semantic bones.
- The leg bridge begins inside `legs_outer` and ends inside `feet_outer`; `audit_leg_opening_continuity_v1.py` checks topology, normalized whitelist weights, boot overlap, exposed span, and lower-ring/boot center alignment across eight motion frames.
- ActorProfile transitions are auxiliary body-fit geometry. They may close an unavoidable boundary caused by the source Actor's segmented topology, but they may not define the garment's silhouette, style, or surface details.

## Headwear compatibility classes

- `head_hair`: ordinary replacement hair generated against the current Actor head.
- `head_hair_accessory`: an enclosing hat/headscarf and its compatible visible hair generated and reconstructed together. This is the preferred contract for tight caps, wrapped scarves, helmets with exposed locks, and other strongly enclosing designs.
- A future standalone `head_accessory` may be rigid-bound only when it fits over a declared hair class such as `bald`, `hide_upper_hair`, or a named compatible hairstyle. Arbitrary hats are not accepted over arbitrary voluminous hair.
- A replacement Actor must rerender head calibration views and rebuild the enclosing asset. Reusing the old Chibi head mesh by scale alone is not considered a valid transfer.

## Accepted milestone evidence

- Complete blend: `milestone/adventurer_set_complete_v1.blend`
- Complete preview: `preview/preview.gif`
- V2 fit/headwear blend: `milestone/adventurer_set_fitfix_headscarf_v2.blend`
- V2 fit/headwear preview: `preview/preview_fitfix_headscarf_v2.gif`
- Actor profile: `reports/actor_wearable_profile_chibi_v1.json`
- Final audits: all seven slot audits plus leg-opening continuity and enclosing-headwear gates pass across frames 1, 11, 21, 31, 41, 51, 61, and 71.

## Known boundary

This is a Dota-style Actor-class wearable workflow, not proof that every arbitrary garment transfers to every arbitrary Actor without regeneration. Loose cloth, skirts, capes, long dangling parts, and radically different skeleton topology remain separate future classes and need their own binding/deformation contracts.
