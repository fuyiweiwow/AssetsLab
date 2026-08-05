# 像素资源完整闭环验收

当前闭环用于验证“像素运行时技术管线可用”，不是最终 Actor V1 的美术验收。

## 运行

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_pixel_asset_end_to_end.ps1
```

它依次：

1. 检查运行时包 manifest、4 方向、8 帧、64×64 尺寸、透明通道和 sprite sheet；
2. 运行 Godot PNG 导入、`AnimatedSprite2D`、可复用演员和导入缓存测试；
3. 运行旧原型回归并检查移动、方向切换和截图输出。

## 当前验证对象

当前脚本固定验证：

`prototype/assets/characters/runtime/chibi_eyes_ears_walk_v1/`

这是旧的技术基线，不代表 Actor V1 已完成像素化，也不代表最终角色外观已经定稿。Actor V1 接入时必须新增或明确替换 runtime 根目录，并在 manifest 中记录来源 Blend、相机合同、采样帧和像素处理版本。

## 通过标准

```text
PIXEL_ASSET_END_TO_END_PASS package=1 godot=1 integration=1
```
