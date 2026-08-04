# Miku 风格动漫眼睛结构研究与 v4 验证

日期：2026-08-02

## 结论先行

Miku 眼睛不应被当作“普通球形眼球复制到演员头部”。更合理的复刻目标是：

1. 眼部是贴合脸部的低深度曲面，而不是向外突出的球体。
2. 可见眼白、虹膜、瞳孔、上眼睑/眼眶遮挡分别作为层处理。
3. 上眼睑使用较平的圆角矩形或短弧带，外眼角只保留小圆角，不使用大半圆弧。
4. 瞳孔使用纵向拉长的圆角矩形/椭圆形，并允许以后做宽度、长度、偏移的随机化。
5. 睫毛不优先建成实体毛束；第一版应作为上眼睑纹理或透明遮罩层，避免侧面悬浮。

## Miku FBX 几何审查

审查工具：`tools/blender/audit_miku_eye_geometry.py`

输入：Miku chibi FBX 的原始解压文件。

输出：`prototype/test_output/miku_eye_geometry_audit/audit.json`

关键观察：

- `eyeball_1_0_node` 只有 130 个顶点、224 个面，并不是高模球体。
- 该对象包含两个互不连接的 65 顶点组件，分别对应左右眼区域。
- 该对象有独立的眼睛材质和眼睛贴图，并且左右眼占据贴图中不同的 UV 区域。
- 正面隔离渲染显示：上部是宽而深的遮挡/眼睑区域，下部才是较窄的椭圆可见区域。
- 侧面隔离渲染显示：眼部整体是薄板状轮廓，没有普通球形眼球应有的明显厚度。
- `eye_007_22_0_node` 使用脸部皮肤材质，包含脸部壳体与两组眼部边界组件，不能直接拓扑转移到我们的演员头上。

因此可以确认：Miku 的“凹进去/二次元”效果主要来自低深度眼部形状、上部遮挡和贴图层组合。FBX 中没有足够证据证明它使用了一个普通球体再通过某个单独的神奇变换实现该效果；具体 shader 内部参数若未随 FBX 导出，只能通过渲染结果推断。

## 网上资料对工作流的支持

- SIGGRAPH 的日本动画眼睛系统明确采用任意手工眼形，而不是强制使用真实球形眼球；虹膜/瞳孔通过纹理与 UV 变形支持椭圆、细缝等形状，并把角膜凸起和眼睑/睫毛阴影作为风格化表现处理：
  [Flexible Eye Design for Japanese Animation](https://history.siggraph.org/wp-content/uploads/2022/08/2020-Talks-Derouet-Jourdan_Flexible-Eye-Design-for-Japanese-Animation.pdf)
- 动漫眼睛的绘制工作流通常拆分为眼白、睫毛/上眼睑阴影、虹膜、轮廓、瞳孔和高光层，适合转化为我们的 `EyeStyleBundle`：
  [Clip Studio Paint：anime eye layers](https://tips.clip-studio.com/en-us/articles/2674)
- 侧面眼形通常需要压缩，眼睛外轮廓可以采用圆形、杏仁形或更有角度的自定义形状；瞳孔也不必保持圆形：
  [XPPen：How to Draw Anime Eyes](https://www.xp-pen.com/blog/how-to-draw-anime-eyes.html)

这些资料支持我们采用“低深度眼部曲面 + 贴图分层 + 可参数化瞳孔”，而不是继续把球形眼球往脸里硬塞。

## v4 实现

场景：`prototype/assets/characters/generated/eye_package_v4_miku_style.blend`

构建入口：`tools/run_eye_package_v3.ps1`

本次变化：

- 保持原有标注中心，不整体把眼睛向外或向远处移动。
- 使用 `concept_eye_frame_v2_L/R.png` 作为上眼睑/眼眶层，轮廓改为较平的圆角矩形倾向。
- 使用 Miku 眼睛贴图提取出的虹膜基底，但把瞳孔单独拆成纵向拉长的透明层。
- 所有层继续通过 Shrinkwrap 贴合演员头部，并绑定 `CC_Base_Head`。
- 生成正面、3/4、侧面和头部转动验证图。

预览：

- `prototype/test_output/eye_package_v4_miku_style/front_face_closeup.png`
- `prototype/test_output/eye_package_v4_miku_style/threequarter_face_closeup.png`
- `prototype/test_output/eye_package_v4_miku_style/right_face_closeup.png`
- `prototype/test_output/eye_package_v4_miku_style_head_turn/frame_12.png`
- `prototype/test_output/eye_package_v4_miku_style_pixel64/front_face_closeup_nearest_view.png`

## v4 判定

通过：

- 正面已出现平直上部、纵向瞳孔和独立眼部层。
- 3/4 与侧面没有恢复成完整球体，也没有明显脱离头部的悬浮轮廓。
- 头部转动测试完成，眼部层跟随 `CC_Base_Head`。
- 64 像素最近邻预览中，眼框与虹膜仍然可辨识。

仍需调整：

- 白色眼白层仍有少量圆球观感；下一轮应压低眼白高度并加强上部遮挡，而不是再移动眼睛中心。
- 上眼睑外角还可以进一步变短、变平，向概念图的圆角矩形靠拢。
- 当前瞳孔参数已分离，但还没有接入随机 `EyeStyleBundle` 生成器。

## 下一步

1. 以 v4 为基准做 v5：压扁眼白，减小外眼角弧度，保持眼睛中心不变。
2. 增加左右眼独立的瞳孔长度、宽度、上下偏移参数。
3. 把上眼睑/睫毛保留为透明纹理层，暂不生成实体睫毛。
4. v6 通过正面、3/4、侧面和像素检查后，再接入随机五官组合。

## v5 对照结果

场景：`prototype/assets/characters/generated/eye_package_v5_flat_miku_style.blend`

本次只改变形状参数，不改变眼睛中心：

- 眼白高度从 `0.80` 降到 `0.68`。
- 虹膜纵向比例降到 `0.92`。
- 瞳孔纵向比例提高到 `1.35`。
- 曲面弯曲从 `0.012` 降到 `0.006`。

结果：

- 正面更接近“上眼睑遮挡 + 薄眼部层”的方向。
- 纵向瞳孔在像素预览中仍然可识别。
- 18° 头部转动测试通过，未出现层脱离或重新变成球形眼球。
- v5 仍不是最终画风定稿；目前最明显的残留问题是上眼框两侧仍有较长的弧线。下一次只收紧两侧圆角，不再继续移动眼睛位置。

## v6 内外上眼角修正

场景：`prototype/assets/characters/generated/eye_package_v6_short_corner.blend`

本次只修改 `tools/prepare_concept_eye_frames_v2.py` 的上眼框轮廓：

- 内上眼角和外上眼角都改为短圆角。
- 顶部和两侧增加更长的直线段。
- 保持眼睛中心、左右间距、眼白高度、虹膜和瞳孔参数不变。

验证结果：

- 正面轮廓已经从大弧线变为更接近圆角矩形。
- 3/4 视图仍贴合头部，没有眼框漂浮。
- 64 像素最近邻预览中，眼框结构清楚。
- 18° 头部转动测试通过。

v6 仍保留轻微的下眼睑辅助线；如果概念图最终不需要下眼线，可以在下一步作为独立开关移除。

## v7-v10 内眼角与动漫睫毛修正

参考原则：内眼角保持简洁，外眼角睫毛更长、更粗，并使用少量清晰的尖束，而不是均匀细线。这个方向与资料中“上眼睑更厚、外侧睫毛更长、内侧线条更短”的动漫眼睛构成一致：

- [Emily Drawing：anime eye lashes](https://www.emilydrawing.com/how-to-draw/how-to-draw-anime-eyes/)
- [Corel Painter：anime eye upper eyelid and eyelashes](https://www.painterartist.com/en/tips/draw-anime/eyes/)

本次最终测试场景：`prototype/assets/characters/generated/eye_package_v10_anime_lashes.blend`

变化：

- 内上眼角只保留圆角，终点不再向下延伸成长竖线。
- 外侧增加三束长度递增的三角形睫毛，最长束位于外侧偏下位置。
- 睫毛继续作为透明纹理层，不创建实体几何，因此不会在侧面悬浮。
- 眼白、虹膜、纵向瞳孔和眼框参数保持 v6 的形状基准。

验证：

- 正面和 64 像素预览完成。
- 3/4、侧面和 18° 头部转动完成。
- 睫毛在高分辨率中可辨识，像素化后仍保留外侧变化，但当前尺寸下会与粗上眼框部分融合。

下一步可将睫毛做成 `subtle / standard / dramatic` 三个透明纹理变体，再交给随机五官系统选择；不建议继续增加实体睫毛几何。
