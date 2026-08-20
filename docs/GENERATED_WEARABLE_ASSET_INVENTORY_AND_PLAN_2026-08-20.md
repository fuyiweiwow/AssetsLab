# 生成式 Actor / 穿戴资产清点与后续计划（2026-08-20）

## 当前决定

本阶段只清点现有资产、识别保存缺口并确定后续顺序，暂不把生成式穿戴工作流接入 AssetsStudio，也不新增 Studio UI、注册表、作业队列或正式 milestone。

目标方向保持不变：

`本地图片 AI 素体多视图 -> 本地 Hunyuan 素体模型 -> canonical Actor 校准视图 -> 本地图片 AI 套装/分 Slot 视图 -> Hunyuan3D-2MV 分 Slot 来源网格 -> ActorProfile / Slot Compiler 自动适配 -> 动作与四向 QA`

目标显卡为 `RTX 3060 12GB`。纹理、UV 烘焙和最终材质质量暂不进入当前计划。

## 1. 环境与模型

| 项目 | 位置/版本 | 当前状态 | 结论 |
| --- | --- | --- | --- |
| Blender | `D:/Apps/CodeXApp/Tests/blender-4.5.10-windows-x64/` | 可用 | 当前权威适配、绑定、审计与渲染执行器 |
| Hunyuan3D 源码 | `Hunyuan3D_Experiment/Hunyuan3D-2-main/` | 可用 | 本机只有 Hunyuan3D 2.1/2MV 路线，没有其他所谓 Hunyuan3D 版本 |
| Hunyuan3D 2.1 权重 | `Hunyuan3D_Experiment/local_models/Hunyuan3D-2.1/` | 已安装 | 可作为单图/基础 3D 生成环境保留 |
| Hunyuan3D-2MV 权重 | `Hunyuan3D_Experiment/local_models/Hunyuan3D-2mv/` | 已安装 | 已用于七槽位来源网格；模型与源码共 262 个文件，约 12.38GB，不进入 Git |
| ComfyUI | `D:/Apps/CodeXApp/Tests/ComfyUI/` | 外壳可用 | 当前只有约 78MB 的 SAM2 tiny 权重，没有 Qwen、Z-Image、SD3.5 或 FLUX 图像生成权重 |
| 本地图像 AI | 未部署 | 缺失 | 当前套装参考图仍由在线 ImageGen 产生；RTX 3060 候选见 `OFFLINE_IMAGE_AI_RTX3060_RESEARCH_2026-08-20.md` |
| AssetsStudio | 独立仓库 `AssetsStudio` | 保持原状 | 当前不接入生成式穿戴资产，只作为未来候选审查与晋级目标 |

## 2. Actor 与动画根基

### 已有

- 当前实验 ActorClass：`ChibiActorV1`。
- 当前权威实验场景：`stage10_adventurer_set_v1/milestone/adventurer_set_workflow_v3.blend`。
- 当前 Actor 使用旧 Actor 的 AccuRIG 骨骼、蒙皮和 Walk 动作；这仍然足以验证工作流合同。
- Actor Profile：`reports/actor_wearable_profile_chibi_v1.json`，模式为 `animated`，已经解析 20 个语义骨骼。
- Profile 提取入口：`extract_actor_wearable_profile_v1.py`。
- 固定审查方向：front/right/back/left；动作样本帧：1、11、21、31、41、51、61、71。

### 缺失

- 尚无“本地图像 AI 三视图 -> Hunyuan 素体模型”的正式素体候选。
- 尚无新 Actor 的自动绑骨、蒙皮或可靠动画重定向。
- 尚无完全通用的 Actor 校准拍摄包；当前头部校准已有脚本，其他 Slot 仍由现有场景和实验命令完成。
- 新生成素体若没有骨骼，只能进入 `static_only`；不能因为有表面模型就声称支持动画穿戴。

## 3. 图像参考与 Hunyuan 输入

### 正式包中已有

- 完整冒险者主设计图：`assets/reference/adventurer_set_master_turnaround_v1.png`。
- 背包、鞋、护腕三类 turnaround 参考。
- 头巾/兼容短发的 Actor 穿戴图、资产图、四张 RGB 和四张清理后的 RGBA。
- 图像拆分、背景清理与连通域清理脚本：
  - `prepare_multiview_rgba_v1.py`
  - `clean_rgba_connected_component_v1.py`

### 仅在本地实验目录，尚未进入正式包

`Hunyuan3D_Experiment/stage10_adventurer_set_v1/` 仍保存以下重要根源输入：

- Actor 头部校准四视图；
- Actor 适配发型四视图；
- `torso_outer` 四张 RGB + 四张 RGBA + manifest；
- `legs_outer` 四张 RGB + 四张 RGBA + manifest；
- `waist_accessory` 四张 RGB + 四张 RGBA + manifest；
- `feet_outer` 与后续 workflow-v2 四张 RGB/RGBA + manifest；
- `wrist_accessory` 四张 RGB + 四张 RGBA + manifest；
- `back_accessory` 四张 RGB + 四张 RGBA + manifest；
- 原始提示意图记录：`imagegen/MASTER_DESIGN_V1.md`、`imagegen/SLOT_SOURCE_RECORD_V1.md`。

这是当前最大的可复现性缺口：正式包拥有生成后的 GLB，却没有完整保留其中六个主 Slot 的最终四视图生成输入。清理实验目录前必须先完成筛选、哈希和迁移。

## 4. Hunyuan 生成来源资产

正式包已经保留七个主 Slot 的 Hunyuan3D-2MV GLB：

| Slot | 文件 | 大小约 | 当前用途 |
| --- | --- | ---: | --- |
| `torso_outer` | `adventurer_torso_outer_2mv_v1.glb` | 12.07MB | 可见上衣来源；当前袖管/躯干自相交 |
| `legs_outer` | `adventurer_legs_outer_2mv_v1.glb` | 13.09MB | 可见下装来源；模型本身在 V3 未发生切换 |
| `feet_outer` | `adventurer_feet_outer_2mv_v1.glb` | 9.50MB | 可见靴子来源；当前整鞋刚性 Foot 绑定失败 |
| `wrist_accessory` | `adventurer_wrist_accessory_2mv_v1.glb` | 8.44MB | 左右护腕来源 |
| `waist_accessory` | `adventurer_waist_accessory_2mv_v1.glb` | 4.78MB | 腰带/腰包来源 |
| `back_accessory` | `adventurer_back_accessory_2mv_v1.glb` | 8.75MB | 背包来源 |
| `head_hair` | `adventurer_head_hair_actorfit_2mv_v2.glb` | 11.79MB | 当前可复用发型来源 |

另有 `adventurer_head_hair_accessory_2mv_v1.glb`（约 10.28MB），用于证明“强包围头饰 + 兼容发型”能够作为一个组合 Slot 生成；当前 V3 已恢复原发型，因此该资产不是当前穿戴基线。

## 5. 适配与审计脚本

### 可保留复用

- 通用入口：`extract_actor_wearable_profile_v1.py`、`prepare_multiview_rgba_v1.py`、`run_hunyuan2mv_slot_v1.py`。
- Slot 编译器：
  - `build_adventurer_torso_outer_v1.py`
  - `build_adventurer_legs_outer_v1.py`
  - `build_adventurer_waist_accessory_v1.py`
  - `build_adventurer_remaining_slots_v1.py`
  - `build_adventurer_head_hair_v1.py`
- 已有 QA：Actor/服装接触、头部包围、袖口轴、腿/鞋开口连续性、腰带/衣服接口、权重白名单、手部遮挡和四向八帧审查。

这些脚本证明“同一 ActorClass 的受控 Slot 编译”可行，但多数仍写有 `ChibiActorV1` 和当前冒险者对象名，不能直接称为通用 Slot Compiler。

### 新诊断，尚未进入正式包

本地实验目录新增：

- `audit_sleeve_torso_self_intersection_v1.py`
- `final_audit_v3_sleeve_torso_self_intersection.json`
- `audit_boot_sole_contact_workflow_v1.py`
- `final_audit_v3_boot_sole_contact.json`

结果：

- 袖管/躯干在 8 帧、左右共 16 次检查中全部出现非相邻面穿插；单次最高 1192 对。
- 鞋底 P95-P05 高差最高约 0.197，最低下穿地面约 -0.049，另有帧悬空约 0.060。

这四个文件必须进入下一正式诊断 checkpoint，不能只留在临时实验目录。

## 6. 里程碑状态

| Checkpoint | 文件 | 正确定位 |
| --- | --- | --- |
| V1 | `adventurer_set_complete_v1.blend` | 历史七槽位技术闭环；旧自动审计通过，但后续人工检查发现的问题意味着它不是当前生产验收结论 |
| V2 | `adventurer_set_fitfix_headscarf_v2.blend` | 头巾/兼容发型和若干 fit-fix 的历史证明；当前已去掉头饰影响，不作为现行基线 |
| V3 | `adventurer_set_workflow_v3.blend` | 当前原发型、七槽位、可复现诊断基线；明确未 accepted，袖管与鞋底是 blocker |

Stage 10 正式包当前共 103 个 Git 跟踪文件，工作树实际内容约 291.2MB，其中大二进制由 Git LFS 管理。三个 Blend 和七/八个来源 GLB 都有 manifest/hash，但 V3 之后的两类新诊断与六个 Slot 的最终多视图输入仍需补齐。

## 7. AssetsStudio 当前资产（只清点，不接入）

AssetsStudio `origin/main` 当前登记六类正式资产：

| 类别 | 状态 | 与本生成式目标的关系 |
| --- | --- | --- |
| Actor V1 + Walk | `accepted` | 可作为未来生成式穿戴候选预览基底 |
| 发型组件池 | `source_contract` | 独立旧发型工作流；不等同于当前 Hunyuan Actor-fit 发型 |
| 五官/眨眼 | `technical_baseline` | 可继续复用 |
| GarmentCode 短袖 | `provisional` | 历史资产，不作为生成式服装主路线 |
| Blender-native 短裤 | `provisional` | 历史资产，不作为生成式服装主路线 |
| 卡通运动鞋 v10 | `accepted` | 可提供 ToeBase/Foot 分区经验，但不是当前 Hunyuan 靴子来源 |

当前冒险者七槽位、Hunyuan 运行器、ActorProfile 和 V3 Blend **均未接入 AssetsStudio**。根据本阶段决定，保持该状态。

## 8. 能力完成度

| 目标阶段 | 状态 | 说明 |
| --- | --- | --- |
| 本地图像 AI 生成素体多视图 | 缺失 | 尚未部署 Qwen/Z-Image/SD3.5；ComfyUI 没有生成权重 |
| Hunyuan 根据多视图生成素体 | 部分 | 本地 2MV 可运行，但只验证过穿戴来源，尚无素体 intake/验收合同 |
| 素体注册为 ActorClass | 部分 | 当前旧 Actor 可用；新 Actor 自动绑骨未解决 |
| canonical Actor 拍摄统一校准包 | 部分 | 当前场景和头部脚本可用，尚未统一全 Slot pass |
| 本地图像 AI 生成套装/分 Slot | 缺失 | 当前使用在线 ImageGen |
| Slot RGB/RGBA 拆分与清理 | 可用 | 已验证，但正式包需要补齐六类输入 |
| Hunyuan3D-2MV 分 Slot 生成 | 可用 | 七主 Slot 已实际生成 |
| 自动适配到同一 ActorClass | 部分 | 七槽位已有实现；袖窿、鞋底和通用化仍未完成 |
| 四向/动作 QA | 部分 | 审计框架可用；新袖管与鞋底指标尚未进入正式门禁 |
| 纹理/UV/最终材质 | 延期 | 按当前决定暂不处理 |
| AssetsStudio 接入 | 延期 | 先让命令行工作流和资产包稳定 |

## 9. 保存与清理边界

### 清理前必须保留

1. canonical Actor、骨骼、Walk、四向相机和 Actor Profile。
2. 主设计图、每个最终 Slot 的四张 RGB、四张 RGBA、manifest 和提示意图。
3. 七个主 Slot GLB、生成参数 JSON、SHA-256 和 Hunyuan 版本。
4. 当前 V3 Blend、完整/上身 GIF、四向 still 和所有 blocker 报告。
5. Profile、分图、rembg、2MV、编译器和 QA 脚本，以及 Stage 9 依赖。
6. V1/V2 manifest 和预览，用于说明被替代路径与头饰兼容结论。
7. 本地 Hunyuan 源码、2.1/2MV 权重与 Python 环境；只记录位置和版本，不上传权重。

### 补齐上述清单并验证哈希后可清理

- `hunyuan_outputs/*_review/` 中可重建的四向检查 PNG；
- 被明确拒绝的正常人比例发型和旧头饰候选；
- 中间 `candidate_vN.blend`、`.blend1` 和重复 review 目录；
- 已被正式 GLB/manifest 替代的重复 Hunyuan 输出副本；
- 旧 feet workflow 候选，但必须先确认当前靴子实际使用哪一个来源输入和网格哈希。

本轮不执行删除。先完成清单、复制、哈希和一次从正式包重建验证，再做 dry-run 清理。

## 10. 后续计划

### Phase 0：封存当前真实资产

1. 从本地实验目录筛选并迁移六个主 Slot 的最终 RGB/RGBA/manifest 和提示记录。
2. 将袖管自相交与鞋底接地脚本/报告加入正式包。
3. 新建下一 checkpoint manifest，记录所有根源输入、GLB、V3 Blend、审查证据和 blocker 哈希。
4. 从正式包独立运行一次输入检查、Slot 编译和审计，确认不依赖散乱实验目录。
5. 之后才执行可重建缓存和失败候选的 dry-run 清理。

### Phase 1：修复当前 ChibiActorV1 的两个硬 blocker

1. 为 `torso_outer` 建立 Actor 专用、不可见的低模变形笼和明确袖窿环；生成上衣仍是可见风格资产。
2. 将腋窝共享网格改为连续权重过渡，并以非相邻面自相交为门禁。
3. 将靴子改为鞋口/鞋面/前掌/鞋底语义分区；优先复用 Actor 的 Foot/ToeBase 信息。
4. 对站立阶段增加足底锁定/IK 或动画接触修正，并以接地报告和四向 GIF 验收。

### Phase 2：建立素体生成上游

1. 在 RTX 3060 12GB 上先验证本地图像 AI 的 640/768 多视图一致性，不下载多个大模型并行试错。
2. 用本地 Hunyuan 生成第一个无骨骼素体，先通过静态 silhouette、轴向、单位和表面质量门禁。
3. 将“静态 ActorClass 注册”和“动画绑骨/重定向”拆成两个阶段；在自动绑骨可靠前继续使用旧 Actor 验证服装工作流。

### Phase 3：替换在线 ImageGen

1. 用 current ChibiActorV1 做 A/B：在线 ImageGen 对比 Qwen-Image-Edit-2511 多图编辑。
2. 验证 Qwen-Image-Layered 是否能分离人物与衣服，并真实补全手臂遮挡后的衣服；失败时仍保留直接分 Slot 生成路线。
3. 只在比例、相机、跨视图对应和 Slot 完整性通过后送入 Hunyuan。

### Phase 4：把当前脚本通用化为 ActorClass/Slot 合同

1. 从冒险者对象名中抽离 Slot manifest、允许骨骼、锚点、遮挡和 QA 配置。
2. 选择第二个 Actor，重跑 ActorProfile 和校准视图；贴身服装必须重新生成，不做旧模型统一缩放。
3. 证明同一 Slot Compiler 可以接受同一 ActorClass 的第二种外观，再验证第二 ActorClass。

### Phase 5：纹理与 Studio

只有前四阶段形成稳定 CLI、manifest、candidate 生命周期和人工审查证据后，才开始纹理/UV 评估与 AssetsStudio 接入。Studio 不负责掩盖尚未解决的生成、绑定和动作问题。
