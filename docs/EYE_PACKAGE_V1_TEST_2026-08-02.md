# EyePackage v1 浅弧面动漫眼睛测试记录（2026-08-02）

## 目标

验证一条不依赖完整球形眼球的二次元眼睛工作流：

- Miku 眼睛贴图拆分为左右眼与虹膜资源；
- 眼白使用贴合头部的杏仁形浅层面；
- 虹膜使用独立透明贴图层；
- 眼框/上缘线作为可选层；
- 所有部件刚性绑定到演员的 `CC_Base_Head`；
- 通过 Shrinkwrap 贴合演员头部表面。

## 新增工具和资源

- `tools/prepare_miku_eye_texture_crops.py`
- `tools/blender/build_eye_package_v1.py`
- `tools/run_eye_package_v1.ps1`
- `tools/pixelize_eye_package_preview.py`
- `prototype/assets/generated/eye_package_v1/miku_eye_left.png`
- `prototype/assets/generated/eye_package_v1/miku_eye_right.png`
- `prototype/assets/generated/eye_package_v1/miku_iris_left.png`
- `prototype/assets/generated/eye_package_v1/miku_iris_right.png`

## 测试版本

### v1

场景：`prototype/assets/characters/generated/eye_package_v1.blend`

问题：眼睛浅弧面位于头部表面之后，贴图大部分被头部遮挡；上缘线也偏长。

### v2

场景：`prototype/assets/characters/generated/eye_package_v2.blend`

问题：增加前置距离后眼睛可见，但侧面再次出现明显前凸，说明仅移动深度不能解决问题。

### v3

场景：`prototype/assets/characters/generated/eye_package_v3.blend`

改动：加入 Shrinkwrap，并增大眼睛。

结果：侧面轮廓明显改善，但眼白与演员白色脸部材质融合，眼框不够清晰。

### v4

场景：`prototype/assets/characters/generated/eye_package_v4.blend`

改动：加入自制杏仁形眼框。

结果：结构正确，但眼框线过长且中心处有不自然汇聚。

### v5/v6

场景：`prototype/assets/characters/generated/eye_package_v6_layered.blend`

改动：把 Miku 贴图拆成眼白几何层与虹膜透明贴图层，并增加面部近景渲染。

结果：这是目前最有价值的结构候选。虹膜清晰，眼睛不再是完整球体，3/4 和侧面没有明显球形悬浮；但上缘线仍然需要按项目概念图重做。

### v7/v8

场景：`prototype/assets/characters/generated/eye_package_v8.blend`

改动：上缘线改为可选，并缩短、降低、变细。

结果：上缘线长度改善，但眼框的浅灰边缘仍不够像最终概念图。因此 v8 只作为“结构验证候选”，不作为最终画风基准。

## 当前判定

通过：

1. 眼睛可拆成眼白、虹膜、眼框三个独立层；
2. 眼睛可以作为一个整体绑定到 `CC_Base_Head`；
3. Shrinkwrap 能明显降低侧面漂浮感；
4. Miku 贴图可以作为虹膜/高光的起始资产；
5. 该结构适合后续按整体 `EyeStyleBundle` 随机化。

未通过：

1. 眼框线条还没有达到 `front-character-anchor.png` 的画风；
2. 当前眼白颜色与演员脸部过于接近；
3. 尚未完成眨眼、视线 UV 偏移和行走动画联动验证。

## 预览

- 全身多视图：`prototype/test_output/eye_package_v8/`
- 面部近景：`prototype/test_output/eye_package_v8/front_face_closeup.png`
- 3/4 近景：`prototype/test_output/eye_package_v8/threequarter_face_closeup.png`
- 侧面近景：`prototype/test_output/eye_package_v8/right_face_closeup.png`
- 64 像素预览：运行 `tools/pixelize_eye_package_preview.py` 生成。

## 下一步

1. 使用 `front-character-anchor.png` 重新定义杏仁形眼框的宽高、上下缘和外眼角；
2. 把眼框从“几何填充”改为带明确黑色轮廓的透明贴图或曲线层；
3. 添加左右虹膜 UV 偏移控制；
4. 测试头部转动、眨眼和 1.3 倍走路动画；
5. 通过后再建立整体眼睛、眉毛、睫毛的随机组合。

## 概念眼框 v2 与头部转动测试

基于 `front-character-anchor.png` 重新测量并人工描点生成了干净的透明眼框层：

- `tools/prepare_concept_eye_frames.py`
- `prototype/assets/generated/eye_package_v2/concept_eye_frame_L.png`
- `prototype/assets/generated/eye_package_v2/concept_eye_frame_R.png`
- `tools/run_eye_package_v2.ps1`

场景：`prototype/assets/characters/generated/eye_package_v2_concept_frame.blend`

结果：

1. 上眼睑厚度、外眼角延伸和像素化后的轮廓明显比 v8 接近概念图；
2. Miku 的虹膜/高光继续作为独立层，没有复制 Miku 的皮肤眼框；
3. 眼框、眼白和虹膜均通过 `CC_Base_Head` 跟随头部；
4. `18°` 头部转动测试通过，未出现部件脱离或重新变成完整球形眼睛。

头部转动测试：

- 场景：`prototype/assets/characters/generated/eye_package_v2_head_turn.blend`
- 输出：`prototype/test_output/eye_package_v2_head_turn/`
- 工具：`tools/blender/test_eye_package_head_turn.py`

当前仍未解决：

- 概念图眼框是绘制风格，当前透明贴图仍有轻微多边形感；
- 眼白颜色与演员脸部接近，像素化后主要依靠深色眼框和虹膜识别；
- 尚未测试视线 UV 偏移和眨眼。

## 概念眼框 v3 比例修正

根据复核反馈，v2 的眼睛横向过宽、纵向过短。本轮将参数调整为：

- `width_scale = 1.0`；
- `height_scale = 1.35`；
- 概念眼框贴图高度同步跟随眼睛高度，不再固定使用原始贴图宽高比。

场景：`prototype/assets/characters/generated/eye_package_v3_concept_proportion.blend`

输出：`prototype/test_output/eye_package_v3_concept_proportion/`

结果：

1. 正面比例更接近概念图，眼睛不再横向铺开；
2. 虹膜仍保持清晰，没有因眼白拉高而变形；
3. 3/4 和侧面仍保持贴脸；
4. 64 像素预览中，眼框和虹膜均可识别。

当前建议以 v3 作为后续视线 UV 与眨眼测试基准。
