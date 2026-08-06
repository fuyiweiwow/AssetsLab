# 官方服装里程碑转移实验（2026-08-06）

## 决策

短袖 v1 的 Actor-derived 袖筒只用于验证骨骼跟随，不作为正式服装版型。
正式短袖实验回到已经通过 GarmentCode Warp 质量门禁的官方 neutral-body
T-shirt 里程碑，以避免重新手工构造领口、袖窿和袖片。

## 里程碑输入

- 源目录：`third_party/GarmentCode/Logs/t-shirt__260805-19-14-57_260805-19-31-09/`
- 官方源：`t-shirt__260805-19-14-57_sim.obj`
- 质量结果：`fails: {}`、`body_collisions: 0`、`self_collisions: 0`、`fin_frame: 405`
- 结构保证：官方 U 型领口、袖窿、缝合短袖、连续前后衣身

## Actor 转移边界

只在转移阶段处理 Actor 适配，不改变官方版型拓扑：

1. 按 Actor 的躯干包围盒做宽度、深度和衣长映射；
2. 用侧面保持的投影与小幅表面余量避免前后表面串面；
3. 继承 Actor 顶点权重和 Armature modifier，让衣服跟随 walk action；
4. 通过四方向 × 8 帧 Gallery 审核领口、袖窿、背部和动作连续性。

## 历史候选

`prototype/test_output/garmentcode_actor_official_neutral_v3_surface_bias/`

该候选已删除。它不是用户确认的无袖里程碑，不能作为后续短袖输入。

它仍然是 `review_required`，不替换已保存的无袖基线，也不进入随机池。只有
领口稳定、袖口和腋下连续、背面完整且动作帧不穿模后，才可作为短袖里程碑。

## 经验

“版型以官方物理里程碑为准，Actor 只负责适配和动画绑定”是本轮工作流的核心。
如果 Actor 转移仍失败，应调整转移参数和身体代理，不应退回到独立圆柱袖筒。
