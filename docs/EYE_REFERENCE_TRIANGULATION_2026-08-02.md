# 三套眼睛参考的职责划分

日期：2026-08-02

## 参考来源

### 1. 概念图

文件：`front-character-anchor.png`

用途：决定最终画风、眼睛外轮廓、上下比例、内外眼角和角色整体表情。

### 2. Procedural Anime Eye

文件：`prototype/assets/external/anime_eye_candidates/blendswap_procedural_anime_eye_shader/Procedural Anime Eye Shader.blend`

示例渲染：`prototype/test_output/blendswap_procedural_anime_eye_shader/source_render/frame_0001.png`

用途：决定虹膜、瞳孔和高光的构成。

关键特征：

- 白色眼白面积明确；
- 虹膜较大，接近眼睛上下边缘；
- 虹膜为纵向椭圆；
- 瞳孔为独立的纵向黑色椭圆；
- 高光形状清晰，适合像素化后保留识别度。

### 3. Miku chibi 模型

输入：Miku FBX 的 `eyeball_1_0_node`、眼睛贴图和材质。

用途：决定眼睛的低深度、上眼睑遮挡、侧面薄轮廓和二次元凹入观感。

## 不再混淆的实现规则

不直接复制三套眼睛的全部内容：

- 不把 Procedural Eye 的完整球体直接放到演员头上；
- 不把 Miku 的虹膜贴图强行拉伸成最终虹膜；
- 不把概念图抠图直接作为最终 3D 贴纸。

最终 EyePackage 应采用：

`概念图外轮廓` + `Procedural Eye 虹膜/瞳孔/高光比例` + `Miku 低深度眼部遮挡结构`

所有层仍需贴合演员头部并绑定 `CC_Base_Head`，最后通过正面、3/4、侧面和像素化检查。

## 当前状态

- v10：概念图眼框 + Miku 虹膜贴图 + 独立纵向瞳孔，作为历史对照。
- v11：虹膜被拉得过高，证明单纯拉伸 Miku 虹膜不是最终方案。
- v12：回到 Miku 低深度分层方案；使用概念图眼框、Miku 虹膜/高光和独立纵向瞳孔，不使用 Procedural Eye 球体。

v12 场景：`prototype/assets/characters/generated/eye_package_v12_miku_structure.blend`

v12 参数：

- `iris_width_scale = 0.96`
- `iris_height_scale = 1.25`
- `pupil_height_scale = 1.45`
- 内外上眼角保持 v10 的短圆角睫毛框。

验证：正面、3/4、侧面、64 像素预览和 18° 头部转动均已完成。当前 v12 是 Miku 结构路线的候选基准；Procedural Eye 仅保留为虹膜比例参考，不再进入演员眼睛主结构。

## ImageGen 概念眼睛测试

用户反馈 v12 仍缺少直接可读的动漫眼睛结构，因此使用 ImageGen 生成了新的概念眼睛纹理，并以 `front-character-anchor.png` 作为主要画风参考、以此前 Procedural/Miku 眼部作为虹膜和高光参考。

生成结果处理：

1. 使用纯绿幕生成左右眼图集；
2. 使用本地绿幕去除工具生成 RGBA；
3. 按左右两半裁剪成独立纹理；
4. 删除与主体不连通的小伪影组件；
5. 作为完整透明 2.5D 眼部层挂接演员头部。

资产：

- `prototype/assets/generated/eye_package_v3/imagegen_anime_eye_sheet_v2.png`
- `prototype/assets/generated/eye_package_v3/imagegen_eye_v2_crops/imagegen_eye_L.png`
- `prototype/assets/generated/eye_package_v3/imagegen_eye_v2_crops/imagegen_eye_R.png`

测试场景：`prototype/assets/characters/generated/eye_package_imagegen_v2_clean.blend`

测试结果：

- 正面、3/4 和侧面可见完整白眼、粉色大虹膜、纵向瞳孔和高光；
- 64 像素预览仍能识别主要结构；
- 18° 头部转动通过；
- 眼部没有恢复为球形外凸。

当前判断：ImageGen 眼部比 v12 更接近“直接可读的动漫眼睛”，暂作为新的视觉候选，不立即替换 Miku 结构基准。
