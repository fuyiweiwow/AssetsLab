# 头发实验状态（2026-08-03）

## 当前坐标契约

演员预览的正面是 `front = -Y`，右侧是 `+X`，背面是 `+Y`，左侧是 `-X`。
头发来源模型的正面不能直接假定与演员一致；导入后必须先做四向静态审计，再进行贴合。

## 本轮结论

Sketchfab 的低模 anime hair FBX 已完成后台审计和 Q 版比例贴合测试，但不保留为正式候选：

- 只有一个静态网格，没有骨骼和动画；
- 旋转到演员正面后，顶部和后脑覆盖不足，会露出大块头部；
- 不旋转时虽然覆盖较完整，但来源模型的正面定义与演员朝向不一致，不能作为可靠的随机发型基础。

本轮下载的发型包、之前的 OBJ/FBX 失败候选、失败预览和猫耳测试产物均已清理。Git 历史仍保留此前的实验记录。

## 保留内容

- `prototype/assets/characters/generated/chibi_base_mesh_accurig_calibrated_v1.fbx`：校准演员导出文件；
- `tools/blender/audit_character_candidate.py`：候选模型四向静态审计；
- `tools/blender/extract_hair_style_candidate.py`：OBJ 发型片段提取和贴合；
- `tools/blender/fit_static_fbx_hair_candidate.py`：静态 FBX 发型贴合；
- `tools/blender/inspect_hair_islands.py`：发型网格分片审计；
- 现有精灵耳朵和五官生成脚本，供后续精调使用。

下一轮应优先寻找真正带连续发帽、且能明确识别正面方向的发型模型，再评估是否需要拆分为发帽、刘海和后发三个可随机化组件。
