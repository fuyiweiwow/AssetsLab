# Koban 下载模型演员测试（2026-08-02）

## 测试决定

当前演员的头部比例和表面形状不适合继续外挂程序化五官，因此改为直接测试下载的 Koban 模型作为完整风格演员。

推荐入口文件：

`prototype/assets/external/koban_chibi_base_mesh/Koban Chibi Base Mesh VRM export.blend`

它包含一个角色网格和一个骨架，适合做渲染入口；`Koban Chibi Base Mesh 1.0.blend` 含有较多控制形状和工作控制对象，不作为本轮渲染入口。

## 运行测试

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\tools\run_koban_walk_test.ps1
```

默认使用当前项目一致的 `1.3` 动作幅度，输出：

- 256×256 四方向 × 8 帧渲染：`prototype/test_output/koban_walk_test_v1/`
- 64×64 像素测试包：`prototype/test_output/koban_walk_pixels_v1/`

## 本轮只回答三个问题

1. Koban 的骨骼能否被稳定驱动；
2. 其眼睛、耳朵和头部轮廓在四方向下是否比当前演员更接近目标风格；
3. 经过像素化后，轮廓和脚步是否仍然可读。

通过后再决定是：

- 直接把 Koban 作为新的 3D 演员；或
- 只参考/提取 Koban 的脸部风格，再为项目演员制作服装和身体。

本测试不会覆盖当前 `chibi_accurig_walk_test_v1` 正式运行时包。

## 本次结果

- Koban VRM export 版本成功驱动四方向 × 8 帧程序化走路；
- `1.3` 动作幅度可用，像素化后的轮廓和脚步仍可读；
- 眼睛、眉眼、耳朵属于同一套角色模型，侧面没有外挂眼球的突出问题；
- 当前主要缺点是身体过于素体化，缺少目标概念图中的发型、披风、上衣、腰包和靴子。

阶段结论：Koban 暂时升级为“风格演员候选”，优先级高于当前 AccuRIG 素体。下一步应在 Koban 上验证服装/发型层，或评估把目标服装重建到 Koban 骨架上；当前 AccuRIG 演员保留为技术基线，不立即删除。
