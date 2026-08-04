# Actor V1 Build Log

## Purpose

This record documents the first reproducible attempt to turn the downloaded
static chibi mesh into an offline 3D generation actor. The actor is not a
runtime asset. The runtime target remains manually cleaned 2D PNG layers.

## Inputs audited

- `third_party/chibi-base-meshblender.zip`
  - Outer ZIP contains `source/chibi base mesh_BLENDER.zip`.
  - Inner blend contains one `Cube` mesh with 534 vertices and 506 polygons.
  - It contains no Armature, vertex groups, Armature modifier, or Action.
- `E:\env\temp\opencode\kiira_anim_pack\Walk.fbx`
  - Contains seven meshes, a 24-bone Armature, and one Action from frame 1 to
    frame 41 with 199 F-curves.
- `third_party/kiira_chibi/Character Base.blend`
  - Contains the related seven-part KIIRA mesh and a 19-bone weighted rig, but
    no animation Action.

## Binding decision

Use the original chibi mesh as the appearance candidate and the KIIRA/FBX rig
as the offline motion driver. The original mesh is assigned with rigid body
regions rather than Blender automatic weights:

- head: `Bone.010`;
- left/right arm chains: `Bone.002`–`Bone.004` and `Bone.006`–`Bone.008`;
- left/right leg chains: `Bone.012`–`Bone.014` and `Bone.016`–`Bone.018`;
- torso fallback: `Bone.009` and the remaining stable body groups.

The source head is scaled around the neck seam by `1.18`; the fitted body is
scaled by `0.86`. The imported FBX source meshes are removed from the saved
actor scene after the action is loaded. The actor keeps only the generated
appearance mesh, the motion rig, and the test action.

## Build command

Run from the project root with Blender 4.5:

```powershell
& 'E:\env\Blender\blender.exe' --background --python `
  'E:\WorkProject\AssetsLab\tools\blender\render_original_chibi_actor_test.py' -- `
  --source-blend 'E:\WorkProject\AssetsLab\third_party\chibi-base-meshblender.zip' `
  --walk-fbx 'E:\env\temp\opencode\kiira_anim_pack\Walk.fbx' `
  --render-dir 'E:\WorkProject\AssetsLab\prototype\assets\characters\generated\original_chibi_actor_test_v5' `
  --blend 'E:\WorkProject\AssetsLab\prototype\assets\characters\generated\original_chibi_actor_test_v5\original_chibi_actor_v5.blend' `
  --head-scale 1.18 --body-scale 0.86
```

The builder now accepts either a direct `.blend` file or the current nested
ZIP layout. The ZIP is extracted to a temporary directory and is not copied
into the project.

## Outputs

- 3D actor scene:
  `prototype/assets/characters/generated/original_chibi_actor_test_v5/original_chibi_actor_v5.blend`
- Eight transparent 256x256 front renders under the same directory.
- Actor manifest:
  `prototype/assets/characters/generated/original_chibi_actor_test_v5/manifest.json`
- Review-only nearest-neighbor 64x64 sheet:
  `prototype/assets/characters/generated/original_chibi_actor_pixel_v1/front_pixel_sheet.png`
- Pixel review manifest:
  `prototype/assets/characters/generated/original_chibi_actor_pixel_v1/manifest.json`

## Technical result

Passed:

- the nested model archive can be consumed automatically;
- the static mesh can be loaded into Blender;
- the Walk action drives the mesh through eight sampled frames;
- the saved actor contains an Armature, Action, vertex groups, and an
  Armature modifier on the generated mesh;
- all eight renders are RGBA 256x256 with transparency;
- nearest-neighbor 256-to-64 conversion completes deterministically;
- the sampled cycle visibly alternates the legs and changes arm phase.

Not yet accepted:

- the actor camera is still fitted to the animated union bounds, not the final
  G0 camera contract;
- no silhouette, part-ID, or depth passes have been produced for this actor;
- the body is still a technical neutral mannequin and needs visual proportion
  review at 64x64;
- the pixel sheet is review-only and requires manual cleanup;
- the Walk FBX remains an external input and is not yet vendored into the
  repository.

## G0 compatibility investigation

The first `v5` output used an animated-union review camera and was sufficient to
prove that the archive, action, binding, transparent render, and nearest-neighbor
pixelization steps can execute. It was not sufficient to prove project
registration.

Attempts `v6` through `v11` tested the fixed G0 camera and exposed three
incompatibilities:

1. the imported FBX actor has a different world-space scale and root offset;
2. moving the rig and mesh independently changes the Armature modifier's
   relative transform, so floor correction must use a shared `ActorRoot`;
3. the original `Cube` is one connected 534-vertex component, and its local
   proportions/topology do not line up with the KIIRA bone regions. A simple
   threshold or nearest-bone rigid bind produces visibly stretched limbs or a
   distorted head under the locked G0 camera.

The mesh topology audit is recorded by
`tools/blender/audit_mesh_components.py`: the source is one connected component,
so it cannot be cleanly separated into head, torso, arms, and legs without a
real retopology or manual vertex-region authoring pass.

Decision: `v5` remains a technical review artifact; `v6`–`v11` are rejected
fixed-camera experiments. No version is runtime-ready and no 3D face work
should begin yet.

## Rejected Q1 GuideRig prototype and test tool

This prototype used the project GuideRig rather than the downloaded mesh.
`tools/blender/create_q_guide_scene.py` builds a neutral,
featureless QQTang-style body with the accepted G1 eight-frame pose contract
and fixed four-direction cameras. This gives us a stable 3D actor for motion,
registration, and pixelization tests while keeping face, hair, and clothing
out of the body gate.

The first reproducible Q1 output is:

- scene: `prototype/assets/characters/generated/neutral_chibi_actor_v1/neutral_chibi_actor_v1.blend`;
- 3D review renders: `prototype/test_output/neutral_chibi_actor_v1_3d/`;
- 64x64 review sheet and manifest:
  `prototype/assets/characters/generated/neutral_chibi_actor_v1_pixels/`;
- validation report:
  `prototype/assets/characters/generated/neutral_chibi_actor_v1/neutral_chibi_actor_v1_validation.json`.

The test entry point is:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\tools\build_neutral_chibi_actor.ps1
```

It builds the scene, performs deterministic nearest-neighbor 256-to-64
pixelization, and checks 4 directions x 8 frames, 32 RGBA render cells, 32
RGBA pixel cells, and manifest consistency. The full tool procedure is in
`NEUTRAL_CHIBI_ACTOR_TESTING.md`.

The Q1 run passes the technical pipeline. It currently emits 32 non-blocking
warnings because the validator reports a foot baseline of y=59, with the last
occupied pixel at y=58, instead of the target bbox end y=60. `-Strict`
intentionally fails until that shared registration difference is corrected.
This is the next actor revision gate; the Q1 output is not yet runtime art.

## Next gate

Correct the Q1 registration before spending time on face variants:

1. move the Q1 actor's shared floor/scale registration so the strict baseline
   check passes;
2. review front animation at 64x64 for alternating legs, opposite arm swing,
   and stable head anchor;
3. then export silhouette, part-ID, depth/order, and beauty passes;
4. only after those gates pass, begin modular face generation.

The original chibi archive is now handled by the separate actual-model
evaluation below. The rejected Q1 GuideRig body is not silently promoted to
the production actor.

## Correction and actual-model execution — 2026-08-01

The GuideRig Q1 mannequin described above was built from zero and is now
explicitly rejected as a production actor. It is retained only as a generic
camera/pixelization test fixture.

The user-requested `third_party/chibi-base-meshblender.zip` was audited
independently and then used for a new model-specific test. The new route keeps
the downloaded `Cube` mesh visible, imports `Walk.fbx` only for its temporary
motion rig/action, preserves the source transform, and exports four camera
directions x eight sampled frames. Its artifacts and acceptance state are
recorded in `CHIBI_BASE_MESH_EVALUATION.md`.

The actual-model build passed the technical render-to-pixel checks, but it is
not runtime-ready. Its remaining gates are model-specific binding quality,
camera registration, and manual silhouette review. No random 3D face work
should be attached to the rejected GuideRig mannequin.

## Head binding correction — v2

The v1 actual-model test showed severe face/neck deformation because the
continuous source mesh assigned head/seam vertices directly to external
character bones. The v2 test applies a better first strategy:

1. apply the source Mirror/Subsurf display modifiers;
2. classify any face touching the head height as part of the head;
3. make the upper head a separate rigid object;
4. parent that object to the torso anchor `Bone.009`;
5. bind only the remaining body mesh to the temporary Walk rig.

The v2 output is under
`prototype/assets/characters/generated/chibi_base_mesh_actor_v2/`. Its front
head silhouette remains stable across the sampled walk frames, so it is the
current technical candidate. The split creates a visible neck seam and the
body weights remain experimental; do not call it runtime-ready yet.

## Manual binding-line execution — 2026-08-01

Because the Blender GUI continued to crash even when opening a mesh-only
annotation scene, the browser annotator was used as the operator-facing
fallback. The user completed the front and side horizontal region annotation
and supplied:

`E:\comic\chibi_base_mesh_binding_lines.json`

The submitted head-bottom and neck-bottom lines were only about 1 px apart.
That is consistent with this model's extremely short visible neck, but it is
too small to be a stable pixel-to-mesh boundary. The renderer therefore
preserved the submitted head line and normalized the neck gap to 6 px. This
adjustment is recorded as `neck_gap_adjusted: true` in the generated manifest;
it is not an unrecorded change to the user's annotation.

The model-specific execution produced:

- actor scene:
  `prototype/assets/characters/generated/chibi_base_mesh_actor_manual_lines_v1/`;
- 3D review renders:
  `prototype/test_output/chibi_base_mesh_actor_manual_lines_v1_3d/`;
- 64x64 review sheet:
  `prototype/assets/characters/generated/chibi_base_mesh_actor_manual_lines_v1_pixels/chibi_base_mesh_pixel_sheet.png`;
- validation report:
  `prototype/assets/characters/generated/chibi_base_mesh_actor_manual_lines_v1/chibi_base_mesh_actor_manual_lines_v1_validation.json`.

Technical acceptance passed: 4 directions x 8 frames, 32 RGBA renders, 32
pixel cells, and source-model identity. Visual acceptance remains pending:
the head is stable, while the nearly absent neck produces a visible seam and
the body binding still needs manual refinement. This is now the preferred
annotated candidate for the next binding experiment; it is not runtime-ready.
## 清理说明（2026-08-02）

KIIRA 外部模型及其 Q2/Q3 试拍脚本已从工作树移除。这里保留的内容仅作为历史决策记录；不要再按照其中的 KIIRA 路线执行。当前基线改为真实演员的运行时四方向像素资源包，详见 `docs/PROJECT_STATUS_2026-08-02.md`。
