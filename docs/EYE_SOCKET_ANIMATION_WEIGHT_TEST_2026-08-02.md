# 眼窝动画权重测试记录

日期：2026-08-02

## 测试目的

验证连续轮廓 Boolean 眼窝在头部骨骼动画下是否会撕裂，以及眼球组件是否会脱离眼窝。

## 失败基线

文件：`prototype/assets/characters/generated/contour_boolean_eye_socket_v1_headturn_test.blend`

测试动作：`CC_Base_Head` 左右约 22° 转动。

结果：Boolean 切口边缘撕裂；眼球组件没有跟随头部，转头后出现错位。

## 修复方式

在干净 Boolean 候选上：

1. 将眼窝周边区域 1,029 个顶点统一绑定到 `CC_Base_Head`。
2. 将 `MikuChibiEyeball` 的 130 个顶点统一绑定到 `CC_Base_Head`。
3. 保持 Boolean 切口几何不变。
4. 使用同样的 1、12、24、36 帧头部转动测试。

## 修复候选

- 模型：`prototype/assets/characters/generated/contour_boolean_eye_socket_v3_headturn_test.blend`
- 帧 12 正面：`prototype/test_output/contour_boolean_eye_socket_v3_headturn_frame12/front.png`
- 帧 24 正面：`prototype/test_output/contour_boolean_eye_socket_v3_headturn_frame24/front.png`
- 帧 12 侧面：`prototype/test_output/contour_boolean_eye_socket_v3_headturn_frame12/right.png`

## 结果

- Boolean 边界撕裂：通过本测试。
- 眼球跟随头骨：通过本测试。
- 侧面无明显脱离：通过本测试。
- 静态美术质量：未通过，眼窝边缘仍偏硬、多边形感明显。

## 决策

该版本是“动画稳定候选”，不是最终演员版本。后续美术优化必须在不破坏头骨统一权重的前提下进行；不要再对它直接执行原网格 Inset，也不要使用会产生大厚度的实体环形眼睑层。
