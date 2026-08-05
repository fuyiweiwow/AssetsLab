# chibi-base-mesh Blender Candidate Evaluation

## Decision

The candidate under `third_party/chibi-base-meshblender.zip` is the actual
downloaded model requested for the early technical test. It is not a
ready-made animated actor and is not approved as the current appearance
source. It remains useful only as a documented pipeline diagnostic until its
silhouette matches `front-character-anchor.png`.

The previous `neutral_chibi_actor_v1` was a body built from zero on GuideRig.
It is rejected and must not be used as evidence for this model. The later
AccuRIG actor renders and scale trials are also rejected as appearance
candidates; they are retained only as failure evidence.

## Audit result

The archive contains a nested Blender archive with:

- one primary `Cube` mesh;
- 534 vertices and 506 polygons;
- Mirror and Subsurf modifiers;
- one connected mesh component;
- no Armature;
- no vertex groups;
- no Action;
- no materials or portable face textures in the extracted source.

The audit output is stored at:

`prototype/assets/characters/generated/chibi_base_mesh_candidate_audit_v1/candidate_audit.json`

The static audit preview is rendered from the actual downloaded mesh. Its
purpose is orientation and topology review, not final art approval.

## Executed route

The first actual-model route kept the downloaded mesh as the visible actor,
imports the external KIIRA `Walk.fbx` only as a temporary motion source, and
removes the FBX source meshes before saving. Because the source mesh's original
transform is part of its usable orientation, the build uses
`--preserve-source-transform`.

Run it with:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\tools\build_chibi_base_mesh_actor.ps1
```

That v1 route exposed the face deformation: the continuous head/neck region
was assigned directly to external KIIRA bones. It is retained as the baseline
comparison, not the active candidate.

The improved v2 route separates the upper head before binding. Any source face
touching the head region is kept with the head, the head follows the torso
anchor as a rigid object, and only the remaining body receives experimental
rigid region weights. This prevents the face from being sheared by arm, leg,
or upper-body bones.

The v2 output is:

- actual-model actor scene:
  `prototype/assets/characters/generated/chibi_base_mesh_actor_v2/`;
- four-direction 256x256 review renders:
  `prototype/test_output/chibi_base_mesh_actor_v2_3d/`;
- four-direction 64x64 review sheet:
  `prototype/assets/characters/generated/chibi_base_mesh_actor_v2_pixels/chibi_base_mesh_pixel_sheet.png`;
- validation report:
  `prototype/assets/characters/generated/chibi_base_mesh_actor_v2/chibi_base_mesh_actor_v2_validation.json`.

## Current gate

The improved technical route passes 4 directions x 8 frames, 32 RGBA render
cells, 32 RGBA pixel cells, and source-model identification. It is still
review-only:

- the external Walk FBX is not vendored into the project;
- the head/body split is a generated working seam, not a finished retopology;
- the body still uses experimental rigid region binding;
- all 32 cells are one pixel above the current project foot-baseline target;
- no silhouette, part-ID, or depth passes have been exported;
- no face, hair, clothing, or Godot runtime layer has been approved.

Strict registration currently fails only on the known y=59 versus target y=60
baseline. The next implementation step is to author and inspect the neck seam
and body weights, not to return to the rejected from-scratch GuideRig body.

## Operator annotation execution

The Blender GUI was not used for the annotation step because it continued to
crash when opening both the helper scene and the mesh-only annotation scene.
The browser tool at `tools/chibi_binding_annotator.html` was used instead.
It displays front and side renders of the actual downloaded mesh and exports
horizontal region boundaries.

The completed annotation is:

`E:\comic\chibi_base_mesh_binding_lines.json`

The renderer consumes this JSON through `--binding-lines` and calibrates the
image Y coordinates against the actual source mesh bounds. The submitted
head/neck lines nearly coincide, so the implementation inserts a minimum 6 px
neck gap for a stable geometry threshold. The exact calibration is preserved
in `prototype/test_output/chibi_base_mesh_actor_manual_lines_v1_3d/manifest.json`.

The resulting annotated candidate is:

`prototype/assets/characters/generated/chibi_base_mesh_actor_manual_lines_v1/`

It passes the automated render-to-pixel checks. The front head silhouette is
stable through the sampled walk, but the tiny neck remains a visible working
seam and the body weights remain experimental. Keep this candidate in review
status until a manual seam/weight pass is accepted.

## Rigging tool decision

The manual-line result also confirmed severe deformation in the arms and legs,
not only the head. This means the main failure is a mismatched external
skeleton and bind pose, not merely an incomplete head boundary annotation.

The old tool research and operator guide described a rejected binding route and
machine-local paths, so they were removed from the active tree. This downloaded
mesh evaluation remains historical failure evidence only. The current 3D
baseline is `prototype/assets/characters/actor_v1/`; do not start another
AccuRIG candidate from this document.

The clean external-rigging upload package has been prepared at:

`prototype/assets/characters/generated/chibi_base_mesh_accurig_input_v3/chibi_base_mesh_accurig_input_v3.fbx`

Its manifest records the mesh counts, bounds, applied display modifiers, and
the fact that no armature or camera was included.

### Mirror correction

The first AccuRIG upload preview exposed an export-order bug. The vendor mesh
is a right-half mesh with a Mirror modifier. Centering the half mesh before
applying Mirror moved the mirror plane and produced two side-by-side copies.
Skipping Mirror produced only half a character. The corrected order is now:

1. load the original mesh without recentering;
2. apply Mirror at the vendor origin;
3. apply Subsurf;
4. recenter the completed mesh;
5. export the FBX.

The corrected v3 preview is stored at
`prototype/test_output/chibi_base_mesh_accurig_input_v3_preview/`. The earlier
v1 and v2 packages are invalid and must not be uploaded to AccuRIG.
