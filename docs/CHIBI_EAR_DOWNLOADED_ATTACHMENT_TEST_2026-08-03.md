# 下载卡通耳朵候选接入测试

日期：2026-08-03
分支：`pixel_asset_test`

## 目的

验证下载的独立卡通耳朵模型能否作为 3D 演员的可替换耳朵部件，并确认它能够跟随 `CC_Base_Head` 骨骼移动。此步骤只做部件接入，不把耳朵并入演员主体网格。

## 输入资产

- 原始下载包：`E:/Env/Assets/low-poly-cartoon-ear.zip`
- 项目归档：`prototype/assets/external/chibi_ear_candidates/low_poly_cartoon_ear/source/low-poly-cartoon-ear.zip`
- 内层 OBJ：`SubTool-0-8292957.OBJ`
- OBJ SHA-256：`BC729F9288C7EDCB1E66C00C71FCAAD1FBCC26B7164A028F948B9545870F7A6B`
- 项目中的独立候选 Blend：`prototype/assets/characters/generated/cartoon_ear_candidate_v3.blend`

OBJ 分离后有 3 个松散部件：

| 部件 | 顶点 | 面 | 处理 |
|---|---:|---:|---|
| `CartoonEarPart_00` | 38 | 34 | 保留作备选 |
| `CartoonEarPart_01` | 557 | 544 | 当前测试候选，耳窝细节最好 |
| `CartoonEarPart_02` | 143 | 136 | 保留作备选 |

## 接入方式

工具：`tools/blender/attach_cartoon_ear_candidate.py`

当前测试使用：

- 演员输入：`prototype/assets/characters/generated/eye_package_imagegen_v4_brows_up.blend`
- 候选部件：`CartoonEarPart_01`
- 头部骨骼：`Armature/CC_Base_Head`
- 位置：`x=±0.82, y=-0.08, z=2.08`
- 缩放：`0.52`
- 左耳使用 X 轴镜像，左右耳保持耳窝朝外
- 材质：临时演员肤色材质 `CartoonEarActorSkin`

输出 Blend：

`prototype/assets/characters/generated/eye_package_imagegen_v4_brows_up_downloaded_ears_v6.blend`

测试图：

- 正面：`prototype/test_output/downloaded_cartoon_ear_on_actor_v6/front.png`
- 右侧：`prototype/test_output/downloaded_cartoon_ear_on_actor_v6/right.png`
- 正面近景：`prototype/test_output/downloaded_cartoon_ear_on_actor_v6/front_face_closeup.png`
- 右侧近景：`prototype/test_output/downloaded_cartoon_ear_on_actor_v6/right_face_closeup.png`

## 结果与结论

1. 骨骼绑定有效：耳朵能够挂到 `CC_Base_Head`，并随头部层级保存。
2. `CartoonEarPart_01` 是目前三个部件中最适合继续观察的候选。
3. 该模型的耳窝开口轴朝左右方向，因此正面投影会显得较薄，侧面更能看到耳窝；这不是绑定失败，而是源模型的几何朝向和造型特征。
4. 当前版本是“下载部件接入候选”，不是最终造型定稿。下一步应在确认耳朵大小、嵌入深度和正侧面轮廓后，再进入随机耳朵变体。

## 网页锚点标注工具

由于 Blender 在部分机器上会闪退，新增了不依赖 Blender 的网页工具：

`prototype/preview/ear_anchor_annotator.html`

使用方法：

1. 打开 `http://127.0.0.1:8766/ear_anchor_annotator.html`，或直接双击该 HTML 文件。
2. 可以直接点击“加载当前演员正面和右侧面”，也可以手动加载 `prototype/preview/assets/ear_anchor_reference/front.png` 和 `right.png`。
3. 拖动耳根中心、耳根上端、耳根下端和朝向终点四类锚点。
4. 点击“下载标注 JSON”，将 `chibi_ear_anchor_calibration.json` 发回项目。

工具保存的是归一化坐标，不依赖图片分辨率；正面图用于左右位置，侧面图用于确认耳朵是否位于头部侧后方以及朝向。

## 保留的失败实验

旋转扫查和早期接入 Blend 保留在本地用于追溯，但不作为当前推荐版本。正式使用以 `v6` 为基准，避免把错误的整体旋转方向带入后续流程。
