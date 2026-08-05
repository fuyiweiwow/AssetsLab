# Eye Anime 重置与成熟方案调研

日期：2026-08-05

## 决策

删除旧 gallery 中全部眼睛实验，保留移动基线。新的实现不从 v22 或更早版本继续修补，而是从“单一 3D 面部结构、单一眨眼参数、统一四方向投影”重新开始。

## 资源策略

`prototype/assets/characters/actor_v1/eye_textures/eye_right.png` 与 `eye_left.png` 是 Actor V1 的权威比例、风格和眉眼关系基准。open 状态直接使用这两份资源；由于 Actor 没有 half/closed 原生状态，image_gen 仅为这两个必要状态生成同风格变体，并以 Actor 资源约束比例、眉毛、睫毛、虹膜和间距，不能替代 open 基准。

## 为什么重置

旧流程把不同来源的眼睛贴图作为独立可见层，再尝试通过位置、父级、眼骨骼和侧面平面去补偿 3D 投影。这会把视觉内容、动画绑定和方向选择混在一起，导致正面叠层、侧面方向反转、眼睛悬浮以及身体帧被打乱。当前实验只允许同一套头部父级 3D 表面切换状态材质，禁止增加独立侧面 PNG。

## 成熟做法对照

| 方案 | 适合本项目的部分 | 不采用的部分 |
| --- | --- | --- |
| Blender Shape Keys | 适合面部表情；可以用相对形态键组合并插值 `Open/Half/Closed` | 不能单独替代正确的 3D 眼窝、头部父级和方向投影 |
| Blender UV Warp | 适合视线/虹膜的 UV 偏移，并可由对象或骨骼驱动 | 不用于生成侧面眼睛，也不用于修复错误的眼睑几何 |
| Live2D EyeBlink 参数模型 | 提供左右眼开合参数、控制器和可复现随机调度的成熟参考 | 项目目标是 Blender 3D→2D，不引入 Live2D 运行时 |
| Godot AnimatedSprite2D | 适合播放 Blender 烘焙后的 SpriteFrames | 不在 Godot 运行时拼装、移动或生成眼睛贴图 |

## 新的最小实验

1. 复制 Actor V1 头部，建立一个 `EyeAssemblyV1` 集合；所有眼球、眼睑、眉毛和材质都从头部局部空间出发。
2. 首先只做静态 `Open`，检查 front/right/back/left；back 必须没有眼睛，right/left 必须由同一几何自然投影。
3. 在同一套 3D 表面上验证 `Open/Half/Closed` 状态材质；之前的皮肤色眼睑几何会破坏 Actor 原生睫毛和透明度，已明确放弃。
4. 用一个 `blink_amount` driver/action 控制状态过渡，先做确定性的单次眨眼，再接入固定 seed 的随机间隔。
5. 每次只增加一个变量；body pass 永远使用移动基线的完整 8 帧，不在眼睛实验中改变身体姿态采样。
6. 只有静态四方向、头部跟随、单次眨眼和完整步态全部通过后，才生成新的 gallery 目录。

## 第一阶段结果

已完成 `EyeAssemblyV1`：open 使用 Actor 原生眼睛，half/closed 使用基于 Actor 参考的 image_gen 状态资源，并由两个同构的浅曲面组成同一个 `EyeAssemblyV1` 集合。两个表面都直接 Bone Parent 到 `Armature/CC_Base_Head`，旧 `EyePackageV1_*` 和 `EyeBlinkV1_*` 对象在实验 Blend 中已移除。

已验证：正面最大睁眼、half、closed、三分之四投影、右侧边缘投影、背面无眼睛、frame 1/31 的头部跟随。测试倍率为 `0.68/0.68`，并使用头部表面 Shrinkwrap；随后已在不改变身体采样的前提下完成一次确定性眨眼，身体采样为 `1,11,21,31,41,51,61,71`，眼睛状态为 `open → half → closed → half → open` 后保持 open。当前只保留四向确定性眨眼步态 gallery。

## 暂不做

- 不再制作独立的 profile 眼睛 PNG 平面。
- 不再把 shrinkwrap 镜片二次绑定到左右眼骨骼。
- 不再通过增加更多贴图状态掩盖错误的 3D 锚点。
- 不把 AI 插帧或像素化工具当作动画结构修复工具；它们最多在结构稳定后用于离线 A/B。
