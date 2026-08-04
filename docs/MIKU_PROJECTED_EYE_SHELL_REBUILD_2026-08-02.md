# Miku 眼部投影重建测试

日期：2026-08-02

## 目标

放弃 Miku 原始眼部外壳的三角面流，改用 `eye_007_22_0_node` 的正面 X/Z 投影轮廓，重建连续浅层网格。

## 流程

1. 导出 `eye_007_22_0_node` 的 227 个顶点和 324 个面。
2. 将面投影到 X/Z 平面并栅格化。
3. 从栅格 mask 提取轮廓。
4. 使用 Shapely 对轮廓重新三角化，得到 1,382 个顶点、1,380 个三角面。
5. 映射到演员眼部区域，并 Shrinkwrap 到头部表面。

工具：

- `tools/blender/export_miku_eye_shell_projection.py`
- `tools/rasterize_miku_eye_shell_projection.py`
- `tools/build_projected_eye_shell_recipe.py`
- `tools/blender/build_projected_eye_shell_test.py`

## 结果

- 原始尖刺和三角折叠：已消除。
- 轮廓网格连续性：通过。
- 侧面明显浮出：未发现明显外凸。
- 与 Miku 风格的可见眼窝效果：未通过，正面视觉仍接近演员原版本。

候选：

- `prototype/assets/characters/generated/miku_projected_eye_shell_v2_upper.blend`
- `prototype/test_output/miku_projected_eye_shell_v2_upper/front.png`
- `prototype/test_output/miku_projected_eye_shell_v2_upper/right.png`

## 结论

`eye_007_22_0_node` 主要提供上部皮肤轮廓，不是完整的可见眼框/眼白结构。仅重建该轮廓无法复刻 Miku 的二次元凹入效果。下一步必须同时提取眼白材质层、虹膜表面和遮挡关系，或直接从 Miku 正面渲染结果生成完整眼部 2.5D 组件。
