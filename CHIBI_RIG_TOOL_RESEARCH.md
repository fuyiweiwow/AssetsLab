# Chibi Rigging Tool Research

Date: 2026-08-01

AccuRIG installation was completed at `E:\env\AccuRIG` and verified as
version `2.1.0.584`. The detailed operator procedure is in
`CHIBI_ACCURIG_BEGINNER_GUIDE.md`.

## Problem confirmed

The downloaded `chibi-base-meshblender.zip` contains a single unrigged mesh
with no armature, vertex groups, or action. The current test directly assigned
body regions to the external KIIRA armature. That is not true animation
retargeting, and it explains the severe deformation in the head, arms, and
legs: the source skeleton proportions and bind pose do not match the chibi
mesh.

The next test must create or generate a skeleton that matches the downloaded
mesh first. Only after that should the Walk action be retargeted.

## Tool comparison

### 1. AccuRIG — first choice

AccuRIG is a standalone guided auto-rigging application. Its official product
documentation specifically covers oversized heads, obstructed shoulders,
atypical limbs, joint placement, skin-weight distribution, and joint masking.
It exports FBX or USD for Blender and other tools.

Why it fits this model:

- it does not require opening the crashing Blender GUI for the rigging step;
- it allows the operator to correct the joint positions in a guided interface;
- it is designed to handle exaggerated cartoon proportions better than a
  naive bone-proximity assignment;
- it gives us a real target skeleton before retargeting animation.

Official references:

- https://www.reallusion.com/auto-rig/accurig/default.html
- https://manual.reallusion.com/AccuRig-2/2.0/09-add-motions/export.htm

### 2. Rigify — Blender fallback

Rigify is built into Blender and generates a control rig from a manually
positioned metarig. It is appropriate when the operator can place bones in
front and side views, but it still requires Blender GUI interaction. Blender's
documentation notes that automatic weights depend on correct bone placement
and sufficient mesh topology.

It remains a good later option if the Blender crash is resolved, but it is not
the safest next step for this project.

Official references:

- https://docs.blender.org/manual/en/4.0/addons/rigging/rigify/index.html
- https://docs.blender.org/manual/en/4.4/addons/rigging/rigify/basics.html

### 3. Mixamo — low-priority fallback

Mixamo uses operator markers for wrists, elbows, knees, and groin, then can
apply its animation library. However, Adobe documents that strongly deformed
proportions may fail, and the service has regional/account restrictions. This
chibi has an oversized head and unusually short limbs, so it is useful only as
a quick experiment if the service is available.

Official references:

- https://helpx.adobe.com/creative-cloud/help/mixamo-rigging-animation.html
- https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html

### 4. Rokoko Studio — animation retargeting option

Rokoko is mainly useful after a target skeleton already exists. Its Blender
plugin supports source-armature to target-armature retargeting and requires
both rigs to use the same pose for reliable results. It does not solve the
initial model-specific rigging problem by itself.

Official references:

- https://support.rokoko.com/hc/en-us/articles/4410463481489-Retargeting-an-animation-in-Blender-Plugin-1-1-and-above
- https://www.rokoko.com/products/studio

## Decision

Use AccuRIG for the first external rigging experiment. Do not spend more time
adding 2D region lines to the current direct KIIRA binding; those annotations
can help segmentation, but they cannot correct a mismatched skeleton and bind
pose.

## Next-step test protocol

1. Export a clean neutral FBX or OBJ from the downloaded mesh: one visible
   mesh, centered, no camera, no armature, Mirror applied, Subsurf applied or
   deliberately preserved as a modifier only if the external tool accepts it.
2. Open the mesh in AccuRIG and correct the center line and body joints in the
   front and side views.
3. Pay special attention to head, neck, shoulder, elbow, wrist, hip, knee,
   ankle, and toe placement. Use the preview animation before export.
4. Export a rigged FBX with the bind/rest pose included.
5. Bring that FBX back into the background Blender pipeline. Do not open the
   GUI. First render the rest pose, then test small isolated motions: head,
   left arm, right arm, left leg, and right leg.
6. Only if those isolated tests pass, retarget the Walk action and run the
   existing 4-direction x 8-frame render-to-pixel validation.

The clean upload package is now prepared by
`tools/blender/export_chibi_mesh_for_accurig.py`:

`prototype/assets/characters/generated/chibi_base_mesh_accurig_input_v3/chibi_base_mesh_accurig_input_v3.fbx`

Its manifest confirms that it contains one neutral mesh, no armature, no
camera, and no external animation. The exported mesh has the source Mirror
and Subsurf display geometry applied in the correct order: the vendor file is
first treated as a right-half mesh, Mirror is applied at its original plane,
and only then is the completed model centered. This avoids the duplicate
left/right body seen in the earlier upload package.

The current manually annotated candidate remains useful as a visual baseline,
but it is not the next production binding path.

## Q 版动画素体参考候选（2026-08-01）

当前最适合用来重新检查膝盖、脚踝和脚掌关系的参考是：

### Low-Poly Chibi Base — der Mondhase

https://dermondhase.itch.io/low-poly-chibi-base

该资源体量很小，页面说明包含 204 个顶点、213 个面，已经绑定并包含 `Walk` 与 `Wave` 两个动画，同时提供 `.blend` 和 `.fbx`。它的比例和我们当前角色更接近，适合观察“没有明显膝盖外形时，膝盖骨骼实际应该放在哪里”。下载后应同时保留压缩包内的许可证文件。

### Chibi Batgirl — Ninesss

https://ninesss.itch.io/chibi-batgirl-free-3d-model-cc-by

该资源包含绑定模型和简单动画，骨骼名称使用英文，适合做第二个 Q 版动画参考；许可证为 CC-BY，若用于游戏成品需要保留作者署名。

### Quaternius RPG Character Pack

https://quaternius.com/packs/rpgcharacters.html

该资源不是严格的 chibi，但包含 6 个带绑定、动画和材质的角色，并提供 FBX、Blend、glTF 等格式，官方页面标注为 CC0。它适合用来确认标准的 `Thigh → Calf → Foot` 链条、脚掌长度和正常 Walk 的支撑脚阶段。

### 参考使用规则

不要直接复制参考角色的骨骼坐标或权重。应先在参考模型的 Walk 动画中观察：

1. 膝盖位于大腿和小腿的真实转折轴心，而不是轮廓上的膝盖凸起；
2. 脚踝位于小腿末端，脚掌骨向前延伸；
3. 支撑脚基本保持稳定，摆动脚先抬起再落下；
4. 头部、躯干和骨盆不会因为膝盖弯曲而被拉长。

下一次重新标定当前模型时，以第一个 `Low-Poly Chibi Base` 的结构作为主要参考，以 Quaternius 角色作为标准人形动作对照。参考模型只用于判断骨骼位置和动作逻辑，不直接替代当前模型的绑定。

### 已下载参考文件与比例检查

参考文件已下载到：

`E:\comic\reference_models\LowPolyChibiBase\extracted\`

其中包含：

- `derMondhase_LowPolyChibiBase.blend`；
- `derMondhase_lowPolyChibiBase.fbx`；
- `Walk.gif`；
- `LICENSE.txt`。

用 `tools/blender/compare_leg_reference.py` 对比当前导出的 FBX 后，得到：

- 参考素体膝盖位于髋部到脚踝距离的 50.0% 处；
- 当前角色的 AccuRIG 膝盖位于 60.2% 处，更靠近脚踝；
- 当前角色的髋到膝距离为 32.23，膝到脚踝为 21.30，比例明显不均衡。

这不是单凭比例就能证明绑定必错，因为两个模型的体型不同；但结合当前膝盖弯曲异常、脚掌不明显和 Walk 动作不自然，下一轮应优先把当前 `Knee` 向腿部中点方向上移约 10% 的腿长，再重新导出测试。不要先改头部或删除膝盖。

### 无膝盖诊断副本

为验证问题是否确实来自膝盖相关权重，已从当前导出的 FBX 创建独立副本：

- `E:\comic\chibi_base_mesh_accurig_rigged_no_knee_test.fbx`；
- `E:\comic\chibi_base_mesh_accurig_rigged_no_knee_test.blend`；
- 测试图：`E:\WorkProject\AssetsLab\prototype\test_output\accurig_no_knee_test\`。

该副本把大腿、小腿和小腿扭转骨骼的权重合并到大腿骨，并让脚部保留为末端骨骼。结果是：膝盖处的局部折叠明显减少，但整条腿变成一根刚性摆杆，无法产生真正的小腿弯曲。因此它适合作为诊断，不适合作为最终角色绑定。

结论：不建议永久移除膝盖。更合理的下一版是保留膝盖，但把它从当前约 60.2% 的位置调整到髋部—脚踝中点附近，并继续把 `Toe` 保持为已解决的独立问题。

### “向前迈步时膝盖向后顶”的原因分析

当前现象更像是腿部弯曲平面/方向错误，而不是 `Toe` 问题：

1. 当前导出骨架的膝盖约在腿长的 60.2% 处，参考 Q 版素体约为 50.0%，膝盖过低会让摆腿时的折点落在错误位置；
2. 当前 `CC_Base_L_Calf` 的局部 X 轴确实是侧面前后摆动轴，正负旋转会产生相反的膝盖方向；如果 Walk 重定向使用了相反符号，就会出现向前迈步、膝盖却向后折的现象；
3. 当前模型膝盖位置位于腿的后侧或不在腿部体积中心时，自动绑定会进一步放大这个方向错误；
4. 无膝盖副本能消除局部折叠，但代价是整条腿变成刚性摆杆，这说明膝盖相关权重参与了异常，却不能证明膝盖本身应该删除。

下一轮绑定的修正顺序：

1. 在 AccuRIG `Rig Body` 侧面视图，把 `Knee` 放到髋部—脚踝中点附近；
2. 在正面视图把它保持在腿部中心，在侧面深度上略偏向角色前方，而不是贴后侧轮廓；
3. 保留 `Knee`，继续使用已经解决的 `Toe` 设置；
4. 在 `Calibrate` 中先用小角度分别测试左右小腿正、反两个方向，再播放 Walk；
5. 如果两个膝盖都反向，优先修正骨骼轴/动作方向；如果只有一侧反向，优先检查该侧标记和权重。

### 中点膝盖副本测试结果

已生成中点膝盖测试副本：

- `E:\comic\chibi_base_mesh_accurig_rigged_mid_knee_test.fbx`；
- `E:\comic\chibi_base_mesh_accurig_rigged_mid_knee_test.blend`；
- `E:\WorkProject\AssetsLab\prototype\test_output\accurig_mid_knee_direction_test\`；
- `E:\WorkProject\AssetsLab\prototype\test_output\accurig_mid_knee_walk_test\`。

该副本把左右膝盖从约 60.2% 移到 50.0%，但正负方向测试仍然表现出相同的前后弯曲特征，改善幅度有限。这说明“膝盖过低”是问题之一，但“向前迈步时反向弯折”的主因更可能是 `Calf` 局部轴/骨骼滚转或 Walk 动作重定向符号，而不是单纯的高度位置。

### 大腿不动：权重审计与重加权诊断（2026-08-01）

用户观察到“走路时大腿完全没动”后，对原始 AccuRIG FBX 执行了直接骨骼权重审计。结果确认：左右 `CC_Base_L_Thigh`、`CC_Base_R_Thigh`、左右 `Calf` 和左右 `Foot` 顶点组均不存在有效的直接权重；原始文件的这些主腿骨骼直接权重顶点数均为 0。孤立旋转测试还显示左右 `Foot` 骨骼移动顶点数为 0。

这说明当前腿部网格主要由髋部、扭转骨骼或其它间接关系驱动，而不是由标准的 `Thigh -> Calf -> Foot` 链直接驱动。它可以解释：大腿像没有参与步态、膝盖出现单独折叠、脚掌跟随不稳定。当前不应继续优先删除膝盖；首先要恢复主腿骨骼的有效权重。

已生成一个仅用于验证假设的重加权诊断副本：

- `E:\comic\chibi_base_mesh_accurig_reweighted_legs_test.fbx`；
- `E:\comic\chibi_base_mesh_accurig_reweighted_legs_test.blend`；
- `E:\WorkProject\AssetsLab\prototype\test_output\accurig_reweighted_legs_walk_test\`。

该副本按髋部—膝盖—脚踝几何锚点给大腿、小腿和脚掌重新分配了线性过渡权重。审计结果为每侧 Thigh 432 个顶点、Calf 583 个顶点、Foot 320 个顶点；脚骨孤立旋转可移动约 317 个顶点。它不是最终生产权重，只用于确认“主腿权重缺失”是否是当前异常的首要原因。

### 膝盖弯曲方向反转测试（2026-08-01）

在重加权诊断副本上执行了 `--reverse-calf` 对照测试，仅把左右 `Calf` 的局部 X 旋转符号取反，大腿和脚掌运动保持不变。测试输出为：

- `E:\WorkProject\AssetsLab\prototype\test_output\accurig_reweighted_legs_reverse_knee_test\`；
- `E:\WorkProject\AssetsLab\prototype\test_output\accurig_reweighted_legs_reverse_knee_pixels\`。

结果确认膝盖弯曲方向可以通过反转小腿动作符号改变。因此，如果实际 Walk/NormalWalk 重定向后出现“向前迈步却向后顶膝”，应先尝试反转 `Calf` 的动作方向。但该测试仍可见腿部局部互穿，说明正式绑定还需要继续检查小腿局部轴和膝盖区域权重过渡；不能把反转符号单独视为最终修复。

### 腿根开裂现象说明（2026-08-01）

反向膝盖测试中出现的腿根开裂感不属于最终角色应有的结果，主要是诊断重加权脚本采用了 `z > 62` 的硬边界：边界以下的腿部顶点被清除了原有权重并重新分配给 `Thigh/Calf/Foot`，边界以上仍保留原始髋部权重，导致髋部与大腿之间出现权重不连续。下一版正式权重应保留髋部权重，并在髋部到大腿根部之间做连续的 `Hip ↔ Thigh` 过渡，同时限制腿部选择区域，避免把躯干侧面顶点纳入大腿权重。
