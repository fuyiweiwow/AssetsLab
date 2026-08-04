# Miku 耳朵替换与手臂轨迹测试（2026-08-04）

## 基线与候选

- 保留基线：`prototype/test_output/chibi_eyes_ears_mixamo_walk_bound_v42_v38_eartilt12.blend`
- 手臂候选：`v50_v42_analyticarm_x058_y130`
- 合并候选：`v52_v50_miku_ears_bindfix`

本轮没有覆盖 v42，也没有采用先前失败的手臂镜像或 IK 约束版本。

## 耳朵

已检查项目中已有的 Miku FBX：

`prototype/assets/external/chibi_eye_model_candidates/miku_chibi/source/extracted/miku (chibi).fbx`

其 `head_org_0_0_node` 含两个各 32 顶点的耳朵连通分件。新工具
`tools/blender/replace_with_miku_source_ears.py` 从该网格提取两耳、使用原标注对应的耳根位置与现有尺寸基准、并 Bone Parent 到 `Armature/CC_Base_Head`。

生成的 v52 使用 `MikuEar_L_SourceV1` / `MikuEar_R_SourceV1`，在正面、右侧和背面均可见，且保留原始耳朵候选的 v42 文件不变。

接触审计（第 1 帧）的耳根带平均距离为左 `0.055045`、右 `0.020855`；相较旧耳朵，右耳明显改善，左耳仍需通过正面/侧面人工复核。该候选的目标是换成更合适的耳朵造型，不应被误称为已完成无缝融合。

## 手臂

新工具：`tools/blender/retime_arm_trajectory_analytic.py`。

它不创建 IK 控制器，不镜像任何一侧手臂；而是围绕每只手腕的时间平均位置，将世界 X 轨迹缩放为 `0.58`、世界 Y 轨迹缩放为 `1.30`，再用两骨解析重建上臂和前臂方向，并保留原始手肘弯曲侧。

测量结果：

| 手 | v42 X / Y | v50 X / Y |
|---|---:|---:|
| 左手 | 0.20908 / 0.43824 | 0.12325 / 0.60310 |
| 右手 | 0.12485 / 0.31508 | 0.09258 / 0.45445 |

因此两侧均满足“减少横向、增加前后纵向摆幅”的本轮目标。最终是否采用仍以 Gallery 的四向 GIF 人工观察为准。

## Gallery

`prototype/preview/animation_gallery/gallery.html` 已将 v52 放在首项，v50 和 v42 紧随其后，便于直接比较耳朵与手臂两项变化。

## v54 微调与脚部侧视审计（2026-08-05）

在 v52 的基础上生成了新的合并候选：

`prototype/test_output/chibi_eyes_ears_mixamo_walk_bound_v54_v53_earforward_inward.blend`

- Miku 耳朵：整体向前（世界 `-Y`）`0.025`，并向头部中线各内收 `0.012`，使耳廓更靠近脸部而不改变耳朵的局部造型。
- 右手：在 v50 已缩小横向摆动的基础上，额外将前后轨迹提高 `1.327` 倍。最终左/右手前后 Y 摆幅为 `0.60689 / 0.64362`，已处于同一量级；横向 X 摆幅为 `0.11344 / 0.11860`。

新增 `tools/blender/audit_foot_side_projection.py`，用 Foot/ToeBase 顶点权重在全部 71 帧上测量侧视 Y 投影长度：

| 脚 | 向后时 Y 投影长度 | 向前时 Y 投影长度 | 差值 |
|---|---:|---:|---:|
| 左脚 | 0.169560（第 14 帧） | 0.144437（第 56 帧） | 约 0.039325 |
| 右脚 | 0.170608（第 48 帧） | 0.140610（第 21 帧） | 约 0.043794 |

两侧的增加幅度和时序均相近，故“内侧后脚比另一只脚长”的主要原因是脚掌/ToeBase 在后摆相位的侧视投影变长与两脚遮挡，而非单侧网格长度被拉伸。此前单纯冻结或固定 Foot 旋转仍不能消除该现象；若未来要修，正确方向是校准 `Calf → Foot → ToeBase` 的休息轴与脚掌轮廓，而不是继续叠加全局脚踝角度。

Gallery 现已将 v54 放在第一项，供正面和侧面 GIF 人工复核。

## v66 耳根旋转、手指冻结与足部复核（2026-08-05）

v54 的“整耳内收”不再作为采用方向；它没有保持用户要求的耳根连接关系。后续候选均从 v52 的 Miku 源耳朵出发，先复用已验证的右臂纵向摆幅匹配，再进行以下处理：

- `v61`：将右臂的世界 Y 轨迹再提高 `1.327` 倍，使两侧纵向摆臂处于同一量级；不使用镜像或 IK。
- `v65`：不做世界 X 内收。耳根保留为旋转支点，耳朵整体仅前移 `0.050`（世界 `-Y`），外耳廓绕世界 Z 轴向脸部旋转 `8°`。此前 20° 的同方向试验会把正面耳朵压成窄边，已否决。
- `v66`：冻结 24 根手指骨（左右手 Thumb/Index/Ring/Pinky 各三节）为首帧姿态，消除 Mixamo 手指关键帧在像素化 GIF 中造成的乱甩/闪烁。

当前供人工复核的主候选：

`prototype/test_output/chibi_eyes_ears_mixamo_walk_bound_v66_v65_fingersfreeze.blend`

对应的四向渲染目录：

`prototype/test_output/chibi_eyes_ears_mixamo_walk_fourway_v66_v65_earpivot08_fingersfreeze_texture`

足部方面，额外候选 v64 将 Foot 的完整四元数动画差量缩放为 `0.45`、ToeBase 缩放为 `0.35`。脚踝旋转数值确已降低，但侧视 Y 投影长度几乎不变；因此它没有解决“后摆脚看起来更长/有蹄形”的根因，不作为主候选。后续若继续修脚，应以步态重定时或脚掌网格轮廓为对象，并在不破坏当前膝盖与腿根动作的前提下单独比较。

## 发布基线 v1（2026-08-05）

用户确认手部保持当前状态，并要求进一步收拢外耳廓。最终发布候选将耳根旋转从 `8°` 提高至 `12°`，仍不做整体内收；正面与侧面复核均保留可见耳朵轮廓。

发布包位于 `prototype/assets/characters/actor_v1/`，其中包含最终 `.blend`、已打包且另存的双眼贴图、AccuRIG 输入、Mixamo Walk/Run FBX 及 Miku 耳朵源 FBX。旧候选只作为本记录中的历史，不再作为可运行资产保留。
