# 服装实验记录与更新工作流

本文件是 AssetsLab 服装实验的持续工作流。它和具体实验记录配合使用：
`GARMENTCODE_OFFICIAL_ACTOR_TRANSFER_2026-08-06.md` 保存 GarmentCode/Actor
路线的详细结果，本文件保存以后每次实验都必须执行的检查和记录规则。

## 1. Gallery 与实验状态规则

- `milestone`：只有物理门禁和视觉审核都通过的结果，长期保留。
- `current`：当前正在审查的唯一实验，固定发布到
  `prototype/test_output/garmentcode_actor_proxy_current/`。
- 其他实验：保留源文件和日志用于追溯，但不再加入新的 Gallery 快照。
- 新实验开始时覆盖 `current`，同时在实验记录中追加一条日志；不能用多个
  `v1/v2/v3` 候选把 Gallery 重新堆长。
- Gallery 页面只显示“通过里程碑 + current”，不显示明显失败的诊断版本。

## 2. 标准实验阶段与门禁

### A. 输入登记

记录源文件、许可证、生成方式、目标 Actor、实验编号、随机参数和预期改变的
单一变量。一次实验只改变一个主要变量，例如深度、衣身宽度、袖子或测量值。

### B. 几何与单位检查

在模拟前检查：

- OBJ 是否为空、闭合、单连通、绕序一致；
- GarmentCode 身体 OBJ 使用米，GarmentCode 运行时会乘 100；测量 YAML 使用厘米；
- Actor Blender 使用米；GarmentCode 轴向和 Actor Blender 轴向必须显式记录；
- 身体分区顶点索引必须对应当前代理 OBJ，不能沿用默认身体的索引。

### C. 身体代理与测量

Q 版 Actor 不能直接作为 GarmentCode 碰撞体。先生成闭合的身体代理，再为代理
生成身体分区和测量。头长、腰线和胸线必须从 Actor 的真实几何分界估计，不能
直接套用普通人体默认值。

### D. 服装生成与物理模拟

先从无袖衣身开始验证躯干链路，再增加袖子、裤腿、盔甲等复杂部件。GarmentCode
模拟需要使用足够大的 `max_sim_steps`，避免在 `max_sim_steps - 1` 处把“达到上限”
误报为静止失败。当前推荐使用 500 作为测试上限。

物理门禁：

- `sim_props.yaml` 中 `fails` 必须为空；
- `body_collisions < 35`；
- `self_collisions < 300`；
- 记录 `fin_frame`、`sim_time`、`spf`；
- 失败结果只能作为诊断，不能进入 Gallery 的 milestone 或随机池。

### E. Actor 转移

服装转移顺序固定为：导入 → 单位缩放 → 坐标/朝向确认 → Cage 范围拟合 →
局部表面间隙 → 权重传递 → 4 方向 × 8 动作帧渲染。不能把“自动权重成功”当成
服装拟合成功。

Actor 躯干的深度必须用实际切片检查。全身 Cage 的深度不能直接作为衣服胸腔深度；
前胸、后背、腋下和衣摆应分别检查。当前实验暴露的典型范围是：Cage 约
`-0.57..0.30 m`，Actor 躯干约 `-0.25..0.18 m`，两者直接使用会使衣服胸腔过大。

### F. 视觉与动作审核

每个 current 必须检查：

- 正面：胸腔是否膨大、领口/肩部是否悬浮、下摆是否自然；
- 侧面：服装是否整体靠前或靠后、身体是否穿出；
- 背面：衣片是否被身体遮挡、是否出现条纹/破面/洞；
- 四方向与 8 个动作帧：服装是否跟随 Actor，而不是悬浮在固定位置；
- 运行时随机化前，必须完成静态、动作和遮挡三项验收。

## 3. 已记录的问题与解决方案

| 问题 | 证据 | 解决方案 | 当前结论 |
|---|---|---|---|
| Actor 原始碰撞体不适合 GarmentCode | 29 个断开组件，非 watertight，约第 104 帧崩溃 | 体素填充 + marching cubes 生成单闭合代理 | 代理路线可运行 |
| 代理输出坐标落在体素索引空间 | 初版 bounds 变成约 0..77 | 应用 voxel transform 后再导出 | 已修复 |
| GarmentCode 身体单位错误 | 官方身体约 1.72 高，运行时乘 100 | Actor 厘米代理导出为米，测量仍用厘米 | 已修复 |
| 默认 `head_l=47 cm` | 下摆约束把衣服推到头颈区 | 根据 Actor 头颈分界改为约 `152 cm` | 已修复 |
| 直接把普通袖装套到 Q 版代理 | 120 帧仍有大量身体碰撞/自交 | 先用无袖衣身隔离验证躯干链路 | 无袖物理基线通过 |
| 衣身 ease 不足 | 放松到 1.2 后自交显著下降 | 当前无袖基线使用 shirt width `1.3` | 物理门禁通过 |
| 初始 Actor 转移整体靠前、胸腔过大 | Cage 深度明显大于 Actor 躯干 | 深度因子收紧到 `0.55`，只给背部增加余量 | current 仍待视觉审核 |
| 收紧深度后背部被遮挡 | 背面出现身体遮挡衣片 | current 增加 `back_clearance=0.10` | 背部可见，但条纹需继续审核 |
| Gallery 过长且失败版本混杂 | 多个 v1/v2/v3 诊断候选长期展示 | 构建脚本只发布两个 milestone 和一个 current | 已更新 |

## 4. 每次实验必须更新的内容

1. 在对应实验记录中追加日期、输入、单变量、命令参数和结果指标。
2. 更新本文件的问题/解决方案表；如果结论被推翻，保留旧结论并标记为废弃，
   不直接改写成“从未发生”。
3. 覆盖 `prototype/test_output/garmentcode_actor_proxy_current/`。
4. 运行 `tools/build_preview_assets.py`，确认 Gallery 只有 milestone 和 current。
5. 运行 `tools/serve_preview.ps1`，记录完整 Tailscale URL，并验证 index 和至少
   一张 current 图片返回 HTTP 200。
6. 运行 `git diff --check`。未得到用户审核前，状态保持 `current` 或
   `review_required`，不进入随机池。

## 5. 当前工作流结论

GarmentCode 现在已经能够为 Actor 代理生成物理上通过的无袖衣身，但这不等于
短袖、长袖、裤子或盔甲已经解决。后续应以 current 覆盖方式逐个增加复杂部件，
每次只推进一个隔离阶段。

## 6. 2026-08-06 骨骼尺寸约束实验

当前无袖衣服的主要问题不是整体缩放，而是 Cage 的肩部/袖窿宽度被直接带到了
Actor。Actor 的骨骼数据（静止帧 1）给出：左右 `CC_Base_Upperarm` 根部跨度约
`0.4985 m`，肩部高度约 `z=1.3554 m`；左右 `CC_Base_Thigh` 根部跨度约
`0.3840 m`，髋部参考高度约 `z=0.5700 m`。

本次在 Actor 转移脚本中增加骨骼约束：

- 用大腿根到上臂根建立躯干横向宽度曲线，收回 Cage 造成的下摆喇叭形；
- 在肩部高度带内按 Actor 躯干实际切片压缩前后深度；
- 后续 raycast 只负责恢复身体外侧的 clearance，不再负责决定衣服的原始肩宽；
- 所有结果仍写入 `garmentcode_actor_proxy_current`，保持 `review_required`。

结果：正面已从连衣裙轮廓恢复为短上衣轮廓；侧面仍有领口连接形态需要审核，背面
仍有水平条纹/面片伪影，因此不能晋级 milestone 或随机池。

### 侧面厚度与背片穿入校正

本轮确认还需要两类身体参数，而不是一个总宽度：

- 按高度采样的躯干前后包络（Actor 表面前后 `Y` 边界 + `0.018 m` clearance）；
- 肩高以上的权重限制，领口不能继承 `CC_Base_Head`，应在
  `CC_Base_NeckTwist01` 与 `CC_Base_Spine02` 之间分配。

此前的 `back_clearance=0.10 m` 已取消。raycast 仅投影到肩高以下的躯干区域，
避免把领口投到脸部；上缘使用躯干包络而不是全身最近表面。校正后侧面外扩线
消失，背片不再卡入脸/颈部。源 OBJ 自带的水平衣料褶皱仍是独立的几何质量问题，
不能误判为尺寸参数已经完全解决。

### 后续校正：禁用无袖衣服的横向射线投影

复核发现，骨骼宽度约束本身已经生效，但横向 raycast 会在低躯干高度命中
Actor 的手臂/手部，把衣服侧缘重新推到约 `x=±0.59 m`，从而再次产生裙摆和
破碎感。当前无袖躯干衣服改为：只做前后深度投影，横向边缘保持骨骼宽度曲线；
`--project-side-x` 仅作为有袖服装的显式开关。校正后最终横向范围约为
`x=±0.30 m`，但背面源衣片条纹仍需单独处理。

### 骨盆上缘下摆约束

侧面复核发现，旧下摆约在 `z=0.62 m`，已进入大腿根区域。根据 Actor 官方骨骼，
`CC_Base_Pelvis.tail` 为 `z=0.73597 m`，左右大腿根约为 `z=0.57017 m`。当前
上衣下摆改为骨盆上缘以上 `0.03 m`，目标 `z=0.76597 m`；不再把衣片延伸到
大腿区域。评估后的最低衣片约 `z=0.7552 m`，保留了蒙皮变形余量。

本次只改变下摆高度，肩宽、领口权重、分层前后深度和上端完整性均保持上一版。

### 躯干垂直宽度采样插值

骨骼直线插值只能保证肩部和髋部两个端点，中段仍可能切进 Actor。当前改为从
Actor 网格按 `0.05 m` 高度采样躯干横向包络，排除上臂/手臂外凸区域，再对采样
宽度做线性插值；肩部骨骼仅作为上端 cap，髋部骨骼仅作为下端锚点。报告保存在
`manifest.json -> bone_shoulder_fit.width_fit`。

这次修正只改变中段横向宽度曲线，不改变已确认的下摆高度、分层前后深度或领口
权重规则。四方向动作帧检查通过，仍保持 `review_required`，因为源衣片水平褶皱
还不是最终拓扑质量。

## 7. 设计阶段曲线迁移结论（2026-08-06）

当前采样曲线已经通过 `tools/garmentcode/build_actor_design_body.py` 固化为
可追溯的设计输入：完整的高度—半宽样本单独保存，GarmentCode YAML 只保存
生成器真正支持的标量字段。这样可以区分“设计阶段尺寸”和“Actor 转移阶段
修正”，避免把转移脚本当成服装设计器。

实验结果：

- 直接把曲线压缩成 `shoulder_w/back_width/waist_back_width/hip_back_width`
  后，标准无袖 T 恤在 `mid_bending` 第 78 帧崩溃，换回默认材质仍在第 120
  帧崩溃；
- 保留通过的身体标量，只把 `flare` 从 `1.0` 改为 `0.92`，默认材质仍在第
  200 帧崩溃；
- 两个候选都没有覆盖 `garmentcode_actor_proxy_current`，也没有进入 Gallery。

因此“采样应在设计阶段解决”这个判断是正确的，但实现方式不能继续粗暴修改
人体标量或只改 flare。下一步应保持通过的身体代理和标量测量，直接在前/后衣片
的侧边界生成高度曲线，并重新建立缝合边；待该设计稳定后，再单独测试布料弯曲
刚度。官方 `enable_body_smoothing` 只平滑身体碰撞网格，不是衣服表面平滑开关。

## 8. 本地第三方环境与同步规则

GarmentCode、NvidiaWarp-GarmentCode 和 blender-mcp-server 都保留为本地
第三方 Git 克隆，不提交到 AssetsLab：它们含有上游 Git 历史、Python 虚拟环境、
Warp 编译产物、MCP 缓存和模拟日志，合计超过 1 GB。目录、版本和复现方式见
`third_party/README.md`。

项目自己的模拟入口是 `tools/garmentcode/run_garmentcode_sim.py`，自定义身体
代理、测量 YAML、分区和最大模拟帧数等参数都在这里保留；因此同步仓库不会丢失
本项目对上游测试脚本的 CLI 改动。`prototype/test_output/` 仍然只作为本地
实验缓存，Gallery 静态审核资源才提交到 `prototype/preview/`。

本轮下一步使用 `tools/garmentcode/apply_actor_torso_profile.py`：它只改变前后
衣片的横向边界坐标，不改变衣片数量、缝合关系或人体 YAML，曲线强度写入输出
specification，便于物理门禁和视觉审核分别定位问题。

## 9. 物理代理与渲染服装分层实验（2026-08-06）

本轮开始验证更接近生产的分层路线：

`GarmentCode sim.obj -> Physics Proxy -> Render Garment -> Surface Deform -> Actor walk`

输入使用上一版已经通过物理门禁的 `garmentcode_actor_transfer_candidate.blend`，
不重新运行不稳定的模拟。`tools/blender/build_garment_proxy_render_pair.py` 执行以下
固定步骤：

1. 保留 Actor 权重和 Armature modifier 的 17,306 顶点衣服为
   `GarmentCodeShirt_PhysicsProxy`，只负责跟随 Actor 动画；
2. 复制为独立的 `GarmentCodeShirt_RenderGarment`，移除 Armature modifier；
3. 对渲染服装应用一级 Catmull-Clark subdivision，得到 102,670 个顶点；
4. 在静止帧绑定 `SurfaceDeformFromPhysicsProxy`，目标为 Physics Proxy；
5. 渲染 4 方向 × 8 个 walk 帧，并保存 pair blend 和 manifest。

本次验证结果：Surface Deform `bound=true`，渲染对象没有 Armature modifier，四方向
均能显示衣服并跟随动作。首次运行发现复制 Blender 对象会同时复制
`hide_render=true`，导致“绑定成功但渲染服装完全不可见”；已在脚本中显式恢复
渲染对象的可见性，并把这条检查加入流程。当前 Gallery 已切换为该 pair 结果；
背面源衣片的水平条带仍然是几何/材质质量问题，尚未进入 milestone 或随机池。

后续诊断确认，轻度平滑、强平滑、全表面重投影和“保留边界的内部重投影”都不能
同时解决肩带卡肩与背部条带：全重投影虽然减少条带，却破坏领口/肩部轮廓。因而
不能继续把修饰器叠加到当前 sim 网格上；下一阶段必须单独生成干净的 Render
Garment 版型，再让它通过 Surface Deform 跟随 Physics Proxy。失败诊断不会覆盖
Gallery current，也不会改变已经通过物理门禁的代理。

本轮 A 方案已完成首个可审核样例：`build_garment_proxy_render_pair.py` 生成
规则四边面无袖 Render Garment，前片保留 U 型领口，后片保留浅领口，肩带、侧缝
和下摆使用独立边界；Physics Proxy 保留 17,306 顶点，Animation Proxy 另行平滑
降面到 5,369 顶点，Render Garment 细分后为 321 个顶点；前后片在肩部增加连接面，
下摆增加内侧闭合面。当前 4 方向 × 8 帧通过后台渲染，背部条带和侧面下缘缺口
消失，状态为 `review_required`，尚未进入 milestone。
