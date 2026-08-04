# Q版耳朵与眉毛上移测试记录

日期：2026-08-02

## 眉毛

在上一版蓝色眼睛基础上再次将眉毛整体上移约 10–12%，保持虹膜、眼白、眼睛间距和眉毛形状不变。新眼部来源为：

`prototype/assets/generated/eye_package_v5/imagegen_anime_eye_sheet_v5_auto.png`

## 耳朵候选

当前先制作一套可动画的 3D Q版人耳，不直接使用平面贴图：

- 外耳：圆润椭圆体，浅灰白材质，保留实体厚度；
- 内耳：较小的粉灰色浅层椭圆，作为正面识别细节；
- 父级：`CC_Base_Head`；
- 位置：左右对称，`x=±0.77`、`y=-0.35`、`z=2.08`；
- 尺寸：宽 `0.24`、高 `0.34`、深 `0.16`。

## 结果

- 正面：耳朵大小和头部比例协调，内耳细节可见；
- 侧面：耳朵具有实体厚度，根部已穿入头部表面，不再是完全漂浮的平面；
- 当前耳朵属于第一版几何候选，后续可继续增加耳轮、耳甲腔和耳垂形状。

## 输出

- Blender 场景：`prototype/assets/characters/generated/eye_package_imagegen_v4_brows_up_ears.blend`
- 正面：`prototype/test_output/chibi_ears_imagegen_v4/front.png`
- 侧面：`prototype/test_output/chibi_ears_imagegen_v4/right.png`
- 正面近景：`prototype/test_output/chibi_ears_imagegen_v4/front_face_closeup.png`
- 侧面近景：`prototype/test_output/chibi_ears_imagegen_v4/right_face_closeup.png`

本次只验证耳朵的基础形态、头部绑定和正/侧视图，不代表耳朵随机生成器已经完成。
