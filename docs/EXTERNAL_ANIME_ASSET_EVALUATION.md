# 外部动漫风格资源评估

日期：2026-08-02  
状态：Koban Wanko 已下载并完成第一轮静态审计

## 结论

当前临时生成的眼睛和耳朵同时存在位置错误与画风不一致问题，不适合继续作为正式资源。

本项目不应优先混用不同作者的独立眼睛和耳朵包。更稳妥的顺序是：

1. 选择一套完整、风格一致的 Chibi/Anime 角色资源作为五官和材质参考；
2. 保留项目自己的 `chibi_base_mesh_accurig_rigged_v1.fbx` 作为身体与动画演员；
3. 从参考资源提取或重建眼睛、耳朵和未来装饰；
4. 将这些 3D 特征绑定到项目演员的 `CC_Base_Head`，再走四方向动画渲染和像素化。

## 候选资源

### A0. Anime Chibi Base Mesh (Fully Rigged) — Koban Wanko

- 页面：[Gumroad / Anime Chibi Base Mesh](https://kobanwanko.gumroad.com/l/ChibiBaseMesh)
- 采用“自愿付费”模式，页面说明即使免费获取也允许商业使用；
- 提供 Blender、FBX 和 VRM 版本；
- 面向 Blender 4.0–4.1，包含 ARKit52 和额外面部 Blendshapes；
- 适合作为第一轮免费的完整动漫风格基准。

它仍然是一个完整的参考角色，而不是直接适配我们演员的零件包。下载后应先检查头部、眼睛和耳朵是否与目标画风足够接近，再决定提取五官还是只参考其材质和轮廓。

### A. Anime Chibi Base Mesh — Minimoku

- 页面：[Superhive / Anime Chibi Base Mesh](https://superhivemarket.com/products/anime-chibi-base-mesh)
- Blender 4.0+，提供 `.blend`、FBX、OBJ 和 Unity 文件；
- 完整绑定，约 6,604 个多边形，带 148 个面部 Shape Keys；
- 包含 2K PSD/PNG 纹理和适合动漫渲染的材质；
- 页面明确允许商业使用，但禁止重新分发或转售原始/修改后的文件；
- 适合作为“完整画风基准”和脸部结构参考，不建议直接替换我们现有演员身体。

这是目前最适合解决“眼睛、耳朵和整体画风不一致”的候选。它的优势不是单个零件，而是头部、五官、材质和绑定属于同一套设计。

### B. Chibi 3D Model — Pluto

- 页面：[itch.io / Chibi 3D Model](https://paperpluto.itch.io/chibi-3d-model)
- 最低售价 1 美元；提供带绑定和纹理的 FBX 以及 Blender 文件；
- 约 1,226 三角形，适合快速测试低多边形渲染流程；
- 脸部包含 3D 眼睛，但眉毛和嘴巴是 2D 纹理；
- 页面允许个人和商业项目使用、修改和重新着色，但禁止重新分发资源包本身。

它适合做低成本的风格验证和渲染对照，但面部系统不够完整，耳朵和随机五官能力需要下载后进一步检查。

### C. Chibi Character Base Pack — Android28

- 页面：[itch.io / Chibi Character Base Pack](https://android28.itch.io/chibi-character-model-bases)
- 最低售价 5 美元；包含男女两个绑定的 Chibi 基础角色；
- 提供 9 种眼睛颜色、多个发型、肤色和面部 Shape Keys；
- 页面明确说明适用于 Blender、Unity 和 VTuber 转换流程。

它适合测试“完整角色 + 随机外观”的方向，但页面没有展示完整授权条款。下载后必须先查看包内许可文件，再决定是否进入正式项目。

### D. 独立五官资源

- [BlenderEffect 动漫风格眼球套件](https://booth.pm/ja/items/6429528)：Blender 文件，提供多种眼球图案和可改颜色，但它只是眼睛，不解决耳朵和整体画风。
- [N/A IT O(N) 免费兔耳](https://booth.pm/en/items/1739839)：免费，提供 Blender 文件、FBX 和绑定结构，作者页面允许修改、再分发和销售，但风格限定为兔耳。
- [Miu Ears 免费耳朵](https://booth.pm/en/items/3149421)：带绑定和权重，可用于公开模型和商业模型，但要求署名且禁止再分享资源本身。
- [BlenderKit Stylised Eye](https://www.blenderkit.com/asset-gallery-detail/d22ba8d6-98c7-4f12-a1c3-f2c3bf56b995/)：免费卡通眼睛，约 544 个多边形，但没有配套耳朵和完整脸部风格。

这些资源可以用于原型或装饰实验，不建议直接组合成最终角色，因为来源不同会再次引入比例、材质和轮廓不一致。

## 推荐执行方案

优先顺序：

1. 先使用 Koban Wanko 做免费的完整风格验证；
2. 若其画风不合适，再采用 Minimoku 作为更完整的商业风格基准；
3. 若只做低成本渲染管线对照，再考虑 Pluto；
4. 暂不采用“独立眼睛 + 独立耳朵”的混搭方式作为最终方案；
5. 下载资源后，只在本地保存源文件，项目仓库只提交评估记录、转换脚本和最终渲染结果，不提交受限制的原始资源包。

## Koban Wanko 实测结果

下载文件：`E:/WorkProject/AssetsLab/prototype/assets/Koban Chibi Base Mesh.rar`
解压目录：`E:/WorkProject/AssetsLab/prototype/assets/external/koban_chibi_base_mesh/`

压缩包内包含：

- `Koban Chibi Base Mesh 1.0.blend`：完整编辑/绑定工作文件；
- `Koban Chibi Base Mesh VRM export.blend`：干净的 VRM 导出工作文件；
- `Koban Chibi Base Mesh VRM export.vrm`；
- 两个绑定/导出辅助插件压缩包；
- `READ ME.txt`。

审计输出：`E:/WorkProject/AssetsLab/prototype/test_output/koban_chibi_base_mesh_audit_v1/`

实测结果：

- 编辑版包含 164 个网格对象，其中大量对象是绑定控制器/控制形状，另有 1 个骨骼；
- VRM 导出工作文件包含 1 个角色网格和 1 个骨骼，角色网格约 5,662 顶点、10,980 多边形、6 个材质槽；
- 角色包含眨眼、视线、嘴型和 `eye size` 等面部 Shape Keys；
- 四方向静态渲染成功，证明 Blender 4.5 可以读取该资源；
- 视觉判断：它更接近人形 Anime Chibi，眼睛和耳朵比我们的当前演员小而规整。这个判断来自实际渲染对照，因此它不适合直接替换当前演员的头部，但可以作为五官形状、材质和面部动画的参考来源。

当前决定：保留该资源作为外部风格参考，不直接并入正式演员。下一步应从它的眼睛/耳朵设计建立“参考特征测试”，再在真实演员上按目标像素尺寸重建，而不是把完整 Koban 头部硬贴到当前演员上。

## 接入验收标准

候选资源进入项目之前，需要检查：

- 正面、侧面和背面是否仍然保持可接受的头部轮廓；
- 眼睛是否是独立对象、材质或可烘焙纹理；
- 耳朵是否能独立绑定到头部或耳朵骨骼；
- 是否能在 Blender 中以正交相机渲染；
- 是否能在不改变我们身体骨骼的情况下挂到 `CC_Base_Head`；
- 许可是否允许生成游戏内渲染结果、修改和商业使用；
- 五官缩小到目标像素尺寸后是否仍能保留轮廓。

下一步应先对候选资源做静态四向对照，不进入走路动画。只有五官位置、轮廓和画风通过后，才接入现有 4 方向 × 8 帧渲染管线。
