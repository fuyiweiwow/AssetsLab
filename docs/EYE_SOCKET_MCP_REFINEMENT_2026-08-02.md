# 眼窝 MCP 精修回环记录（2026-08-02）

## 基线与保护

- 原演员基线：`prototype/assets/characters/generated/miku_chibi_eye_on_accurig_v13_restore_v5_state.blend`
- 盒形 MCP 失败候选：`prototype/assets/characters/generated/mcp_manual_eye_socket_v3_macro_applied.blend`
- 精确网格失败候选：`prototype/assets/characters/generated/mcp_precise_eye_socket_v2_mesh_edit.blend`
- 原演员文件未被覆盖。

## MCP 验证结果

### 1. `legacy-manual` MCP 盒形凹槽宏

MCP 返回两次 `macro_cutout_recess: success`，但渲染结果为：

- 正面：两个白色矩形/内部面片；
- 右侧：眼部出现明显外凸块；
- 结论：工具执行成功不代表视觉目标通过，候选淘汰。

证据：

- `prototype/test_output/mcp_manual_eye_socket_v3_macro_applied/front.png`
- `prototype/test_output/mcp_manual_eye_socket_v3_macro_applied/right.png`

### 2. MCP 选面 + Inset + 内推

从干净副本读取 16,256 个面，按前向法线和眼睛区域筛选左眼 201 面、右眼 212 面，共 413 面；通过 MCP 完成：

1. 进入 Edit Mode；
2. 选中 413 个面；
3. `mesh_inset(thickness=5.0)`；
4. `mesh_extrude_region(move=[0, 2.5, 0])`；
5. 返回 Object Mode 并保存。

网格面数从 16,256 增加到 16,516，说明几何操作确实发生。渲染结果显示眼球进入了头部，但眼窝边界碎裂、四边形断层明显，右侧轮廓也不自然，候选淘汰。

证据：

- `prototype/test_output/mcp_precise_eye_socket_v2_mesh_edit/front.png`
- `prototype/test_output/mcp_precise_eye_socket_v2_mesh_edit/right.png`
- `prototype/test_output/mcp_precise_eye_socket_v1/face_selection.json`

## 失败分类

- 主失败维度：`geometry/topology`；
- 次失败维度：`multiview/depth consistency`；
- MCP 层状态：已接通、可执行、可返回结构化结果；
- 工具层状态：盒形宏粒度过粗，低层选面工具可执行但无法修复现有头部拓扑；
- 根因：当前演员头部的面流不是为动漫眼窝/眼睑环设计的，直接 Inset 会跨越不连续或低质量面流。

## 技术决策

停止对当前头部继续做参数微调。下一条生产路线应是：

1. 复制头部并建立一个局部、连续、四边形为主的眼窝补片/重拓扑区域；
2. 用 Miku 轮廓只约束正面形状，不直接复制 Miku 面片；
3. 将补片边界 Shrinkwrap 到演员头部，眼球放在补片后方；
4. 通过正面、右侧和动画姿态检查后，再决定是否合并回演员。

这意味着 MCP 已经证明“能执行编辑”，但不能替代局部重拓扑。继续使用旧演员头部直接 Inset 会重复产生碎裂面，属于质量回环中的“技能/拓扑缺口”，不是参数缺口。
