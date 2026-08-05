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
- 当前实验状态：v15 在独立 `body` / `eyes` / `composite` 三阶段中关闭原生 `EyePackageV1_*` 眼睛对象，只播放自有的 `EyeBlinkV1_OpenTexture_*`、`HalfTexture_*`、`ClosedTexture_*` 状态层；身体层不含眼睛，眼睛层为透明 RGBA，合成后再进入 gallery。gallery 采样显式包含最大睁眼帧，full/eyes pass 均不允许原生眼框回灌；前、左、右、背四向均已通过检查，背面无眼睛。
- Gallery 参考：`prototype/preview/animation_gallery/eye-anime-v15/`；其中 64px GIF 仅为最近邻观察，不是最终像素资产。

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

## 中间帧工具评估

- ToonCrafter、AnimateDiff 属于生成式动画/卡通插帧工具，适合离线概念验证，但会改变线稿、透明边缘和角色身份，不适合作为随机眼睛的运行时依赖。
- FILM 或 RIFE 属于通用帧插值，能减少显式 `half` 状态，但对透明 2D 眼睛层和像素边缘需要逐帧人工验收；后续可作为离线 A/B，不替换当前确定性的 3D→2D 流程。
- 当前保留 `open/half/closed` 三态的原因是可复现、可随机换 bundle、可单独替换 Face/Eyes 层；若工具试验通过，优先把它用于离线生成候选，再固化为少量状态贴图。
- v15 独立层入口：`tools/blender/render_eye_blink_experiment.py --layer body|eyes`，合成入口：`tools/composite_eye_layers.py`；`body`、`eyes` 和 `full` pass 均不再渲染原生 EyePackage 动画。
