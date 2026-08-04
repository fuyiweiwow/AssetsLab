# REJECTED: Neutral Chibi Actor Testing

> This is a rejected from-scratch GuideRig prototype. It is not the downloaded
> `chibi-base-meshblender` model and must not be treated as the production
> actor.

## Purpose

This document records a reproducible test tool for a neutral, featureless
QQTang-style chibi body built from zero on the project GuideRig. The user-
requested downloaded model was not used in this build. The output is retained
only to test camera contracts, rendering, pixelization, and validation.

## One-command build and validation

Run from the repository root:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\tools\build_neutral_chibi_actor.ps1
```

The explicit `ExecutionPolicy Bypass` form is the portable invocation for
machines where local `.ps1` execution is restricted. To build a named test
copy:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\tools\build_neutral_chibi_actor.ps1 `
  -OutputName neutral_chibi_actor_tool_test
```

The wrapper performs these stages in order:

1. Blender builds a four-direction, eight-frame-per-direction neutral actor
   using the accepted camera and pose contracts.
2. Python downsamples the 256x256 transparent beauty renders to 64x64 with
   nearest-neighbor sampling and writes a contact sheet.
3. Python validates the scene, manifests, render count, image sizes, alpha,
   direction count, frame count, and foot-baseline registration.

## Outputs

For the default name, the important outputs are:

- 3D scene and pose manifest:
  `prototype/assets/characters/generated/neutral_chibi_actor_v1/`
- 256x256 render review tree:
  `prototype/test_output/neutral_chibi_actor_v1_3d/`
- 64x64 pixel review output:
  `prototype/assets/characters/generated/neutral_chibi_actor_v1_pixels/`
- machine-readable validation report:
  `prototype/assets/characters/generated/neutral_chibi_actor_v1/neutral_chibi_actor_v1_validation.json`

The pixel output is still a review/reference asset, not final runtime art.
Manual pixel cleanup and layer separation remain later gates.

## Validation modes

The default validator accepts the current one-pixel foot-baseline tolerance:

```powershell
python .\tools\validate_neutral_chibi_actor.py `
  --render-dir .\prototype\test_output\neutral_chibi_actor_v1_3d `
  --pixel-dir .\prototype\assets\characters\generated\neutral_chibi_actor_v1_pixels `
  --blend .\prototype\assets\characters\generated\neutral_chibi_actor_v1\neutral_chibi_actor_v1.blend `
  --pose-3d .\prototype\assets\characters\generated\neutral_chibi_actor_v1\neutral_chibi_actor_v1_pose_3d.json `
  --report .\prototype\assets\characters\generated\neutral_chibi_actor_v1\neutral_chibi_actor_v1_validation.json
```

Use strict mode when the baseline is expected to be fully corrected:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\tools\build_neutral_chibi_actor.ps1 -Strict
```

Strict mode currently fails intentionally: all 32 Q1 cells report a foot
baseline of y=59, with the last occupied pixel at y=58, rather than the target
bbox end y=60. The default mode reports this as a warning so the rest of the
render/pixel pipeline can be reviewed. The next actor revision should correct
this shared baseline before runtime integration.

## Current acceptance result

The tool was run successfully on 2026-08-01:

```text
NEUTRAL_CHIBI_ACTOR_PASS directions=4 frames=8 renders=32 pixels=32 warnings=32
```

This proves only that the generic Q1 test route is reproducible. It does not
prove that the downloaded model is rigged, and it does not approve final pixel
art, clothing, hair, face variants, or Godot integration.

## Related tools and contracts

- Build scene: `tools/blender/create_q_guide_scene.py`
- Pixelize: `tools/process_q_guide_pixels.py`
- Validate: `tools/validate_neutral_chibi_actor.py`
- One-click wrapper: `tools/build_neutral_chibi_actor.ps1`
- Camera contract:
  `prototype/assets/characters/generated/skeleton_walk_pipeline_v1/3d_guide_v1/camera_contract.json`
- Pose contract:
  `prototype/assets/characters/generated/skeleton_walk_pipeline_v1/3d_guide_v1/g1_pose_contract.json`
