# Blender 建模 Skill / MCP 检索记录（2026-08-02）

## 结论

联网检索后，找到了与当前项目真正相关的可安装 Blender skill，但它们通常不是单独的 Blender 插件，而是“SKILL.md 工作流 + Blender MCP 后端”的组合。

最匹配当前项目的是：

1. `RobLe3/cc-blender-skill`
2. `PatrykIti/blender-ai-mcp`

## 候选一：RobLe3/cc-blender-skill

仓库：<https://github.com/RobLe3/cc-blender-skill>

它包含多个可链式加载的工作流，尤其匹配本项目的部分包括：

- `reference-to-3d`：锁定参考图进行重建；
- `reference-analysis-validator`：参考图遮罩、轮廓、边界和对比验证；
- `contour-to-mesh`：从轮廓建立网格；
- `orthographic-registration`：正面/侧面/背面坐标对齐；
- `multiview-fit-loop`：多视图渲染、比较、修正；
- `blender-uv-texturing`：UV、投影、贴花和烘焙；
- `texture-driven-mesh-fitting`：根据贴图/轮廓拟合网格；
- `quality-refinement-autoloop`：输出不合格时先诊断失败维度，再修正。

安装方式需要通过 Blender MCP 工作；仓库文档给出的插件安装方式是将 `plugin/skills/` 下的技能安装到 agent 的 skills 目录，并依赖 Blender MCP。

重要限制：仓库明确说明“人脸不能靠简单几何体自动得到”，真正的人脸仍需要减法雕刻、手工拓扑或导入已有模型后修整。这与我们当前遇到的眼窝问题完全一致，因此它更适合约束流程和验证，不应被当成一键生成器。

## 候选二：PatrykIti/blender-ai-mcp

仓库：<https://github.com/PatrykIti/blender-ai-mcp>

它不是 SKILL.md 本身，而是更受控的 Blender MCP 后端。它提供了与当前任务直接相关的宏操作：

- `macro_cutout_recess`：制作凹槽、开口和切割；
- `macro_attach_part_to_surface`：把部件贴合到曲面；
- `macro_align_part_with_contact`：修正接触间隙；
- `reference_compare_stage_checkpoint`：参考图阶段检查；
- `scene_measure_*` 和 `scene_assert_*`：确定性测量和断言。

它比“让模型直接生成任意 bpy 脚本”更适合本项目，因为每次修改都可以带检查结果。不过官方仓库主要在 Blender 5.0 上验证，当前项目使用 Blender 4.5，安装后必须先做隔离验证。

## 候选三：ahujasid/blender-mcp

仓库：<https://github.com/ahujasid/blender-mcp>

它功能成熟、资料多，支持对象修改、材质、场景检查和 Python 执行，但其中的任意代码执行能力风险较高。公开 issue 已记录 `execute_blender_code` 可以在 Blender 中执行未限制的 Python，因此不建议直接接入生产项目。

## 对本项目的建议

暂不安装普通的生成型 Blender MCP。推荐先采用：

1. `cc-blender-skill` 的参考图、轮廓、UV 和多视图验证流程；
2. `blender-ai-mcp` 的受控凹槽/贴合/检查工具；
3. 当前项目的本地 Blender 脚本继续作为可重复回退方案；
4. 眼窝任务先做“参考图锁定 → 头部浅凹 → 眼球容纳检查 → UV 睫毛贴图 → 正侧面验证”；
5. 验证通过后才进入随机五官生成。

## 当前状态

- 已找到匹配的 Blender SKILL.md 候选；
- 已安装以下 10 个 Codex skill 到 `C:\Users\Admin\.codex\skills`：
  - `reference-to-3d`
  - `reference-analysis-validator`
  - `contour-to-mesh`
  - `orthographic-registration`
  - `blender-uv-texturing`
  - `atlas-uv-fitting`
  - `texture-driven-mesh-fitting`
  - `multiview-fit-loop`
  - `fit-repair-optimizer`
  - `quality-refinement-autoloop`
- 当前 Codex 会话没有暴露 `mcp__blender__*` 工具，因此这些 skill 的 Blender MCP 执行部分尚未启用；
- 已安装 `PatrykIti/blender-ai-mcp` 到 `E:\Env\blender-ai-mcp`，并验证 Blender RPC 与 MCP 握手；
- 当前眼窝测试资产全部仍标记为研究/失败候选。

## 安装结果

Skill 安装脚本执行成功。根据安装器说明，新 skill 会在下一轮 Codex 对话中被识别。Blender MCP 已完成本地安装与握手验证，但当前 Codex 会话仍通过本地 MCP 客户端脚本调用，尚未动态暴露原生 `mcp__blender__*` 工具。

## Blender MCP 接入结果（2026-08-02）

在真实布尔凹槽测试失败后，按约定接入 `PatrykIti/blender-ai-mcp`：

- 源码目录：`E:\Env\blender-ai-mcp`
- Blender 插件包：`E:\Env\blender-ai-mcp\outputs\blender_ai_mcp.zip`
- Python 虚拟环境：`E:\Env\blender-ai-mcp\.venv`
- Blender 版本：4.5.0
- Blender RPC：`127.0.0.1:8765`
- MCP 配置：`ROUTER_ENABLED=true`、`MCP_SURFACE_PROFILE=llm-guided`

验证结果：

1. 插件已安装到 Blender 4.5 用户插件目录并成功启动 RPC；
2. 直接 RPC `ping` 返回 Blender 4.5.0；
3. 最小 MCP 客户端握手通过，返回 11 个受限工具，包括 `router_set_goal`、`search_tools`、`call_tool`；
4. MCP 服务端未常驻，避免后台孤立进程；后续由 MCP 客户端按配置启动；
5. 当前 Codex 会话尚未动态加载 `mcp__blender__*` 工具，因此本轮不能声称已经通过 MCP 执行了模型修改。

下一步：使用已接入的 MCP 客户端对“演员头部副本”执行只读场景检查，再调用受控的 `macro_cutout_recess` 或网格编辑工具；每次修改后必须做正面/右侧渲染和拓扑/接触断言。原演员和 `true_eye_socket_boolean_v1` 失败候选均保持不变。
