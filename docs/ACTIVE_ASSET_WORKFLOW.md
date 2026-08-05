# AssetsLab 当前保留流程

本文档是当前项目的开发入口。日期型实验文档只用于审计，不代表当前资产、当前命令或当前运行时路径。

## 当前核心资产

- 3D 演员基线：`prototype/assets/characters/actor_v1/`
- 3D 发布场景：`prototype/assets/characters/actor_v1/chibi_actor_mixamo_walk_v1.blend`
- 当前 Godot 技术运行时：`prototype/assets/characters/runtime/chibi_eyes_ears_walk_v1/`
- 头部/五官注册参考：`prototype/assets/characters/rebuild_atlas_v1_runtime/male/`
- 发型源：`prototype/assets/hair/Blender-Chloe_Hair.blend`、`prototype/assets/hair/male_source/Blend_Hair.blend`
- 发型 catalog：`prototype/assets/hair/hair_component_catalog_v1.json`
- 发型随机池：`prototype/assets/hair/hair_random_pool_v1.json`
- 运动与图层顺序合同：`prototype/assets/characters/limb_puzzle.json`

Actor V1 是离线生成基线；`chibi_eyes_ears_walk_v1` 是已通过 Godot 技术测试的旧包。两者不能混称，后续必须先完成 Actor V1 的 3D→2D→Godot 闭环，再决定是否替换旧包。

## 锁定的输出合同

- 4 个方向：front/right/back/left。
- 每个方向 8 帧。
- 每帧 64×64、透明、最近邻。
- 所有图层使用同一注册框、脚底 y=60 和共享帧索引。
- 3D 参考至少输出 beauty、silhouette、part-ID、depth/order；最终像素层必须人工检查轮廓、调色板、接缝和帧间跳动。

## 最简验证流程

1. 用 Blender 4.5+ 检查 `actor_v1/chibi_actor_mixamo_walk_v1.blend` 的动作、耳朵连接和已知脚部限制。
2. 以固定四向相机和 8 帧合同渲染 Actor V1 的透明参考及辅助 pass；不要直接把 3D 渲染当作最终像素图。
3. 用现有 `tools/process_accurig_walk_pixels.py` 或新的等价处理器生成 64×64 review 资源。
4. 用 `tools/validate_pixel_runtime_package.py` 检查 manifest、方向、帧数、尺寸、透明度和图层一致性。
5. 接入 Godot 后运行：

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\tools\run_pixel_asset_end_to_end.ps1
   ```

   该命令当前仍验证旧的 `chibi_eyes_ears_walk_v1` 技术包，直到 Actor V1 有明确的新 runtime 路径。
6. 人工复核需要发布 `prototype/test_output/` 中的 gallery；使用 Tailscale 地址，不依赖 Blender/Godot GUI。

## 发型流程

发型只在离线阶段生成候选：

1. 先选必选 `base_cap`；
2. 再组合后发、侧发、刘海和附件；
3. 生成四视图、64×64 像素预览并检查耳朵关系、露白、穿插和后脑覆盖；
4. 通过验收的组合固化为整体 bundle；运行时按 seed 选择 bundle，不运行 Blender。

组合工作台：`tools/build_hair_workbench.py`；单部件工作台：`tools/build_hair_component_workbench.py`。

## 眨眼流程

眨眼不是头部或身体动画。只有在眼睛能独立导出为方向化 Face 层后，才允许增加 open/half/closed 眼睛状态，并在 Godot 中只替换 Face 层。详细方案见 [EYE_BLINK_DESIGN.md](EYE_BLINK_DESIGN.md)。

## 开发待办

- [ ] `eye_anime`：拆分 Actor V1 眼睛层，生成可复用的眼睛状态和四方向候选，完成移动眨眼 headless 小实验。
- [ ] `pixelization`：建立 Blender 原生像素化、免费插件和可选 2DFactory 的统一 A/B 输出与验收报告；MCP 只作为批处理编排层候选。

## 清理规则

- `prototype/test_output/` 只保留当前需要人工查看的输出，历史结果从源文件重建。
- 不删除 Actor V1、动作源、眼睛贴图、耳朵源、发型源、catalog、随机池和像素化工具。
- 历史实验文档如果仍用于记录失败原因，必须标明“历史候选”；如果文档仍声称旧资源是当前入口，应更新或删除。
