# 衣服资源拟合试验记录（2026-08-05）

## 结论

`prototype/assets/clothes/Blender_clothes.blend` 可以作为服装目录资源使用，但目前不是可直接接入 Actor 的生产服装包。

这次试验已经验证了两件事：

1. 可以把无绑定的衣服网格从目录 Blend 复制到 Actor 场景，并修正目录对象的父级缩放。
2. Blender 自动权重绑定可以让衣服跟随 Actor 的 Mixamo 走路动作，当前测试覆盖四方向、每方向 8 个动作采样帧。

自动绑定通过不等于服装拟合通过。当前仍需按四方向剪影检查每一件衣服，不能直接把目录中的所有模型随机组合到运行时。

## 输入资源审计

- 输入：`prototype/assets/clothes/Blender_clothes.blend`
- 资源形态：Colin 男性小人服装目录
- 目录中没有可复用的 Armature、Action、相机或灯光
- 服装对象依赖父级 Empty 的缩放和位置；忽略父级变换会造成约 100 倍尺寸错误
- 当前资源不是针对项目 Actor 身体比例制作的服装，女性版本也不能由简单缩放得到

## 本次候选

测试脚本：`tools/blender/build_clothes_fit_candidate.py`

公共参数：

- Actor：`prototype/assets/characters/actor_v1/chibi_actor_mixamo_walk_v1.blend`
- 下装：`Colin_trouser_long`
- 拟合缩放：`2.5`
- 上衣深度缩放：`1.6`
- 下装深度缩放：`2.1`
- 上衣底部 Z：`0.58`
- 下装底部 Z：`0.05`
- 采样：四方向 × 8 帧，256×256，`soft_flat_v1`

| 候选 | 结果 | 说明 |
| --- | --- | --- |
| `Colin_shirt_short + Colin_trouser_long` | 当前最佳审查候选 | 正面基本成立，侧面可接受；背面上衣覆盖不足，腰背露体明显，暂不能生产使用 |
| `Colin_shirt_long + Colin_trouser_long` | 淘汰 | 正面大部分衣服被身体遮住，只剩局部蓝色区域；不是简单调深度就能解决 |
| `Colin_Tshirt_slim + Colin_trouser_long` | 淘汰 | 正面没有形成完整上衣剪影，主要只显示领口/局部区域 |

审查输出位于 `prototype/test_output/`，属于临时产物，不提交到仓库。诊断蓝/棕色材质只用于区分上衣和下装，也不代表最终材质。

## 当前阶段判断

当前应停留在“离线服装资源审查/拟合”阶段，还不应进入 Godot 运行时随机换装。原因是：

- 服装库中不同对象的实际版型和可见方向不一致；
- 自动权重可以绑定，但不能自动修复穿插、露体和背面覆盖；
- 当前 Actor 仍是男性基线，女性身体需要独立的尺寸、肩胯比例和版型拟合；
- 运行时只应该选择已经通过四方向和动作采样验收的服装包。

## 下一步

详细的 Cage、局部拟合、遮挡、权重和关键服装生成流程见：
`docs/CLOTHES_FIT_AND_GENERATION_PIPELINE_2026-08-05.md`。

1. 为目录中的上衣、下装建立静态四方向缩略审查表，先筛掉不形成完整剪影的对象。
2. 对通过筛选的服装做身体贴合：位置、胸腹/臀部深度、腰线和袖口分别调整，不再使用一个全局深度参数解决所有部位。
3. 对通过静态审查的服装再做自动权重与走路动作检查；必要时用权重传递或少量手工修权重替代纯自动权重。
4. 形成带元数据的服装包后，才接入运行时随机化。随机化约束至少包括性别体型、上衣/下装槽位、互斥组、覆盖关系和验收状态。
5. 女性服装作为独立适配目标测试，不把男性衣服直接缩放后视为女性版本。

## 可重复命令

```powershell
$blender = 'D:\Apps\CodeXApp\Tests\blender-4.5.10-windows-x64\blender.exe'
& $blender -b --python tools/blender/build_clothes_fit_candidate.py -- `
  --actor-blend prototype/assets/characters/actor_v1/chibi_actor_mixamo_walk_v1.blend `
  --clothes-blend prototype/assets/clothes/Blender_clothes.blend `
  --output prototype/test_output/clothes_fit_animated_v5_slot_depth `
  --top Colin_shirt_short --bottom Colin_trouser_long `
  --scale 2.5 --top-depth-scale 1.6 --bottom-depth-scale 2.1 `
  --top-bottom-z 0.58 --bottom-bottom-z 0.05 `
  --resolution 256 --animate --diagnostic-colors
```

## Clothing Cage 首轮记录

新增 `tools/blender/build_actor_clothing_cage.py` 与 `tools/blender/fit_clothing_to_actor_cage.py`。Cage 已生成并包含软服装区域、刚性盔甲区域、分层配件区域，以及胸部、双肩、腰部、双手硬点。

本轮使用 `Colin_shirt_short` 做保守基线，输出 `prototype/test_output/clothes_legacy_shirt_short_v1/`，完成正/右/背/左四方向和每方向 8 个走路采样帧，同时完成 Actor 权重传递和 Armature 绑定。它可以用于下一轮审核，但仍未进入运行时随机池：侧面衣摆轮廓和背面覆盖需要继续修正。

诊断结果：`cage_bbox` 直接重塑会破坏当前源衣服的前片/袖片结构；Shrinkwrap 会导致身体从衣服前片透出；增大前后余量又会造成侧面膨胀。因此当前正式候选采用 `legacy_actor_scaled_plus_cage_validation_weight_transfer`，Cage 暂作为校准与验收基准，不强行重塑这套源网格。

## 外部资源候选：OverScore Proxy 1.5

本轮新增并审查了 CC0 的 [OverScore Proxy 模块化低模服装资源](https://opengameart.org/node/157297)，文件位于 `prototype/assets/clothes_external/overscore_proxy_1_5/proxy_1.5.blend`。资源约含 320 个网格对象、50 件上衣、30 件下装和 20 套全身服装，但没有 Armature，仍需适配项目 Actor。

拟合脚本已修正两项基础问题：先烘焙 Proxy 的 Mirror/Solidify，再计算真实服装范围；使用最近邻方式复制 Actor 顶点组，避免 Blender Data Transfer 在空顶点组目标上静默产生无效权重。

| 候选 | 结果 | 说明 |
| --- | --- | --- |
| `Collared Shirt` v5 | 拟合失败 | 只是包围盒缩放，未真正贴合身体；虽然能随手臂运动，但侧面外扩，不能视为已穿上 |
| `Cropped Sweatshirt` v1 | 未通过 | 正面比例较好，但侧面袖部块状外扩，不能直接进入随机池 |

该资源暂定为“继续筛选候选”，不是已验收服装。下一轮先制作资产清单，按上衣、下装、全身服装分组逐件筛选四方向剪影；盔甲单独走刚性锚点流程。

## Actor 派生基础服装首轮

新增 `tools/blender/build_actor_derived_tshirt.py`，从 Actor 网格提取躯干和上臂区域，沿表面法线外扩 `0.025` 世界单位，并继承 Actor 原有顶点组和 Armature。v3 输出 `prototype/test_output/actor_derived_tshirt_v3/`，完成四方向 × 8 动作采样。

该候选的定位是“合身基准”，不是最终美术服装。首轮画面显示它已经保持在身体外侧，侧面和背面没有 Proxy 版本那种包围盒横向外扩；仍需人工确认领口、下摆、腋下间隙和动作中是否有穿模，当前状态为待审查。

## Actor 派生基础服装 v4 修正

针对 v3 的三项问题进行修正：袖口从上臂/前臂/手部权重边界截断，避免手被衣服包裹；在下摆和肩部使用平面切口，消除不规则边缘；增加 Solidify 实体厚度，使服装从视觉上区别于贴身皮肤层。v4 仍继承 Actor 的顶点组和 Armature，并重新完成四方向 × 8 动作采样。

输出：`prototype/test_output/actor_derived_tshirt_v4/`。当前状态为待审查，下一步重点检查领口、腋下、袖口和大幅动作中的穿模。

## v5/v6 袖口与边界修正

复核后确认 v4 的袖口仍然是按面/权重删除形成的截断，不是服装缩放；v5/v6 的二次切割又造成袖子破损，均废弃。v10 改为独立生成完整袖筒，继承 Actor 的上臂骨骼权重，并把袖筒肩部与躯干衣片重叠，避免缺面。v10 输出位于 `prototype/test_output/actor_derived_tshirt_v10/`，状态仍为待审查。
