# 官方参数化短袖重生成实验（2026-08-06）

## 目的

验证短袖应从官方 GarmentCode 参数重新生成，而不是拉伸或手工拼接现有网格。

## 官方版型输入

- 身体：`third_party/GarmentCode/assets/bodies/mean_all.yaml`
- 设计源：`third_party/GarmentCode/assets/design_params/t-shirt.yaml`
- `sleeveless=false`
- `sleeve.length=0.30`
- `sleeve.connecting_width=0.20`
- `sleeve.end_width=1.0`
- `sleeve.cuff.type=null`
- `collar.f_collar=CircleNeckHalf`
- `collar.b_collar=CircleNeckHalf`
- 衣身参数保持官方默认：`shirt.length=1.2`、`width=1.05`、`flare=1.0`

输出版型包含 8 个衣片、16 个 stitches，保留官方袖窿、袖片和 U 型领口结构。

## 官方物理结果

官方 Warp 模拟成功：

- `fin_frame=406`；
- `fails={}`；
- `body_collisions=0`；
- `self_collisions=0`；
- `Static with 0 non-static vertices out of 7155`。

这证明“短袖参数化生成”本身是可行的。

## Actor 转移结果

当前候选：`prototype/test_output/clothes_next_short_sleeve_official_transfer_v1/`

转移参数沿用已验证的官方源转移路线：侧面保持投影、`clearance=0.018`、
`front_flatten=0.008`、`back_clearance=0.008`、`sleeve_clearance=0.006`，并继承
Actor 权重和 Armature modifier。

统一检测结果为 `fail`：

- 肩部位置：通过；
- 身体离体：通过；
- 背部完整性：通过；
- 非流形：通过；
- 下摆穿透：失败，8 个动作采样帧均有问题；
- 总体穿透：每帧约 660–947 个顶点，最大下摆穿透约 0.033–0.044 m。

结论：官方短袖版型和物理模拟已经通过，但 Actor 转移仍未通过。当前 Gallery
只作为调优候选，不能替换无袖基线或进入随机池。下一步应优先修正转移阶段的
袖窿/下摆深度映射，而不是修改官方版型。
