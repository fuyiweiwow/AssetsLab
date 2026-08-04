# 眼窝实验记录：连续轮廓 Boolean 切口

日期：2026-08-02

## 背景

此前在演员原头部网格上直接执行 MCP Inset/Extrude，虽然工具返回成功，但产生了矩形面片、碎裂边界和侧面突起。原因是原头部面流没有为动漫眼窝设计，不能靠继续调整 Inset 参数修复。

## 本轮测试

从 Miku 眼球模型提取正面 X/Z 轮廓，映射到演员当前眼球位置，生成封闭 16 点棱柱，沿 Y 轴穿过头部，使用 Blender Exact Boolean Difference 在干净演员副本上切出眼窝。

测试文件：

- `prototype/assets/characters/generated/contour_boolean_eye_socket_v1.blend`
- `prototype/test_output/contour_boolean_eye_socket_v1/front.png`
- `prototype/test_output/contour_boolean_eye_socket_v1/right.png`
- 脚本：`tools/blender/create_contour_boolean_socket_test.py`

## 结果

- 通过：眼窝轮廓连续，不再出现 Inset 方案的锯齿碎片。
- 通过：正面看眼球进入头部，而不是整块矩形浮在脸上。
- 部分通过：侧面能看到真实切口，但切口边缘偏硬、带明显多边形感。
- 未通过：眼球白色区域和动漫眼睑/眼框层尚未恢复，风格还不能作为最终资源。
- 未验证：绑定动画下的切口是否稳定。

## 决策

该 Boolean 文件仅作为实验候选，不替换基础演员，也不覆盖旧版本。当前结论是：

1. “原网格直接 Inset”路线停止。
2. “轮廓驱动的连续切口”是可继续发展的方向。
3. 下一步是在切口边缘增加圆滑、连续的眼睑/眼框层，再重新调整眼球深度。
4. 通过正面、侧面和头部动画测试后，才考虑合并回演员主文件。
