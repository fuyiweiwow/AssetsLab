# 服装里程碑清理记录（2026-08-06）

## 保留的唯一 Actor 服装里程碑

```text
prototype/test_output/garmentcode_official_side_supported_arc_clearance_final2_test/
```

该版本由用户确认作为当前 Q 版 Actor 的无袖上衣基线。它采用官方 GarmentCode
Demo 所参考的连续侧面过渡、开放下摆和 Surface Deform 动画链路，包含四方向 ×
8 动作帧、候选 Blend、manifest 和适配检测报告。

## 已清理内容

- 删除 `prototype/test_output` 下 101 个有完整四方向预览的旧服装候选；
- 删除另外 24 个服装版型、身体代理和布料诊断中间缓存；
- 删除正式 Gallery 中旧的 Actor 转移、官方 neutral/mean_male 和短袖误导候选；
- 未删除 Actor 原始资源、第三方 GarmentCode 源码与模拟日志、项目脚本和实验文档。

清理后，`prototype/test_output` 中仅保留上述确认里程碑作为服装生成结果。

## 下一轮短袖规则

短袖实验必须从这个无袖 Render Garment 的衣身开始：

1. 保留衣长、下摆、领口、前后深度和连续侧面过渡；
2. 参考官方 GarmentCode T-shirt 的袖窿曲线、袖片连接方式和短袖比例；
3. 只新增袖窿和袖筒，不重新生成整件普通 T-shirt；
4. 通过四方向 × 8 动作帧和适配检测后，才更新 Gallery current；
5. 失败候选只保留在临时实验目录，不覆盖本里程碑。

官方 Demo 是结构参考，不是当前 Actor 的替代基线。
