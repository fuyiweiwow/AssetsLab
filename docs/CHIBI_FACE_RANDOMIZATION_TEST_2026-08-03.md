# Chibi Face Randomization Test (2026-08-03)

> 历史五官随机化候选测试（2026-08-03）。当前 Actor V1 的眼睛贴图已随 Blend 发布；只有完成独立 Face 层导出后，本文候选才可能重新评估。

## Scope

This is the first constrained 3D face-style generator for the verified
`chibi_eyes_ears_pixel_walk_source_v1.blend` actor.  It does not replace the
runtime package and does not alter the accepted ear attachment.

The design reuses the useful part of the earlier Bombo Adventure 2D experiment:
facial components remain independently authored and every direction/frame is
rendered on the same canvas.  It does **not** copy Bombo atlas assets or its
2D runtime composition into the 3D actor pipeline.

## Generator contract

`tools/blender/render_accurig_chibi_walk_test.py` now accepts:

```text
--appearance-seed=<integer>
--face-style=<0..3>
```

The seed uses a BLAKE2b integer mapping so the selected style is stable across
runs.  The explicit style option is only for review and overrides seed
selection.  Each style is a bounded `EyeStyleBundle`:

| Id | Name | Controlled changes |
| --- | --- | --- |
| 0 | `classic` | baseline eye geometry and low-arch brows |
| 1 | `bright_tall` | slightly taller/raised eyes and high-arch brows |
| 2 | `soft_round` | wider/taller eyes and round brows |
| 3 | `focused` | narrower/raised eyes and flatter angled brows |

The eye package is adjusted by copying its meshes and transforming vertices in
world X/Z around each eye's own bounds.  This preserves the established
`CC_Base_Head` attachment.  Brows are independent curves parented to the same
head bone.  Ears remain `locked_verified_attachment`; ear randomization is a
later, separate stage.

## Review output

Four seeds cover all first-pass styles:

| Seed | Style |
| --- | --- |
| 20260802 | classic |
| 20260807 | bright_tall |
| 20260800 | soft_round |
| 20260803 | focused |

The preview output is intentionally static (two frames rendered per direction)
because this test evaluates facial fit, not the still-procedural walk cycle:

- `prototype/test_output/face_randomization_v1/face_randomization_contact_sheet.png`
- `prototype/test_output/face_randomization_v1/face_randomization_manifest.json`

`tools/build_chibi_face_variant_contact_sheet.py` validates 64x64 source
frames, unique style ids, and writes the phone-readable comparison sheet.

## Validation

- All four seeds rendered four directions and two frames, then passed nearest
  neighbour 64x64 processing.
- The contact-sheet builder passed with four unique styles.
- Existing runtime regression passed:
  `PIXEL_ASSET_END_TO_END_PASS package=1 godot=1 integration=1 appearance=1`.

## Re-run

Use the batch entry point to rebuild the disposable static review output.  It
only permits deletion below `prototype/test_output`, renders the four coverage
seeds, creates 64px frames, builds the contact sheet, and checks that every
style is represented exactly once:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\tools\run_chibi_face_randomization_preview.ps1
```

The current output is
`prototype/test_output/face_randomization_v2/`.  The validator is also
available independently:

```powershell
python .\tools\validate_chibi_face_randomization.py `
  --root .\prototype\test_output\face_randomization_v2
```

Create the dependency-free mobile gallery after a preview run:

```powershell
python .\tools\build_chibi_face_randomization_gallery.py `
  --root .\prototype\test_output\face_randomization_v2
```

It writes `gallery.html` next to the preview manifest and uses relative image
paths, so the same static preview server can expose it without a Godot GUI or
web build step.

## Next decision

Review the four face-style candidates before promoting one or more styles to
the runtime/export layer.  Hair must remain a separate head-anchor layer so it
can mask or reveal ears without changing face seed selection.
