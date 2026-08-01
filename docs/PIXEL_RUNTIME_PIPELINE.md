# 像素演员接入原型测试管线

## 目的

把 `PixelRuntimeActor` 接入现有的 Godot 原型，而不是只在独立测试场景中验证资源。默认模式继续使用旧的分层 `Player`；测试参数 `--pixel-runtime-actor` 会在 `main.tscn` 启动时替换为新的运行时演员。

## 运行

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_pixel_runtime_pipeline_test.ps1
```

测试脚本会先运行旧的 `smoke_test.gd`，确认旧管线没有回归，然后运行 `capture_test.gd --pixel-runtime-actor`，检查新演员的移动和四方向动画。

## 验收标准

- 旧管线输出 `SMOKE_TEST_PASS`。
- 新演员输出四个方向的移动通过信息。
- 新演员输出 `PIXEL_RUNTIME_CAPTURE_PASS directions=4 frames=32`。
- 生成 32 张 960x600 PNG 到 `prototype/test_output/pixel_runtime_capture_frames/`。
- `PixelRuntimeActor` 使用 `TEXTURE_FILTER_NEAREST`，动画帧仍来自 64x64 运行时资源。

## Headless 说明

Godot 4.7 的 headless dummy 渲染器不能读取窗口纹理，因此像素演员模式会从当前 `AnimatedSprite2D` 帧生成截图；这仍会验证移动、方向切换、帧读取和输出文件。编辑器或普通窗口运行时，原有截图函数仍读取实际窗口纹理。

当前结果：Godot 4.7 下旧管线回归通过，新演员四方向移动和 32 帧输出通过。Godot 4.6.2 安装后需用同一命令复测。
