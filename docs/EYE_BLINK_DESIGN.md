# 移动中的眨眼设计记录

更新时间：2026-08-05

## 结论

应该做，但应作为独立的小型表现层实验，不应修改当前 4 方向 × 8 帧的身体动画合同。

当前开发分支：`eye_anime`。本分支第一项先在 Actor V1 的 3D 场景中建立可替换的 Face/Eyes 层，再把 open/closed 状态烘焙到 3D→2D 渲染流程；随机眼睛候选会在离线渲染前按 seed 选择，不在运行时临时生成或绘制像素。

眨眼对大头角色的表情收益高，且只需要切换完整的 Face/Eyes 组合层。眉毛和眼睛必须由 image_gen 一起生成，避免 open/closed 切换时眉眼错位；再由 Blender 离线渲染为 2D 参考。背面没有眼睛几何，因此背面保持透明，不生成背面眼睛贴图。

## 推荐实现

- 3D 渲染阶段准备 `open`、`half`、`closed` 三种状态；三种状态均使用 image_gen 生成的“眼睛+眉毛”组合贴图。`half` 入场和出场各保持 3 帧，避免 open/closed 之间瞬间跳变。
- 眨眼只改变 Blender 的 `Face/Eyes` 层，不改变 `Head`、身体帧、脚底基线或锚点；导出后的 Godot 只加载烘焙 2D 结果。
- 眨眼帧索引独立于行走帧索引；角色移动时仍连续播放身体 8 帧循环。
- 使用稳定的角色 seed 生成眨眼间隔，避免录制、回放和测试时出现不可复现差异。
- 默认间隔约 2.5–5 秒，半睁入场 3 帧、闭眼 2 帧、半睁出场 3 帧（30 fps 下完整过渡约 267 ms）；攻击、受伤、对话等特殊状态以后可以覆盖普通眨眼。

推荐序列：

```text
open → half → closed → half → open
```

第一阶段使用 3D 相机自动覆盖正面、右侧、左侧和背面验证；背面不生成眼睛，保持透明 Face 层。侧面使用 image_gen 生成的组合层进行离线参考渲染，不作为运行时 3D 方向贴图。

## 验收标准

1. 眨眼不造成头部、耳朵或发型跳动；
2. 行走帧不重置，方向切换不丢失眨眼状态；
3. 同一个 seed 的间隔和帧序列一致；
4. 1× 和游戏实际显示尺寸下都能看出闭眼，而不是随机噪点；
5. headless Blender 测试可以输出一次固定 seed 的眨眼序列，并且同 seed 重建 manifest 一致。

## 暂不做的方案

当前不把浅曲面贴图直接当作最终 2D 资产，也不把侧面平面作为运行时方案。第一版先使用独立的眼睛+眉毛组合层完成离线 3D→2D 参考；如果需要 `half`，再单独验证 Shape Key 或最终透明眼睛 pass，不让它影响已稳定的头部绑定。

## 当前实现

- Blender 构建脚本：`tools/blender/build_eye_blink_experiment.py`
- 无窗口材质渲染：`tools/blender/render_eye_blink_experiment.py`
- image_gen 眼睛+眉毛源的去色键与尺寸归一化：`tools/process_imagegen_eye_texture.py`
- 派生实验输出：`prototype/test_output/eye_anime/`（不修改 Actor V1 原始 Blend）
- 当前实验状态：v20/v22 在独立 `body` / `eyes` / `composite` 三阶段中关闭原生 `EyePackageV1_*` 眼睛对象，只播放自有的 `EyeBlinkV1_OpenTexture_*`、`HalfTexture_*`、`ClosedTexture_*` 状态层；眼睛可见性先按眼睛帧缓存，再清除原生可见性动作并手动按方向应用，避免 depsgraph 复活旧对象。正面保持 Actor 标准眉眼尺寸；左右独立眼层绑定到 `CC_Base_L_Eye` / `CC_Base_R_Eye`，通过面部骨骼链继承头部和面部动画；侧面 profile 平面保持刚性并放大有效可视区域，避免 shrinkwrap 把眼睛压成细缝。body pass 严格使用完整 8 帧身体采样，gallery 采样显式包含最大睁眼帧，背面无眼睛。
- Gallery 参考：`prototype/preview/animation_gallery/eye-anime-v22/`；其中 64px GIF 仅为最近邻观察，不是最终像素资产。

## 标准一致性与缺陷记录

- **EYE-SCALE-01（v6）**：新生成的组合层没有锁定 Actor 标准眼睛的外框和眉眼间距，导致 3D review 中眼睛显得像另一套角色。标准参数记录为：运行时画布 `64×64`；正面角色 alpha bbox `[18,7,46,57]`；标准 `eye_right.png` 内容 bbox `[13,12,488,597]`。后续组合层必须保留这个 bbox 和眉眼相对位置。
- **EYE-WINDOW-01（v7）**：标准贴图原本带透明 alpha，但处理脚本把已有 `alpha=0` 改成了不透明黑色；同时眼睛材质使用 hashed/dithered alpha，造成随帧变化的黑色矩形“小窗”。现已修复为保留源 alpha，并使用 `BLENDED/BLEND`。
- **v8**：front open 直接基于标准 `eye_right.png` 归一化，closed 与左右侧组合层均由 image_gen 参考标准生成；已复查 open/closed 和背面状态。
- **EYE-TRANSITION-01（v9）**：虽然加入了真实 `half` 组合贴图，但每侧仅保持 2 帧，30 fps 下仍显得过快。v10 将入场和出场各延长到 3 帧，并保留闭眼 2 帧；过渡状态仍由眼睛与眉毛一起生成。
- **EYE-WALK-01（v10）**：gallery 为了展示眨眼选用了不连续的身体帧，跳过了原始 Walk 动作的步态相位，导致看起来像只剩半个走路循环。v11 增加 `--body-frames`，身体采样固定为 `[1,11,21,31,41,51,61,71]`，眼睛仍使用连续的 `[27..34]` 时间帧。
- **EYE-LAYER-01（v12）**：即使 v11 将身体帧和眼睛时间帧分离，仍在同一 Blender 场景中恢复姿态，可能影响 walk review。v12 将身体和眼睛分别渲染，再用 RGBA 离线合成，避免眼睛动画参与身体渲染。
- **EYE-NATIVE-01（v12）**：独立眼睛层仍混入原生 `EyePackageV1_*` 的开合动画，导致原生眼睛与新状态层重叠。v13 在 `eyes` pass 中强制隐藏原生对象，只保留 `EyeBlinkV1_*`。
- **EYE-OPEN-01（v13）**：v13 隐藏原生对象后，独立层缺少自己的最大睁眼几何；v14 新增 `EyeBlinkV1_OpenTexture_L/R`，三态本身不依赖原生动画。
- **EYE-OPEN-02（v14）**：最大睁眼素材虽然已存在，但 gallery 仍采样 `[27..34]`，从半睁帧开始，造成“没有最大眼睛帧”的观感；v15 固定采样 `[24,26,27,29,30,32,34,35]`，首尾均为最大睁眼。
- **EYE-SIDE-01（v14）**：方向 pass 只在 `eyes` 层隐藏原生对象，full 渲染仍可能保留 `EyePackageV1_AlmondFrame_*`，导致侧面独立眼层与旧眼框重叠；v15 在所有独立眨眼渲染层统一禁用完整 `EyePackageV1_*`。
- **EYE-SIDE-02（v15）**：仅设置 `hide_render` 仍不足以阻止带关键帧的眼睛对象在 depsgraph 中复活；v18 先缓存 `EyeBlinkV1_*` 在目标眼睛帧的状态，再清除可见性动作并手动应用方向筛选。
- **EYE-SIDE-03（v15）**：侧眼平面位置仍落在鼻侧，且左右法线与相机方向相反；v18 将平面移到侧面眼窝位置，右侧使用 `-X`、左侧使用 `+X` 法线，并使用贴图自发光材质保持 image_gen 颜色。
- **EYE-WALK-02（v15）**：body pass 仍先跳到 eye frame 再恢复骨骼姿态，造成走路周期看起来不完整；v18 在 body pass 直接使用 `[1,11,21,31,41,51,61,71]`，只有 eyes/full pass 才进行身体姿态锁定。
- **EYE-BIND-01（v18，已被 v20 扩展）**：眼睛对象必须保持 `parent_type=BONE`，不能只保存世界坐标。v18 先以 `CC_Base_Head` 验证头部跟随；v20 将合同扩展为左右眼分别绑定眼骨骼，以覆盖面部动画。
- **EYE-BIND-02（v20）**：仅绑定 `CC_Base_Head` 只能继承头部移动，不能继承独立的面部/眼球动画。正面左右眼、侧面左右 profile 层现在分别绑定 `CC_Base_L_Eye` / `CC_Base_R_Eye`，通过 `CC_Base_FacialBone -> CC_Base_Head` 继承上层运动；脚本同时验证每个独立层的 parent bone。
- **EYE-SIDE-04（v20）**：侧面 image_gen 画布透明留白较多，且对 profile 平面使用 shrinkwrap 会把平面投影变形为细缝。侧面层改为刚性骨骼绑定，平面尺寸固定为 `0.68×0.64`，只用 bone transform 跟随面部动画。

## 中间帧工具评估

- ToonCrafter、AnimateDiff 属于生成式动画/卡通插帧工具，适合离线概念验证，但会改变线稿、透明边缘和角色身份，不适合作为随机眼睛的运行时依赖。
- FILM 或 RIFE 属于通用帧插值，能减少显式 `half` 状态，但对透明 2D 眼睛层和像素边缘需要逐帧人工验收；后续可作为离线 A/B，不替换当前确定性的 3D→2D 流程。
- 当前保留 `open/half/closed` 三态的原因是可复现、可随机换 bundle、可单独替换 Face/Eyes 层；若工具试验通过，优先把它用于离线生成候选，再固化为少量状态贴图。
- v20 独立层入口：`tools/blender/render_eye_blink_experiment.py --layer body|eyes`，合成入口：`tools/composite_eye_layers.py`；`body`、`eyes` 和 `full` pass 均不再渲染原生 EyePackage 动画。
