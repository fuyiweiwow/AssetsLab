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

## 锚点校准接入 v1

根据用户提供的 `chibi_ear_anchor_calibration_v1.json`，新增了：

`tools/blender/attach_calibrated_cartoon_ear.py`

该脚本将正面图的左右耳根位置、侧面图的右耳深度和正面耳根上下范围转换为演员世界坐标。由于本次方向点接近垂直，v1 不把它解释成大角度旋转，而是保持耳朵基本竖直并向两侧镜像，避免再次把耳廓翻到脸前。

测试输出：

- Blend：`prototype/assets/characters/generated/eye_package_imagegen_v4_brows_up_downloaded_ears_calibrated_v1.blend`
- 正面：`prototype/test_output/downloaded_cartoon_ear_calibrated_v1/front.png`
- 右侧：`prototype/test_output/downloaded_cartoon_ear_calibrated_v1/right.png`
- 右侧近景：`prototype/test_output/downloaded_cartoon_ear_calibrated_v1/right_face_closeup.png`

状态：`calibrated_attachment_review_pending`。当前版本已解决“耳廓落在面部”的主要定位错误，下一步只需观察耳朵大小、嵌入深度和耳窝朝向。

## 旋转修正 v2

根据复核反馈，v1 的局部耳朵方向仍然错误：侧视图中耳孔朝上、外耳廓朝下。已增加绕右侧视图轴的 `+90°` 旋转，并用 `-90°` 对照验证：

- `+90°`：正面可见完整耳廓，侧面可见耳窝，为当前推荐方向。
- `-90°`：主要显示耳背，判定为错误方向。

当前推荐输出：

- Blend：`prototype/assets/characters/generated/eye_package_imagegen_v4_brows_up_downloaded_ears_calibrated_v2.blend`
- 正面：`prototype/test_output/downloaded_cartoon_ear_calibrated_v2/front.png`
- 右侧：`prototype/test_output/downloaded_cartoon_ear_calibrated_v2/right.png`
- 右侧近景：`prototype/test_output/downloaded_cartoon_ear_calibrated_v2/right_face_closeup.png`

校准脚本默认旋转已更新为 `rotation_x=90`；连接位置仍来自用户锚点，不再使用手工猜测的耳朵位置。

## 当前异常分析（2026-08-04）

当前耳朵的奇怪感不是单纯的前后或左右位置错误，主要有三个结构原因：

1. `CartoonEarPart_01` 是侧向开口的独立耳朵几何，耳窝轴朝左右；从正面看本来就会显得薄，不能直接当成与头部轮廓同向的面部部件。
2. 现在的接入把整只耳朵作为刚体挂到 `CC_Base_Head`，并以包围盒内侧点近似耳根。这个点能对齐整体位置，却不能同时让上缘和下缘都贴住头部。
3. v38/v42/v44/v47 的内收、前移、前视倾斜都是整体变换；当上缘被推到合适位置时，下方耳梗仍会因源模型自身形状向外张开，所以继续全局平移会让另一侧更糟。

因此下一次耳朵修正应改为“耳根局部变形”：固定真正耳根顶点，上缘和下缘分别沿头部法线移动，必要时增加一个根部 Shape Key；不再叠加整对象的位置和旋转。v48 只测试手臂镜像，耳朵沿用 v42，避免把尚未解决的耳朵问题混入动作判断。

## 已采用的 Q 版耳朵 v15

2026-08-03 经正面与右侧面多轮复核后，采用下载件 `CartoonEarPart_01` 的 Q 版缩小方案。先以窄耳根的真实几何中心对齐标注锚点，再以耳根为枢轴调整姿态，避免旋转后出现连接端脱离头部的问题。

> 归档说明（2026-08-05）：本文件记录的下载耳朵方案已退休，相关外部资源不再保留在工作区或 Git。当前唯一采用的是 `prototype/assets/characters/actor_v1/` 内的 Miku 源耳朵及其耳根旋转方案；请以 `docs/ACTOR_V1_RELEASE_2026-08-05.md` 为准。

- 最终资产：`prototype/assets/characters/generated/eye_package_imagegen_v4_brows_up_downloaded_ears_chibi_v15.blend`
- 审核预览：`prototype/test_output/ear_attachment_chibi_scale_v15/front.png` 与 `right.png`
- 尺寸：以标注推导尺寸的 `0.82` 倍
- 根部内嵌：`0.04`
- 左右后倾：`52°`
- 上端后移 / 下段梗前移：`12°`

两只耳朵均已验证以 Bone Parent 挂到 `Armature/CC_Base_Head`，可随头部动作移动：

```text
EAR_HEAD_BINDING_PASS CartoonEar_L_Downloaded Armature BONE CC_Base_Head
EAR_HEAD_BINDING_PASS CartoonEar_R_Downloaded Armature BONE CC_Base_Head
```

此前未采用的耳朵试验输出已清理；后续像素化移动测试以本版资产为唯一耳朵基线。
