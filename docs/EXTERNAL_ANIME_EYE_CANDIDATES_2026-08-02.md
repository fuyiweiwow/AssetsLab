# 外部动漫眼睛补件候选评估（2026-08-02）

## 目标

为原始 3D 演员 `chibi_base_mesh_accurig_rigged_v1.fbx` 寻找可独立挂接的动漫眼睛补件。评估重点是：

- 正面是否有清晰、好看的眼白、虹彩、瞳孔、高光和睫毛层次；
- 侧面是否是连续、薄、可控的眼球轮廓，而不是贴在脸前的厚块；
- 是否能脱离原角色头部，独立缩放、定位，并进入后续随机化流程；
- 授权是否允许进入项目资源生成流程。

## 候选一：Open3DLab Procedural Anime Eyes — 淘汰

来源：[Procedural Anime Eyes (With Rig)](https://open3dlab.com/project/614fa95f-e032-4a87-af86-1e2d72c288a8/)

- 页面标注 CC0，并提供 `Anime_Eyes.blend` 和眼部骨骼；
- 本地文件：`prototype/assets/external/anime_eye_candidates/open3dlab_procedural_anime_eyes/Anime_Eyes.blend`；
- 检查结果：主要眼睛对象是四顶点平面，外观依赖节点材质；在当前渲染测试中只得到灰黑圆片；
- 结论：不满足当前“好看且侧面正确”的要求，保留文件仅用于候选审计，不进入正式运行时。

## 候选二：OpenGameArt Generic Anime Face — 淘汰

来源：[Generic Anime Face](https://opengameart.org/content/generic-anime-face)

- 页面标注 CC0；
- 本地文件：`prototype/assets/external/anime_eye_candidates/opengameart_generic_anime_face/animefaceshare.blend`；
- 文件中存在独立的 `H.cornea`、`H.face.l.iris`、`H.face.r.iris` 和睫毛材质面；
- 已完成挂接工具和四视图测试：`prototype/test_output/opengameart_anime_eyes_on_accurig_v2/`；
- 用户复核结果：正面造型不够好看，侧面仍然呈现厚块状贴片，眼睛状态不正确；
- 结论：明确淘汰，不作为基础五官，也不作为正式运行时依赖。测试脚本仅保留作失败案例记录。

## 候选三：Blendkit / BlenderKit Stylised Eye — 下一轮优先测试

来源：[Stylised Eye](https://www.blendkit.com/asset-gallery-detail/d22ba8d6-98c7-4f12-a1c3-f2c3bf56b995/)

- 页面描述为 procedural stylised cartoon blue eye；
- 页面显示质量评分 9.5、544 个多边形、99 KiB、Royalty Free；
- 标签包含 anime、stylised、toon、eye、eyeball、iris、pupil；
- 这比前两个候选更符合“可控 3D 眼球补件”的方向，优先检查其真实侧面轮廓、睫毛结构和材质导入结果；
- 获取方式不是普通直链，需要通过官方 BlenderKit 插件导入。官方插件仓库见：[BlenderKit 官方插件](https://github.com/BlenderKit/blenderkit)；
- 当前状态：已确认候选，尚未下载到项目资产目录，未通过我们的四视图测试，因此不能宣称已可用。

## 当前决策

Open3DLab、OpenGameArt 和 BlenderKit 的球形 `Stylised Eye` 均不满足当前目标。下一步优先取得 Love-chan 的眼睛参考，使用同一套四视图、近景侧面、像素化预览标准；如果仍然失败，再考虑付费的完整动漫眼球资源或按参考结构自行建模。

> 2026-08-02 更新：Love-chan 已确认属于平面眼睛路线，不再作为候选。下面的重新检索以“有实际曲面厚度的眼球/椭球、可见侧面轮廓、眼睑沿曲面工作”为准。

## 候选四：BlendAtlas Tiny Eye — 淘汰

来源：[Tiny Eye](https://blendatlas.com/products/tiny-eye)

- 页面描述为程序化风格眼睛，支持 EEVEE/Cycles，并提供 iris、pupil、cornea 的形态键；
- 实际查看展示图后发现它的默认方向更接近写实眼球，展示封面不是我们需要的 Q 版动漫眼睛；
- 它还需要通过 Gumroad 领取文件，不能在未完成领取前进入项目资产目录；
- 结论：作为通用程序化眼球工具保留参考，但不作为当前演员的首选五官。

## 候选五：Easy Anime Eye — 免费包不足，暂不采用

来源：[Easy Anime Eye](https://kingmusa.gumroad.com/l/jjbrz)

- 展示图的正面画风更接近目标，且页面说明支持 Blender 4.4/4.5；
- 但免费包只包含睫毛、眉毛、对应材质和眼影，真正的动漫眼球、眼睛材质属于付费内容；
- 结论：免费包不能解决当前问题，未经付费授权不采用。其展示图可作为风格参考。

### 实际下载与挂接复测记录

- 用户实际下载文件：`E:\Env\Assets\簡単アニメアイ_販売用ファイル_Gumroad_無料.blend`；
- 原文件单独渲染正常，能看到白色眼白、黑色瞳孔、棕色睫毛和眉毛；
- 初次挂接只提取六个对象，结果漏掉 `eyelashes.body`、`eyelashes.sharp`、`eyebrows` 和 `eye.under.shadow`；
- 已修正挂接工具，改为整组提取十个眼部对象，并在解绑父级前更新世界矩阵；
- 四视图结果：`prototype/test_output/easy_anime_eye_on_accurig_v19_adapted/`。正面可以看到眼线轮廓，但眼球/瞳孔层次明显丢失；侧面眼睛变成向外突出的薄片/小圆体，不满足当前演员的侧面要求；
- 额外加入 `--adapt-source-materials`、`--debug-flat-eye`、`--hide-highlights` 作为诊断参数。即使使用扁平材质适配，结果仍不达到正式资源标准；
- 逐对象审计工具：`tools/blender/isolate_easy_anime_eye_source.py`；输出：`prototype/test_output/easy_anime_eye_source_isolation/`；
- 结论更新：该免费文件适合保留为画风和分层参考，不适合作为当前演员的可拆装基础五官。不要继续在此文件上消耗绑定/缩放时间。

## 候选六：Love-chan Low Poly Eye Rig — 当前最值得拿来拆解参考

来源：[Love-chan Low Poly Eye Rig](https://blendatlas.com/products/low-poly-eye-rig-example-blend-file-love-chan)

- 页面说明是免费 `.zip`，包含 Blender 4.4+ 的完整低模角色和可摆动、可动画化的眼睛；
- 展示图显示的是 Q 版动漫眼睛，包含白色眼球、虹彩/瞳孔、高光以及眼线/睫毛层；
- 这不是直接替换演员的成品补件，但很适合作为眼球深度、虹彩贴合和眼睛骨骼控制的参考源；
- 获取需要 Gumroad 0 美元领取，页面会提交当前登录邮箱。当前未替用户提交表单，需用户确认后下载；
- 结论：优先级高于前面所有失败候选，下一步应下载后检查对象、材质、骨骼和侧面视图，再决定是否拆出为补件。

## 评估顺序调整

1. 先取得并检查 Love-chan 的 `.blend`，重点观察侧面眼球与眼眶的关系；
2. 如果其眼睛结构可拆分，提取为“参考基准眼”并挂接到原演员；
3. 如果仍不适合直接复用，再考虑购买 Easy Anime Eye 的完整眼球包或自行按其结构重建；
4. 不再继续调 OpenGameArt、Open3DLab 或 BlenderKit 球形眼球的缩放参数。

## 失败案例测试工具

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\run_opengameart_anime_eye_test.ps1
```

该工具仅用于复现 OpenGameArt 候选的失败结果，不代表正式资源管线。

## 第二轮检索：真正的 3D 曲面眼睛候选

### 优先候选 A：DadsCastle / Toon Eye Collection

来源：[BlenderNation 介绍](https://www.blendernation.com/2024/02/08/blender-toon-eye-collection/)、[BlendAtlas 条目](https://blendatlas.com/products/toon-eye-collection)

- 基于 UV Sphere 眼球，不是 Love-chan 那种平面贴片；
- 提供 simple toon 和 stylized 两种程序化眼睛；
- 眼睑、睫毛可通过 Geometry Nodes 生成，并有示例 rig 和 driver；
- 官方说明支持把眼睛缩放成椭圆，并接入角色 rig；
- 这是目前最贴近我们“Q 版、3D 曲面、可动画、可渲染像素化”要求的候选；
- 优先级：最高。

### 优先候选 B：Procedural Cartoon Eyeball

来源：[BlendAtlas 条目](https://blendatlas.com/products/procedural-cartoon-eyeball-for-blender)

- Geometry Nodes 生成可定制卡通眼球；
- 有六种眼睛预设和十二种眼球材质；
- 可以分别调眼球旋转、上下眼睑方向和比例；
- 适合先作为“高质量基础眼球”，再把眼睑/眉毛接到我们的演员；
- 优先级：很高。

### 优先候选 C：Eye Rig / Geonodes Eye Rig

来源：[Eye Rig](https://blendatlas.com/products/blender-31-eye-rig-with-geometry-nodes)、[Geonodes Eye Rig](https://blendatlas.com/products/geonodes-eye-rig-procedural-rig-for-blender-51)

- 都是可领取的 Geometry Nodes 眼睛 rig；
- `Eye Rig` 明确包含 pupil、iris、cornea 控制，还可以把圆形瞳孔变成裂缝形；
- `Geonodes Eye Rig` 包含眼睑与可调睫毛，基础眼球形状可修改而不破坏控制；
- 外观可能需要我们重新做成目标画风，但作为“正确的 3D 运动结构”很有价值；
- 优先级：高，适合作为技术基准。

### 候选 D：BlendSwap Cartoon // Real Eyes

来源：[Cartoon // Real Eyes - Model and Materials](https://www.blendswap.com/blend/25742)

- 页面明确提供模型和材质，并包含 toon、realistic、glow 三种方向；
- 适合检查能否直接提取白眼球、虹彩、瞳孔和材质层；
- 视觉风格未必直接匹配我们的演员，但比单纯材质球更值得实际挂接测试；
- 优先级：中高。

### 候选 E：BlendSwap Procedural Anime Eye Shader

来源：[Procedural Anime Eye Shader](https://blendswap.com/blend/23319)

- 页面提供 Blender 文件，标记为 Eevee/Cycles 和 procedural anime eye；
- 更偏“程序化材质+眼球模型”，不保证有完整眼睑 rig；
- 可作为低成本备用测试，但优先级低于 Geometry Nodes 眼球方案。

### 候选 F：BMBrice Sonic Style Eye Rig

来源：[Sonic Style Blender Eye Rig](https://www.youtube.com/watch?v=3IDD5_HtPYE)

- 重点是解决曲面眼球、瞳孔与眼球运动的关系；
- 不是我们的 Q 版画风成品，但适合观察“瞳孔不贴片、侧面不穿帮”的结构；
- 保留为技术参考，不作为首个下载测试对象。

### 暂不作为下载目标

- `Projected Texture Eyes`：虽然整体是 3D 眼睛 rig，但核心是投影纹理/位移，仍然偏 2D 视觉路线；
- Packt 的 `animeEyes_Start.blend`：教程明确采用较平的动漫眼睛结构；
- TadayoshiCG 的高质量程序化眼睛：适合作为目标画风参考，但当前没有可直接取得的独立测试文件。

## 第二轮执行顺序

1. 先取得并测试 `Eye Rig` 与 `Geonodes Eye Rig`，确认眼球、虹彩、瞳孔和眼睑的真实 3D 关系；
2. 再测试 `Procedural Cartoon Eyeball`，重点看 Q 版材质和四视图轮廓；
3. 然后测试 BlendSwap `Cartoon // Real Eyes`；
4. 统一接入现有演员测试工具，输出正面、左右侧面、背面和 256 像素预览；
5. 只保留能通过“正面好看 + 侧面连续 + 不明显突起 + 可独立定位”的候选。

## 2026-08-02 下载与首轮审查：BlendSwap Procedural Anime Eye Shader

- 用户已下载原始文件：`E:\Env\Assets\Procedural Anime Eye Shader.blend`。
- 已复制到项目候选资源目录：`prototype/assets/external/anime_eye_candidates/blendswap_procedural_anime_eye_shader/Procedural Anime Eye Shader.blend`。
- SHA-256：`BB4987A1F492987AAB7AFE9BBB9051EC4083853ED3884290842360ED3D1BD2FF`；源文件与项目副本一致。
- Blender 4.5.0 可正常打开并使用原文件的 Cycles 渲染设置，原始场景渲染可见白色眼白、粉色虹膜、黑色瞳孔和高光，说明程序化材质没有在当前 Blender 版本中失效。
- 内容审查：场景含 `EyeL`、`EyeR` 两个独立球形眼睛网格，以及一个 `Armature`；同时含有用于演示的 `Suzane` 角色和 `BoneShape`，不是可直接放入演员的干净眼睛包。
- 已生成源文件审查结果：`prototype/test_output/blendswap_procedural_anime_eye_shader/source_audit/candidate_audit.json` 与四向 Workbench 图；原始 Cycles 渲染：`prototype/test_output/blendswap_procedural_anime_eye_shader/source_render/frame_0001.png`。
- 初步结论：该资源比平面眼睛更值得继续测试，具备真实曲面和可独立眼睛对象；但目前只能列为“待拆分/待挂接”，不能直接宣布为演员五官基准。下一步应从 `EyeL`/`EyeR` 和对应材质中拆出可复用副本，再挂接到原演员头部，重点验证侧视轮廓、眼球朝向、缩放和像素化后的清晰度。
- 已新增测试工具：`tools/blender/render_procedural_anime_eye_on_accurig.py`。工具支持 `--scale`、`--eye-spacing`、`--eye-z-ratio`、`--face-front-bias` 和头骨父级开关，默认将眼睛挂到 `CC_Base_Head`，便于后续动画验证。
- 已完成两组四视图挂接测试：
  - `prototype/test_output/blendswap_procedural_anime_eye_shader/on_accurig_v1/`：`scale=1.0`、`eye-spacing=0.34`；眼睛的虹彩/瞳孔偏小，白色眼白与演员白色材质融合。
  - `prototype/test_output/blendswap_procedural_anime_eye_shader/on_accurig_v2_scale14/`：`scale=1.4`、`eye-spacing=0.44`；正面可读性改善，但侧面仍有明显前凸，需要继续调整眼球前后位置和轮廓遮挡。
- 当前判断：进入“可继续修正”的候选，不进入正式基准。它已经通过“可打开、材质可渲染、独立球形网格、可挂骨骼”四项基础门槛；尚未通过“演员正面画风、侧面不突兀、白眼轮廓清晰”三项视觉门槛。
- 深度校准结论：演员头部前表面约为 `Y=-0.72`；v1/v2 使用负向偏移，导致眼球中心在头部外侧。将 `face-front-bias` 改为正向内嵌偏移 `0.22` 后，v3 侧面只露出眼睛前端和虹彩，眼球主体已进入头部内部。该调整由工具参数完成，不需要重新制作人工标注。
- v3 结果：`prototype/test_output/blendswap_procedural_anime_eye_shader/on_accurig_v3_inset/`；参数为 `scale=1.4`、`eye-spacing=0.44`、`face-front-bias=0.22`。工具默认值已同步更新。
- 由于 v3 仍出现左右/上下位置和虹彩朝向偏差，已新增人工校准工具：`tools/chibi_eye_calibration_annotator.html`。用户只需标注正面左/右眼中心，以及侧面眼球中心和虹彩朝向点；不需要重新标注头部、四肢或骨骼。
- 已读取用户标注：`E:\comic\chibi_eye_calibration.json`，并复制到 `prototype/assets/characters/generated/chibi_eye_calibration.json`。v1 校准测试输出位于 `prototype/test_output/blendswap_procedural_anime_eye_shader/on_accurig_calibrated_v1/`；眼睛的高度和左右位置已改善，但部分眼白被头部遮挡，说明还需要头部前表面深度辅助点。
- 校准工具现已升级为 v2：侧面新增“头部前表面点”，用于估算眼球嵌入深度；脚本已支持 `assetslab_chibi_eye_calibration_v2`，等待用户补标后再生成下一版。
- 已读取并测试用户第二版标注 `E:\comic\chibi_eye_calibration (1).json`，项目副本为 `prototype/assets/characters/generated/chibi_eye_calibration.json`。结果输出：`prototype/test_output/blendswap_procedural_anime_eye_shader/on_accurig_calibrated_v2_lit/`。
- v2 结果判断：正面两只虹彩已经同时出现，左右和高度基本按照人工标注；侧面眼球主体大部分进入头部，虹彩朝向正确。当前剩余问题是眼白可见面积偏小、眼球仍需少量向头部前表面调整；这属于参数微调，不代表本次标注失败。
- 纠错记录：`on_accurig_calibrated_v2_lit/` 曾因错误地把侧视屏幕右侧映射为模型 `+Y`，导致眼球被放到后脑勺，判定为无效结果。已恢复项目约定的角色正面 `-Y`，并保留源眼睛的原始朝向。
- 当前有效结果：`prototype/test_output/blendswap_procedural_anime_eye_shader/on_accurig_calibrated_v4_front/`。正面可见双眼虹彩，背面不再出现眼睛，侧面眼球位于脸部前侧且主体嵌入头部。后续视觉微调应基于 v4，不再参考 v2_lit。
- 已生成可供用户手动调整的 Blender 场景：`prototype/assets/characters/generated/procedural_anime_eye_manual_adjustment_v1.blend`。该场景包含演员、`ProceduralAnimeEye_EyeL`、`ProceduralAnimeEye_EyeR` 和正面相机；眼睛暂不绑定头骨，调整完成后可再由脚本转换为正式挂接结果。
- 用户反馈原手动场景无法打开；后台验证原文件可读，但为降低 GUI 显卡/程序化材质触发崩溃的风险，已另生成安全编辑版：`prototype/assets/characters/generated/procedural_anime_eye_manual_adjustment_safe_v1.blend`。该版本将眼球临时替换为简单蓝/粉材质，仅用于手动位置调整，不代表最终渲染材质；Blender 4.5 后台打开验证通过。
- 为支持“边移动边看最终虹彩/瞳孔”，已使用 `--factory-startup` 生成真实材质编辑版：`prototype/assets/characters/generated/procedural_anime_eye_manual_adjustment_final_v1.blend`。该版本保留程序化眼睛材质、暂不绑定头骨，并通过 Blender 4.5 后台打开验证；调整后可用 `F12` 查看真实渲染效果。
- 已增加稳定的后台预览工具：`tools/render_manual_eye_preview.ps1`。它会读取保存后的 `.blend`，生成 `prototype/test_output/manual_eye_preview/frame_0001.png`，用于界面渲染失败时查看最终眼睛效果。
- 根据用户对正面瞳孔位置的描述，工具新增左右眼独立水平转向参数 `--left-yaw-deg` / `--right-yaw-deg`。测试组 `on_accurig_yaw_test_v1` 使用左眼 `-18°`、右眼 `+4°`，对应“左眼向画面左侧明显转、右眼向画面右侧轻微转”。
- 工具进一步新增共同俯仰参数 `--pitch-deg`。测试组 `on_accurig_look_left_up_v1` 使用左右眼水平 `-12°`、共同向上 `-10°`，对应“两只眼睛同时向画面左上方转，幅度接近”。

## 2026-08-02 网页交互校准器

由于用户多次遇到 Blender 图形界面打开闪退，新增不依赖 Blender GUI 的网页校准路径：

- 页面：`prototype/preview/chibi_eye_calibrator.html`。
- 浏览器模型：`prototype/preview/assets/chibi_eye_web_calibrator.glb`，由演员 FBX、Procedural Anime Eye Shader 的 `EyeL`/`EyeR` 和当前 v2 人工标注生成。
- 导出脚本：`tools/blender/export_web_eye_calibrator_asset.py`。
- 启动脚本：`tools/serve_chibi_eye_calibrator.ps1`，默认地址为 `http://127.0.0.1:8766/chibi_eye_calibrator.html`。
- 页面支持正面、右侧、背面、上方视角；支持移动/旋转工具；支持直接输入眼球位置和 XYZ 旋转；支持恢复初始值。
- 页面中的青色/粉色瞳孔是方向辅助标记，用于判断眼球是否朝向正确；最终外观仍以 Blender 程序化材质渲染为准。
- 点击“更新 JSON”后可复制文本，或下载 `chibi_eye_web_calibration.json` 发回项目。网页坐标采用 glTF/Three.js 坐标系，后续脚本会转换回 Blender 坐标，不应直接手抄到 Blender。
- 2026-08-02 验证：GLB 导出成功、页面模型加载成功、模型对象 `EyeL`/`EyeR` 可识别、初始 JSON 可生成。首次页面验证发现 Blender→glTF 的上下/前后轴转换，已修正网页正面方向和瞳孔方向标记。
- 网页校准器修正：虹膜辅助标记改为使用眼球实际网格包围盒中心，而不是源对象原点，避免虹膜看起来脱离眼球；移动模式新增 `DragControls`，可直接用鼠标拖动彩色眼球，拖动结果会同步到位置输入框和 JSON。旋转模式仍使用旋转工具。

## 2026-08-02 Miku Chibi 眼睛候选挂接测试

- 用户提供候选压缩包：`E:\comic\miku-chibi.zip` 与 `E:\comic\nijisanjien-chibi-selen-pomu-and-rosemi.zip`。
- 已解压到项目外部候选目录：`prototype/assets/external/chibi_eye_model_candidates/`；Miku 候选包含 `miku (chibi).fbx` 与眼睛贴图，Nijisanji 候选包含 `SelenPomuRosemi(Rigged).fbx`。
- Miku FBX 审查确认有独立眼部对象：`eyeball_1_0_node` 使用 `eye_CHM_EYE_mat` 和眼睛贴图，`eye_007_22_0_node` 使用 `face_CHM_SKIN_mat`，可作为眼部外轮廓；不是平面贴图方案。
- 新增挂接工具：`tools/blender/render_miku_eye_on_accurig.py`。它只复制 Miku 的眼球/眼部网格到演员，不复制 Miku 的身体、头发或骨架；当前输出是静态四视图评估。
- 第一轮 `miku_on_accurig_v1` 发现深度不适配：Miku 眼球厚度小于 Procedural Eye，沿用旧中心深度会被演员头部遮住，正面只露出小三角形，判定为深度失败。
- 第二轮 `miku_on_accurig_v2_depthfix` 按 Miku 眼球最前表面重新计算嵌入深度，正面双眼贴图清晰、左右和高度符合标注；右侧眼睛有一定前凸，但仍可作为优先候选继续微调。
- 同时生成 `miku_on_accurig_v3_no_outline`：只保留带眼睛贴图的 `eyeball_1_0_node`，正面更干净，但动漫轮廓表现弱于 v2。当前建议先观察 v2，再决定是否去掉外轮廓。
- v2 Blender 场景：`prototype/assets/characters/generated/miku_chibi_eye_on_accurig_v2_depthfix.blend`；四视图：`prototype/test_output/external_chibi_eye_candidates/miku_on_accurig_v2_depthfix/`。
- 用户复核指出 v2 的眼部组件浮在头部正面。原因确认：Miku 的 `eye_007_22_0_node` 是独立皮肤面片，不是演员头部拓扑的一部分；直接复制会产生贴纸感。
- `miku_on_accurig_v4_outline_inset` 尝试把该皮肤面片整体向内嵌入，结果只剩零碎边角，不采用。
- `miku_on_accurig_v7_conformed_outline` 尝试用 Shrinkwrap 投射到演员头部，侧面更贴合，但外轮廓基本被演员头部遮掉；保留为技术实验。
- 当前推荐的整合候选为 `miku_on_accurig_v8_eyeball_large_conformed`：只保留带真实虹膜贴图的 Miku `eyeball_1_0_node`，按前表面重新嵌入并放大到 `1.2x`，避免皮肤面片漂浮。Blender 场景为 `prototype/assets/characters/generated/miku_chibi_eye_on_accurig_v8_eyeball_large_conformed.blend`；仍需用户确认正面风格和侧面突出程度后，再绑定头骨与测试行走动画。
- 用户反馈 v8 眼球略大，已回退到 `1.0x` 版本 `miku_on_accurig_v9_eyeball_1x`；该版本保留 Miku 眼球贴图、去掉不贴合的皮肤眼框，尺寸更接近用户认可的中间过程图。
- Miku 的 `eyebrow_008_56_0_node` 已验证可独立复制；新增 `--include-eyebrow` 参数并生成 `miku_on_accurig_v10_eyeball_eyebrow`。眉毛按独立深度定位，正面可见，侧面没有明显悬浮；Blender 场景为 `prototype/assets/characters/generated/miku_chibi_eye_on_accurig_v10_eyeball_eyebrow.blend`。
- 用户继续反馈眼球略大，已生成 `miku_on_accurig_v11_eyeball_09_eyebrow`，眼球与眉毛统一缩放为 `0.9x`；右侧视图已输出，当前等待最终尺寸确认。
- 用户反馈双眼距离过近，已新增独立 `--spacing-multiplier` 参数；`miku_on_accurig_v12_spacing112` 使用眼球 `0.9x`、眼距 `1.12x`、眉毛同步跟随。正面间距已拉开，侧面深度保持不变。
- 用户要求恢复 Shrinkwrap 尝试之前认可的状态，已生成 `miku_on_accurig_v13_restore_v5_state`：只保留 Miku `eyeball_1_0_node`，不含皮肤眼框和眉毛，眼球 `1.0x`，表面内嵌 `0.04`，眼距 `1.0x`。该版本不覆盖 v12。
- 在 v13 基础上继续测试眉毛：`miku_on_accurig_v15_restore_eyeball_eyebrow` 使用眼球 `1.0x`、眼距 `1.0x`、眼球表面内嵌 `0.04`，眉毛使用独立 `brow-inset=0`，正面可见且没有明显前凸。当前眉毛候选 Blender 场景为 `prototype/assets/characters/generated/miku_chibi_eye_on_accurig_v15_restore_eyeball_eyebrow.blend`。
- 用户反馈 v15 眉毛仍被头部上方曲面遮住一部分，已生成 `miku_on_accurig_v16_brow_front`；眼球保持 v5 状态，眉毛单独使用 `brow-inset=-0.04` 前移，正面眉毛轮廓完整，侧面仅有轻微边缘露出。

## Nijisanji 眼睛/睫毛解析结果

- 已审查 `SelenPomuRosemi(Rigged).fbx` 及其 `Selen_Diffuse.png`、`Pomu_Diffuse.png`、`Rosemi_Diffuse.png`。
- FBX 只有 `Selen`/`Pomu`/`Rosemi` 角色整体网格及对应 Outline 网格，没有独立眼睛、眼线或睫毛对象。
- 眼睛颜色、眼线、睫毛和脸部细节均烘焙在角色 Diffuse 贴图的 UV 区域中，无法无损拆成可直接挂接到演员的 3D 睫毛补件。
- 已生成源模型参考图：`prototype/test_output/external_chibi_eye_candidates/nijisanji_source/selen_front.png`。该资源可作为睫毛轮廓参考，不作为直接移植源。
- 下一步更合适的实现是：以 Miku 眼球为核心，单独制作可贴合演员头部的睫毛网格/曲线，并把睫毛作为 `EyeStyleBundle` 的可选层；这样后续可以做睫毛粗细、长度和外翘程度的随机预设。
- 复核修正：Miku 的 `ctr_mikp001_eye.png` 明确包含虹膜、瞳孔和黑色眼线，但没有清晰独立的睫毛图形；`eye_007_22_0_node` 的连通部分主要是皮肤/眼部轮廓面片，不能安全当作睫毛直接拆出。当前“睫毛”应按独立新补件制作，而不是继续强行提取原模型。

## 随机五官启动条件

- 随机五官不需要等待完整走路动画完成；只要演员头部、眼球、眉毛和耳朵的局部坐标/父级关系稳定，就可以开始建立随机生成器。
- 当前眼球基准已基本确定，眉毛已有可移植对象；耳朵仍需找到可拆分的独立网格或制作一套耳朵补件。当前 Miku FBX 没有独立耳朵对象，Nijisanji FBX 主要是整角色网格，因此不能直接当作耳朵补件。
- 正式随机生成建议顺序：先锁定眼球/眉毛/耳朵锚点 → 建立带随机种子的变体参数 → 输出正面/侧面检查 → 接入 3D 渲染与像素化 QC。鼻子和嘴巴暂不加入随机系统。

## 2026-08-02 睫毛候选资源复查

当前结论：Miku 和 Nijisanji 都没有可直接、干净拆出的独立 3D 睫毛，因此改为寻找独立网格或可参数化生成器。筛选标准是：能单独定位到演员头部、正侧面都能保持贴合、可导出或应用于 Blender 4.5、适合后续做随机参数。

### 候选 A：Easy Anime Eye（优先测试）

- 来源：[Easy Anime Eye](https://kingmusa.gumroad.com/l/jjbrz)。页面说明免费内容包含睫毛模型、眉毛模型、睫毛/眉毛材质和眼影，不需要外部贴图；完整眼睛模型属于付费内容。
- 优点：Blender 4.4/4.5 已测试，正好接近当前环境；睫毛和眉毛是模型层，不依赖 Miku/Nijisanji 的脸部贴图；最适合作为“现成动漫风格部件”测试。
- 风险：免费内容的具体对象命名、左右分离方式和网格厚度仍需下载后审查；不能直接假定它一定符合当前演员头型。
- 评估：优先级 A，先检查睫毛是否是独立对象，再做演员四视图挂接。

### 候选 B：Flat Eyelashes Geometry Nodes（优先测试）

- 来源：[Flat Eyelashes using Geometry Nodes](https://ffuthoni.gumroad.com/l/eylfgeonodes)。页面说明包含上睫毛、下睫毛、控制曲线、父级 Empty、示例材质和节点组，支持 Blender 3.2 以上。
- 优点：上/下睫毛本身就是独立层，控制曲线适合新手用移动控制点调整；平面化形状更容易匹配我们的 Q 版像素渲染，而不是生成真实毛发。
- 风险：它不是某个动漫角色的成品眼型，需要我们在演员头部上重新放置和弯曲；必须检查 Blender 4.5 下 Geometry Nodes 与 Curve Deform 是否仍正常。
- 评估：优先级 A-，最适合建立我们自己的可随机参数化睫毛基准。

### 候选 C：Eyelashes with the help of Geometry Nodes（备用）

- 来源：[Eyelashes with the help of Geometry Nodes](https://ffuthoni.gumroad.com/l/eyelashgeonodes)。页面说明包含上/下睫毛、控制曲线、父级 Empty、四种自定义 strands 示例、bevel 示例和材质节点组，支持 Blender 3.1 以上。
- 与候选 B 的区别：这一版更偏曲线/细条与可调 strands，形状变化空间更大；B 版更偏平面睫毛，可能更适合像素化。
- 评估：优先级 B，作为“稍微立体、外翘更明显”的第二种睫毛风格。

### 候选 D：Eyelashes & Eyebrows Generator（随机系统参考）

- 来源：[Eyelashes & Eyebrows Generator](https://deanzarkov.gumroad.com/l/awddvk)，以及其资源汇总页 [BlendAtlas 条目](https://blendatlas.com/products/eyelashes-eyebrows-generator-for-blender)。页面说明它使用 Geometry Nodes，根据简单网格线生成睫毛和眉毛，并提供风格控制；基础生成器免费，独立 UI 插件为付费内容。
- 优点：很适合研究“睫毛长度、粗细、弯曲、外翘程度”的参数化方式，后续可纳入随机种子系统。
- 风险：当前项目使用 Blender 4.5，而新的 Eye Features Set 已要求 Blender 5.0+，不能把该新版本直接作为当前管线依赖；本轮只考虑 Blender 4.5 可用的免费生成器/节点组。
- 评估：优先级 B，适合做随机生成技术参考，不作为第一份下载测试。

### 候选 E：BlendSwap Eyelashes（结构参考）

- 来源：[BlendSwap Eyelashes](https://blendswap.com/blend/5257)。页面标明这是独立的睫毛模型，CC0，但资源较旧，使用 Blender 2.6x 和 Blender Internal，且偏真实女性睫毛。
- 优点：可作为独立网格、曲线形态和父级关系的最简单参考。
- 风险：画风不接近我们的 Q 版演员；旧版文件在 Blender 4.5 中可能需要清理和重建材质。
- 评估：优先级 C，只在 A/B 不能正常下载或导入时使用。

### 本轮建议顺序

1. 先测试 Easy Anime Eye，确认是否有能直接复制的动漫睫毛对象。
2. 同时测试 Flat Eyelashes Geometry Nodes，作为我们自己的平面睫毛基准。
3. 对两个候选都输出正面、左右侧面和 256 像素化预览。
4. 只要其中一个满足“正面好看、侧面不漂浮、能单独移动”，就停止继续寻找资源，开始制作 `EyelashStyleBundle`。
5. 随机化先只开放四个参数：长度、粗细、外翘、上/下睫毛开关；不让随机过程改变眼球锚点。

本轮暂不下载或安装付费插件；先用免费/可领取候选确认结构是否适配。若 Easy Anime Eye 和 Flat Eyelashes 都不合适，再考虑自己制作一条低面数曲线作为正式基准。

### 本地资源审查补充

- `E:\Env\Assets\簡単アニメアイ_販売用ファイル_Gumroad_無料.blend` 已存在，并可由 Blender 4.5 后台正常打开。
- 该文件确实包含独立网格：`eyelashes.body`、`eyelashes.sharp`、`eyebrows`，以及独立的 `anime eye.L/R` 和 `eyeball.L/R`。`eyelashes.sharp` 还是 `eyelashes.body` 的子对象，说明它不是烘焙在脸部贴图里的假睫毛。
- 该文件同时包含左右睫毛材质及内/外睫毛材质，可以先只提取 `eyelashes.body`/`eyelashes.sharp`，避免把不兼容的完整眼球系统带入演员。
- 因此 Easy Anime Eye 已从“待下载候选”升级为“可立即挂接测试候选”；下一步应直接做演员四视图测试，而不是继续寻找同类资源。

### Easy Anime Eye 睫毛挂接实测

- 已扩展 `tools/blender/render_easy_anime_eye_on_accurig.py`，新增 `--lashes-only` 和 `--save-blend`，可以只测试独立睫毛而不带入候选眼球。
- 已新增 `tools/blender/attach_easy_anime_lashes_to_miku_scene.py`，将 `eyelashes.body`/`eyelashes.sharp` 挂接到已校准的 `MikuChibiEyeball` 位置，并让睫毛跟随演员 `CC_Base_Head`。
- 已新增 `tools/pixelize_four_view_preview.py`，把四视图缩到 64×64 最近邻像素预览，用于检查睫毛在最终资源尺寸下是否仍可见。
- 仅睫毛基准测试：`prototype/test_output/easy_anime_lashes_on_accurig_v1/`。结果显示睫毛被放在演员头部过高位置，不能作为有效对照。
- 结合 Miku 眼球的第一版：`prototype/test_output/easy_anime_lashes_on_miku_v1/`。正面睫毛覆盖在眼睛上沿，侧面前凸较明显，且颜色偏红。
- 当前推荐第二版：`prototype/test_output/easy_anime_lashes_on_miku_v2_inset_dark/`。参数为 `lash-scale=0.92`、`front-offset=-0.04`、`z-offset=0.015`；正面位置和颜色更合适，侧面只剩小幅前缘。
- 当前判断：Easy Anime Eye 睫毛可以作为独立结构候选，但原始形状在 64×64 像素化后过细；暂不作为最终随机睫毛库。后续需要在不改变眼球锚点的情况下增加睫毛厚度/高度，或改用 Flat Eyelashes Geometry Nodes 作为像素化基准。

### 睫毛贴合修正记录

- v2/v3 的问题不是单纯缩放：源睫毛与源 `anime eye.L/R` 眼框的相对高度没有被使用，直接对齐 Miku 眼球包围盒中心会造成睫毛上下错位。
- 已新增 `tools/blender/audit_eye_source_layout.py`，审查源眼框、眼球和睫毛的包围盒关系；已确认源睫毛最高点应作为上缘锚点，而不是使用整组中心。
- 已新增 `tools/blender/probe_actor_front_surface.py`，检查演员脸部在眼睛区域的实际前表面深度。
- 已将挂接工具升级为上缘/前缘双锚点，并新增逐顶点脸部投射 `--raycast-conform`；每个睫毛顶点沿正面射线贴到演员脸部表面外侧，避免整体浮在眼球前方。
- v5 已验证逐顶点投射能解决前后浮动，但直接使用 Miku 眼球包围盒顶部会把睫毛推到眉毛位置。
- v6/v7 增加 `--vertical-offset`，将实际可见睫毛带向下调整；当前对照版本为 `prototype/test_output/easy_anime_lashes_on_miku_v7_upper_rim/`，参数 `vertical-offset=-0.20`、`raycast-conform=true`。
- v7 当前判断：侧面已基本贴脸，正面已回到眼睛上缘附近；仍需进一步增加睫毛厚度或微调下移量，才能达到清晰的像素资源表现。

## 2026-08-02 概念图眉毛重建

- 用户确认 Easy Anime Eye 的睫毛/眉毛无法同时满足清晰度、位置和贴脸要求，改为依据 `front-character-anchor.png` 自行制作。
- 已新增 `tools/blender/create_concept_eyebrows_on_miku_scene.py`，生成左右独立的低面数 3D 曲线眉毛，并使用演员脸部前表面射线确定深度。
- 眉毛参数：默认宽度 `0.34`、左右中心间距 `0.62`、弧度高度 `0.04`、曲线厚度 `0.018`；对象为 `ConceptEyebrow.L` / `ConceptEyebrow.R`，父级为 `CC_Base_Head`。
- 当前测试结果：`prototype/test_output/concept_eyebrows_on_miku_v1/`，场景文件为 `concept_eyebrows_on_miku_scene.blend`，正面近景为 `front_face_closeup.png`。
- 初步判断：该自制眉毛比来源模型眉毛更适合作为我们的基础眉毛；形状、粗细、弧度和左右位置都可以直接参数化，后续可纳入 `EyebrowStyleBundle` 随机系统。
