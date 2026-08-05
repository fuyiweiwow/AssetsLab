# 像素演员接入原型测试管线

## 当前状态

Godot 原型的目标版本是 4.6，工程启用 `GL Compatibility`。当前已通过技术验证的运行时包是：

`prototype/assets/characters/runtime/chibi_eyes_ears_walk_v1/`

它验证 4 方向、8 帧、64×64 PNG、最近邻过滤、移动、方向切换和导入缓存。新发布的 `prototype/assets/characters/actor_v1/` 仍是离线 3D 生成基线，尚未自动接入本管线。

## 运行

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_pixel_runtime_pipeline_test.ps1
powershell -ExecutionPolicy Bypass -File .\tools\run_pixel_runtime_godot_test.ps1
```

完整技术闭环：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_pixel_asset_end_to_end.ps1
```

## 验收标准

- 旧管线输出 `SMOKE_TEST_PASS`。
- `PixelRuntimeActor` 能完成四方向移动和方向切换。
- 输出 `PIXEL_RUNTIME_CAPTURE_PASS directions=4 frames=32`。
- 生成 32 张截图到 `prototype/test_output/pixel_runtime_capture_frames/`。
- 运行时图像保持 64×64、透明、最近邻，不发生图层漂移。

## Headless 说明

自动化必须使用 Godot 4.6.2 console executable、`--headless`、Windows/OpenGL 兼容渲染参数和隐藏进程。不要回退到 GUI 可执行文件。

Headless 模式主要验证资源读取、帧选择、移动和输出文件；普通窗口或编辑器预览才用于人工观察实际画面。

## 与 Actor V1 的关系

完成 Actor V1 的 3D→2D 处理后，应新增独立 runtime 目录并先运行本页全部测试，再替换旧包。旧包的通过结果不能直接证明 Actor V1 的像素质量或美术风格合格。
