# AssetsLab 当前保留流程

本文档是当前项目的唯一简化开发入口。旧的 Miku、Koban、失败骨骼动作、旧身体重建和历史贴图实验不属于当前流程。

## 当前核心资产

- 素体演员与骨骼：`prototype/assets/characters/generated/chibi_eyes_ears_pixel_walk_source_v1.blend`
- AccuRIG 标定交换文件：`prototype/assets/characters/generated/chibi_base_mesh_accurig_input_v3/`、`chibi_base_mesh_accurig_calibrated_v1.fbx`
- 眼睛/眉毛/耳朵随机化运行时层：`prototype/assets/characters/base_features_v1/`
- 当前耳朵候选与锚点：`cartoon_ear_candidate_v3.blend`、`chibi_ear_anchor_calibration_v1.json`
- 当前像素运行时包：`prototype/assets/characters/runtime/chibi_eyes_ears_walk_v1/`
- 当前发型源：`prototype/assets/hair/Blender-Chloe_Hair.blend`、`prototype/assets/hair/male_source/Blend_Hair.blend`
- 发型组件分类和兼容规则：`prototype/assets/hair/hair_component_catalog_v1.json`、`docs/HAIR_COMPONENT_RANDOMIZATION_2026-08-04.md`
- 发型设计/随机池/评审页面设计：`docs/HAIR_DESIGN_RANDOM_POOL_REVIEW_2026-08-04.md`

`female_more` 与 Chloe 源几何重复，不作为独立资源保留。男性源中的全部刘海和女性 Chloe 的全部后发先进入审查 gallery，只有通过四视图和像素验收的候选才能进入推荐池。

## 最简验证流程

1. 用 Blender 后台把演员、眼睛、眉毛和耳朵挂载到 `CC_Base_Head`，不打开 Blender GUI。
2. 用 `tools/run_chibi_face_randomization_preview.ps1` 生成固定种子的人脸/耳朵随机化预览。
3. 用 `tools/validate_chibi_face_randomization.py` 检查 4 方向、像素尺寸、种子稳定性和耳朵锚点策略。
4. 用 `tools/blender/fit_blend_hair_candidate.py` 生成发型四视图。
5. 用 `tools/build_hair_randomization_gallery.py` 生成候选页，再用 `tools/build_hair_gallery_index.py` 生成统一入口；入口使用男女 Tab 筛选，避免为性别增加独立页面 UI。
6. 用 `tools/process_accurig_walk_pixels.py` 和 `tools/validate_pixel_runtime_package.py` 完成 3D 到像素运行时包的转换与检查。
7. 用 `tools/run_pixel_asset_end_to_end.ps1` 运行 Godot 的无 GUI 端到端验证。

## 当前 Gallery

统一入口：

```text
prototype/test_output/hair_candidates_2026_08_04/index.html
```

服务手机查看时必须使用 Tailscale 地址，不使用 Blender/Godot GUI 或本地临时附件。

## 清理规则

- `prototype/test_output/` 只保留当前需要人工查看的输出，历史输出可以删除并从源文件重建。
- 旧实验素材和文档不作为当前开发依赖；删除前先用 `rg` 检查引用。
- 不删除核心演员 Blend、骨骼标定文件、当前眼睛/眉毛/耳朵随机化资源、当前发型源和像素化工具。
- 任何未通过四视图、侧视像素补偿或接缝检查的发型只能放在实验池。
