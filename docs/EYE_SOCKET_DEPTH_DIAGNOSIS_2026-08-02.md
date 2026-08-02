# 眼球突出问题诊断记录

日期：2026-08-02

## 用户反馈

当前结果与最初版本区别不大，眼睛仍然突出，没有达到 Miku 的二次元凹入效果。

## 证据链

### 1. 贴面眼睑层

`contour_boolean_eye_socket_v6_shrinkwrapped_headturn_test.blend` 解决了眼睑线的侧面浮出和动画跟随，但没有改变眼球本体的前后关系。因此它不能解决核心问题。

### 2. 向内压扁眼球

v7、v8 将眼球压扁并向头内移动，结果是眼球被原头部开口边缘遮挡，只剩局部虹膜可见。

### 3. 向外移动并压扁眼球

v9 将眼球移动到脸部前方，正面完整可见，但侧面形成明显凸出的白色眼球，直接复现用户拒绝的问题。

### 4. 只压扁、不移动

v10 仍然被头部开口遮挡，说明开口边缘、眼球深度和脸部曲面之间不是可通过单一参数协调的关系。

证据：

- `prototype/test_output/contour_boolean_eye_socket_v7_flattened_frame01/front.png`
- `prototype/test_output/contour_boolean_eye_socket_v9_flat_eye_surface_frame01/front.png`
- `prototype/test_output/contour_boolean_eye_socket_v10_flat_eye_surface_frame01/front.png`

## 结论

当前演员头部缺少与 Miku 相同的眼窝/眼睑表面结构。继续移动或缩放现有 `MikuChibiEyeball` 只能在三种失败结果之间切换：凸出、被遮挡、或切口断裂。

## 路线变更

停止继续调整当前眼球深度参数。下一条生产路线应把 Miku 的眼部表面视为一个整体组件，包括：

1. 眼窝/眼睑外壳；
2. 眼白或眼部底面；
3. 虹膜/瞳孔表面；
4. 统一的头骨权重。

先在 Miku 组件自身上验证正面、侧面和头部动画，再把这个整体组件局部适配到演员头部。当前 Boolean 文件和眼球深度实验全部保留为证据，不替换基础演员。
