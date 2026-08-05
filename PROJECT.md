# AssetsLab Project

## 项目规则

- 工作目录：`D:\Apps\CodeXApp\Tests\AssetsLab`
- 文件名使用英文。
- Blender 只作为离线建模、动作、深度和注册参考；Godot 运行时只加载处理后的透明 2D PNG。
- 需要人工查看的预览通过 Tailscale 地址发布；不需要人工查看时使用隐藏的 headless 验证。

## 当前基线（2026-08-05）

### 3D 演员基线

唯一保留的 3D 演员基线是：

`prototype/assets/characters/actor_v1/`

其中 `chibi_actor_mixamo_walk_v1.blend` 是 v78 耳朵、手臂、手指和后摆腿修正后的发布场景。发布包同时保留 AccuRIG 输入、Mixamo Walk/Run 源文件、眼睛贴图和 Miku 耳朵源文件，可在 Blender 4.5+ 中复查或重建。

已知限制：侧视后摆脚的投影仍可能显得偏长；若继续修正，应调整步态时序或脚掌轮廓，不再叠加无效的 Foot/ToeBase 全局旋转缩放。

Actor V1 是离线生成基线，不等于已经接入 Godot 的最终运行时资源。

### 2D/Godot 技术基线

当前 Godot 原型的技术运行时资源仍是：

`prototype/assets/characters/runtime/chibi_eyes_ears_walk_v1/`

它用于验证 4 方向、8 帧、64×64 透明图层、最近邻导入、移动和截图。它不是 Actor V1 的最终美术结果；下一道正式门槛是将 Actor V1 在固定相机合同下转换为可人工清理的 2D 参考，再决定是否替换该技术基线。

## 锁定的生产合同

- 方向：`front`、`right`、`back`、`left`。
- 每个方向：8 帧，保持统一的步态相位和帧索引。
- 画布：64×64 透明 PNG。
- 脚底基线：运行时 y=60。
- 图层：`Feet`、`LowerBody`、`Arms`、`Torso`、`Head`，以及可选的 `Face`、`Hair`、`Clothing`、`Accessory`。
- 所有图层共享注册框、头部锚点和帧索引；不得逐层独立缩放或裁切。
- 最终像素图必须经过轮廓、调色板、接缝和逐帧稳定性检查；3D 直出图只能作为参考。

## 当前已完成

- 四方向骨骼行走阶段：静态骨架、腿、骨盆、手臂、左镜像和锚点复核均已通过独立 headless 阶段。
- 中性身体块和校准头部挂接已通过阶段检查。
- Actor V1/v78 已发布并成为唯一保留的 3D Walk 基线。
- 发型组件 catalog、随机池、组合工作台和单部件变体工作台已建立离线评审入口。
- Godot 4.6 原型的导入、移动、分层精灵和 headless 回归工具已存在。

## 当前未完成及顺序

1. **Actor V1 像素化闭环**：在统一四向相机和 8 帧采样合同下输出透明参考、轮廓/部件/深度辅助图，再生成 64×64 参考并进行人工像素清理。
2. **运行时替换评估**：把新像素层接入 Godot，验证脚底、头部锚点、方向映射、最近邻和图层同步；通过后才替换旧技术基线。
3. **移动眨眼小实验**：眼睛必须先成为独立的方向化透明层，眨眼只替换 Face 层，不改变 Head、身体帧或锚点。
4. **发型/服装 bundle**：先完成四视图和 64×64 像素验收，再将通过的组合固化为可按 seed 选择的整体 bundle。
5. 对角线方向和运行时 3D 角色暂不进入当前阶段。

## 开发待办

- [~] **eye_anime：移动眨眼与眼睛层**。已在派生 Actor V1 Blend 中建立可替换的 `Face/Eyes` 组合层，眉毛与眼睛由 image_gen 一起生成，并按 Actor 标准 bbox 校准；已修复 alpha 误覆盖导致的黑色“小窗”和透明抖动，接入 open/closed 状态、稳定 seed 烘焙、四向 headless 验证和 movement gallery；下一步验证 `half` 形变与正式透明 2D eye pass，不修改身体 8 帧合同。
- [ ] **pixelization：像素化质量 A/B**。比较 Blender 原生 Pixelate/Closest/Box、免费像素化插件和可选 2DFactory；固定相机、锚点、调色板、透明 pass 和 manifest 后再决定是否引入外部工具或 MCP。

## 当前入口文档

- [当前保留流程](docs/ACTIVE_ASSET_WORKFLOW.md)
- [3D 到 2D 像素计划](3D_TO_2D_PIXEL_ART_PLAN.md)
- [Actor V1 发布记录](docs/ACTOR_V1_RELEASE_2026-08-05.md)
- [像素化方案调研](docs/PIXELIZATION_PIPELINE_RESEARCH_2026-08-05.md)
- [眨眼设计记录](docs/EYE_BLINK_DESIGN.md)
- [发型组件随机化策略](docs/HAIR_COMPONENT_RANDOMIZATION_2026-08-04.md)
- [发型 Gallery 规范](docs/HAIR_GALLERY_STANDARD_2026-08-04.md)

日期型实验文档保留用于审计时，必须明确标注为历史候选；不得把其中的旧演员、旧耳朵、旧眼睛或旧运行时路径当作当前入口。

## 验证命令

运行 Godot 4.6.2 的隐藏回归：

```powershell
.\tools\run_headless_tests.ps1 -RebuildHead -VerticalCandidate -AppearanceSeed 20260731
```

运行现有像素运行时技术闭环：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_pixel_asset_end_to_end.ps1
```

后一命令目前验证的是 `chibi_eyes_ears_walk_v1` 技术包，不会自动验证 `actor_v1`；在 Actor V1 接入前，不能把它的通过结果表述为最终角色已完成。

## 预览规则

预览输出默认写入 `prototype/test_output/`，该目录按项目规则忽略。需要手机或人工复核时，使用 `tools/serve_preview.ps1` 或现有发布工具，并在交付消息中提供完整 Tailscale URL。
