# Chibi Eyes and Ears Pixel Runtime Test

> 历史技术基线测试（2026-08-03）。结果只适用于 `chibi_eyes_ears_walk_v1`，不代表当前 Actor V1 的最终像素质量。

## Validated asset

- Source actor: `prototype/assets/characters/generated/chibi_eyes_ears_pixel_walk_source_v1.blend`
- Runtime package: `prototype/assets/characters/runtime/chibi_eyes_ears_walk_v1/`
- Directions and frames: four directions, eight walk frames each, 64 x 64 pixels per frame.

The actor combines the previously verified 3D eye package and chibi ear attachment.  Eyes are vertically scaled by 1.45; ears use a 0.72 size multiplier.  Eye vertical position remains a later random-feature-tool adjustment and is not changed in this validation run.

The horizontal runtime mapping is deliberate: the Blender `right` camera sees the actor's left-facing image and the Blender `left` camera sees the actor's right-facing image.  The Godot player therefore maps screen-right input to the `left` asset folder and screen-left input to `right`.

## Rendering rule

The walk render uses EEVEE Next without Freestyle.  Freestyle outlines the rectangular eye mesh and creates a false black sticker border after pixelization.

## Verification

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_pixel_runtime_godot_test.ps1
powershell -ExecutionPolicy Bypass -File .\tools\capture_walk_gif.ps1 -PixelRuntimeActor
```

The Godot test forces an asset import pass before validation so replacing a runtime sprite folder cannot reuse stale imported textures.  Success markers are `PIXEL_RUNTIME_GODOT_TEST_PASS tests=5` and `PIXEL_RUNTIME_CAPTURE_PASS directions=4 frames=32`.
