# Miku 睫毛人工标注流程记录（2026-08-02）

## 当前决定

前面多轮自动生成的睫毛在形状、粗细、外侧终点和贴脸关系上仍然不符合目标，因此暂停继续猜测参数，改为“用户标注轮廓，工具按轮廓建模”。

## 正面参考图

- 生成脚本：`tools/blender/render_miku_front_lash_annotation.py`
- 基础场景：`prototype/assets/characters/generated/miku_chibi_eye_on_accurig_v13_restore_v5_state.blend`
- 输出图：`prototype/test_output/miku_lash_annotation_front.png`
- 分辨率：1024 x 1024
- 图中保留：演员头部、Miku 眼球
- 图中隐藏：旧的 `ConceptEyebrow*`、`ConceptEyelash*` 和 `eyelashes.*`

## 用户标注内容

请直接在 PNG 上绘制左右眼的上睫毛轮廓，至少包含：

1. 左眼内侧起点与外侧终点；
2. 右眼内侧起点与外侧终点；
3. 睫毛轮廓的上下边界，或用粗线直接表示目标厚度；
4. 如果外侧需要明显翘起，请把翘起的终点完整画出来。

收到标注图后，再根据标注曲线建立贴合演员脸部曲率的 3D 睫毛网格，并输出正面、侧面和像素化预览。
