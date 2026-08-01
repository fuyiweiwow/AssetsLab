# 当前角色候选复审记录

更新时间：2026-08-02

## 当前外观基准

当前唯一有效的外观与轮廓参考是：

`E:/WorkProject/AssetsLab/front-character-anchor.png`

这是一张正面角色设计图，验收重点包括：大头比例、蓝色发型、肩部披风、上衣/腰带/腰包、短裤、手部和靴子。`base-mannequin-4way-female-sheet.png` 已降级为历史资料；此前对比板中列出的 3D 候选也全部视为淘汰，不再作为外观来源。

## 本轮复审：`third_party/kiira_chibi/Character Base.blend`

### 静态审计结果

- 有 7 个网格对象和 1 个骨架，绑定顶点组存在于多个身体部件中。
- 没有内置 Action，因此不能直接证明它能提供可用的行走动画。
- 模型按头、躯干、四肢、手、脚、脸等部件拆分，具备继续做运动测试的技术条件。
- 头部网格为 373 个顶点、726 个面；完整审计器会把所有网格一起渲染，而不是只查看头部。
- 审计没有修改源文件，也没有把它接入当前运行时或像素资源管线。

审计清单：

`prototype/test_output/kiira_character_base_anchor_audit/candidate_audit.json`

正面静态预览：

`prototype/test_output/kiira_character_base_anchor_audit/candidate_static_y_negative.png`

完整角色四向预览：

`prototype/test_output/kiira_character_base_complete_audit/candidate_static_front.png`

本轮使用的通用候选审计工具：

`tools/blender/audit_character_candidate.py`

例如：

```powershell
& E:\env\Blender\blender.exe --background --python tools\blender\audit_character_candidate.py -- `
  --source path\to\candidate.blend `
  --output prototype\test_output\candidate_audit
```

工具目前支持 `.blend`、`.fbx`、`.glb`、`.gltf` 和 `.obj`，会输出完整角色的
`front/right/back/left` 静态图和 `candidate_audit.json`。它只做读取和渲染，不会保存或修改候选源文件。

### 外观判定

判定为：**不符合当前 `front-character-anchor.png` 外观基准，不作为最终演员外观。**

原因是它更像一个灰色的中性技术素体：头部虽然偏大，但身体、四肢都很细，缺少目标图中的发型、披风、服装层次、腰包和靴子，正面剪影无法直接映射到目标角色。继续给它绑动画或做像素化，只会验证“技术流程能跑”，不能验证“角色资源方向正确”。

它可以暂时保留为：

1. 骨架结构和部件拆分的参考；
2. 运动测试的备用来源；
3. 未来新演员绑定时的技术对照。

它不能作为：

1. 当前角色的最终 3D 演员；
2. `front-character-anchor.png` 的建模替代品；
3. 最终像素资源的渲染来源。

## 当前决策

当前不再继续修补已淘汰的 `chibi-base-meshblender.zip` 外观，也不把 `Character Base.blend` 当作最终外观。下一阶段应寻找或制作一个带服装/披风/靴子、正面剪影接近 `front-character-anchor.png` 的新中性 3D 演员。

### 路线分层修正

这不影响当前已经调好的技术实验演员 `chibi_accurig_walk_test_v1`。它继续承担以下验证工作：

- 走路/跑步动作幅度与方向；
- 3D 渲染到 2D 像素化；
- 4 方向资源打包；
- Godot 运行时加载、方向切换和最近邻采样。

该演员不再承担 `front-character-anchor.png` 的最终美术验收。新的外观演员通过正面轮廓门槛后，再替换到同一套技术管线中。这样可以继续推进流程实验，同时避免把旧模型误标为最终角色。

当前技术基线已重新验证通过：

```text
PIXEL_ASSET_END_TO_END_PASS package=1 godot=1 integration=1
```

候选模型必须依次通过以下门槛：

1. 正面静态轮廓接近目标图；
2. 头、躯干、手臂、大腿、小腿、脚掌能分别控制；
3. 绑定后膝盖向前迈步不反折，腿根不明显开裂；
4. 四方向静态渲染稳定；
5. 最后才接入走路、跑步和像素化输出。

## 后续执行顺序

1. 以 `front-character-anchor.png` 制作候选筛选板，先只看正面剪影和服装块面。
2. 对新的候选执行 Blender 静态审计；不通过正面门槛的候选不进入绑定。
3. 通过后再做骨骼标注、绑定和单部件运动测试。
4. 绑定稳定后复用现有 `chibi_accurig_walk_test_v1` 的渲染、像素化和 Godot 验证管线。
