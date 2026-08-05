# 移动时眼睛动画设计记录

更新时间：2026-08-05

## 当前结论

旧的 eye-anime gallery 实验已经全部撤下。它们反复引入正面叠层、错误的侧面眼睛、面部抖动和身体步态不完整等问题，因此不再把 v6–v22 视为可复用的实现基线。

`eye_anime` 分支现在保留移动动画基线，以及一个明确标注的眨眼状态测试。它仍不是最终眼睛资源，也没有接入完整步态或随机调度。

## 重新采用的原则

1. 眼睛属于头部的 3D 面部结构，不能作为固定在世界坐标上的独立平面。
2. 正面、三分之四和侧面应由同一套 3D 眼睛/眼睑结构投影得到；背面不生成眼睛。
3. 眨眼状态必须复用同一套 3D 面部表面；当前先用 `open/half/closed` 状态材质验证视觉资源，暂不把几何眼睑层叠到 Actor 头部。
4. 身体动画合同保持不变：四方向、完整 8 帧步态采样，眼睛实验不得改变身体姿态或采样相位。
5. image_gen 只用于生成经过人工确认的眉毛与眼睛视觉资产参考，不能代替 3D 锚点、拓扑和面部跟随关系。

## 推荐的成熟路线

### A. Blender 原生面部结构

先在 Actor V1 的头部上建立一套浅曲面，并让它们统一挂在 `CC_Base_Head` 的面部结构下。当前验证使用同一套表面切换 `Open`、`Half`、`Closed` 材质；之前尝试的皮肤色眼睑几何会造成矩形遮罩和原生睫毛破坏，因此已撤销，不作为实现基线。

Shape Keys 仍可作为后续几何方案的研究方向，但本阶段先以状态材质验证资源和投影关系；不会在验证失败时继续堆加眼睑几何。

### B. 视线与眨眼分离

眨眼使用眼睑形态键；视线偏移才考虑 UV Warp 或眼球控制器。UV Warp 可以由对象或骨骼驱动 UV 的移动、旋转和缩放，但它不是解决侧面投影或眼睑几何的办法。参考：[Blender UV Warp 官方手册](https://docs.blender.org/manual/en/latest/modeling/modifiers/modify/uv_warp.html)。

### C. 参数和随机调度

运行时只保留一个可复现的 `blink_amount` 参数，离线渲染时由固定 seed 生成眨眼间隔；`open → half → closed → half → open` 只是参数曲线，不是五套互相漂移的图层。Live2D 的官方 EyeBlink 方案也采用左右眼开合参数、控制器和可调随机间隔，可作为参数设计参考，但不引入 Live2D 运行时依赖。参考：[Live2D EyeBlink 官方教程](https://docs.live2d.com/en/cubism-sdk-tutorials/eyeblink/)。

### D. 最后才进入 Godot

Blender 完成四方向 3D→2D 烘焙后，Godot 只负责播放已经验证的 SpriteFrames；不在 Godot 中再移动或拼装眼睛贴图。参考：[Godot AnimatedSprite2D 官方文档](https://docs.godotengine.org/en/4.6/classes/class_animatedsprite2d.html)。

## 重新开始的验收闸门

1. 静态正面：最大睁眼比例与 Actor 标准一致，眉眼相对位置稳定。
2. 头部动作：眼睛随头部和面部动画移动，不出现悬浮、抖动或重复层。
3. 侧面：同一 3D 结构自然投影出正确方向和可见度；没有通过错误的侧面 PNG 平面“补眼睛”。
4. 动画：身体四方向均保留完整 8 帧步态，眼睛控制不能改变身体采样。
5. 眨眼：至少有最大睁眼、半睁、闭眼三个可检查状态，过渡连续且同 seed 可复现。
6. 透明度：所有眼睑/眼睛 pass 保留 alpha，不使用会产生黑色小窗或马赛克的错误混合方式。
7. 只有通过以上检查，才新建一个 gallery 候选；失败的中间结果不再长期堆积在 gallery。

## 当前工程状态

- 移动基线：`prototype/preview/animation_gallery/walk-v78/`
- 原始角色基线：`prototype/preview/animation_gallery/actor-v1/`
- 旧 eye-anime gallery：已删除，可从 Git 历史恢复，但不再作为当前实现引用。
- 第一阶段已建立 `EyeAssemblyV1` 静态结构：`tools/blender/build_eye_assembly_v1.py`。
- 第一阶段 image_gen 资产：`prototype/assets/generated/eye_assembly_v1/`，眉毛与眼睛由同一张 Q 版日系参考生成，再经过 chroma-key 去背景和左右裁切；没有本地绘制像素。
- 资源基准：`prototype/assets/characters/actor_v1/eye_textures/eye_right.png` 与 `eye_left.png` 继续作为 open 状态的权威比例和风格基准。
- 因 Actor 没有原生 half/closed 状态，已按 Actor 原生眉毛、睫毛、虹膜和间距约束，用 image_gen 生成这两个必要状态；它们只作为状态过渡测试资源，不得反向修改 open 基准。
- 当前实现使用相对 Actor 原生眼睛宽高倍率 `0.68/0.68`，并在同一头部父级下使用 `EyeAssemblyV1_FitToHeadSurface` Shrinkwrap 贴合头部表面；这些是当前测试参数，最终尺寸仍以 Actor 标准复核为准。
- 当前 gallery 只保留已选定的确定性眨眼步态候选：`prototype/preview/animation_gallery/eye-assembly-v2-blink-walk-native/`。
- 当前已验证 `Open/Half/Closed` 三个状态、正面与三分之四投影、透明度和头部跟随。
- 当前确定性眨眼输出：`prototype/test_output/eye_assembly_v2_blink_walk_native/`，身体仍采样 `1,11,21,31,41,51,61,71`，眼睛状态为 `open → half → closed → half → open` 后保持 open；gallery 对照位于 `prototype/preview/animation_gallery/eye-assembly-v2-blink-walk-native/`。
- 下一步才是固定 seed 的随机间隔；在此之前先人工确认四向 GIF 中没有侧面重叠、身体缺帧或状态切换跳变。
