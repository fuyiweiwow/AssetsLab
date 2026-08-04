# AssetsLab Prototype

当前项目只保留一条可重建的最小流程：

```text
素体演员 + 骨骼标定
  -> 眼睛/眉毛/耳朵挂载与随机化
  -> 发型候选组装与 Gallery 审查
  -> 四方向渲染
  -> 最近邻像素化
  -> Godot 无 GUI 运行时验证
```

详细保留清单、命令和清理规则见：

```text
docs/ACTIVE_ASSET_WORKFLOW.md
```

## 当前核心路径

- 演员：`assets/characters/generated/chibi_eyes_ears_pixel_walk_source_v1.blend`
- 骨骼标定：`assets/characters/generated/chibi_base_mesh_accurig_input_v3/`、`chibi_base_mesh_accurig_calibrated_v1.fbx`
- 眼睛/眉毛/耳朵：`assets/characters/base_features_v1/`
- 当前像素运行时：`assets/characters/runtime/chibi_eyes_ears_walk_v1/`
- 发型：`assets/hair/`

## 无 GUI 验证

使用项目上级目录的 Blender console 可执行文件：

```powershell
& ..\blender-4.5.10-windows-x64\blender.exe -b --python tools\blender\fit_blend_hair_candidate.py -- --help
```

生成人脸/耳朵随机化预览：

```powershell
.\tools\run_chibi_face_randomization_preview.ps1
```

运行像素运行时端到端检查：

```powershell
.\tools\run_pixel_asset_end_to_end.ps1
```

所有 Blender 和 Godot 验证均使用后台/console 模式，不打开 GUI。视觉检查通过预览服务器的 Tailscale 地址完成。

## 发型 Gallery

发型规范见 `docs/HAIR_GALLERY_STANDARD_2026-08-04.md`。统一入口由以下命令生成：

```powershell
python .\tools\build_hair_gallery_index.py `
  --root .\test_output\hair_candidates_2026_08_04 `
  --catalog .\assets\hair\hair_gallery_catalog_v1.json
```

推荐池和实验池必须分开；未通过四视图、接缝、耳朵遮挡和侧视像素补偿检查的候选只能进入实验池。

随机化评审工作台由 `tools\build_hair_workbench.py` 生成，支持整体发型随机化、组件装配随机化和本机评审列表。它通过统一 Gallery 入口的“发型随机化与组件装配工作台”链接打开。
