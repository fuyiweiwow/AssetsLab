# Miku 眼部整体组件移植测试

日期：2026-08-02

## 目标

尝试将 Miku 的眼球 `eyeball_1_0_node` 与皮肤材质眼部候选 `eye_007_22_0_node` 作为一个整体移植到演员头部。

## 发现

Miku 模型中确实存在一个独立的脸部皮肤眼部对象：

- `eye_007_22_0_node`
- 材质：`face_CHM_SKIN_mat`
- 顶点数：227
- 面数：324

它不是单纯的眼球，尺寸也大于 `eyeball_1_0_node`，符合眼窝/眼框候选的特征。

## 测试文件

- `prototype/assets/characters/generated/miku_eye_socket_shell_transfer_v1.blend`
- `prototype/test_output/miku_eye_socket_shell_transfer_v1/front.png`
- `prototype/test_output/miku_eye_socket_shell_transfer_v1/right.png`
- 脚本：`tools/blender/transfer_miku_eye_socket_shell_test.py`

## 结果

失败。直接把 `eye_007_22_0_node` 的世界坐标按 X/Z/Y 范围缩放到演员头部后，出现明显三角折叠和尖刺。原因是 Miku 眼部外壳的原始面流、深度方向和演员头部坐标不兼容，不能直接做 3D 仿射移植。

## 路线决策

保留 Miku 的正面轮廓和材质意图，但放弃原始面流直接移植。下一步改为：

1. 从 `eye_007_22_0_node` 提取正面 X/Z 投影轮廓或渲染遮罩。
2. 使用轮廓重建连续的浅层眼窝外壳。
3. 用演员头部表面控制 Y 深度，不复制 Miku 的原始三角面。
4. 将新外壳、眼白、虹膜统一绑定到 `CC_Base_Head`。

当前基础演员和之前通过动画测试的 v6 候选均不被覆盖。
