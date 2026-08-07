# 从确认无袖里程碑扩展官方结构短袖（2026-08-06）

## 实验边界

本实验的输入固定为用户确认的无袖里程碑：

`prototype/test_output/garmentcode_official_side_supported_arc_clearance_final2_test/`

躯干网格、U 型领口、正背面衔接、Surface Deform 动画链路均不重新生成。短袖实验只增加袖筒，避免再次改变已经通过人工审核的衣身。

## GarmentCode 官方 Demo 参考

官方短袖设计的结构参考参数为：

- `sleeveless=false`
- `sleeve.length=0.30`
- `sleeve.connecting_width=0.20`
- `sleeve.end_width=1.0`
- `sleeve.cuff.type=null`
- 正、背领口使用 `CircleNeckHalf`

这里不把官方完整 T 恤直接替换到 Actor 上。由于官方 `sleeve.length` 是纸样/衣身参数，不等同于 Actor 上臂骨骼长度，本实验将其转译为“沿 `CC_Base_L/R_Upperarm` 的短袖壳”，并保留官方结构意图：短袖、开放袖口、不覆盖手部、从袖窿方向连续接入。

## 当前实现

工具：`tools/blender/build_garment_proxy_render_pair.py`

- `--reuse-existing-render-pair`：复用已确认的 RenderGarment 和 AnimationProxy，不重建躯干；
- `--build-clean-short-sleeve-render-garment`：创建左右独立袖筒；
- 使用上臂骨骼头尾作为轴线，10 段环、5 个轴向采样环；
- 每侧使用独立上臂顶点组和 Armature modifier，袖口保持开放；
- 当前实验参数：`sleeve-length-fraction=0.65`、`sleeve-clearance=0.012m`；
- 袖筒在 `armature_rest_pose` 中生成，并使用 `forward_offset=0.04m` 解决 Actor 放松姿态下手臂位于躯干后侧造成的正面遮挡；
- 上臂半径只从对应的 `CC_Base_L/R_Upperarm` 权重顶点采样，采样范围放宽到 `0.20m`，避免把躯干点混入或截掉 Q 版上臂外轮廓；当前外壳半径范围为 `0.10--0.18m`；
- 实际上臂长度只有约 0.14m，因此官方 `0.30` 不能直接当作 Blender 世界坐标或骨骼比例使用；该映射必须作为模型专属参数记录，不能泛化到其他人体。

## 检测结果

输出：`prototype/test_output/clothes_short_sleeve_from_confirmed_milestone_v1/`

- 四方向 × 8 帧已生成；
- `garment_actor_fit_report.json`：自动门禁 `pass`；
- 肩部位置、身体间隙、下摆穿透、非流形检查通过；
- 检测器同时检查躯干和袖筒，但把袖筒开放袖口与躯干背部完整性分开统计，避免把合法袖口误报为背部撕裂；
- 该候选仍为 `review_required`，自动通过不等于人工确认通过。

## 失败经验与修正

第一次构建时重新生成了一个躯干副本。它与确认里程碑的 Surface Deform 绑定空间不同，导致检测器报告约 0.20m 的上部穿透。问题不在短袖参数，而在违反了“基线衣身不可重建”的实验边界。

修正为复用确认里程碑的 RenderGarment/AnimationProxy 后，躯干门禁恢复通过；本次 Gallery 只发布复用基线的短袖候选。

## 袖筒遮挡修正（2026-08-07）

人工检查发现首版袖筒只在侧面露出残留，正面像卡进手臂。复核单独袖筒渲染后确认不是材质丢失，而是两个几何问题叠加：袖筒之前在姿态空间生成后又被 Armature modifier 变形一次，并且半径采样上限过小。现已改为 REST 空间生成、对应上臂权重采样，并加入小幅前向偏移。四方向动作帧重新渲染，自动适配门禁仍为 `pass`。

## 审核重点

请优先观察：

1. 正面袖筒是否足够可见、是否仍然像无袖；
2. 侧面袖筒与肩部是否有悬浮、卡入或不连续；
3. 背面肩袖连接是否平滑；
4. 走路 8 帧中袖口是否跟随上臂而没有覆盖手部；
5. 袖筒是否显得像硬壳，而不是布料。

候选只有在上述人工审核通过后，才可进入后续随机化种子池。
