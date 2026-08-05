# 真实演员 2.5D 五官测试记录（2026-08-02）

> 历史候选测试（2026-08-02）。不作为当前 Actor V1 的五官或运行时入口。

## 目标

在真实演员 `E:/comic/chibi_base_mesh_accurig_rigged_v1.fbx` 上测试浅层 3D 五官，而不是把独立 2D 眼睛和耳朵直接贴到运行时角色上。

本轮只测试眼睛、虹膜、高光、耳朵和耳朵内层；鼻子、嘴巴继续不进入资源系统。所有特征都挂到演员的 `CC_Base_Head`，因此后续头部动画可以带动它们。

## 本轮实现

工具入口：

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\tools\run_accurig_2p5d_feature_test.ps1
```

可选的紧凑眼睛配置：

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\tools\run_accurig_2p5d_feature_test.ps1 -Profile compact_v1
```

输出目录：`prototype/test_output/accurig_2p5d_feature_test_v1/`

## 与上一版诊断的区别

- 眼睛改为浅层椭圆体，不再使用近似球体，减少“眼球漂浮”的感觉；
- 眼睛宽高和间距缩小，先解决“眼睛大于脸”的问题；
- 增加独立虹膜和高光，便于后续替换颜色和形状；
- 耳朵改为更小、更薄的外层与内层组合；
- 所有部件继续绑定到 `CC_Base_Head`；
- 仍然只做静态四方向审查，不接入当前运行时像素包。

## 验收门槛

1. 正面眼睛不能超过脸部轮廓的主要宽度；
2. 侧面眼睛不能明显穿出头部形成大球；
3. 耳朵不能盖住头部轮廓，也不能与头部脱节；
4. 背面不应出现正面五官；
5. `feature_manifest.json` 必须确认父骨骼为 `CC_Base_Head`，并通过自动校验。

本轮只验证“挂载方式和比例是否可控”，不代表最终画风已经通过。通过静态审查后，才进入四方向动画渲染和像素化。

## 本次执行结果

- `soft_anime_v1`：四方向渲染和自动契约校验通过；
- `compact_v1`：四方向渲染和自动契约校验通过；
- 特征父骨骼确认：`CC_Base_Head`；
- 当前结论：可以继续做人工画风审查，但暂不接入正式运行时资源包。
