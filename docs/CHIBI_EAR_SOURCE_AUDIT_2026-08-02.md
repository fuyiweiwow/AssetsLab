# Q版耳朵资产来源审计

日期：2026-08-02  
分支：`pixel_asset_test`

## 结论

目前已下载的 Miku、Niji 和 Koban 资产中，没有可以像眼球那样直接复制到演员头部的独立耳朵网格。当前手工生成的圆润耳朵仅用于定位和渲染流程测试，已标记为临时方案，不作为最终耳朵资产。

## 已检查的本地资产

| 资产 | 检查结果 | 结论 |
|---|---|---|
| `prototype/assets/external/chibi_eye_model_candidates/miku_chibi/source/extracted/miku (chibi).fbx` | 59 个网格；包含 `head_set_2_0_node`、`head_back_2_0_node`、`eyeball_1_0_node`、眉毛和眼睛，但没有独立 `ear` 网格 | Miku 的耳部外观不能干净移植；提取 `head_set` 会连带头发/头部结构 |
| `prototype/assets/external/chibi_eye_model_candidates/nijisanji_chibi` | 以完整角色网格为主，没有可识别的耳朵部件 | 不适合作为耳朵补件来源 |
| `prototype/assets/external/koban_chibi_base_mesh/Koban Chibi Base Mesh 1.0.blend` | 主要角色网格和控制器，没有独立耳朵部件 | 不适合作为耳朵补件来源 |
| `third_party/chibi-base-meshblender.zip` | 内部 `chibi base mesh.blend` 只有一个 `Cube` 网格，534 顶点、506 面，全部面属于同一个连通组件 | 耳朵已经并入整体拓扑，不能直接拆成现成补件 |

分析工具：`tools/blender/analyze_mesh_components.py`  生成报告：`prototype/test_output/chibi_base_mesh_components.json`

## Miku 的可复用范围

Miku 仍然适合继续作为眼球/虹膜风格参考，且眼球已经在当前眼部包中验证过。耳朵则不应继续尝试从 Miku 的 `head_set` 或 `head_back` 中拆出，因为这会把头发、头部遮挡面和其他面片一起带入，无法保证侧面贴合演员头部。

## 外部候选

优先候选是 Sketchfab 的 [Low Poly Cartoon Ear](https://sketchfab.com/3d-models/low-poly-cartoon-ear-37754d020eae48c3a82ea0dfa503cfdb)：它是独立卡通耳朵模型，约 1.4k 三角面、738 顶点，页面标注 CC Attribution。当前浏览器未登录 Sketchfab，下载按钮未提供文件，因此尚未写入项目目录。

备选是 [Chibi Base Mesh.BLENDER](https://sketchfab.com/3d-models/chibi-base-meshblender-26dc2e543fbd486cad313637eac07159)，但它是完整角色基础模型，不是独立耳朵补件；不应把它作为耳朵下载目标。

## 下一步

1. 使用已登录的 Sketchfab 会话下载独立卡通耳朵，保存到 `prototype/assets/external/chibi_ear_candidates/`。
2. 在 Blender 中单独渲染耳朵的正面、侧面和背面，确认它是可移植的完整几何，而不是贴图或半成品。
3. 将下载的耳朵作为外部部件绑定到 `CC_Base_Head`，只调整位置、旋转、缩放和材质，不重新捏造耳朵形状。
4. 输出演员正面和右侧面测试图，再决定是否进入随机耳朵变体。
