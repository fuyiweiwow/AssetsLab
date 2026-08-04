# 眼窝贴面细节测试记录

日期：2026-08-02

## 目标

在已经通过头部转动稳定性测试的 Boolean 眼窝上，增加 Miku 轮廓驱动的上眼睑细节，同时避免实体眼睑层在侧面浮出。

## 测试方式

1. 从 Miku 眼球轮廓提取左右上半段轮廓。
2. 去掉中央内眼角连接，避免形成眼镜框。
3. 生成窄条状装饰网格。
4. 使用 Shrinkwrap Project 沿 Y 轴投射到演员头部表面。
5. 应用 Shrinkwrap 后，再统一绑定到 `CC_Base_Head`。
6. 通过静态正面、静态侧面和约 22° 转头测试。

## 候选文件

- 模型：`prototype/assets/characters/generated/contour_boolean_eye_socket_v6_shrinkwrapped_eyelid_offset.blend`
- 动画模型：`prototype/assets/characters/generated/contour_boolean_eye_socket_v6_shrinkwrapped_headturn_test.blend`
- 脚本：`tools/blender/create_shrinkwrapped_eyelid_decal_test.py`
- 静态正面：`prototype/test_output/contour_boolean_eye_socket_v6_shrinkwrapped_frame01/front.png`
- 静态侧面：`prototype/test_output/contour_boolean_eye_socket_v6_shrinkwrapped_frame01/right.png`
- 转头正面：`prototype/test_output/contour_boolean_eye_socket_v6_shrinkwrapped_frame12/front.png`

## 验收结果

- 正面左右眼睑分离：通过。
- 侧面明显外凸：通过，未观察到实体挂边。
- 转头跟随头骨：通过。
- Miku 风格还原度：部分通过，线条仍需美术调整。
- 真实眼窝几何质量：不作为本贴面层的目标；真实凹陷由 Boolean 候选提供。

## 当前决策

该版本作为“动画稳定 + 贴面细节候选”保存，不替换基础演员。实体环形眼睑方案停止；后续若继续提升风格，应优先调整贴图/颜色/线宽，而不是增加 Y 方向实体厚度。
