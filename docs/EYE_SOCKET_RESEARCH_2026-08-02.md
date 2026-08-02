# 眼眶制作方案研究记录（2026-08-02）

## 结论先行

当前不再继续“把 Miku 的完整头部或完整眼圈直接贴到演员头上”。这两种方式都会产生明显的外来部件感，不能得到真正的动漫眼窝。

下一步应在演员原头部上建立眼窝边界：眼球位于边界后方，眼眶只保留上眼睑、下眼睑短段和内侧阴影，不做完整黑色椭圆圈。

## 已测试并否定的方案

### 1. 直接替换 Miku 头部

测试文件：

`prototype/assets/characters/generated/miku_head_on_accurig_body_v1.blend`

问题：Miku 的头部模型依赖完整发型、下颌和脸部配套拓扑。移除头发和嘴后，头部顶部、后脑和颈部关系不完整，不能作为演员头部的最终替换件。

结论：保留为参考，不作为生产路线。

### 2. 直接投射 Miku 的 `eye_007_22_0_node`

测试文件：

`prototype/assets/characters/generated/conformed_miku_eye_socket_v1.blend`

问题：该网格不是独立的眼眶补件，而是 Miku 面部拓扑的一部分。投射到演员头上后会覆盖脸部区域，不能正确形成眼眶开口。

结论：只能用于观察轮廓，不能直接复用为最终几何。

### 3. 自制完整椭圆眼圈

测试文件：

`prototype/assets/characters/generated/anime_eye_socket_shell_v1.blend`

问题：正面容易变成泳镜或眼镜圈，侧面会出现薄板感。即使贴合头部表面，也仍然是外加部件，不是真正的眼窝。

结论：否定完整闭环眼圈。

## 推荐的可用路线

### 阶段 A：演员头部副本

复制演员头部区域，保留原始演员文件不变。所有实验在副本上进行。

### 阶段 B：建立眼窝边界

参考 Miku 的正面轮廓，在演员头部表面建立左右两个杏仁形边界。边界应满足：

- 外眼角向脸部轮廓方向延长；
- 上眼睑比下眼睑更明显；
- 内眼角较短；
- 不形成完整黑色环；
- 眼球中心不超过脸部最前平面。

Blender 的 Inset 工具适合先建立内外边界并控制深度；官方文档说明它可以产生内插边界，并通过深度参数把新面抬高或压低。[Blender 内插面文档](https://docs.blender.org/manual/zh-hans/3.0/modeling/meshes/editing/face/inset_faces.html)

### 阶段 C：眼窝深度

优先使用“浅凹面 + 眼睑遮挡”的方式，而不是直接对低密度头部做 Boolean。Boolean Difference 可以切割体积，但官方文档也提示非流形网格容易产生伪影；我们的演员头部需要先确认网格封闭性。[Blender Boolean 文档](https://docs.blender.org/manual/en/dev/modeling/modifiers/generate/booleans.html)

### 阶段 D：绑定

眼窝补件和眼球统一挂到 `CC_Base_Head`。如果最终把眼窝并回演员头部，新增顶点的权重复制为 `CC_Base_Head=1.0`，避免脸部再次被身体骨骼拉变形。

## 当前决策

1. Miku 头部替换方案暂停；
2. Miku 只作为眼窝轮廓、上下眼睑比例和眼球凹入深度参考；
3. 下一次测试制作“开放式杏仁眼窝补件”，而不是完整环形眼圈；
4. 完成正面、右侧和像素化三项检查后，再决定是否把它合并到演员头部。

## 开放式眼睑测试（追加）

测试脚本：`tools/blender/create_open_anime_eye_socket.py`

测试文件：

- `prototype/assets/characters/generated/open_anime_eye_socket_v1.blend`
- `prototype/assets/characters/generated/open_anime_eye_socket_v2.blend`
- `prototype/assets/characters/generated/open_anime_eye_socket_v3_smaller_eyes.blend`

结果：v2/v3 的正面轮廓比闭合环形眼圈更接近动漫上眼睑，但侧面仍出现不自然的薄线，且当前 Miku 眼球几何会在下方形成旧轮廓。因此它们只能作为比例和轮廓实验工具，不能作为最终眼窝组件。

最终眼窝需要在头部表面形成真实的内外层级，而不是把线条放在头部前方。下一步应制作一个带内侧浅凹面的头部局部副本，并把眼球置于该凹面之后。

## Miku 材质检查结果（追加）

通过 Blender 导入 Miku FBX 并检查材质节点，得到以下关系：

- `head_org_0_0_node` 使用 `face_CHM_SKIN_mat`；
- `eye_007_22_0_node` 使用同一个 `face_CHM_SKIN_mat`；
- `eyebrow_008_56_0_node` 也使用同一个 `face_CHM_SKIN_mat`；
- 上述材质引用 `ctr_mikp001_face.png`；
- `eyeball_1_0_node` 使用独立的 `eye_CHM_EYE_mat`，引用 `ctr_mikp001_eye.png`。

这说明 Miku 的眼眶、眉毛和睫毛视觉不是由多个独立睫毛实体组成，而是由脸部材质贴图和少量眼眶几何共同完成。项目中应将睫毛视为脸部贴图/投影贴花层，而不是随机 3D 睫毛部件。

## 新的技术路线

1. 先在演员头部制作浅凹眼窝，解决眼球容纳和侧面体积问题；
2. 把 Miku 的脸部贴图作为画风参考，不直接套用 UV；
3. 为演员头部建立专用眼部 UV 区域，使用透明 PNG 或 alpha 通道承载睫毛、上眼线和眉毛；
4. 眼球仍作为独立 3D 部件，眼窝和眼球统一跟随 `CC_Base_Head`；
5. 随机生成时随机化眼部贴图参数和眼球几何，而不是随机生成睫毛实体。

Blender 的 UV Project Modifier 可以把图像像投影仪一样投射到模型 UV 上，适合先制作脸部贴花原型；正式版本再把投影结果整理为稳定 UV。[Blender UV Project 文档](https://docs.blender.org/manual/en/dev/modeling/modifiers/modify/uv_project.html)

## 真实凹槽布尔测试（2026-08-02，失败证据）

为验证“按 Miku 眼球轮廓在演员头部切出真实眼窝”，建立了独立测试副本：

- 脚本：`tools/blender/create_true_eye_socket_boolean.py`
- 场景：`prototype/assets/characters/generated/true_eye_socket_boolean_v1.blend`
- 正面渲染：`prototype/test_output/true_eye_socket_boolean_v1/front.png`
- 右侧渲染：`prototype/test_output/true_eye_socket_boolean_v1/right.png`
- 机器记录：`prototype/test_output/true_eye_socket_boolean_v1/manifest.json`

测试过程依次修复了 Blender 4.x 凸包索引、演员对象缩放、局部/世界坐标、射线距离、Shape Keys 和 Armature 姿态问题；最终射线已经命中头部表面，但两次 Boolean Difference 都删除了 0 个原始多边形。渲染仍表现为正面白色外置面片、侧面悬浮，未形成真实眼窝。

结论：当前演员头部是开放/薄壳并带有现有变形结构，不能继续用 Boolean 参数调优来获得可靠眼窝。该候选标记为 `failed_boolean`，不得作为生产资产。下一步应使用 Blender 交互式网格编辑/MCP，在副本上选定眼窝区域后执行 Inset、局部法线内推和拓扑检查；若仍需保持现有演员拓扑，则改走“眼窝局部补片 + 贴合头部曲面 + 眼部 Alpha 贴图”的路线。
