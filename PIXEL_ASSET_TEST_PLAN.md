# pixel_asset_test 阶段计划

## 目标

把已经打通的 3D 渲染到像素化流程，整理成可重复验收的游戏资源生成流程。

## 第一条基线

当前使用重加权腿部诊断角色的反向膝盖测试作为输入样本：

`prototype/test_output/accurig_reweighted_legs_reverse_knee_pixels/`

这不是最终生产角色，只是用于验证资源格式和导出合同。

## 验收合同 v1

- 方向：`front`、`right`、`back`、`left`；
- 每个方向：8 帧；
- 单帧尺寸：128×128；
- 文件格式：RGBA PNG，保留透明背景；
- 文件命名：`{direction}/frame_{index:02d}/pixel.png`；
- 每个方向同时生成一个 sprite sheet 和 GIF 预览；
- `manifest.json` 必须记录源渲染目录、尺寸、方向、帧数和透明边界；
- 资源验证通过后，才进入调色、轮廓清理和运行时导入测试。

## 当前已知限制

本阶段只验收资源管线，不把腿根开裂、膝盖方向和权重质量标记为已解决。正式角色绑定修复仍应在独立的 Blender/AccuRIG 任务中完成。
