# 2026-08-03 动作失败修正：演员网格权重

> 历史权重修复记录。本文输出不再是当前运行或生成入口，当前 3D 基线为 `prototype/assets/characters/actor_v1/`。

## 失败证据

Walk/Run 的 Mixamo 动作曲线已经写入演员 `Armature`，但 GIF 中手臂接近 T-Pose、大腿几乎不变形。检查失败版本：

`prototype/test_output/chibi_eyes_ears_mixamo_walk_bound_v2.blend`

## 根因

目标动作驱动的是 `CC_Base_*` 主骨骼，但身体网格 `ChibiBaseMesh_AccuRIG_InputMesh` 缺少关键主骨骼顶点组。网格只有上臂/前臂/小腿的部分 `Twist` 权重，没有对应的主上臂、前臂、大腿、小腿、脚掌和脚趾权重，因此骨骼旋转值变化不会完整传递到网格。

## 修复方法

新增工具：

`tools/blender/repair_accurig_mesh_weights.py`

它不会覆盖原演员文件，而是：

1. 将 `UpperarmTwist` / `ForearmTwist` 权重转移到对应的 `Upperarm` / `Forearm` 主骨骼。
2. 根据顶点到骨骼线段的最近距离，将 `CalfTwist02` 权重重新分配到 `Thigh`、`Calf`、`Foot`、`ToeBase`。
3. 保存新的演员版本，并生成同名 JSON 报告。

修复演员：

`prototype/assets/characters/generated/chibi_eyes_ears_pixel_walk_source_v2_reweighted.blend`

左右大腿、 小腿、脚掌、脚趾、上臂、前臂均已出现实际顶点权重。

## 验证结果

- Walk 绑定：`prototype/test_output/chibi_eyes_ears_mixamo_walk_bound_v3_reweighted.blend`
- Walk 四向 GIF：`prototype/test_output/chibi_eyes_ears_mixamo_walk_pixels_v3_reweighted/`
- Run 绑定：`prototype/test_output/chibi_eyes_ears_mixamo_run_bound_v3_reweighted.blend`
- Run 四向 GIF：`prototype/test_output/chibi_eyes_ears_mixamo_run_pixels_v3_reweighted/`

当前验证重点是：手臂不再固定为 T-Pose，腿部网格会随 Mixamo 的大腿/小腿动作变形。下一轮应重点观察膝盖方向、脚掌接地和腿根是否开裂；如仍有问题，应调整权重分界或使用手工权重，而不是继续更换动作源。
## 2026-08-04 后续修复：髋部串权与 Mixamo 坐标轴

### 新发现

首次转移权重后，部分小腿区域同时保留了 `CC_Base_Hip` 权重。髋部权重会抵消大腿/小腿的局部动作，使大腿看起来不参与行走。现已在修复脚本中先合并这部分髋部权重，再按腿段最近距离分配到 `Thigh / Calf / Foot / ToeBase`。

### 当前修复工具

- `tools/blender/repair_accurig_mesh_weights.py`
- 当前演员基线：`prototype/assets/characters/generated/chibi_eyes_ears_pixel_walk_source_v3_reweighted_hipfix.blend`

### Mixamo 重定向调整

`tools/blender/retarget_mixamo_to_accurig_actor.py` 当前使用首帧相对旋转差值，并加入 Mixamo Y-up 到演员 Z-up 的全局 X 轴转换。转换角度可通过 `--global-axis-deg` 调整，默认 `90`。这不是重新标定五官或重新绑定 Mixamo，而是动作导入时的坐标转换参数。

### 当前测试结果

- Walk 渲染：`prototype/test_output/chibi_eyes_ears_mixamo_walk_fourway_v6_globalaxis/`
- Walk 像素 GIF：`prototype/test_output/chibi_eyes_ears_mixamo_walk_pixels_v6_globalaxis/`
- Run 渲染：`prototype/test_output/chibi_eyes_ears_mixamo_run_fourway_v6_globalaxis/`
- Run 像素 GIF：`prototype/test_output/chibi_eyes_ears_mixamo_run_pixels_v6_globalaxis/`

侧视图已能观察到腿部前后交替和手臂前后摆动；正视图动作变化较小，因为主要运动发生在前后深度轴。跑步版本仍需人工确认摆臂幅度与腿根是否自然，暂不把它标记为最终动作。

## 2026-08-04 重定向根因修正

对 v6 进行骨骼审计后确认：动作曲线确实存在，22 根 `CC_Base_*` 目标骨骼也在帧间旋转，网格拥有对应权重；错误不在“没有使用骨骼动画”，而在于错误地减去了 Mixamo 第 1 帧的绝对姿势。该帧本身是手臂下垂、膝盖已弯曲的动作姿势，而演员基线是 T Pose，减掉它会把手臂重新放回 T Pose。

当前脚本默认改为：

- `source_pose_mode=absolute`：保留 Mixamo 初始姿势偏移；
- `global_axis_deg=0`：使用 Blender FBX 导入器已经完成的坐标转换，不再重复旋转。

最终测试输出：

- `prototype/test_output/chibi_eyes_ears_mixamo_walk_bound_v11_final.blend`
- `prototype/test_output/chibi_eyes_ears_mixamo_walk_pixels_v11_final/`
- `prototype/test_output/chibi_eyes_ears_mixamo_run_bound_v11_final.blend`
- `prototype/test_output/chibi_eyes_ears_mixamo_run_pixels_v11_final/`

## 2026-08-04 上肢中立姿势修正

v11 的手臂虽然不再是 T Pose，但由于直接保留源动作的初始上肢姿势，手会偏到身体前方。当前脚本对上臂增加左右镜像的局部 Z 轴中立姿势修正，默认 `arm_neutral_deg=60`；摆动部分仍使用 Mixamo 首帧相对差值，腿部继续使用绝对姿势方案。

最新输出：

- `prototype/test_output/chibi_eyes_ears_mixamo_walk_bound_v13_armneutral.blend`
- `prototype/test_output/chibi_eyes_ears_mixamo_walk_pixels_v13_armneutral/`
- `prototype/test_output/chibi_eyes_ears_mixamo_run_bound_v13_armneutral.blend`
- `prototype/test_output/chibi_eyes_ears_mixamo_run_pixels_v13_armneutral/`
