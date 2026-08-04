# 像素资源完整闭环验收

当前阶段先验收“流程可用”，再处理角色细节。统一入口是：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_pixel_asset_end_to_end.ps1
```

它按以下顺序执行：

1. 校验运行时包的 manifest、四方向、8 帧、64×64 尺寸、透明通道、sprite sheet 和 GIF。
2. 运行 Godot 文件读取、AnimatedSprite2D、可复用演员、导入缓存场景测试。
3. 运行旧原型回归，并用 `--pixel-runtime-actor` 接入原有移动和逐帧截图管线。

通过标准是最后输出：

```text
PIXEL_ASSET_END_TO_END_PASS package=1 godot=1 integration=1
```

当前测试资源是 `chibi_eyes_ears_walk_v1`，使用已验证的 3D 眼睛与耳朵组合，属于技术基线，不代表最终角色外观已经定稿。后续更换模型或动作时，先运行这个闭环；只有闭环通过后，再进入头部、四肢、五官和配色细节修正。
