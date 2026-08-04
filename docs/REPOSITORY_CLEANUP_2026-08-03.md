# 仓库资源精简记录

日期：2026-08-03
分支：`pixel_asset_test`

## 保留资源

- 3D 演员输入：`prototype/assets/characters/generated/chibi_base_mesh_accurig_input_v3/`
- 当前眼睛和眉毛资源：`prototype/assets/characters/generated/eye_package_imagegen_v4_brows_up.blend`
- 独立耳朵源资源：`prototype/assets/characters/generated/cartoon_ear_candidate_v3.blend`
- 耳朵标注数据：`prototype/assets/characters/generated/chibi_ear_anchor_calibration_v1.json`
- 耳朵下载源压缩包：`prototype/assets/external/chibi_ear_candidates/low_poly_cartoon_ear/source/low-poly-cartoon-ear.zip`
- 当前像素资源：`prototype/assets/characters/chibi/`、`prototype/assets/characters/base_features_v1/`
- 当前网页标注工具、必要脚本和项目文档

## 删除内容

删除 `prototype/assets/characters/generated/` 中除上述保留项以外的旧眼睛、Miku 眼窝、程序眼睛、身体重建、骨骼行走、失败耳朵接入和旧像素测试资源，共 436 个已跟踪文件，约 717 MB；同时删除未跟踪的失败 Blend 和 Godot `.import` 缓存。

耳朵源只保留压缩包，删除重复解压目录。删除操作仅针对项目工作树中的旧资源，未改写 Git 历史。

另外删除 `prototype/assets/characters/` 下旧的 female、male、faces、rebuild、runtime、turnaround 和旧 chibi 变体目录，仅保留 `chibi/`、`base_features_v1/` 与当前核心资源目录 `generated/`。
