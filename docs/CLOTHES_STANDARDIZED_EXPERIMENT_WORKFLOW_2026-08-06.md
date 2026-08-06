# 规范化服装实验流程（2026-08-06）

## 目标

每个服装候选都必须留下可复现的输入、检测报告、四方向动作截图和审核状态。
`review_required` 只表示“可以给人看”，不表示“可以进入随机池”。

## 标准目录

每个候选使用独立目录，例如：

```text
prototype/test_output/<candidate>/
  *.blend
  manifest.json
  front_00.png ... front_07.png
  right_00.png ... right_07.png
  back_00.png ... back_07.png
  left_00.png ... left_07.png
  garment_actor_fit_report.json
```

## 六个阶段

1. **输入登记**：记录来源文件、许可证、版型方法、身体/Actor 版本、参数和随机种子。
2. **静态生成**：只在独立实验目录生成，不覆盖无袖基线和 Gallery 的已通过里程碑。
3. **几何门禁**：运行 `check_garment_actor_fit.py`，固定采样动作帧
   `1/11/21/31/41/51/61/71`。
4. **四方向动作渲染**：固定 `front/right/back/left × 8 frames`，统一光照和相机。
5. **人工审核**：检查领口、肩部/袖窿、袖口、下摆、背部、穿模、离体和动作连续性。
6. **状态决策**：只有自动门禁通过且人工审核通过，才允许进入 Gallery 的通过区和随机池。

## 自动门禁

当前检测器会报告并判定：

- 肩部高度与左右位置；
- 身体穿透与下摆/大腿穿透；
- 衣服离体距离；
- 背面内部边界；
- 非流形边；
- 8 个动作帧是否都能读取 Actor walk action。

标准通过条件是：上述检查全部通过、无异常退出、四方向帧完整。检测器是几何回归
门禁，不替代对布料质感、领口形状和“像不像衣服”的人工判断。

## 统一执行命令

```powershell
.\tools\run_clothing_fit_gate.ps1 `
  -BlenderPath D:\Apps\CodeXApp\Tests\blender-4.5.10-windows-x64\blender.exe `
  -Blend prototype\test_output\<candidate>\<candidate>.blend `
  -Output prototype\test_output\<candidate>\garment_actor_fit_report.json `
  -GarmentName GarmentCodeShirt_ActorTransfer
```

脚本退出码为 0 才表示自动门禁通过；非 0 必须保留报告并标记为 `fail`，不能仅凭
Gallery 截图把它提升为通过。

## 当前官方短袖参数化转移结果

候选：`prototype/test_output/clothes_next_short_sleeve_official_transfer_v1/`

已运行统一检测，结果为 `fail`：

- `shoulder_placement`: pass；
- `hem_penetration`: fail；
- `body_clearance`: pass；
- `back_integrity` 与 `nonmanifold`: pass；
- 8 个动作采样帧中仍有明显的衣身/下摆穿透。

因此当前候选可以继续用于 Gallery 调优，但不能称为短袖里程碑，也不能进入随机池。
下一轮应优先修正 Actor 转移的肩部、表面余量和下摆深度，再重新跑同一门禁；不能
通过修改阈值来制造“通过”。
