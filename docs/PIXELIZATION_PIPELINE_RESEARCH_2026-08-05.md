# Blender 到像素资源的工具调研

更新时间：2026-08-05

## 结论

可以使用 Blender 插件或 MCP 协调流程，但它们解决的是“重复操作、相机注册、批量渲染和导出”，不会自动替代像素美术判断。当前粗糙感的主要来源更可能是：直接最近邻缩小 3D 渲染、没有固定调色板、轮廓没有人工修整、透明接缝和逐帧漂移没有分别处理。

因此不建议把核心质量交给一个黑盒插件。推荐保留项目自己的 manifest/validator 和 headless 脚本，把插件用于生成候选，把 Aseprite 或等价的离线像素步骤用于调色板和人工清理。

## 待办

- [ ] 用同一份 Actor V1 参考完成 Blender 原生节点基线。
- [ ] 用免费像素化候选做 A/B 输出。
- [ ] 在不破坏脚底、头部锚点和分层合同的前提下评估 2DFactory。
- [ ] 只有重复批处理成为瓶颈时，才接入本地 Blender MCP。

## 候选工具

### 1. 2DFactory：最适合先做候选验证

页面：<https://tamara-rifqi.itch.io/2dfactory>

版本 1.2.0 页面声明支持 Blender 3.3 LTS 至 5.1，并提供固定相机参数、2D 像素尺寸测量、自定义 pivot、动作队列、4–24 方向、模块化 sprite sheet、GIF 和 JSON 导出。它与本项目的“固定注册框 + 模块化图层 + JSON manifest”最接近，价格为 10 美元起。

风险：它是外部闭源/付费工作流，页面描述不能替代在本项目 Actor V1 上的实际兼容性测试；自动裁切必须关闭或受项目注册合同约束，不能让每帧独立裁切破坏脚底和头部锚点。

### 2. Pixel Art Rendering：免费像素风渲染候选

页面：<https://lucasroedel.artstation.com/projects/qeYoKR>

该免费 Blender 插件面向 EEVEE 像素风渲染，并支持 Bayer dithering、多光源和 sprite sheet 场景展示。它适合与当前 256→64 的实验做 A/B 对照，但页面没有给出本项目所需的 Blender 4.5、透明 pass、分层输出和 manifest 保证，因此只应作为 review 候选。

### 3. Blender Pixel Sprite Renderer：轻量批处理候选

页面：<https://efeitos-visuais-brasil.itch.io/blender-pixel-sprite-renderer>

页面列出 4/8/16 方向、自动相机旋转、像素转换、sprite sheet、JSON、帧跳过和多动作支持。它适合快速验证批量导出，但体量很小，不能假定它能满足本项目的深度 pass、分层图层和固定锚点要求。

### 4. Pribambase：适合 Blender 与 Aseprite 的人工清理回路

页面：<https://www.illusionofmana.art/Pribambase.html>

它把 Blender 和 Aseprite 的纹理/UV 编辑连接起来，支持动画帧和像素材质设置。它更适合“Blender 提供参考、Aseprite 做像素清理”的工作方式，不是完整的 3D 演员批量 sprite 渲染器。

### 5. Blender 原生合成节点：应先实现

Blender 自带 Pixelate 节点，官方示例建议将它放在缩小和放大 Scale 节点之间；Image Texture 的 `Closest` 插值可避免纹理平滑；Film 的 Pixel Filter 可选 Box 以获得不额外柔化的渲染。这个方案没有外部依赖，最适合先写进项目自己的 headless 脚本。

## MCP 的作用和边界

可用候选：

- <https://github.com/ahujasid/blender-mcp>：通过 Blender 插件 socket 接收场景检查、对象操作、渲染和任意 Python 执行。
- <https://github.com/djeada/blender-mcp-server>：提供 MCP server、Blender bridge、渲染/导出/异步任务和 Python 执行能力。

MCP 可以协调以下流程：打开指定 Blend、设置相机/渲染参数、批量设置动作和帧、调用项目脚本、等待渲染、读取 manifest 和触发验证。但 MCP 本身不会决定哪些像素轮廓更好，也不应成为唯一的可复现入口。核心步骤仍应由仓库内的 Python/PowerShell 脚本完成，MCP 只做本地编排层。

MCP 安全规则：只使用本地可信 server，固定版本；不要让任意远程文本直接执行 Blender Python；渲染输出和源 Blend 使用显式路径；所有最终产物仍通过 Git 中的工具和 validator 复现。

## 推荐的 A/B 实验

使用同一份 Actor V1、同一四向相机、同一 8 帧采样和同一 64×64 注册合同，比较：

1. 当前项目处理器；
2. Blender 原生 Pixelate + Box Filter + Closest；
3. Pixel Art Rendering；
4. 2DFactory（如果确认购买/试用）。

每个候选都输出 beauty、silhouette、part-ID、depth、64×64 RGBA、调色板版本和 JSON manifest。验收重点不是“更像滤镜”，而是轮廓可读、调色板稳定、四视图一致、脚底不漂、头部不跳、图层可替换。

## 推荐顺序

1. 先实现并验证 Blender 原生合成节点路径；
2. 再用免费 Pixel Art Rendering 和轻量 Sprite Renderer 做对照；
3. 若 A/B 证明固定相机、pivot、模块化导出明显节省时间，再试用 2DFactory；
4. 只有重复操作成为瓶颈时，才接入 Blender MCP；MCP 不进入最终资产质量合同。
