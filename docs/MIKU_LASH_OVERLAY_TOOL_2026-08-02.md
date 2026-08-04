# Miku 睫毛参考贴合网页工具（2026-08-02）

## 目的

提供一个不依赖 Blender 的正面参考工具：把原始 Miku 模型的睫毛区域圈选出来，再贴到我们的演员正面图上观察位置、长度、粗细和比例。

## 文件

- 网页：`prototype/preview/miku_lash_overlay_tool.html`
- 启动脚本：`tools/serve_miku_lash_overlay_tool.ps1`
- Miku 正面参考：`prototype/preview/assets/lash_reference/miku_face_front.png`
- 演员正面参考：`prototype/preview/assets/lash_reference/actor_front.png`
- Blender 生成 Miku 正面图脚本：`tools/blender/render_miku_face_reference.py`

## 使用流程

1. 运行 `tools/serve_miku_lash_overlay_tool.ps1`。
2. 浏览器打开 `http://127.0.0.1:8766/miku_lash_overlay_tool.html`。
3. 在左侧 Miku 图上，沿一只上睫毛点击多个点。
4. 点击“完成圈选并生成部件”，网页会自动清除多边形并把部件放到右图。
5. 如果需要重新使用当前圈选，可点击“重新抠取当前圈选”。
6. 在右侧演员图上拖动部件；滚轮缩放，Shift+滚轮旋转。
7. 左右睫毛分别操作，最后导出“合成 PNG”和“标注 JSON”。

## 结果用途

导出的合成 PNG 用于视觉确认，JSON 保留圈选多边形和部件变换参数。收到这两项后，再按人工标注曲线建立贴合演员脸部曲率的 3D 睫毛网格。

## 当前限制

网页使用多边形裁剪，不做自动语义抠图。因此圈选时应尽量紧贴睫毛轮廓，避免把眉毛、眼球或大面积脸部一起选入。
