# Chibi Manual Binding Assistant

The downloaded model is a single continuous mesh. Automatic weights cannot
reliably infer the intended head/neck seam, so the next binding pass accepts a
small amount of manual annotation from the user.

## If the helper scene crashes Blender

Use the mesh-only fallback. It contains only the downloaded mesh and three
empty vertex groups: no cameras, no armature, and no modifiers.

Open:

`E:\WorkProject\AssetsLab\prototype\assets\characters\generated\chibi_base_mesh_annotation_only.blend`

In this fallback, skip the bone-moving section. Assign only
`Bind_Head`, `Bind_Neck`, and `Bind_Torso`, then save as:

`E:\WorkProject\AssetsLab\prototype\assets\characters\generated\chibi_base_mesh_annotation_only_annotated.blend`

Export with:

```powershell
& 'E:\env\Blender\blender.exe' --background --python `
  'E:\WorkProject\AssetsLab\tools\blender\export_chibi_mesh_groups.py' -- `
  --blend 'E:\WorkProject\AssetsLab\prototype\assets\characters\generated\chibi_base_mesh_annotation_only_annotated.blend' `
  --output 'E:\WorkProject\AssetsLab\prototype\assets\characters\generated\chibi_base_mesh_groups.json'
```

The fallback was verified in Blender background mode with exactly one mesh
object and zero modifiers. If even this file crashes, the problem is almost
certainly the local Blender installation or graphics driver rather than the
scene contents.

## If all Blender files crash: browser annotation fallback

You can avoid the Blender interface completely. Open this file in a normal
browser:

`E:\WorkProject\AssetsLab\tools\chibi_binding_annotator.html`

The page shows the real model in front and side views. Drag the three colored
horizontal lines:

- red: bottom of the head, including the chin/jaw; this is not the back of the skull;
- yellow: bottom of the neck transition;
- blue: bottom of the torso, above the legs.

The region between the red and yellow lines is the neck. If the model has an
almost nonexistent neck, a 5–10 pixel gap is enough. Do not enlarge the neck
region by including the shoulders.

Do not try to make the lines pixel-perfect. The front and side views only need
to agree on the broad head/neck/body regions. Click `下载标注 JSON`, then place
the downloaded `chibi_base_mesh_binding_lines.json` in:

`E:\WorkProject\AssetsLab\prototype\assets\characters\generated\`

This gives me the manual boundaries without requiring Blender to open. I can
then map the source mesh vertices to those boundaries in background Blender and
continue the binding automatically.

## Create the assistant scene

Run from the project root:

```powershell
& 'E:\env\Blender\blender.exe' --background --python `
  'E:\WorkProject\AssetsLab\tools\blender\create_chibi_binding_assistant.py' -- `
  --source 'E:\WorkProject\AssetsLab\third_party\chibi-base-meshblender.zip' `
  --blend 'E:\WorkProject\AssetsLab\prototype\assets\characters\generated\chibi_base_mesh_binding_assistant_safe.blend' `
  --manifest 'E:\WorkProject\AssetsLab\prototype\assets\characters\generated\chibi_base_mesh_binding_assistant_safe.json' `
  --safe
```

Open the generated `.blend` in Blender. The model is named
`ChibiBaseMesh_ANNOTATE`; the helper armature is
`ChibiManualBindingRig`.

## What to annotate

You only need to provide two kinds of information:

1. vertex groups on the mesh;
2. approximate bone positions in Armature Edit Mode.

In Edit Mode on `ChibiBaseMesh_ANNOTATE`, enable X-Ray and assign selected
vertices to these groups:

`Bind_Head`, `Bind_Neck`, `Bind_Torso`, `Bind_Arm_L`, `Bind_Arm_R`,
`Bind_Leg_L`, `Bind_Leg_R`.

The only required groups are `Bind_Head`, `Bind_Neck`, and `Bind_Torso`.
The arm and leg groups are optional and can be rough; do not spend time
painting smooth weights. Use the front and side views to make sure the head
group includes the whole face and jaw, while the neck group contains only the
transition ring. If selecting the limbs is tedious, leave those four groups
empty and I will derive an initial body binding from the annotated torso.

In Armature Edit Mode, move these guide bones so they match the actual model:

- `BindHead`: center inside the head volume;
- `BindNeck`: head at the neck seam and tail toward the head center;
- `BindSpine`: torso center;
- `BindArm_L/R` and `BindLeg_L/R`: approximate limb center lines.

The helper bones are guides only. They do not deform the model in this scene.
Save the annotated file when finished.

## Export the annotation

```powershell
& 'E:\env\Blender\blender.exe' --background --python `
  'E:\WorkProject\AssetsLab\tools\blender\export_chibi_binding_annotation.py' -- `
  --blend 'E:\WorkProject\AssetsLab\prototype\assets\characters\generated\chibi_base_mesh_binding_assistant.blend' `
  --output 'E:\WorkProject\AssetsLab\prototype\assets\characters\generated\chibi_base_mesh_binding_annotation.json'
```

Send me the resulting `chibi_base_mesh_binding_annotation.json` or tell me
that it is saved in the path above. I can then generate a model-specific
binding scene from the exact groups and bone anchors instead of guessing from
height thresholds.

## Beginner walkthrough for Blender 4.5

### 1. Open the helper scene

1. Start Blender.
2. Choose `File > Open`.
3. Open:

   `E:\WorkProject\AssetsLab\prototype\assets\characters\generated\chibi_base_mesh_binding_assistant_safe.blend`

4. If Blender asks whether to save the current file, choose `Don't Save`.
5. Do not open or edit `third_party/chibi-base-meshblender.zip` directly.

The large central area is the 3D Viewport. The list in the upper-right is the
Outliner. The vertical strip of icons on the right is the Properties editor.

### 2. Learn the basic viewport controls

If your mouse has a middle button:

- hold the middle button and drag to orbit;
- hold `Shift` plus the middle button and drag to pan;
- use the mouse wheel to zoom.

Useful view shortcuts:

- `Numpad 1`: front view;
- `Numpad 3`: right-side view;
- `Numpad 7`: top view;
- `Home`: frame all objects;
- `Numpad .`: frame the selected object;
- `Alt+Z`: toggle X-Ray, which lets you select vertices through the model;
- `Tab`: switch between Object Mode and Edit Mode.

If your keyboard has no numpad, use the viewport menu `View > Viewpoint >
Front` or `Right` instead. If the model is too small, select it in the
Outliner and press `Numpad .` or choose `View > Frame Selected`.

### 3. Select the mesh and enter vertex selection

1. In the Outliner, click `ChibiBaseMesh_ANNOTATE`.
2. Move the mouse into the 3D Viewport and press `Tab`.
3. At the top-left of the viewport, choose vertex select mode. It is the icon
   with one dot; the shortcut is `1` (the number-row key, not numpad `1`).
4. Press `Alt+Z` to enable X-Ray.
5. Press `Alt+A` to deselect everything.

Do not press `A` unless you intentionally want to select every vertex. Do not
delete vertices, dissolve edges, apply modifiers, or move the mesh itself.

### 4. Assign the head group

The head group is the most important one. It must include the entire large
head, face, cheeks, jaw, and the lower head edge. It must not include the
shoulders or torso.

1. Use `Numpad 1` for the front view.
2. Press `B` and drag a rectangle around only the head and jaw. With X-Ray on,
   this selects the front and back vertices together.
3. Orbit to the side with `Numpad 3` and check that the back of the head is
   also selected. Add missing vertices with `B` or `C` (Circle Select).
4. In the Properties editor, click the green triangle Object Data icon.
5. Find the `Vertex Groups` panel and select `Bind_Head`.
6. Click `Assign`.

The head group should be one connected region. It is better to include a
small amount of the lower jaw in the head group than to leave a strip of face
vertices in the body group.

### 5. Assign the neck group

The neck group should be a narrow transition between the head and torso. It
is not the whole upper body.

1. Press `Alt+A` to deselect.
2. In front view, use `B` or `C` to select the narrow neck/connection ring
   directly below the head.
3. Check the same selection in right-side view.
4. Select `Bind_Head` in the Vertex Groups panel and click `Remove` so the
   neck vertices do not remain in both groups.
5. Select `Bind_Neck` and click `Assign`.

If selecting the exact ring is difficult, select a slightly wider transition
area. Do not include the arms.

### 6. Assign the torso group

1. Press `Alt+A`.
2. Select the chest, abdomen, and pelvis, excluding the head, neck, arms, and
   legs.
3. Select `Bind_Torso` and click `Assign`.

Only `Bind_Head`, `Bind_Neck`, and `Bind_Torso` are required. You may leave
the four limb groups empty for the first pass. The exporter will report them as
optional rather than failing.

### 7. Move the guide bones

1. Press `Tab` to leave mesh Edit Mode.
2. In the Outliner, click `ChibiManualBindingRig`.
3. Move the mouse into the viewport and press `Tab` again.
4. The orange/black guide bones should be visible through the mesh.
5. Select and move these bones with `G`:

   - `BindHead`: place its middle inside the head volume;
   - `BindNeck`: place it across the head/neck connection;
   - `BindSpine`: place it vertically through the torso center.

Keep the bones roughly vertical. They are guides for my next script, not a
finished rig. The arm and leg guide bones can remain at their initial rough
positions. If a bone is hard to click, use X-Ray and orbit to the side.

### 8. Save the annotated file

Use `File > Save As` and save it as:

`E:\WorkProject\AssetsLab\prototype\assets\characters\generated\chibi_base_mesh_binding_annotated.blend`

This keeps the original helper scene unchanged. If Blender asks about saving
external files, keep the default project-relative save choice.

### 9. Export and check the annotation

Open PowerShell and run:

```powershell
& 'E:\env\Blender\blender.exe' --background --python `
  'E:\WorkProject\AssetsLab\tools\blender\export_chibi_binding_annotation.py' -- `
  --blend 'E:\WorkProject\AssetsLab\prototype\assets\characters\generated\chibi_base_mesh_binding_annotated.blend' `
  --output 'E:\WorkProject\AssetsLab\prototype\assets\characters\generated\chibi_base_mesh_binding_annotation.json'
```

The successful result should contain:

```text
CHIBI_BINDING_EXPORT_PASS required_groups=3
```

The earlier `chibi_base_mesh_binding_annotation_empty.json` is only an empty
tool test and should be ignored.
