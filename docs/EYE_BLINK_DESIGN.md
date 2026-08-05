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
- 当前实验状态：v10 已通过前、左、右、背四向的 `open/half/closed/half/open` 组合层切换验证；背面无眼睛，身体材质 review render 已关闭不必要的透明抖动。
- Gallery 参考：`prototype/preview/animation_gallery/eye-anime-v10/`；其中 64px GIF 仅为最近邻观察，不是最终像素资产。

## 标准一致性与缺陷记录

- **EYE-SCALE-01（v6）**：新生成的组合层没有锁定 Actor 标准眼睛的外框和眉眼间距，导致 3D review 中眼睛显得像另一套角色。标准参数记录为：运行时画布 `64×64`；正面角色 alpha bbox `[18,7,46,57]`；标准 `eye_right.png` 内容 bbox `[13,12,488,597]`。后续组合层必须保留这个 bbox 和眉眼相对位置。
- **EYE-WINDOW-01（v7）**：标准贴图原本带透明 alpha，但处理脚本把已有 `alpha=0` 改成了不透明黑色；同时眼睛材质使用 hashed/dithered alpha，造成随帧变化的黑色矩形“小窗”。现已修复为保留源 alpha，并使用 `BLENDED/BLEND`。
- **v8**：front open 直接基于标准 `eye_right.png` 归一化，closed 与左右侧组合层均由 image_gen 参考标准生成；已复查 open/closed 和背面状态。
- **EYE-TRANSITION-01（v9）**：虽然加入了真实 `half` 组合贴图，但每侧仅保持 2 帧，30 fps 下仍显得过快。v10 将入场和出场各延长到 3 帧，并保留闭眼 2 帧；过渡状态仍由眼睛与眉毛一起生成。
