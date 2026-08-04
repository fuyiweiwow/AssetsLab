# 3D 演员 v1 发布记录（2026-08-05）

## 当前基线

唯一保留的可运行 3D 演员包：`prototype/assets/characters/actor_v1/`。

- 最终场景：`chibi_actor_mixamo_walk_v1.blend`
- 动作源：`animation_sources/mixamo_standard_walk.fbx`、`animation_sources/mixamo_run.fbx`
- 原演员输入：`actor_accurig_input.fbx`
- 面部：眼睛贴图在 Blend 内已打包，同时保存至 `eye_textures/`
- 耳朵：`ear_source/miku_chibi_ear_source.fbx`；最终耳朵直接嵌入 Blend 并绑定到 `CC_Base_Head`

当前 Walk 的确认调整：右臂使用两骨解析轨迹匹配；手指冻结；耳朵不整体内收，耳根向前 `0.050`，外耳廓以耳根为支点绕世界 Z 轴向脸部转 `12°`。

## 可复现方式

使用 Blender 4.5 或更高版本打开最终 Blend 即可查看已绑定 Walk。若需重做动作绑定，使用同目录的 AccuRIG 输入和 Mixamo FBX；若需重新提取耳朵，使用同目录的 Miku 耳朵源及 `tools/blender/replace_with_miku_source_ears.py`。

## 后续可选方案

1. **保持当前耳朵，并参数化变体。** 最低风险；以后可按角色生成器参数改变耳根位置、前移量和旋转量。
2. **耳根网格融合/重拓扑。** 能消除连接缝，但会改变头部拓扑和权重，是较高成本的建模步骤，适合角色外观定稿后再做。
3. **像素阶段遮挡缝线。** 在最终 2D 像素化中用发型、阴影或耳根色阶覆盖连接区，成本低，但不改善高分辨率 3D 正面。

侧视后摆脚偏长目前保留为已知限制：Foot/ToeBase 旋转缩放无效，后续应从步态时序或脚掌轮廓修正入手。

## 清理范围

所有旧的 Blender 动作候选、四向渲染候选和已下载的外部眼睛/耳朵候选均已移出工作区到 `E:\Env\Assets\AssetsLab_recoverable_cleanup\`，没有纳入 Git。仍被现有 Godot 场景引用的旧 2D 运行资源没有删除。
