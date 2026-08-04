# Chibi 模型 AccuRIG 中文新手指南

日期：2026-08-01

## 一、安装位置

AccuRIG 已安装到：

`E:\env\AccuRIG\AccuRIG.exe`

已验证版本：`2.1.0.584`

## 二、只使用修正后的模型

在 AccuRIG 中导入：

`E:\WorkProject\AssetsLab\prototype\assets\characters\generated\chibi_base_mesh_accurig_input_v3\chibi_base_mesh_accurig_input_v3.fbx`

不要使用 v1 或 v2 文件。它们的 Mirror 镜像处理顺序错误，目录中已经放置了废弃说明。

当前模型的正确处理顺序是：

1. 读取原始右半模型，不先居中；
2. 在原始位置应用 Mirror；
3. 应用 Subsurf；
4. 将完整人物整体居中；
5. 导出单个网格，不包含骨骼、相机和动画。

## 三、导入并检查模型

启动 `E:\env\AccuRIG\AccuRIG.exe`。如果软件要求登录，请使用你自己的 Reallusion 账号登录。

导入 v3 FBX 后，在模型检查步骤确认：

- 模型是正立的；
- 头部是一整个完整头部，不是左右两套头部；
- 左右两条手臂都存在；
- 左右两条腿都存在；
- 身体后面没有隐藏的第二个人物；
- 模型没有旋转 90 度。

如果看到两个完整人物并排，立即停止，不要继续绑定，说明选错了文件。

## 四、定位身体关节

AccuRIG 会从多个角度显示模型。每个关节都要放在身体内部，不要放在外轮廓表面。

### 头部和颈部

- Head（头部）：放在头部体积的上半部内部；
- Neck（颈部）：放在头部下方、身体真正连接的位置；
- 不要把 Head 放在下巴位置；
- 不要把 Neck 放在后脑勺位置。

### 手臂

- Shoulder（肩膀）：放在手臂离开躯干的位置；
- Elbow（肘部）：放在手臂实际弯曲的中心；
- Wrist（手腕）：放在前臂与手掌的连接处。

在侧面视图中，肩膀和肘部也必须位于手臂厚度的中间，不要贴在手臂前表面或后表面。

### 腿部

- Hip（髋部）：放在骨盆与大腿连接的中心；
- Knee（膝盖）：放在腿部真正的弯曲位置；
- Ankle（脚踝）：放在小腿与脚连接的位置；
- Toe（脚趾）：放在脚掌前端附近。

这个 chibi 模型的膝盖和脚踝位置非常重要。手部很小，如果 AccuRIG 无法稳定识别手指，可以减少手指骨骼数量，或者屏蔽未使用的手指骨骼。

### 膝盖是否需要标定

对于当前角色和“走路后渲染成 2D 像素资源”的目标，**需要保留并标定膝盖**。即使模型外观上没有明显的膝盖折痕，也仍然需要 `Hip → Knee → Ankle` 这条腿部链条：`Knee` 决定小腿能否独立弯曲，缺少它时，抬腿和走路会变成整条腿从髋部硬折，后续很难修正。

标定时不要把膝盖放在表面上“看起来像膝盖”的位置，而应放在腿部体积内部、预期的弯曲轴心上：

- 侧面：放在髋部到脚踝连线的中段，短腿角色可略向实际弯曲方向调整；
- 正面：保持在左右轮廓之间的腿部中心线上；
- 不要因为没有膝盖形状，就把 `Knee` 直接放到脚踝或腿的最下端；
- 如果这条腿确实被设计成完全不弯的刚性短柱，才考虑屏蔽膝盖，但这时不应再期待普通人形 `NormalWalk` 正常工作。

标定后在 `Calibrate` / `Check Animation` 中关闭 `Mirror`，只旋转一侧膝盖约 10–20 度。正确结果应是：只有该侧小腿折叠，髋部、躯干、头部和另一条腿基本不动；若整条腿被拉长或邻近部件跟着移动，返回 `Rig Body` 调整膝盖位置。AccuRIG 官方文档支持在身体示意图或 `Body Part` 中选择单个骨骼，并通过 X/Y/Z 控制器微调。[单骨骼微调说明](https://manual.reallusion.com/ActorCore-AccuRIG-1/Content/ENU/1.0/08-Check-Animation/Fine-Tuning-Bone.htm)

### 没有明显脚掌时的处理

当前模型的脚掌和脚踝几乎没有形状区分，不要强行制造一个脚掌关节。

- `Ankle`：放在小腿末端、接近脚底但略高于最低点的位置；
- `Toe`：如果侧面看不到向前伸出的脚掌，就把 `Toe` 屏蔽；
- 如果能看到很短的前伸部分，才把 `Toe` 放在那个最前端；
- 不要把 `Ankle` 放在腿的中间；
- 不要为了满足标记点而把 `Toe` 放在不存在的脚掌上。

屏蔽 `Toe` 后，将脚部视为“小腿末端的刚性脚块”。这对像素风角色通常比生成一条不存在的脚趾骨更稳定。AccuRIG 官方支持在没有完整肢体或不需要某些骨骼时使用 Mask 功能，屏蔽的关节不会生成对应骨骼。[AccuRIG 屏蔽关节说明](https://manual.reallusion.com/AccuRig-2/1.1/06-body-rig/body-rig.htm)

## 五、检查左右对称和姿势

如果界面提供中心线或对称功能，请优先启用。先检查一侧，再确认另一侧的镜像关节位置。

不要为了强行做成人类 T Pose 而拉扯模型。这个角色头大、四肢短，应先保持原始姿势；必要时再使用 AccuRIG 的 Pose Offset（姿势偏移）或 Posture Correction（姿势修正）。

## 六、绑定后预览动作

生成骨骼后，不要立即导出。请逐项预览：

1. 转动头部；
2. 抬起左手；
3. 抬起右手；
4. 弯曲左膝；
5. 弯曲右膝；
6. 播放一小段走路动作。

出现以下情况时，应返回移动对应关节：

- 头部变椭圆；
- 头部从颈部滑开；
- 肩膀拉扯头部或躯干；
- 肘部塌陷或出现尖刺；
- 膝盖把整条腿拉长；
- 脚踝把脚向上拉；
- 两只脚合并或交叉。

修正肘部问题时移动肘部，不要用移动手腕来补偿。每个关节都应放在自己的实际弯曲位置。

## 七、如何测试单个部件

AccuRIG 的 2.1 版本通常把最后一步叫作 `Calibrate`，旧版文档中也可能叫作 `Check Animation`。进入这一步后，可以先不播放完整走路动作，而是逐个测试关节。

### 1. 进入单关节调整

1. 完成 `Load Character`、`Check Model`、`Rig Body` 和 `Rig Hand`；
2. 点击左侧的 `Calibrate` 或 `Check Animation`；
3. 如果当前正在播放动作，先点击暂停；
4. 找到 `Pose Offset` 或骨骼调整区域；
5. 点击人体示意图中的关节，或者在 `Body Part` 下拉框中选择关节；
6. 使用 X、Y、Z 三个旋转控制，先做小幅度测试。

官方文档说明，可以通过人体示意图或 `Body Part` 下拉框选择具体骨骼，并用 X/Y/Z 控制器调整骨骼方向。[AccuRIG 单骨骼调整说明](https://manual.reallusion.com/ActorCore-AccuRIG-1/Content/ENU/1.0/08-Check-Animation/Fine-Tuning-Bone.htm)

### 2. 左右单独测试

测试单侧手臂或腿时，确认 `Mirror` 没有勾选。否则左右两边会同时移动，无法判断单侧绑定是否正确。

建议按以下顺序测试：

1. 选择 `Head`，左右旋转约 10 到 15 度；
2. 选择 `Neck`，上下旋转约 5 到 10 度；
3. 选择左肩，只抬左臂；
4. 选择左肘，只弯左前臂；
5. 选择右肩和右肘，重复测试；
6. 选择左髋，只抬左腿；
7. 选择左膝，只弯左小腿；
8. 选择右髋和右膝，重复测试；
9. 最后测试左右脚踝。

每次只改变一个关节。测试完后把数值恢复为 0，再测试下一个关节。

### 3. 每个部件要观察什么

#### 头部

- 转头时头部应整体移动；
- 颈部不应被拉成长条；
- 肩膀和手臂不应跟着头部移动。

#### 手臂

- 抬肩时只应带动对应手臂；
- 弯肘时前臂应围绕肘部旋转；
- 躯干、头部和另一侧手臂不应明显变形。

#### 腿部

- 抬髋时整条腿应一起移动；
- 弯膝时主要是小腿折叠；
- 脚踝旋转时脚掌不应被拉长；
- 另一条腿不应被带动。

### 4. 如何判断问题属于哪一类

- 单个关节一动，其他部件也被拉扯：关节位置或权重有问题，应返回 `Rig Body` 调整；
- 单关节测试正常，但 `NormalWalk` 很奇怪：绑定基本可用，是动作比例不适合 chibi；
- 只有脚底滑动、抬脚幅度小：通常是走路动作和短腿比例不匹配；
- 头部或身体出现左右重复：导入了错误的 v1/v2 文件，应改用 v3；
- 关节附近出现小范围穿插：可以先在 `Pose Offset` 中修正骨骼角度。

### 5. 再进行走路测试

单关节测试通过后，再选择 `NormalWalk`。预览时可以打开 `Move in Place` 或 `Zero Root Animation`，让人物固定在画面中央，避免根骨移动影响观察。AccuRIG 官方文档也建议使用固定位置和镜像动作来检查角色的对称性与绑定状态。[AccuRIG 预览与固定位置说明](https://manual.reallusion.com/AccuRig-2/2.0/03-introducing-the-user-interface/preview-window.htm)

如果单关节通过、走路失败，不要回去重绑模型；下一步应改用短腿 chibi 动作或对 NormalWalk 做姿势偏移。

## 八、第一次导出设置

第一次只导出角色和骨骼，不导出动作：

- 格式：FBX；
- 目标应用：如果有选项，选择 Blender；
- 导出内容：Character / Skeleton Only；
- 保留 Bind Pose 或 Rest Pose；
- 当前没有可用贴图，因此暂时不必嵌入纹理；
- 导出路径：

`E:\comic\chibi_base_mesh_accurig_rigged_v1.fbx`

导出后把这个文件路径发给我。我会在后台 Blender 中依次检查：

1. 静止姿势；
2. 单独转头；
3. 单独抬手；
4. 单独弯腿；
5. 最后才测试 Walk 动画。

## 九、相关项目文件

- 模型文件：
  `E:\WorkProject\AssetsLab\prototype\assets\characters\generated\chibi_base_mesh_accurig_input_v3\chibi_base_mesh_accurig_input_v3.fbx`
- 模型预览：
  `E:\WorkProject\AssetsLab\prototype\test_output\chibi_base_mesh_accurig_input_v3_preview\`
- 绑定工具研究记录：
  `E:\WorkProject\AssetsLab\CHIBI_RIG_TOOL_RESEARCH.md`

## 十、官方参考

- AccuRIG 安装说明：
  https://manual.reallusion.com/actorcore-accurig-1/Content/ENU/1.1/03-Introducing-the-User-Interface/ActorCore%20AccuRIG%20Installation%20Guide.htm
- AccuRIG 导出说明：
  https://manual.reallusion.com/AccuRig-2/2.0/09-add-motions/export.htm
- AccuRIG 官方功能介绍：
  https://www.reallusion.com/auto-rig/accurig/default.html

## 十一、导出后的自动检查结果（2026-08-01）

本次导出的文件：

`E:\comic\chibi_base_mesh_accurig_rigged_v1.fbx`

Blender 检查结果：

- 文件可以正常导入；
- 包含 1 个网格、16,296 个顶点和 1 个 101 根骨骼的骨架；
- 左右腿均存在 `Thigh → Calf → Foot` 链条；
- 单独旋转左右 `Calf` 时，小腿可以独立变形，头部和另一条腿没有明显跟随变形；
- FBX 内目前只有 T-Pose，没有嵌入 `NormalWalk` 动作。

项目中生成了一套幅度较小的 8 帧 chibi 步行动作，用于验证绑定而不是作为最终动作：

- 测试工具：`tools/blender/audit_accurig_rigged_fbx.py`；
- 步行测试工具：`tools/blender/render_accurig_chibi_walk_test.py`；
- 测试输出：`prototype/test_output/accurig_rigged_v1_chibi_walk_test/`。

当前判断：绑定结构已经达到“可以继续测试动作”的状态；但由于模型腿短、脚掌不明显，普通人形 `NormalWalk` 仍可能出现脚部重叠或脚底滑动。下一步应优先调整动作幅度和脚部接触，而不是重新标定头部或删除膝盖。

## 十二、短腿动作与像素化测试结果

为了避免把普通人形走路动作直接套到短腿角色上，项目生成了一个幅度较小的 8 帧诊断动作：

- 大腿摆动约 12 度；
- 膝盖摆动约 6–14 度；
- 脚部只做轻微滚动；
- 头部和躯干保持稳定。

测试结果显示，正面帧的头部和身体轮廓稳定，侧面帧的腿部仍会因模型没有明显脚掌而发生局部重叠，但没有出现头部脱离或整条腿拉长。这个结果说明当前绑定可以进入下一阶段，后续应通过动作设计和像素层处理解决脚部表现。

上一版动作过于保守，视觉上接近原地摆动。随后将动作改为明显步态：大腿前后摆动约 24 度，摆动腿增加约 26 度膝盖弯曲，脚部做滚动，手臂反向摆动。四方向像素化输出采用 256×256 渲染图以最近邻方式缩小到 64×64，未使用平滑插值，共生成 4 个方向 × 8 帧：

`E:\WorkProject\AssetsLab\prototype\test_output\accurig_rigged_v1_visible_walk_v4_pixels\`

其中 `right.gif` 和 `front.gif` 可直接播放，用来判断动作是否像行走；这仍是绑定验证动作，不是最终生产动作。

如果缩小到 64×64 后动作仍显得太弱，可在测试工具中提高 `--amplitude`。本次追加生成的 1.5 倍幅度版本使用：

`E:\WorkProject\AssetsLab\prototype\test_output\accurig_rigged_v1_visible_walk_v5_amplitude150_pixels\`

1.5 倍版本更容易看出抬腿和摆臂，但侧面会出现更明显的腿部重叠，因此它适合判断“动作是否足够明显”，不代表最终动作幅度。

该目录只是绑定与动作诊断结果，尚未标记为可直接进入游戏的最终资源。
