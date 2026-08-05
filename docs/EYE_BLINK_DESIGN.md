# 移动时眼睛动画设计记录

更新时间：2026-08-05

## 当前结论

旧的 eye-anime gallery 实验已经全部撤下。它们反复引入正面叠层、错误的侧面眼睛、面部抖动和身体步态不完整等问题，因此不再把 v6–v22 视为可复用的实现基线。

`eye_anime` 分支暂时只保留移动动画基线和研究结论，不发布新的眼睛候选。下一轮必须先验证眼睛的 3D 结构、头部跟随和四方向投影，再进入 2D 烘焙与 gallery。

## 重新采用的原则

1. 眼睛属于头部的 3D 面部结构，不能作为固定在世界坐标上的独立平面。
2. 正面、三分之四和侧面应由同一套 3D 眼睛/眼睑结构投影得到；背面不生成眼睛。
3. 眨眼控制只驱动一个连续参数或一组稳定的形态键，不再通过多个独立贴图层叠加来模拟开合。
4. 身体动画合同保持不变：四方向、完整 8 帧步态采样，眼睛实验不得改变身体姿态或采样相位。
5. image_gen 只用于生成经过人工确认的眉毛与眼睛视觉资产参考，不能代替 3D 锚点、拓扑和面部跟随关系。

## 推荐的成熟路线

### A. Blender 原生面部结构

先在 Actor V1 的头部上建立一套浅层的日系动漫眼睛/眼睑几何，并让它们统一挂在 `CC_Base_Head` 的面部结构下。眼睑使用相对 Shape Keys，例如 `Open`、`Half`、`Closed`；不额外把已有 shrinkwrap 镜片重复绑定到眼骨骼。

Blender 官方文档把 Shape Keys 作为面部动画的常用方法，并支持相对形态键的组合与插值；这比逐帧替换独立 PNG 更适合保持眉眼关系和头部跟随。参考：[Blender Shape Keys 官方手册](https://docs.blender.org/manual/en/latest/animation/shape_keys/introduction.html)。

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
- 现有 Blender 脚本：保留为研究/回退材料；下一步应拆出“单一 3D 眼睛结构 + Shape Keys”实验，而不是继续扩展旧的贴图层方案。
