# 3D 演员到像素资源阶段检查点

日期：2026-08-01

## 阶段结论

本阶段已经完成“3D 演员 → 3D 渲染 → 四方向测试 → 像素化输出”的最小闭环，可以进入 `pixel_asset_test` 阶段。当前成果属于技术闭环，不代表角色已经达到最终生产质量。

## 已验证内容

- 使用 `chibi-base-meshblender` 作为当前候选模型，而不是从零搭建的废案演员。
- 完成 AccuRIG 标注、FBX 导出、Blender 后台导入和四方向渲染测试。
- 完成 128 像素最近邻像素化测试，并生成四方向 sprite sheet/GIF。
- 确认原始导出文件的主腿骨骼缺少直接权重：左右 Thigh、Calf、Foot 直接权重均为 0。
- 创建重加权诊断副本，确认大腿和脚掌能够参与运动。
- 创建小腿弯曲方向反转测试，确认膝盖反向问题可以通过动作符号修正。

## 当前已知限制

- 重加权副本的腿根存在权重过渡不连续，运动时有开裂感；它是诊断版本，不是最终生产绑定。
- 正式 NormalWalk 仍需重新绑定或修正重定向后的 Calf 局部轴/动作符号。
- 当前像素化输出用于验证管线和画面稳定性，尚未进入正式调色、轮廓清理和资源命名规范阶段。

## 关键外部测试文件

- `E:\comic\chibi_base_mesh_accurig_rigged_v1.fbx`：原始导出文件。
- `E:\comic\chibi_base_mesh_accurig_reweighted_legs_test.fbx`：重加权诊断文件。
- `E:\comic\chibi_base_mesh_accurig_reweighted_legs_test.blend`：重加权 Blender 诊断场景。
- `E:\WorkProject\AssetsLab\prototype\test_output\accurig_reweighted_legs_reverse_knee_pixels\`：反向膝盖像素测试。

## 下一阶段入口

新分支 `pixel_asset_test` 用于测试：固定相机合同、渲染分辨率、最近邻像素化、透明背景、四方向帧命名、调色和批量导出。腿部正式权重修复应保留为独立任务，避免把诊断权重误当成最终角色资产。
