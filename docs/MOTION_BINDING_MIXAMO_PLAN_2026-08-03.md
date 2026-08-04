# 动作绑定与 Mixamo 重定向记录

## 当前结论

本项目的眼睛、眉毛和耳朵位置标定与动作来源无关，不需要因为改用 Mixamo 而重新标定。它们当前都挂在演员骨架的 `Armature / CC_Base_Head` 上；只要新的动作最终驱动同一套演员骨架，三类五官会继续跟随头部。

如果 Mixamo 能识别已有绑定 FBX，应优先使用“上传已绑定角色”并让 Mixamo 映射骨骼。只有在放弃现有 AccuRIG 骨架、改用 Mixamo 自动重新绑骨时，才需要重新放置 Mixamo 的手腕、肘、膝和胯部标记。那是骨骼标记，不是五官标定。

## 本轮绑定测试

- 演员基线：`prototype/assets/characters/generated/chibi_eyes_ears_pixel_walk_source_v1.blend`
- 动作源：`prototype/assets/characters/generated/catwalk-loop-378982.fbx`
- 绑定脚本：`tools/blender/bind_motion_to_accurig_actor.py`
- 四向渲染脚本：`tools/blender/render_bound_fourway_test.py`
- Mixamo 重定向脚本：`tools/blender/retarget_mixamo_to_accurig_actor.py`
- 绑定结果：`prototype/test_output/chibi_eyes_ears_catwalk_bound_v1.blend`
- 渲染结果：`prototype/test_output/chibi_eyes_ears_catwalk_fourway_v1/`
- 像素结果：`prototype/test_output/chibi_eyes_ears_catwalk_pixels_v1/`

动作源和演员均为 101 根 AccuRIG 骨骼。本次成功复制 1010 条姿态曲线，动作范围为第 1 至 78 帧。四个方向各输出 8 帧，并降采样为 64×64 像素帧。

## 验证结果

- 演员网格仍由 `Armature` 驱动。
- 眼睛、耳朵均保持 `CC_Base_Head` 骨骼父级。
- 眉毛由测试渲染器生成，并同样挂到 `CC_Base_Head`。
- 正面与侧面观察到五官随头部同步，没有出现五官脱离。
- 当前动作是绑定闭环验证用的 Catwalk 动作，不代表最终 Mixamo 普通行走动作已经接入。

## 大腿不动问题修正

初版动作复制器只复制了 FBX 的 `rotation_quaternion` 曲线，但目标演员骨骼仍处于 Blender 默认的 XYZ Euler 旋转模式，造成“曲线已复制、骨骼看似没有动画”的静默失败。绑定器现已根据动作曲线自动切换目标骨骼旋转模式为 `QUATERNION`。修正后左右大腿在采样帧中均有变化，渲染结果已重新输出为 `chibi_eyes_ears_catwalk_*_v2_quaternion`。

## 替换为 Mixamo 动作时

1. 优先上传已有绑定的演员 FBX，不要重新自动绑骨。
2. 若 Mixamo 返回可映射骨架，下载动作或动作 FBX。
3. 将 Mixamo 骨骼映射到演员的 `CC_Base_*` 骨骼，再运行同一套四向渲染和像素化测试。
4. 重点检查膝盖方向、脚掌接地、根骨位移和头部五官跟随。
5. 只有映射失败并决定重新自动绑骨时，才创建新的骨架版本，不覆盖当前演员基线。

Mixamo FBX 下载后可使用：

```powershell
& E:\Env\Blender\blender.exe --background --python tools\blender\retarget_mixamo_to_accurig_actor.py -- `
  --actor prototype\assets\characters\generated\chibi_eyes_ears_pixel_walk_source_v1.blend `
  --mixamo-fbx E:\Env\Assets\Mixamo_Walk.fbx `
  --output prototype\test_output\chibi_eyes_ears_mixamo_walk_bound_v1.blend
```

该工具识别标准 `mixamorig:` 骨骼名，通过姿态空间 Copy Rotation 逐帧烘焙到 `CC_Base_*` 骨架；如果 Mixamo 文件没有标准骨骼名或映射数量不足，会直接失败并报告，不会生成半成品。

## 可复现命令

```powershell
& E:\Env\Blender\blender.exe --background --python tools\blender\bind_motion_to_accurig_actor.py -- `
  --actor prototype\assets\characters\generated\chibi_eyes_ears_pixel_walk_source_v1.blend `
  --motion-fbx prototype\assets\characters\generated\catwalk-loop-378982.fbx `
  --output prototype\test_output\chibi_eyes_ears_catwalk_bound_v1.blend

& E:\Env\Blender\blender.exe --background --python tools\blender\render_bound_fourway_test.py -- `
  --input-blend prototype\test_output\chibi_eyes_ears_catwalk_bound_v1.blend `
  --output prototype\test_output\chibi_eyes_ears_catwalk_fourway_v1 `
  --frame-count 8 --face-style 0 --soft-toon-lighting

python tools\process_accurig_walk_pixels.py `
  --render-dir prototype\test_output\chibi_eyes_ears_catwalk_fourway_v1 `
  --output-dir prototype\test_output\chibi_eyes_ears_catwalk_pixels_v1 `
  --size 64 --frame-count 8 --fps 8
```

## 2026-08-03 Mixamo Walk/Run 实测记录

### 下载文件

- `E:\Env\Assets\Mixamo_Standard_Walk.fbx`：FBX Binary、Without Skin、30 FPS、Keyframe Reduction=none、In Place。
- `E:\Env\Assets\Mixamo_Run.fbx`：同样设置。
- Walk 审计结果：65 根源骨骼，动作帧 `1-71`，520 条曲线。
- Run 审计结果：65 根源骨骼，动作帧 `1-43`，520 条曲线。

### 重定向结果

使用 `tools/blender/retarget_mixamo_to_accurig_actor.py`，两个动作均成功映射 22 根 `mixamorig:* -> CC_Base_*` 骨骼。

初版使用绝对 Copy Rotation 时，目标演员在渲染中保持接近 T-Pose。原因是 Mixamo 与 AccuRIG 的骨骼休息姿态轴不同，直接复制绝对四元数并不能得到正确的目标姿态。

当前版本改为：

1. 读取 Mixamo 首帧与当前帧的旋转差值。
2. 将旋转差值叠加到演员自身的休息姿态。
3. 逐帧写入演员动作，并保持根骨骼原地不平移，速度交给后续运行时/像素资源工具控制。

### 当前测试输出

- Walk 绑定：`prototype/test_output/chibi_eyes_ears_mixamo_walk_bound_v2.blend`
- Walk 四向渲染：`prototype/test_output/chibi_eyes_ears_mixamo_walk_fourway_v2/`
- Walk 像素表：`prototype/test_output/chibi_eyes_ears_mixamo_walk_pixels_v2/`
- Run 绑定：`prototype/test_output/chibi_eyes_ears_mixamo_run_bound_v2.blend`
- Run 四向渲染：`prototype/test_output/chibi_eyes_ears_mixamo_run_fourway_v2/`
- Run 像素表：`prototype/test_output/chibi_eyes_ears_mixamo_run_pixels_v2/`

两组动作均已看到腿部、膝盖、手臂和躯干的逐帧变化；眼睛、眉毛、耳朵继续跟随 `CC_Base_Head`，没有重新标定。

### 可复现命令

```powershell
& E:\Env\Blender\blender.exe --background --python tools\blender\retarget_mixamo_to_accurig_actor.py -- `
  --actor prototype\assets\characters\generated\chibi_eyes_ears_pixel_walk_source_v1.blend `
  --mixamo-fbx E:\Env\Assets\Mixamo_Standard_Walk.fbx `
  --output prototype\test_output\chibi_eyes_ears_mixamo_walk_bound_v2.blend

& E:\Env\Blender\blender.exe --background --python tools\blender\retarget_mixamo_to_accurig_actor.py -- `
  --actor prototype\assets\characters\generated\chibi_eyes_ears_pixel_walk_source_v1.blend `
  --mixamo-fbx E:\Env\Assets\Mixamo_Run.fbx `
  --output prototype\test_output\chibi_eyes_ears_mixamo_run_bound_v2.blend
```
## 2026-08-04 当前状态补充

Mixamo 的 Walk 和 Run 均已下载并能够映射到现有 `Armature / CC_Base_*` 演员骨架。当前不需要重新在 Mixamo 标定：只要继续使用同一套演员骨架，眼睛、眉毛和耳朵会继续跟随 `CC_Base_Head`。

动作导入的当前入口：

```powershell
& E:\Env\Blender\blender.exe --background --python tools\blender\retarget_mixamo_to_accurig_actor.py -- `
  --actor prototype\assets\characters\generated\chibi_eyes_ears_pixel_walk_source_v3_reweighted_hipfix.blend `
  --mixamo-fbx E:\Env\Assets\Mixamo_Standard_Walk.fbx `
  --global-axis-deg 90 `
  --output prototype\test_output\chibi_eyes_ears_mixamo_walk_bound_v6_globalaxis.blend
```

当前结论：演员权重问题已修复，动作曲线也已写入目标骨架；Mixamo 与演员的轴向差异仍会影响正面观看时的摆臂观感，因此下一步应以 GIF 逐帧检查摆臂平面、膝盖方向和腿根连续性，再决定是否增加动作幅度参数。

## 2026-08-04 重定向修正版

前一版将 Mixamo 第 1 帧当成无动作基准，导致演员的 T Pose 被保留，且掩盖了 Mixamo 原本的下垂手臂姿势。当前脚本已改为保留源动作的绝对姿势偏移，并将额外全局轴修正默认设为 `0°`，因为 Blender FBX 导入已经完成 Y-up 到场景坐标的转换。

验证结果：Walk 和 Run 的目标骨架均有 22 根映射骨骼和完整动作曲线；最终 GIF 位于 `prototype/test_output/chibi_eyes_ears_mixamo_walk_pixels_v11_final/` 与 `prototype/test_output/chibi_eyes_ears_mixamo_run_pixels_v11_final/`。后续检查重点是视觉上的膝盖弯曲方向和腿根连续性，不再重复 Mixamo 五官或骨骼标定。

### 上肢中立姿势

v11 中手臂仍偏向身体前方。当前已增加 `arm_neutral_deg=60` 的左右镜像上臂修正：Walk/Run 的起始手臂位于身体两侧，动作曲线只负责前后摆动。最新测试为 `prototype/test_output/chibi_eyes_ears_mixamo_walk_pixels_v13_armneutral/` 和 `prototype/test_output/chibi_eyes_ears_mixamo_run_pixels_v13_armneutral/`。
