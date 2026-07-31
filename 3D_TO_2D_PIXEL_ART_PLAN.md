# 3D-Guided 2D Pixel Character Plan

## Decision

Use a hybrid **3D reference -> manual pixel cleanup -> layered runtime sprite**
pipeline. The 3D scene is an offline production tool only. Godot continues to
ship and animate fixed-size transparent 2D PNG layers; it does not render the
character model at runtime.

This is the right fit for the current 64 x 64 QQTang-style target. A direct
low-resolution 3D render is useful for repeatable poses, silhouette, limb
overlap, and lighting direction, but is too noisy and rigid to be the final
pixel art at this size. The final pixels remain intentionally authored.

The approach is established in production: Motion Twin described the *Dead
Cells* characters as 3D animation exported into a pixel-art style, while the
backgrounds remained hand-drawn. Blender provides orthographic cameras,
transparent film, non-filtered renders, and separate outline passes; Aseprite
can export the final tagged layers/frames as a sprite sheet.

Sources: [Motion Twin interview](https://www.nintendolife.com/news/2018/05/feature_reanimating_the_roguelike_with_dead_cells_developer_motiontwin),
[Blender film settings](https://docs.blender.org/manual/en/latest/render/cycles/render_settings/film.html),
[Blender Freestyle passes](https://docs.blender.org/manual/en/3.0/render/freestyle/view_layer.html),
[Aseprite CLI](https://www.aseprite.org/docs/cli/).

## Locked Production Contract

- Canvas: 64 x 64 transparent PNG per runtime frame.
- Directions and rows: `front`, `right`, `back`, `left`.
- Walk: eight frames per direction, retaining the accepted skeleton timing.
- Foot baseline: y=60 in the runtime frame; fixed origin and head/neck anchors.
- Runtime layers: `Feet`, `LowerBody`, `Arms`, `Torso`, `Head`, then optional
  `Face`, `Hair`, `Clothing`, and `Accessory` layers.
- The 3D output is never copied straight into the runtime atlas. It is stored
  as reproducible reference material with a pose manifest.

## Pipeline

1. **Create the 3D guide scene.**
   Build a deliberately plain low-poly mannequin in Blender: oversized head,
   torso, upper/lower arms, upper/lower legs, hands, and feet. Use one armature
   and separate material IDs for each future runtime layer. Do not model face,
   hair, or clothing yet.

2. **Lock camera and registration.**
   Create four orthographic cameras, one per direction. Their scale, target,
   head center, neck point, floor plane, and crop box are written to a JSON
   contract. Render at a larger integer multiple of the target (for example
   256 x 256) with a transparent background and no smoothing; downsampling is
   nearest-neighbor only.

3. **Transfer the accepted walk.**
   Key the eight existing skeleton poses onto the Blender rig. The old
   rectangle/skeleton contract remains the authority for leg identity,
   foreground order, arm counterphase, and contact frames. The rig is a visual
   guide, not a new source of motion.

4. **Bake reference passes.**
   For every direction/frame, export: transparent beauty render, flat
   silhouette, per-part ID masks, depth/order guide, and optional Freestyle
   outline. These passes make the front/back limb ordering inspectable instead
   of guessing from a single shaded image.

5. **Pixel-author the neutral base.**
   Import each eight-frame reference strip into Aseprite. On indexed palette
   layers, redraw a compact neutral mannequin using the silhouette and ID
   masks. Keep the 3D guide hidden in exports. First complete a front static
   frame, then the full front walk, then right/left, then back. Review at 1x
   and intended game scale after every direction.

6. **Split stable modular slots.**
   Once a direction reads correctly, separate the authored pixels into the
   runtime layers above. Each layer uses the same 64 x 64 registration box and
   carries only its own alpha. Clothing replaces/overlays `Torso`, `Arms`,
   `LowerBody`, and `Feet`; hair/face never shift the locked head.

7. **Export and integrate.**
   Export deterministic PNG sequences and a sheet/JSON manifest. The existing
   Godot pipeline imports the layers with nearest filtering, uses one shared
   frame index, and runs the current hidden movement capture.

## Gates and Acceptance

| Gate | Deliverable | Must pass before continuing |
| --- | --- | --- |
| G0 | 3D camera/anchor contract | Four cameras share the 64 x 64 crop, head/neck anchors, and y=60 floor. |
| G1 | Eight-frame 3D guide renders | Both legs and both arms visibly alternate; masks show correct limb ordering. |
| G2 | Front authored pixels | Loop has no pop, no foot sliding, and no same-side-only motion. |
| G3 | Right/left/back authored pixels | Left is a mirrored pose contract; back and front preserve the same head registration. |
| G4 | Neutral modular atlas | Every layer is 64 x 64, alpha-clean, and aligned across 32 direction/frame cells. |
| G5 | Godot capture | W/A/S/D GIF has nearest filtering, no layer drift, and correct direction mapping. |

## Implementation Order

1. Add the G0 Blender scene/template and `camera_contract.json`; render one
   four-direction static contact-pose sheet for review.
2. Add a headless Blender export script for G1 and a validator that compares
   the exported poses to the current skeleton anchors and limb-depth contract.
3. Produce and review only the front eight-frame neutral pixel base (G2).
4. Produce right/left/back in that order (G3), reusing the same palette and
   anchor contract.
5. Build the runtime layer atlas and run the existing Godot tests (G4-G5).
6. Only then add male/female presentation, face, hair, clothing, and random
   appearance variants.

## Non-Goals

- No generative image service is in the critical path.
- No runtime 3D character, 3D-to-2D shader, or automatic sprite conversion.
- No clothing/hair work before the neutral four-direction walk passes G5.
