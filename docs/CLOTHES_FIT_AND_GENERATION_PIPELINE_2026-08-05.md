# 服装拟合与关键服装生成流程（2026-08-05）

> 持续实验记录、问题—解决方案表、Gallery current 覆盖规则和每次实验门禁见
> [服装实验记录与更新工作流](CLOTHES_EXPERIMENT_WORKFLOW.md)。

## 目标

项目最终将 Blender 3D 渲染转换为像素素材，因此服装不需要达到电影级布料模拟，但必须满足：

- 四方向剪影完整；
- 衣服确实套在身体外部；
- 腰部、胯部、腿部没有明显穿模；
- 走路动作中衣服跟随正确的身体部位；
- 生成的像素帧不会因为服装错误而破坏角色轮廓。

当前 `Blender_clothes.blend` 仍然值得保留，但它应被视为“源身体上的服装目录”，不能直接用全局缩放和自动权重套到 Actor。

## 成熟流程的共同结构

```text
源身体 + 源服装
      ↓
目标身体与源身体对齐
      ↓
目标身体 Clothing Cage / 身体标记
      ↓
服装局部拟合与离体间隙
      ↓
隐藏被衣服覆盖的身体区域
      ↓
权重转移或自动蒙皮
      ↓
四方向静态检查
      ↓
8 帧走路和关键姿势检查
      ↓
通过的服装包进入随机化池
```

### 1. 源身体与目标身体

- 源身体：服装原本制作或摆放所依据的身体，例如 `Colin_dummy`。
- 目标身体：项目实际 Actor，例如 `Armature` 下的 `ChibiBaseMesh_AccuRIG_InputMesh`。
- 两者都应先处于中立 A-pose/T-pose，应用旋转、缩放和必要的原点修正。
- 不能只匹配整个人物包围盒；肩宽、胸腹深度、腰线、胯宽、腿长必须分区域处理。
- Q 版男性和女性身体应视为不同目标身体，不能假设一套服装通过统一缩放即可兼容。

### 2. Clothing Cage

为 Actor 建立不渲染的服装笼，至少包含：

- 上衣区域：颈部、肩膀、腋下、胸腹、腰线、袖口；
- 下装区域：腰线、胯部、大腿、膝盖、小腿和裤脚；
- 内边界：身体外轮廓加最小离体间隙；
- 外边界：允许宽松衣服和叠穿衣服占据的空间。

Cage 的用途不是替代衣服，而是让每个衣服顶点知道应该跟随身体的哪个区域，避免裤子顶点错误地跟随脚或上衣顶点错误地跟随头部。

### 3. 局部拟合

- 紧身衣、裤子：优先匹配身体形状和拓扑流向；
- 宽松上衣、外套：保留衣服本身的肩部、衣摆和袖子形状，只调整整体落点和碰撞间隙；
- 裤子和上衣分开拟合，不能共用一个深度缩放参数；
- 使用 Shrinkwrap、Surface Deform、局部比例编辑或 Cage 变形，不能继续使用单一全局缩放；
- 静态阶段先修正穿模，再绑定动作。

### 4. 身体遮挡和服装层级

衣服通过静态检查后，应按服装覆盖关系建立身体遮挡区域：

- 上衣覆盖的胸腹区域可以隐藏身体内层面；
- 裤子覆盖的胯部和腿部可以隐藏身体内层面；
- 多层服装按内层到外层排序；
- 遮挡只用于消除服装内部的身体穿出，不能用来掩盖衣服本身没有套上的问题。

### 5. 权重与动作

- 静态拟合通过后再转移权重；
- 紧身衣/裤子优先从身体进行距离或表面邻域权重转移；
- 宽松衣服的肩、领、袖口和衣摆需要单独检查，必要时手动修权重；
- 自动权重只能解决运动跟随，不能解决衣服大小、位置和穿模。

### 6. 验收门槛

每件服装进入随机化池前必须通过：

1. 正、右、背、左四方向静态剪影；
2. 每方向至少 8 个走路采样帧；
3. 抬臂、迈腿、腰部最大摆动等关键姿势；
4. 身体穿出检查、服装互相穿插检查、服装缺失检查；
5. 256×256 预览及最终像素缩小预览。

## 关键服装的生成路线

### 路线 A：二维版型/缝合生成（推荐）

对主角关键服装，优先从版型生成，而不是继续寻找随机成品网格：

1. 以 Actor 的中立代理身体作为 Avatar；
2. 在 CLO/Marvelous Designer 中制作前片、后片、袖片、领口、裤片等二维版型；
3. 缝合并模拟到代理身体；
4. 用测量、压力/拉伸图检查衣服是否过小或过紧；
5. 导出低模网格到 Blender；
6. 在 Blender 中做减面、材质、Cage、权重和四方向渲染。

CLO 的官方流程明确要求先制作或导入二维版型，再缝合、披挂到 Avatar，并用测量和 Fit Map/Stress Map 检查贴合。[CLO 服装拟合说明](https://support.clo3d.com/hc/en-us/articles/115013660447-How-do-you-fit-3D-Garments-in-CLO)

这是目前最适合“关键服装”的方法，因为衣服尺寸从版型和身体测量开始就可控。

### 路线 B：Blender 原生缝合与布料模拟

适合简单 T 恤、裤子、披风和裙子：

- 用平面片或低模版片建立衣服；
- 使用 Cloth Sewing、Pin Group 和碰撞体；
- 模拟后应用变形；
- 再做低模整理和权重转移。

Blender 官方 Cloth 文档支持 Pin Group 和 Sewing Springs，可用于固定和缝合布片。[Blender Cloth Shape](https://docs.blender.org/manual/en/latest/physics/cloth/settings/shape.html)

这条路线不依赖第三方生成模型，许可证最清晰，但对复杂外套、装饰和精细版型需要更多手工工作。

### 路线 C：研究型自动生成

- [Garment3DGen](https://github.com/nsarafianos/Garment3DGen)：从输入图像和基础服装网格生成/变形服装，适合研究和原型，不作为当前生产依赖。
- [Bolt: Clothing Virtual Characters at Scale](https://arxiv.org/abs/2504.17614)：提出“服装转移 → 二维版型优化 → 披挂解缠 → 重新绑定”的自动流程，说明自动化方向可行，但不是现成 Blender 插件。
- [Dress Anyone](https://doi.org/10.1145/3747858)：研究自动将服装版型重适配到不同身体，适合作为未来工具设计参考。

这类方法可以帮助我们理解自动拟合，但实际接入前必须单独核对代码、模型、数据和生成结果的许可证。

## 当前项目决策

1. 现有服装库继续保留，用作风格和款式参考。
2. 不再使用全局包围盒缩放作为正式拟合算法。
3. 先建立 Actor Clothing Cage 和一套自有的局部拟合/遮挡/权重验证脚本。
4. 关键上衣和裤子优先采用路线 A 或路线 B 重新生成；普通随机服装再考虑适配已有资源。
5. 只有通过四方向和动作验收的服装，才进入运行时随机化池。

## MIT 参数化生成路线：GarmentCode / PyGarment

本轮先记录并尝试一条更适合“关键服装随机生成”的开源路线：
[GarmentCode](https://github.com/maria-korosteleva/GarmentCode)。它以参数化缝纫版型程序生成衣片，再通过模拟得到可导入 Blender 的服装网格；核心代码采用 MIT 许可证，适合作为原型生成器和离线候选生成器，而不是直接把随机网格塞进运行时。

### 项目接入边界

1. 输入：由本项目自行从 Actor 网格提取的身高、胸围、腰围、臀围、肩宽、袖长、裤长等测量值。
2. 生成：用自有设计参数范围生成低模 T 恤、长裤等候选，保留款式参数和随机种子，确保结果可复现。
3. 拟合：先完成版型/布料模拟，再进入 Actor Clothing Cage、局部间隙、遮挡、权重和四方向动作验收。
4. 许可：只纳入 GarmentCode 核心代码与我们自行编写的测量/导入脚本；不将其关联的 GPL 数据集或测量库作为项目运行时依赖。特别是 `GarmentMeasurements` 标记为 GPL-3.0，本项目暂不引入。
5. 依赖：官方文档以 Python 3.9 为目标环境，完整披挂还依赖其 NVIDIA Warp 分支；该分支 README 当前标注 NVSCL 且只允许非商业使用，因此不纳入本项目的生成依赖。改由 Blender 作为离线制作工具执行 Cloth Sewing/布料模拟，项目只保存导出的服装网格和自有脚本。

### 本轮实施顺序

1. 在 `third_party/GarmentCode` 固定源码快照并核对许可证、示例和依赖。
2. 编写本项目自有的 Actor 测量提取器，不复制 GPL 测量库代码。
3. 用一组明确的 T 恤/长裤参数生成首个低模候选。
4. 导入 Blender，接入现有四方向和 8 帧走路审核 gallery；未通过的候选不得进入随机化池。

这条路线的定位是“MIT 版型生成 + Blender 离线缝合披挂 + 项目内严格验收”，不是承诺一次生成即可穿好。官方 Warp 分支的非商业许可边界记录在这里：[NvidiaWarp-GarmentCode](https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode)。

### 首次试跑记录（2026-08-05）

- 已固定 `third_party/GarmentCode` 的源码快照，并使用独立 Python 3.9 环境验证 PyGarment 核心导入。
- 已生成 `mean_all` 身体的低模 T 恤版型：8 个衣片、16 条缝合关系，版型 PNG/SVG 和可复现 manifest 输出到忽略目录 `prototype/test_output/garmentcode_candidates/`。
- 已完成 Actor 网格测量提取器，但直接把 Q 版 Actor 的测量值喂给通用人体版型会产生退化衣片；原因是头身比、手臂姿态和胸廓比例超出 GarmentCode 默认人体假设。
- 因此第一件可验证候选先采用 GarmentCode 的标准身体版型，下一步在 Blender 中按 Actor 的肩宽、胸廓、腰线和衣长做区域拟合；Actor 测量值保留为后续 Q 版专用版型的校准数据，不能被误认为已通过的服装尺寸。
- 已完成首个 Blender 静态放置预览，但它本质上仍是平面衣片的预摆放：躯干衣片能够进入 Actor 场景，袖片与肩部有断开，且没有完成缝合和布料披挂。该结果记录为 `pre_drape_static_fit_only` 失败基线，不能作为可用 3D 服装，也不进入随机化池。
- 已开始 Blender 原生 Cloth Sewing 实验：将 16 条版型缝合关系转换为 32 条 sewing-spring 边，并烘焙出 `prototype/test_output/garmentcode_cloth_preview/garmentcode_draped_tshirt.blend`。目前仍是失败候选：低分辨率衣片在 Actor 上出现开口、袖部偏移和局部塌陷，说明还需要提高衣片内部网格密度、校正缝合边映射和局部 Clothing Cage 间隙；它也不进入随机化池。

### Blender MCP 受控试验（2026-08-05）

本轮采用 MIT 许可的 [blender-mcp-server](https://github.com/djeada/blender-mcp-server) 做控制层验证，MCP 服务只绑定 `127.0.0.1:9876`，不作为服装算法或运行时依赖。

- 已通过 MCP 读取 Actor 场景信息。
- 已通过 MCP 创建并删除 `AssetsLab_MCP_SmokeTest`，确认对象操作链路可用。
- 已通过 MCP 的 `python.execute` 调用本项目的 Cloth Sewing 脚本，并输出到忽略目录 `prototype/test_output/garmentcode_mcp_cloth_preview/`。
- MCP 能够协调 Blender、脚本、渲染和导出，但不会自动修复版型、缝合边、身体间隙或穿模；MCP 生成的这次服装预览仍按失败候选处理。
- 测试结束后已停止 Blender MCP 进程，未保存覆盖 Actor 原始场景。

### MCP 第二轮几何修正（2026-08-05）

- 不再手工猜测袖子锚点，改用 GarmentCode 版型中已有的 `translation/rotation` 信息映射到 Actor。
- 每条版型边先做 4 段细分，再生成 sewing springs；缝合弹簧边数由 32 增加到 80。
- MCP 调用后的结果比第一轮明显改善了躯干覆盖和袖部连接，但仍存在三角折面、肩部不自然和局部间隙；继续标记为失败候选，不进入随机化池。

结论：MCP 适合做“调度器和交互入口”，正式生成仍必须依赖可复现的版型、缝合、模拟、Cage 和验收脚本。

### 服装类型契约（补充）

服装不能全部按软布料处理，后续候选按以下类型登记：

- `soft_garment`：T 恤、衬衫、裤子、裙子。使用 Inner/Outer Cage、局部间隙、权重绑定；只有需要真实动态时才使用 Cloth。
- `rigid_armor`：胸甲、护肩、护腕、护腿、盾牌等。使用硬点/骨骼锚点、刚性或少量骨骼权重和碰撞间隙，不使用布料缝合模拟。
- `layered_accessory`：腰包、背包、披肩、挂件等。使用层级顺序、硬点或局部 Cage，并检查与软服装的遮挡关系。

盔甲也必须通过四方向和动作验收，但验收重点从“布料褶皱”改为：锚点跟随、碰撞间隙、刚性轮廓、相邻部件不互相穿插。

### Clothing Cage 首轮实现与边界（2026-08-05）

已新增 `tools/blender/build_actor_clothing_cage.py`，从 Actor 中建立不参与渲染的 `ActorClothingCage_Outer`，并写入软服装、刚性盔甲、分层配件三类区域组。盔甲锚点绑定到 `CC_Base_Spine02`、双侧锁骨、腰部和双手骨骼。

已新增 `tools/blender/fit_clothing_to_actor_cage.py`，支持两种明确模式：

- `legacy_actor_scaled`：保留现有衣服资源自身比例，只做整体尺度/落点校准，再传递 Actor 权重；用于当前 Colin 目录的保守基线。
- `cage_bbox`：按 Cage 局部范围重映射衣服包围盒；仅用于研究诊断，不能默认视为生产算法。

首轮验证结论：当前 Colin 网格不适合直接经过 Shrinkwrap 或 Cage 包围盒重塑。Shrinkwrap 会使上衣前片被身体遮挡，过度增加前后余量又会造成侧面横向膨胀。因此当前资源暂保留 `legacy_actor_scaled` 路线，Cage 先承担区域契约、间隙校验和后续遮挡/权重验证职责；T 恤样板尚未进入随机化池。

当前可复现实验输出（均位于被忽略的 `prototype/test_output/`）：

- `clothes_cage_fit_wide_v1`：Cage 全躯干包围盒，偏宽偏长，拒绝。
- `clothes_cage_fit_wide_v2`：收紧胸腰区但启用 Shrinkwrap，出现身体透出，拒绝。
- `clothes_cage_fit_wide_v3`：取消 Shrinkwrap，仍有前片遮挡，拒绝。
- `clothes_cage_fit_wide_v4`：增加服装前后余量，侧面膨胀，拒绝。
- `clothes_legacy_shirt_short_v1`：保留资源比例并完成 4 方向 × 8 动作帧、权重传递；作为下一轮人工审核基线，尚未宣称通过。

### 外部服装资源试验：OverScore Proxy 1.5（2026-08-05）

为寻找比当前 Colin 目录更适合作为随机服装来源的资源，新增候选：

- 来源：[OverScore Proxy - Modular Low-Poly Female Character Creation Set](https://opengameart.org/node/157297)
- 许可：页面标注 CC0；原始下载文件保存在 `prototype/assets/clothes_external/overscore_proxy_1_5/proxy_1.5.blend`。
- 资产规模：约 320 个网格对象，无 Armature；页面说明包含 50 件上衣、30 件下装、20 套全身服装及配件。
- 适配价值：低模、四边面、Blender 资源组织清晰，且版本说明提到对服装动画和肩背区域做过改进；但它不是针对本项目 Actor 制作的即插即用服装包。

本轮用项目自有 `cage_bbox` 流程测试了 `Collared Shirt` 和 `Cropped Sweatshirt`：

1. 发现 Proxy 服装使用 Mirror/Solidify，直接按评估包围盒拟合会造成重复横向缩放；现已改为先烘焙这两个源几何修饰器，再用烘焙网格计算拟合范围。
2. 发现 Blender Data Transfer 在目标没有预先顶点组时没有产生有效 Actor 权重；现已改为最近邻复制 Actor 顶点组，再挂接 Armature。
3. `Collared Shirt` 的 v5 结果虽然能跟随手臂并保持身体中心，四方向 × 8 动作采样完整，但本质上只是包围盒缩放，未真正贴合 Actor 身体；标记为“拟合失败”。
4. `Cropped Sweatshirt` 正面比例更接近 Q 版，但侧面袖部仍有块状外扩，标记为“未通过”。两者都不进入运行时随机池。

当前结论：OverScore Proxy 比原 Colin 目录更值得继续研究，但当前拟合流程仍不能产出“已穿好”的服装。资源本身必须按服装类别、肩点、胸廓、腰线、袖口和局部间隙逐件适配；不能把整个 `.blend` 直接当作随机池。盔甲仍按 `rigid_armor` 契约单独处理，优先使用骨骼锚点和刚性轮廓验收，不纳入本轮软服装拟合结论。

下一步是为 Proxy 建立“上衣/下装/全身服装”的资产清单和逐件四方向筛选，先找出一件真正通过的基础上衣，再扩展裤子与盔甲硬点测试。

### Actor 派生基础服装试验（2026-08-05）

为验证“先建立合身基准，再适配外部资源”的路线，新增 `tools/blender/build_actor_derived_tshirt.py`。脚本从 Actor 表面提取 `torso_upper_arm_surface_band`，保留 Actor 原有顶点组和 Armature，修正复制对象的世界变换后沿法线外扩 `0.025` 世界单位，并输出四方向 × 8 动作采样。

`prototype/test_output/actor_derived_tshirt_v3/` 的首轮结果已经形成连续的身体外层，侧面不再是包围盒挤出的悬浮块；它暂定为合身基准候选，仍需人工检查领口、下摆、腋下和动作穿模。只有这类基准通过后，才继续把 Proxy 的款式迁移到该基准上。

v4 针对首轮反馈加入三项几何约束：袖口按 Actor 上臂权重截断，避免手部被包裹；上下边界使用平面切割，获得可控下摆；使用 Solidify 增加实体厚度。v4 输出位于 `prototype/test_output/actor_derived_tshirt_v4/`，仍需人工审查后才能作为服装随机化的正式基准。

复核发现，按权重删除面仍然属于“截断”，不能称为服装缩放；v5/v6 的二次切割还会破坏袖子连续性，因此废弃。v10 改为躯干表面基准 + 独立完整袖筒，袖筒绑定上臂骨骼并与肩部重叠。真正的宽松缩放仍应在躯干、袖子分离后进行，避免整体缩放破坏 Actor 比例。
