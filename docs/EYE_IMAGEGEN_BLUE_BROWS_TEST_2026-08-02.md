# ImageGen 蓝色眼睛与眉毛整体包测试记录

日期：2026-08-02

## 目标

针对上一版眼睛偏小、抠图边缘不够干净、缺少眉毛的问题，重新生成一套更接近 `front-character-anchor.png` 的动漫眼部资源：使用蓝色虹膜、洋红色抠图底，并将眉毛与眼睛一起渲染。

## 处理结果

1. 使用概念图作为主要画风参考，生成蓝色渐变虹膜、纵向瞳孔、白色高光、上眼线/睫毛和深蓝色眉毛。
2. 使用洋红色背景进行键控抠图，转换为 RGBA。
3. 左右眼分别裁切；保留主眼部和面积足够大的眉毛组件，删除小型孤立噪点。
4. 贴到演员头部浅弧面，并 Shrinkwrap 到头部表面；整体宽度放大 `1.10x`，高度放大 `1.05x`。

## 资源

- 洋红原图：`prototype/assets/generated/eye_package_v3/imagegen_anime_eye_sheet_v3_magenta_key.png`
- 透明总图：`prototype/assets/generated/eye_package_v3/imagegen_anime_eye_sheet_v3.png`
- 左眼：`prototype/assets/generated/eye_package_v3/imagegen_eye_v3_crops/imagegen_eye_L.png`
- 右眼：`prototype/assets/generated/eye_package_v3/imagegen_eye_v3_crops/imagegen_eye_R.png`
- Blender 场景：`prototype/assets/characters/generated/eye_package_imagegen_v2_blue_brows.blend`
- 正面近景：`prototype/test_output/eye_package_imagegen_v2_blue_brows/front_face_closeup.png`
- 像素化预览：`prototype/test_output/eye_package_imagegen_v2_blue_brows_pixel64/front_face_closeup_nearest_view.png`
- 18° 转头测试：`prototype/test_output/eye_package_imagegen_v2_blue_brows_head_turn/frame_12.png`

## 验证结论

- 正面、三分之四、右侧近景渲染通过。
- 64×64 最近邻像素化后，眉毛、上眼线和蓝色虹膜仍可识别。
- 18° 头部转动测试通过，眼部贴图跟随 `CC_Base_Head`，未观察到重新悬浮或脱离头部。
- 该版本适合作为当前眼部视觉候选，但仍属于静态多视图验证，不代表已经完成随机资产批量生成。

## 随机化约定

眉毛、睫毛和眼睛应作为一个整体 `EyeStyleBundle` 随机生成，而不是先随机眼睛再独立随机眉毛。这样可以保持横向间距、倾角、大小和线条粗细一致。

建议结构：

```text
EyeStyleBundle = {
  eye_outline,
  iris,
  pupil,
  highlights,
  upper_lashes,
  eyebrows,
  scale,
  tilt
}
```

后续只有在建立明确锚点和兼容性规则后，才允许跨整体包组合眉毛或睫毛。

## 间距修正版

上一版在放大眼睛后沿用了原始中心点，导致两眼内侧视觉距离偏小。本次保留眼睛宽高不变，仅增加横向中心间距：

- `width_scale = 1.10`
- `height_scale = 1.05`
- `spacing_scale = 1.06`

验证：正面近景、64×64 像素化预览和 18° 头部转动测试已重新生成并通过。

## 虹膜与眉毛比例修正版

本次以 `front-character-anchor.png` 为主要比例参照，重新生成并键控处理了一版贴图：

- 虹膜略微放大，使上下边界更接近眼框；
- 眼白可见区域收窄，但保留白色边缘；
- 眉毛整体上移，与眼睛拉开距离；
- 保留蓝色虹膜、纵向瞳孔、白色高光和洋红色抠图流程。

新资源：

- 透明贴图：`prototype/assets/generated/eye_package_v4/imagegen_anime_eye_sheet_v4_auto.png`
- 左右眼裁切：`prototype/assets/generated/eye_package_v4/imagegen_eye_v4_auto_crops/`
- Blender 场景：`prototype/assets/characters/generated/eye_package_imagegen_v3_blue_brows_iris.blend`
- 正面近景：`prototype/test_output/eye_package_imagegen_v3_blue_brows_iris/front_face_closeup.png`
- 像素化预览：`prototype/test_output/eye_package_imagegen_v3_blue_brows_iris_pixel64/front_face_closeup_nearest_view.png`
- 18° 转头测试：`prototype/test_output/eye_package_imagegen_v3_blue_brows_iris_head_turn/frame_12.png`

参数保持：`width_scale=1.10`、`height_scale=1.05`、`spacing_scale=1.06`。正面比例、像素化识别度和头部跟随测试均通过。
