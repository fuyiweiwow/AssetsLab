# 三维生成演员到像素移动帧工作流

## 目标

把一个风格匹配的三维生成演员和现成走路动作，转换成四方向、每方向八帧、64 x 64 的 QQTang/Q 风格像素动画参考。正面风格基准是 `front-character-anchor.png`：大头、短身、简洁轮廓。最终游戏运行时仍使用透明 2D PNG，不在 Godot 中实时渲染三维模型。

本方案不是建模或动画教学。三维模型在这里是离线“生成演员”：负责提供可重复的身体比例、姿态、脚步、遮挡和四方向拍摄；真正进入游戏的是我们自己的 2D 像素资产。

自动化负责资产审计、动作采样、相机注册、渲染、降采样、帧验证和 Godot 集成。人工只负责美术方向判断、动作可读性、像素清理和最终验收。

## 当前结论

`third_party/chibi-base-meshblender.zip` 内部包含 `chibi base mesh.blend` 和 `.blend1`。模型只有一个网格对象，没有 Armature，没有 Action，也没有可播放动画。因此它是外观网格，不是“模型 + 运动骨骼动画”资产。

上一轮已经用自动生成的临时骨架为它渲染了 32 帧实验参考，输出在：

`prototype/assets/characters/generated/chibi_base_mesh_walk_v1/`

这些帧用于验证管线，不代表模型已经正确绑定，也没有进入 runtime。下一步优先寻找风格接近、带 rig 和动作库的生成演员；当前静态网格继续作为最终外观参考，不要求它自己承担动作骨骼。

## 推荐路线

### 0. 资产和许可审计

输入：模型文件、动作文件、来源页面、许可证。

自动化检查：

- 模型是否能在 Blender 打开；
- 是否存在 Armature；
- 是否存在网格的 Armature modifier 和顶点组；
- 是否存在 Action、NLA strip 或可导入 FBX/GLB 动画；
- 模型是否有明显空场景或损坏依赖。

人工确认：

- 许可证是否允许商业使用、修改和生成衍生图片；
- 是否要求署名；
- 动作源是否允许和模型一起使用；
- 模型是否符合目标的大头、短身、无脸中性基准。

通过条件：模型至少有一个可用 Armature，或动作文件可明确导入并绑定到该模型。当前 `chibi-base-meshblender.zip` 未通过这一条件。

### 1. 选择生成演员和动作源

优先级：

1. 风格接近且自带 rig 和 walk 动画的角色包；
2. 同一角色包的独立动作库；
3. 同一 humanoid 标准的动作库和角色；
4. 最后才做不同骨架的 Blender retarget；
5. 无骨骼静态网格只作为外观参考，不作为动作演员。

建议先只找一条 walk 动作，不要同时找攻击、跳跃、跑步等动作。动作应包含接触、下压、经过、抬升等完整循环，最好是 24 至 30 帧，然后在 Blender 中重采样为八个关键帧。

人工确认：只检查生成演员是否能稳定表现动作。重点是脚是否滑动、膝盖是否反向、手臂是否脱离身体、动作是否完整循环。不需要修改模型拓扑。

### 2. 导入生成演员

有骨骼模型：导入模型，导入或启用动作，确认 Armature modifier、顶点权重和动作轨道。

只有静态网格：不进入人工绑定教学。把它保留为外观参考，使用独立的风格接近演员播放动作，然后在像素阶段把动作转绘到我们的外观标准。

人工操作：

- Blender 的 Pose Mode 播放动作；
- 检查模型站立时脚底接近同一地面；
- 检查动作第一帧和最后一帧能循环；
- 选择要拍摄的动作和起止帧。

通过条件：动作能播放，模型不完全塌陷，脚底和头部没有持续漂移。

### 2A. `Walk.fbx` 在 Blender 中的加载方式

`Walk.fbx` 是动作包文件，不是 Blender 工程文件。不要用 `File > Open` 打开它，应使用导入：

1. 打开 Blender 4.5。
2. 用 `File > Open` 打开 `third_party/kiira_chibi/Character Base.blend`。
3. 先保存一个临时副本，例如 `E:\env\temp\opencode\kiira_walk_work.blend`，避免覆盖原始模型。
4. 选择 `File > Import > FBX (.fbx)`。
5. 选择动作包中的 `Walk.fbx`。
6. 在右侧导入选项中保持 `Automatic Bone Orientation` 关闭；如果出现 `Add Leaf Bones`，关闭它。
7. 点击 `Import FBX`。
8. 场景中会出现第二个 Armature 和一套 FBX 网格。先选中 FBX 导入的角色，在 Timeline 播放 1 到 41 帧，确认 Walk 动作本身正常。

这里导入后出现两个角色是正常的：原始 KIIRA 模型和 FBX 自带的带动作角色各有一套骨架。第一阶段先用 FBX 自带角色拍摄，最稳定；不要在 Blender 界面中手工拖动骨骼。

如果要让仓库中的 `Character Base.blend` 使用这个动作，使用“动作转移”而不是重新绑定：两套骨架的 19 根主骨骼名称一致，FBX 额外的 5 根是末端辅助骨骼。后续脚本会复制同名主骨骼的 Action F-curves 到原始 KIIRA 骨架，并忽略末端骨骼。

人工只需要确认 FBX 自带角色的 Walk 是否符合节奏。确认通过后，我会自动做动作转移和无五官渲染，不要求你手工操作骨骼。

### 2B. 演员素体和五官延期

生成演员不承担最终角色设计，必须使用“无五官、无发型、无服装细节”的中性版本。原因是后续要随机生成五官并保持所有方向和帧的注册稳定。

三维拍摄阶段保留：

- 头部体积和轮廓；
- 颈部、肩膀和身体比例；
- 手脚、腿臂遮挡关系；
- 固定光照或平面材质。

三维拍摄阶段移除或隐藏：

- 眼睛、眉毛、嘴、鼻子；
- 耳朵，除非耳朵是单独可替换层；
- 头发、帽子、饰品；
- 会改变头部轮廓的服装和配件。

当前主线只完成无五官演员素体。素体必须先锁定以下内容：

- 大头、短身的整体比例；
- 头部体积和身体轮廓；
- 肩、胯、手、脚和腿臂遮挡；
- Walk 动作的脚步、手臂相位和身体重心；
- 四方向相机注册；
- 每方向八帧和统一脚底基线。

三维五官随机化延期到素体验收之后。延期后的流程保留如下：

1. 使用 `appearance_seed` 生成三维五官方案，包括眼睛样式、间距、大小、眉毛高度、腮红开关和头部局部坐标；
2. 在无五官三维头部上实例化临时 Eyes/Brows/Blush 几何；
3. 让方案随演员动作和四方向相机一起拍摄，确认轮廓、遮挡和方向注册；
4. 分别渲染 `HeadBase`、`Eyes`、`Brows`、`Blush`；
5. 以最近邻降采样输出 64x64 2D 图层；
6. Godot 只选择已拍摄的 2D 图层，不在运行时生成或渲染三维五官。

`tools/generate_3d_face_variant_plan.py` 已保留为后续实验工具，但当前不执行、不接入素体渲染，也不作为本阶段验收条件。它只生成可审计的几何方案 JSON，状态为 `plan_only`。

当前只使用无五官 `HeadBase` 素体。现有 `prototype/assets/characters/rebuild_atlas_v1/` 的 `face_base`、`eyes`、`eyebrows` 和 `ears` 暂不接入素体试拍，待素体验收后再作为五官输出层。

### 3. 重定向到项目动作合同

项目当前合同固定为四方向：`front`、`right`、`back`、`left`，每方向八帧。脚底基线为 runtime `y=60`，头部和颈部锚点固定。

不要让外部动作直接改变项目方向、帧数和注册框。使用 Blender 作为动作源，再将动作采样到项目的八帧合同。外部动作解决“自然运动”，项目合同解决“方向、帧数、遮挡和游戏注册”。

自动化输出：每方向八个 256 x 256 的透明参考帧，并同时输出 beauty、silhouette、part-ID、depth/order（如果模型可分件）。

人工确认：先只检查正面八帧。重点看双腿是否交替、双臂是否反向摆动、接触帧是否踩地、头部是否稳定。正面不通过，不生成其余方向的像素成品。

### 4. 低分辨率渲染和像素化

渲染原则：

- 正交相机；
- 先渲染 256 x 256，再按 4 倍整数比例最近邻降采样到 64 x 64；
- 透明背景；
- 固定光照和相机；
- 不使用双线性或平滑缩放；
- 输出参考图，不直接当作最终像素美术。

“三维渲染成像素风插件”可以作为初始轮廓、阴影和颜色参考，但不能替代人工像素清理。64 x 64 下必须手动处理轮廓、脚、手臂交叠、头部比例和颜色数量。

### 5. 像素清理

推荐顺序：

1. 只清理 front 的静态接触帧；
2. 清理 front 八帧；
3. 清理 right；
4. 由 right 镜像生成 left，再做必要的方向修正；
5. 清理 back；
6. 最后拆分 `Feet`、`LowerBody`、`Arms`、`Torso`、`Head` 层。

人工操作：使用 Aseprite、Pixelorama 或其他支持逐像素编辑的工具。保持 64 x 64、固定脚底和固定头部锚点。不要在每帧单独缩放角色。

通过条件：1x 查看时轮廓清楚，游戏尺寸查看时动作能读懂，首尾帧无明显跳变，脚不漂移。

### 6. Godot 集成验证

只在像素清理和分层完成后接入 Godot。每个层必须使用相同的方向和帧索引。运行现有 headless 测试和 W/A/S/D 捕获，验证尺寸、透明度、脚底、层对齐和方向映射。

## 文件和工具约定

- 项目动作合同：`prototype/assets/characters/generated/skeleton_walk_pipeline_v1/3d_guide_v1/g1_pose_contract.json`
- 相机和锚点合同：`prototype/assets/characters/generated/skeleton_walk_pipeline_v1/3d_guide_v1/camera_contract.json`
- 当前三维参考计划：`3D_TO_2D_PIXEL_ART_PLAN.md`
- 模型/动作审计工具：`tools/blender/audit_animation_source.py`
- 当前无骨骼模型实验渲染工具：`tools/blender/create_chibi_base_walk.py`
- 当前实验像素化工具：`tools/process_chibi_base_walk_pixels.py`
- FBX 动作审计工具：`tools/blender/audit_fbx_animation_source.py`
- 正面试拍 GIF：`tools/make_kiira_front_test_gif.ps1`
- 原始 chibi 网格演员试拍：`tools/blender/render_original_chibi_actor_test.py`

## 当前执行状态

| 步骤 | 状态 | 说明 |
| --- | --- | --- |
| 0 资产和生成演员审计 | 已完成 | 当前外部网格无骨骼；KIIRA 同系列 Walk.fbx 已确认可导入 |
| 1 选择现成动作 | 已完成 | 已找到并下载 KIIRA 同系列 `Walk.fbx`，动作帧为 1-41 |
| 2 导入并绑定 | 已完成 | Walk.fbx 有 7 个身体部件、24 根骨骼；与仓库 KIIRA 骨骼名称一致 |
| 3 重定向到八帧合同 | 试拍完成 | 已生成无五官 KIIRA 正面八帧，动作采样自 1-41 帧 |
| 4 原始 chibi 素体演员 | 技术试拍完成，生产绑定未通过 | v5 可驱动并输出 8 帧；固定 G0 测试显示原始单体网格与 KIIRA 骨骼区域不匹配 |
| 5 生成正确比例的中性素体 | 待选择演员路线 | 在 KIIRA 稳定演员、手工区域绑定原网格、或项目 guide rig 新建素体之间做决定 |
| 6 演员素体四方向 | 暂缓 | 生产演员通过 front G0/G1 后再扩展 right/back/left |
| 7 三维五官方案 | 延期 | 素体验收后再启用 `generate_3d_face_variant_plan.py` |
| 8 人工像素清理 | 未开始 | 素体比例和动作通过后开始 |
| 9 Godot 集成 | 未开始 | 等待像素清理和分层通过 |

## 已完成的关键执行记录

`ACTOR_V1_BUILD_LOG.md` 记录了原始网格、Walk.fbx 和 KIIRA 骨架的审计，
刚性绑定策略，构建命令，输出路径和验收结果。当前生成物为：

- `prototype/assets/characters/generated/original_chibi_actor_test_v5/`：3D 演员和 8 帧 256x256 front 试拍；
- `prototype/assets/characters/generated/original_chibi_actor_pixel_v1/`：256 到 64 最近邻像素化的 review-only 试拍。

本次构建脚本 `tools/blender/render_original_chibi_actor_test.py` 已支持直接
读取当前双层 ZIP，并在保存演员前移除 FBX 自带的源网格。

## 需要用户手动确认的事项

1. 在 Blender 中播放 KIIRA `Walk.fbx`，确认模型没有明显塌陷和脚底漂移。
2. 确认先输出正面八帧试拍，而不是直接生成四方向最终帧。
3. 在像素清理阶段确认 QQTang 风格比例、轮廓、颜色和服装是否符合预期。

原始 chibi 网格的第一版绑定曾出现只显示头部的问题，原因是自动权重和相机使用了错误的 rest-pose 范围。当前 v5 已改为按身体区域刚性绑定，并按八个动画姿态的联合边界设置试拍相机；它证明绑定、动作驱动、透明截图和 256 到 64 最近邻像素化技术可行，但还没有通过固定 G0 相机和 G1 多通道输出验收。

当前决定：KIIRA `Walk.fbx` 保留为动作源；原始 `chibi-base-meshblender.zip` 的直接绑定仅作为技术试拍，不作为已通过的生产演员。固定 G0 实验显示它与 KIIRA 骨骼区域不匹配，下一步必须选择稳定 KIIRA 演员、手工重做原网格绑定，或在项目 guide rig 上制作新的中性 chibi 素体。

## 原始 chibi base 模型为什么仍然可以使用

`third_party/chibi-base-meshblender.zip` 不是不能使用，而是不能直接播放 `Walk.fbx`：它只有一个静态网格，没有 Armature、顶点组或 Action。

有三条可用路线：

1. **保留它作为最终外观模型。** 使用 KIIRA `Walk.fbx` 作为生成演员，提取步幅、腿臂相位、脚底和遮挡关系，然后把这些运动转绘到这个模型对应的 2D 像素基底。这是当前最稳妥的路线。
2. **给它绑定 KIIRA 同名骨架。** 将静态网格绑定到 19 根主骨骼，再使用现有 `transfer_same_name_action.py` 或绑定后的动作驱动。这能让三维网格参与渲染，但需要额外检查自动权重和身体变形质量。
3. **将它拆成身体部件后刚性绑定。** 适合这个低面数 chibi 网格，但关节处可能出现硬折，需要手动检查。

头部变大、身体变小也有机会改变。推荐先在三维演员阶段统一调整头/身体比例，再重新拍摄，而不是对每个像素帧单独缩放：

- 头部整体放大约 1.15 到 1.30 倍；
- 身体和四肢整体缩小约 0.75 到 0.90 倍；
- 头部中心、颈点和脚底必须继续对齐项目合同；
- 先只做 front 八帧比例试拍，通过后再扩展四方向。

如果原始静态网格的轮廓明显比 KIIRA 更接近 `front-character-anchor.png`，就应该优先使用原始网格作为外观基底，KIIRA 只提供动作演员，不应因为它已有 Walk 就把它当作最终角色。

## 已找到的候选资产

### 已降级：Mixamo 自动绑定 + Walking 动作

来源：

- Mixamo：`https://www.mixamo.com/`
- Adobe Mixamo FAQ：`https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html`

Mixamo 依赖 Web 服务，当前环境和地区可用性不稳定，也无法保证当前夸张比例网格能通过自动绑定，因此不再作为本项目主路线。筛选主标准改为动画质量和与当前 chibi 形体的匹配程度。

但这不是“完全没有限制”：

- 需要 Adobe ID；
- Mixamo 的自动绑定只支持人形角色，夸张比例、断开的身体部件、额外肢体或复杂服装可能失败；
- Mixamo 只作为可选快速实验，不作为主路线。

对当前 `chibi-base-meshblender.zip`，不再把 Mixamo 作为必要步骤。只有用户已经能正常访问 Mixamo 时，才把它作为可选快速实验。

### 不作为主演员：Blender Studio Rain v3

来源：`https://studio.blender.org/characters/rain/v3/`

- 免费下载；
- Blender 4.1+；
- 有完整 `RIG-rain` 骨架和蒙皮网格；
- 页面明确标注 `CC-BY`，要求保留署名：`Rain Rig (CC) Blender Foundation | studio.blender.org`；
- 适合本地测试 Blender 相机、动作采样和像素化，但模型本身是有衣服和脸的真人比例角色，不适合作为 QQTang 最终外观。

本地审计结果：Rain v3 有 1 个骨架、20 个蒙皮网格和 NLA 动画轨道，但其默认文件中的动作主要是 rig/面部演示，不确认包含完整 walk cycle。因此它适合作为“可靠骨骼和绑定测试模型”，不应直接当作最终走路动作源。

### 不作为主演员：Blender Studio Snow v4

来源：`https://studio.blender.org/characters/snow/v4/`

- 免费下载；
- Blender 4.1+；
- 完整角色 rig；
- `CC-BY`，要求署名：`Snow Rig (CC) Blender Foundation | studio.blender.org`；
- 页面包含 parkour 动作展示，但不等于提供可直接复用的 walk cycle 文件。

### 不作为首选：Blender Studio Walking Vanilla 文件

来源：`https://studio.blender.org/training/animation-fundamentals/5d70e888679d15ec6e692988/`

该页面确实是公开课程中的行走动画文件，并标注 `CC-BY`，但下载需要 Blender Studio 登录。它可以作为人工动作参考，不作为当前自动化流程的第一依赖。

### 当前最匹配：KIIRA Chibi + Chibi Animations

来源：

- 模型：`https://opengameart.org/content/chibi-3dm-collection-textured-rigged-redone`
- 动作：`https://opengameart.org/content/3d-chibi-animations-idle-and-walk`
- 动作包：`ANIM PACK 1.zip`，包含 `Walk.fbx`、`IDLE1.fbx`、`IDLE2.fbx`、`IDLE3.fbx`

这是目前最符合美术方向的候选：页面标签包含 `chibi`、`anime`、`cel shaded`、`animated`，动作页面明确提供 `Walk`。动作包与当前仓库的 `third_party/kiira_chibi/Character Base.blend` 属于同一 KIIRA 角色系列，理论上比跨模型重定向更直接。

模型和动作只作为内部生成演员，不直接进入 Godot 或最终资源包。项目只保留最终重绘的 2D 像素帧，以及来源和处理记录。

## 推荐执行决策

当前建议按这个顺序执行：

1. 使用 KIIRA 模型和同系列 `Walk.fbx`；
2. 自动审计 FBX 的骨架、动作帧范围和蒙皮；
3. 在 Blender 中把动作和模型绑定到现有四方向相机合同；
4. 先生成正面八帧 256px/64px 试拍；
5. 根据试拍结果调整演员比例、镜头和动作采样；
6. 再输出四方向 32 帧和像素参考。

如果当前动作演员失败，下一步不是手工建模，而是：

1. 使用 Quaternius 或 KayKit 的 stylized 演员和动作库作为技术备用；
2. 保留当前项目已经验证的八帧姿态合同；
3. 把动作转换成几何/关节参考；
4. 继续使用当前 `chibi-base_mesh_walk_v1` 的外观实验或由用户在像素阶段重新绘制。

## 来源记录规则

模型和动作只作为内部生成演员时，筛选主标准是美术风格、动作质量和管线可用性，不把商用许可作为主要决策条件。仍然保留来源记录，避免后续无法追溯生成参考：

- 模型来源 URL；
- 模型页面和动作页面；
- 动作来源 URL、动作名称和下载日期；
- 使用的 Blender 版本和导出格式；
- 最终像素图是否经过人工重新绘制；
- 源模型和动作不进入最终运行时资源。

如果最终像素图不包含原模型的纹理、脸、服装或可识别细节，而只是根据动作和轮廓重新绘制，通常比直接分发模型或渲染贴图更容易满足许可要求。但这不是法律意见，遇到商业发布仍应按具体许可文本确认。

## 用户现在需要做的唯一手动步骤

1. 用 Blender 打开 `third_party/kiira_chibi/Character Base.blend`。
2. 导入临时动作包中的 `Walk.fbx`，或直接播放动作包中的 FBX。
3. 观察正面走路是否有明显塌陷、脚底漂移或身体比例不协调。
4. 将观察结果告诉我：`通过`，或描述具体问题。

如果正面动作通过，不需要用户继续操作。我会自动完成八帧采样、四方向相机、256 到 64 降采样和帧验证。
## 当前状态说明（2026-08-02）

本文早期章节中的 KIIRA 模型、Q2/Q3 绑定和试拍命令已经废弃，相关外部模型与脚本已从工作树移除。它们只用于解释历史尝试，不是当前执行入口。当前执行入口是 `tools/run_pixel_asset_end_to_end.ps1`，当前运行时基线是 `prototype/assets/characters/runtime/chibi_accurig_walk_test_v1/`。
