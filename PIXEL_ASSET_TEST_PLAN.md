# pixel_asset_test 阶段计划

## 目标

把已经打通的 3D 渲染到像素化流程，整理成可重复验收的游戏资源生成流程。

## 第一条基线

当前使用重加权腿部诊断角色的反向膝盖测试作为输入样本：

`prototype/test_output/accurig_reweighted_legs_reverse_knee_pixels/`

这不是最终生产角色，只是用于验证资源格式和导出合同。

## 验收合同 v1

- 方向：`front`、`right`、`back`、`left`；
- 每个方向：8 帧；
- 单帧尺寸：128×128；
- 文件格式：RGBA PNG，保留透明背景；
- 文件命名：`{direction}/frame_{index:02d}/pixel.png`；
- 每个方向同时生成一个 sprite sheet 和 GIF 预览；
- `manifest.json` 必须记录源渲染目录、尺寸、方向、帧数和透明边界；
- 资源验证通过后，才进入调色、轮廓清理和运行时导入测试。

## 当前已知限制

本阶段只验收资源管线，不把腿根开裂、膝盖方向和权重质量标记为已解决。正式角色绑定修复仍应在独立的 Blender/AccuRIG 任务中完成。

## 后续任务清单

### A. 像素资源测试

- [x] 建立四方向、8 帧、128×128、RGBA 的基础验收合同；
- [x] 添加像素资源验证工具；
- [x] 检查画布居中、上下裁切和脚底基线；
- [x] 比较 128、64、32 像素规格；
- [x] 建立临时调色板、轮廓线和阴影规则（诊断版）；
- [x] 输出运行时 sprite sheet、GIF 和逐帧 PNG（测试包）；
- [x] 在 Godot headless 中测试 PNG 文件读取、纹理创建和尺寸；
- [x] 在 Godot headless 中动态创建 AnimatedSprite2D 并测试 8 帧播放容器；
- [x] 在 Godot headless 场景中测试四个 AnimatedSprite2D、最近邻过滤和实际播放状态；
- [ ] 在 Godot 编辑器导入缓存就绪后测试可视化场景播放。

### B. 3D 演员完善

- [ ] 修复髋部到大腿根的权重过渡；
- [ ] 修复大腿、小腿和脚掌的正式权重；
- [ ] 校正膝盖弯曲方向和小腿局部轴；
- [ ] 测试 NormalWalk、站立、抬腿和转身；
- [ ] 重新生成四方向像素资源。

### C. 随机五官 3D 生成

- [ ] 建立眼睛、眉毛、嘴巴和腮红模块；
- [ ] 定义五官挂点和尺寸规范；
- [ ] 制作随机组合与随机种子规则；
- [ ] 批量渲染并检查四方向稳定性；
- [ ] 输出五官配置 manifest。

### D. 自动化与资源整理

- [ ] 一键完成 Blender 渲染、像素化和资源验证；
- [ ] 自动生成 manifest 和预览图；
- [ ] 增加透明通道、帧数、尺寸、裁切和脚底漂移检查；
- [ ] 固化文件命名和目录结构；
- [ ] 编写最终使用指南。

## A-3 画布与脚底基线检查结果

检查对象：

`prototype/test_output/accurig_reweighted_legs_reverse_knee_pixels/`

检查标准：角色横向居中、主体不被裁切、同一方向的脚底高度稳定、四方向帧数和尺寸一致。结果将在 `pixel_asset_test` 分支的验证记录中更新。

验证结果：通过。当前基线为 4 个方向、32 帧、128×128 RGBA PNG；透明边界与 manifest 一致，横向中心偏差在 2 像素以内，脚底基线漂移不超过 2 像素，主体高度漂移不超过 3 像素，未发现裁切。

## A-4 输出尺寸比较结果

同一组渲染帧已分别输出到：

- `prototype/test_output/pixel_asset_size_128/`；
- `prototype/test_output/pixel_asset_size_64/`；
- `prototype/test_output/pixel_asset_size_32/`。

三种规格均通过自动验收。以 `right/frame_00` 为例，角色有效透明边界分别为：

- 128 画布：49×100 像素；
- 64 画布：24×50 像素；
- 32 画布：12×24 像素。

视觉比较结论：128 适合作为较大尺寸母版和人工检查规格；64 仍能保留身体、腿部和步态轮廓，适合作为当前运行时测试规格；32 下头部、腿部和脚掌细节明显合并，暂不作为主资源规格。当前建议采用 `128 母版 → 64 运行时资源`，32 仅保留为缩略图或低分辨率实验。

## A-5 调色板与轮廓测试结果

已用 `tools/apply_pixel_style_test.py` 对 64 像素版本生成诊断样式：

`prototype/test_output/pixel_asset_style_test_64/`

针对原始渲染边缘发糊的问题，又生成了二值透明边缘版本：

`prototype/test_output/pixel_asset_hard_style_test_64/`

当前临时规则为：

- 轮廓：深蓝灰 `#1F1E2B`，通过透明轮廓膨胀生成 1 像素外轮廓；
- 阴影：`#67626F`；
- 主体：`#A9A6AE`；
- 亮面：`#DAD6DE`；
- 高光：`#F2EEF5`；
- 透明区域继续保持 RGBA 透明；
- 边缘透明度阈值为 128，输出只保留透明和完全不透明两级，避免半透明抗锯齿造成模糊。

原始样式中单帧存在 46 个透明度等级；硬边版本已降为 2 个透明度等级（0/255），并通过 4 方向 × 8 帧的资源验证。轮廓能够把身体、腿部和脚掌从透明背景中分离出来。颜色目前只作为灰模诊断基线，尚未锁定为最终角色配色。

## A-6 Blender Freestyle 轮廓对照测试

当前侧视手部轮廓问题已使用 Blender 内置 Freestyle 做对照。Freestyle 在 Blender 渲染阶段根据可见网格边缘生成轮廓，测试参数为深蓝灰线条、绝对线宽 2 像素，并保留当前反向小腿动作。

测试输出：

- 原生 256 渲染：`prototype/test_output/accurig_freestyle_walk_test/`；
- 64 像素版本：`prototype/test_output/accurig_freestyle_pixels_64/`；
- 硬边 64 像素版本：`prototype/test_output/accurig_freestyle_hard_pixels_64/`。

三组结果均通过资源验收。Freestyle 比纯后处理轮廓更稳定地保留了手臂外缘，但如果手在侧视投影中被躯干遮挡，Freestyle 也无法生成被遮挡部分的分隔线。因此最终方案仍需在 3D 姿态上让手臂稍微错开，或把手臂单独渲染为可控图层。当前实现已加入 `tools/blender/render_accurig_chibi_walk_test.py --freestyle`，作为后续批量渲染选项。

## B-1 走路幅度对照测试

在相同的 Freestyle、反向小腿和 64 像素导出条件下，生成了两组幅度测试：

- `prototype/test_output/accurig_freestyle_walk_amp150_hard_pixels_64/`；
- `prototype/test_output/accurig_freestyle_walk_amp200_hard_pixels_64/`。

两组均通过 4 方向 × 8 帧资源验收。结果判断：

- `amplitude=1.5`：比默认 1.0 更容易观察大腿、膝盖和手臂摆动，但视觉上已经接近快走/小跑；
- `amplitude=2.0`：可以作为极限诊断值，但会放大腿根开裂、腿部穿插和脚掌问题，不作为正式走路默认值。

补充判断：从视觉节奏看，`amplitude=1.5` 已经接近快走/小跑，而不是普通 Walk。它可以作为未来 `jog` 或 `run` 的候选起点，但当前仍缺少专门的步频、身体前倾和腾空相位控制，暂不标记为正式跑步动作。

## B-2 走路幅度微调结果

在 `amplitude=1.2` 和 `amplitude=1.3` 下重新渲染并完成像素化验收：

- `prototype/test_output/accurig_freestyle_walk_amp120_hard_pixels_64/`；
- `prototype/test_output/accurig_freestyle_walk_amp130_hard_pixels_64/`。

两组均通过 4 方向 × 8 帧验证。视觉判断：`1.2` 保留了普通 Walk 的节奏，同时比 1.0 更容易观察大腿运动；`1.3` 更有力但仍可作为当前角色的 Walk。根据当前观感，暂时把 `amplitude=1.3` 设为项目 Walk 基线，`1.2` 作为保守对照，`1.5` 以上留给慢跑/跑步候选测试。

动作幅度通过渲染工具参数传入，不写死在动画资源中：

```powershell
blender.exe --background --python tools/blender/render_accurig_chibi_walk_test.py -- `
  --fbx actor.fbx --output test_output/walk_amp130 --amplitude 1.3
```

之后可以把 `amplitude` 放入 Walk/Run 的动作配置 manifest，由批量导出工具读取。

## 后续跑步动作规划

跑步不应简单地把走路 `amplitude` 无限放大。需要单独建立 `run` 动作配置，至少包含：更高步频、更大的大腿摆幅、更高的膝盖抬升、更明显的脚掌离地、身体前倾和更强的反向手臂摆动。建议先完成正式走路绑定和 64 像素导入，再增加 8 帧跑步诊断，之后根据画面稳定性决定是否扩展到 12 帧或 16 帧。

## A-7 运行时测试包与 Godot 文件读取结果

已使用当前 `amplitude=1.3` 的 Freestyle 硬边像素结果生成运行时测试包：

`prototype/assets/characters/runtime/chibi_accurig_walk_test_v1/`

包内包含四方向逐帧 PNG、四方向 sprite sheet、GIF 预览和 `runtime_manifest.json`。manifest 记录了 64×64 画布、8 帧、最近邻过滤、透明背景和动作幅度 1.3。

Godot 4.7 headless 测试已通过：直接读取 32 张 PNG、创建 `ImageTexture`，验证四张 sprite sheet 和所有逐帧纹理的尺寸，并动态创建 `AnimatedSprite2D`，确认 right 动画包含 8 帧且可以启动播放。测试脚本为 `prototype/tests/pixel_runtime_import_test.gd`，输出为 `PIXEL_RUNTIME_GODOT_FILE_PASS` 和 `PIXEL_RUNTIME_GODOT_ANIMATEDSPRITE_PASS`。

另外，`prototype/tests/pixel_runtime_scene_test.tscn` 会实际创建四个 `AnimatedSprite2D`，分别播放四个方向，并强制检查 `TEXTURE_FILTER_NEAREST`。Godot headless 场景测试输出为 `PIXEL_RUNTIME_SCENE_PASS actors=4 directions=4 frames=8 filter=nearest`。

当前仍未把“编辑器导入缓存”和 `AnimatedSprite2D` 场景播放标记为完成；项目 headless 导入时还会提示 Blender 路径未配置，因此实际 Godot 播放测试单独保留。
