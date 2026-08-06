# GarmentCode 官方 neutral body 基线复现（2026-08-05）

## 目的

在继续尝试 Actor 或自定义真人模型之前，先按 GarmentCode 官方脚本复现 `t-shirt + neutral body`。这一步用于区分：

- 参数化裁片本身是否正确；
- 官方披挂模拟器是否能产生完整服装；
- 当前问题是否来自我们之前的 Blender/BoxMesh/投影适配层。

## 官方流程

```text
body_measurements + design_params
        ↓
test_garmentcode.py
        ↓
sewing pattern JSON / printable pattern
        ↓
test_garment_sim.py
        ↓
BoxMesh + GarmentCode Warp draping
        ↓
sim.obj + front/back render + simulation statistics
```

官方文档要求先从身体测量和服装设计参数生成裁片，再把裁片披挂到对应的基础身体上；不能先在无关人体上生成服装，再用 Shrinkwrap 转移到另一个身体。

## 本地环境

- Python 3.9.25
- GarmentCode 本地源码：`third_party/GarmentCode`
- `libigl==2.6.0` Windows wheel
- `cgal==5.5.3.post202307282311` Windows wheel
- `NvidiaWarp-GarmentCode` commit `63baf6855efdd89b2834b74640f84b3bb0d86b50`
- Warp 使用 CPU-only 构建；本机 CUDA 13 与该旧版 fork 的 CUDA 源码不兼容
- Warp CPU JIT 使用仓库自带 Packman 的 LLVM 15.0.7 预编译库

## 复现命令

在 `third_party/GarmentCode` 下执行：

```powershell
.venv\Scripts\python.exe test_garmentcode.py
.venv\Scripts\python.exe test_garment_sim.py `
  -p Logs\t-shirt__260805-19-14-57\t-shirt__260805-19-14-57_specification.json `
  -s assets\Sim_props\default_sim_props.yaml
```

## 结果

### 裁片生成：通过

`test_garmentcode.py` 成功生成：

- `body_measurements.yaml`
- `t-shirt.yaml`
- pattern specification JSON
- pattern SVG/PNG

### 视觉披挂：通过参考人体基线

输出目录：

`third_party/GarmentCode/Logs/t-shirt__260805-19-14-57_260805-19-24-20/`

已生成：

- `t-shirt__260805-19-14-57_sim.obj`
- `t-shirt__260805-19-14-57_render_front.png`
- `t-shirt__260805-19-14-57_render_back.png`

检查结果：

- 正面前片连续，没有中央空洞；
- 背面裁片连续，没有被投影切开；
- 两侧袖子完整；
- 衣服轮廓贴合 neutral body；
- 不再出现之前自定义转移中的“前片压扁”和“侧面裁片重叠”。

### 质量门禁：通过

首次普通运行曾留下不完整的统计记录；在补齐匹配的 Warp CPU JIT 并使用逐帧诊断重新运行后，最终输出目录为：

`third_party/GarmentCode/Logs/t-shirt__260805-19-14-57_260805-19-31-09/`

最终 `sim_props.yaml` 为：

```yaml
fails: {}
fin_frame:
  t-shirt__260805-19-14-57: 405
self_collisions:
  t-shirt__260805-19-14-57: 0
body_collisions:
  t-shirt__260805-19-14-57: 0
```

逐帧诊断显示，初始自交数从 206 逐步下降到 0；第 405 帧达到静态平衡。官方 neutral-body 基线现在在视觉和自动质量统计两方面均通过。

## mean_male 体型复测

为验证服装不是只对 neutral body 有效，增加了 `--body` 和 `--body-name` 参数，使用官方 `mean_male` 身体测量与身体网格重新运行：

```powershell
.venv\Scripts\python.exe test_garmentcode.py --body mean_male
.venv\Scripts\python.exe test_garment_sim.py `
  --body-name mean_male --max-sim-steps 600 `
  -p Logs\t-shirt__260805-19-36-01\t-shirt__260805-19-36-01_specification.json `
  -s assets\Sim_props\default_sim_props.yaml
```

输出目录：

`third_party/GarmentCode/Logs/t-shirt__260805-19-36-01_260805-19-38-18/`

结果同样通过：

- `fails: {}`；
- `fin_frame: 405`；
- 身体碰撞：`0`；
- 自交：`0`；
- 正面、背面裁片连续，袖子完整。

这说明官方参数化服装可以随官方体型参数变化保持稳定；问题不在“服装无法生成”，而在于自定义 Actor 尚未被转换为 GarmentCode 可接受的身体输入。

## 结论与下一步

1. 官方流程在参考人体上能够生成正确服装；之前失败主要来自绕过官方模拟器后的自定义 BoxMesh/投影路线。
2. `neutral body` 已经通过视觉、静态、自交和身体碰撞门禁。
3. `mean_male` 体型复测也通过，官方体型参数变化稳定。
4. 下一步才开始建立 Actor 的服装代理身体和对应测量参数；不能直接把当前真人/neutral 服装 Shrinkwrap 到 Actor。
