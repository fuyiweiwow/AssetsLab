# Miku 头部替换演员身体测试记录（2026-08-02）

## 目的

验证是否可以移除 Miku 的头发和嘴，只保留 Miku 的动漫头部结构，并将其安装到当前 `ChibiBaseMesh_AccuRIG_InputMesh` 演员身体上。

## 当前测试文件

- Blend：`prototype/assets/characters/generated/miku_head_on_accurig_body_v1.blend`
- 正面图：`prototype/test_output/miku_head_on_accurig_body_v1/front.png`
- 右侧图：`prototype/test_output/miku_head_on_accurig_body_v1/right.png`
- 参数与对象清单：`prototype/test_output/miku_head_on_accurig_body_v1/manifest.json`
- 生成脚本：`tools/blender/assemble_miku_head_on_accurig_body.py`

## 保留对象

1. `head_org_0_0_node`：Miku 面部主体
2. `head_back_2_0_node`：后脑头部主体
3. `eye_007_22_0_node`：眼眶/眼睑面片
4. `eyeball_1_0_node`：眼球
5. `eyebrow_008_56_0_node`：眉毛

## 移除对象

- Miku 前发、后发、发饰
- Miku 嘴部与牙齿
- Miku 原始骨架
- 演员原头部面片
- 之前的 Miku 眼球和眼眶试验对象

## 绑定方式

Miku 头部各部件作为刚性对象，统一父级到演员 `Armature` 的 `CC_Base_Head` 骨骼。这样可以保留头部整体形状，避免再次出现脸部被身体骨骼拉伸的问题。

## 结果判断

方案在技术上可行，头部已经成功安装到演员身体上。当前版本主要用于判断头型、眼睛位置和头身比例。

当前限制：

- 没有头发时，头部顶部和后脑轮廓会显得像一个裸头模型，这是预期现象；
- 当前头部是刚性父子绑定，还没有制作面部表情骨骼；
- 本测试文件保留的是当前演员文件中的 T-Pose 状态，尚未在本次测试中重新接入走路动作；
- 颈部接缝需要根据用户观察继续调整，必要时增加颈部过渡面或保留 Miku 头部下缘。

## 下一步建议

如果正面和侧面的头型方向可接受，下一步按以下顺序处理：

1. 调整头部与颈部接缝；
2. 为 Miku 头部部件制作可复用的头部替换组件；
3. 接入已有 walk 动作，验证刚性头部是否跟随身体；
4. 再决定是否恢复发型，以及是否把眼睛、眉毛作为随机生成组件。
