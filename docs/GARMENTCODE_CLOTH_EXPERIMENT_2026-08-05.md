# GarmentCode + Blender Cloth 实验记录（2026-08-05）

## 目标

验证“参数化裁片 + 缝合 + Blender 离线 Cloth”能否替代当前的 Actor 表面增补袖筒，生成没有明显拼接痕迹的完整 T 恤。

## 实验过程

- 使用 `third_party/GarmentCode` 的 MIT 核心和现有 T 恤版型。
- 保留版型中的 `translation` / `rotation`，修正了旧适配器把前后片和袖片压到固定深度平面的错误。
- 将每条版型边细分为 12 段，缝合弹簧从 80 条提高到 208 条。
- 提高 Cloth 质量、缝合力、布料张力和肩部 Pin 刚度。
- 在 Actor 网格上加入碰撞并烘焙到第 120 帧。

## 结果

输出：`prototype/test_output/garmentcode_cloth_v4/`

状态：`review_required_failed_fit`

画面仍出现：

- 肩部开口；
- 袖片翻折/散开；
- 背部衣片无法稳定闭合。

因此该候选不进入随机化池。

## 结论

GarmentCode 本身能提供结构化裁片和缝合关系，但默认人体版型、Q 版 Actor 的肩宽/胸廓比例以及当前 Actor 姿态不一致。把默认版型直接映射到 Actor 后再做 Cloth，不足以得到可靠结果。

下一步应改为：

1. 在 GarmentCode 匹配的身体上完成衣服悬垂；
2. 将烘焙后的完整服装作为独立网格；
3. 通过 Actor Clothing Cage 和最近表面/骨骼权重转移适配 Actor；
4. 再验证四方向与走路帧。

Blender MCP 的作用应限于调度生成、模拟、碰撞检查和批量渲染，不把 MCP 当作服装几何生成器。
