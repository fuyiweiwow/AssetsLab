# AdventurerSetV1 workflow status: V3

## Intent

V3 remains a reusable modular clothing workflow for an Actor class. The styled visible assets come from ImageGen references and Hunyuan3D-2MV reconstruction. Rule-built geometry is limited to small ActorProfile interface adapters and must not replace garment design.

Headwear remains frozen and the original `AdventurerHair_Chestnut` is active. Helmet, headscarf, crown, and hairstyle-compatibility contracts remain future work.

## Current visual verdict

V3 is a reproducible diagnostic checkpoint, not a final accepted outfit. Motion review still shows severe interference between the generated sleeve and torso shell. The boot is rigidly bound to the foot bone, so its complete sole rotates with the animated foot and reads as a hoof instead of maintaining believable planted contact. Passing slot metadata does not override either visual rejection.

## Current file

`adventurer_set_workflow_v3.blend`

The file contains:

- original Actor and original hair
- Hunyuan3D-2MV torso outer, legs outer, boots, bracers, belt, and backpack
- one canonical neck boundary seal
- two 80-face ActorProfile short-sleeve interface rings
- equipped-state torso shape key `AccessoryFit_AdventurerWaistV1`

No leg bridge or generated skin replacement is present.

## V3 corrections

### Sleeve and arm ownership

The Hunyuan sleeve remains the visible styled shell. The Actor body mask hides only the torso, shoulder root, and upper-arm region physically covered by the sleeve. Forearms, hands, and meaningful hand-weight vertices remain visible.

The old Actor has sparse arm topology, so a direct body-surface copy produced rectangular patches. V3 instead compiles a narrow open interface ring from the calibrated Actor arm axis and circumference. The ring covers parameters 0.42 through 0.82 of the calibrated arm axis, is buried inside the generated sleeve terminal, and carries upper-arm/forearm weights. It is Actor-specific fit support, not garment artwork. Bracers are centered at 0.22 of the wrist-to-elbow chain with 0.18 half-length, leaving a visible skin interval between sleeve and bracer.

### Waist accessory

The belt is a rigid outer-layer slot bound to `CC_Base_Waist`. Equipping it activates `AccessoryFit_AdventurerWaistV1` on the generated tunic. The shape key moves 8,359 tunic vertices with a maximum correction of 0.063424 and creates the expected cinched silhouette. Belt/tunic contact is allowed; belt/Actor contact is forbidden.

This is the preferred high-success contract for tight accessories. Runtime cloth is reserved for loose regions, while fitted compression uses an authored or compiled corrective shape.

### Boots and exposed legs

Both boots are rebuilt from the same Hunyuan source. The stale-right-boot duplication bug is removed. Source sole percentile 2 is mapped to the ground plane, the cuff is anchored toward the Actor calf, and the top is expanded by 14 percent. Actor geometry is hidden only through the solid boot core; the open cuff and calf remain visible. No fake leg bridge is used.

The current old Actor has visibly coarse exposed calf geometry. A future Actor must pass an exposed-skin topology/normal quality gate; the wearable compiler must not manufacture replacement skin to conceal a poor Actor.

### Backpack

The backpack front percentile 5 is aligned to the generated torso back percentile 90 with 0.004 clearance. This surface-contact anchor is compiled before rigid spine binding.

### Pants identity

`Wearable_Adventurer_LegsOuterV1` is byte-for-byte identical at the vertex-coordinate level across the accepted complete V5, headscarf V6, and workflow V2 comparisons:

- 58,166 vertices
- 116,336 faces
- vertex hash `ffd596333f50535edf76530baaa65ea2ac4389bed53f948a9f0fc6605ef29735`

The apparent thickness regression came from the neighboring torso depth and footwear/leg boundary, not from switching or modifying the pants model. V3 restores the torso depth to 0.456792.

## Reproduction chain

1. Start from `adventurer_set_complete_candidate_v5.blend`.
2. Compile `hunyuan_outputs/adventurer_torso_outer_2mv_v1.glb` with `build_adventurer_torso_outer_v1.py`.
3. Compile the generated belt and torso corrective with `build_adventurer_waist_accessory_v1.py`.
4. Compile boots, bracers, and backpack with `build_adventurer_remaining_slots_v1.py` and `actor_wearable_profile_chibi_v1.json`.
5. Run sleeve-interface, remaining-slot, waist-interface, and full four-direction eight-frame reviews.
6. Treat the old zero-contact torso audit as a diagnostic until it is made layer-aware for the sleeve interface ring.

## Acceptance evidence

- Current blend: `adventurer_set_workflow_v3.blend`
- Four-direction GIF: `review_workflow_v3_fourway.gif`
- Sleeve interface audit: `final_audit_v3_sleeve.json` - pass
- Remaining slots audit: `final_audit_v3_remaining.json` - pass
- Waist interface audit: `final_audit_v3_waist_interface.json` - pass
- Legacy torso zero-contact audit: `final_audit_v3_torso.json` - diagnostic fail; 29 to 38 Actor faces (594 to 814 triangle-pair contacts) meet the generated sleeve per sampled frame under the accepted interface boundary, plus one pre-existing evaluated degenerate face

## Remaining gates

- Resolve sleeve/torso shell ownership and self-interference without replacing the generated garment style.
- Replace whole-boot rigid foot binding with a sole-aware deformation or corrected foot-animation contract, then re-run planted-contact review.
- Visual approval of a new four-direction GIF after both blockers are resolved.
- A layer-aware torso audit that subtracts contact fully covered by the ActorProfile sleeve ring while continuing to reject uncovered skin leaks.
- Actor migration test using a newly profiled body and skeleton.
- Separate headwear/hairstyle compatibility system.
