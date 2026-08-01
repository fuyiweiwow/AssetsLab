# 项目进度与清理记录（2026-08-02）

## 当前结论

3D 演员到 2D 像素资源的最小闭环已经跑通：

`3D 演员 → 四方向渲染 → 最近邻像素化 → 运行时资源包 → Godot 加载与移动测试`

当前结果是“技术闭环通过”，还不是最终美术质量通过。腿部权重、腿根开裂感、脸部和耳朵的最终风格仍需要下一阶段继续处理。

## 当前基线

- 工作分支：`pixel_asset_test`
- 当前演员测试包：`prototype/assets/characters/runtime/chibi_accurig_walk_test_v1/`
- 运行时端到端测试：`tools/run_pixel_asset_end_to_end.ps1`
- 3D 脸部特征诊断：`tools/run_accurig_3d_face_test.ps1`
- 外部风格资源审计记录：`docs/EXTERNAL_ANIME_ASSET_EVALUATION.md`
- 原始演员文件仍保留在项目外部：`E:/comic/chibi_base_mesh_accurig_rigged_v1.fbx`

## 本次清理

已确认不再作为当前管线输入的 KIIRA 候选路线被移除：

- `third_party/kiira_chibi/`
- `tools/blender/render_kiira_walk_front_test.py`
- `tools/process_kiira_front_test_pixels.py`
- `tools/make_kiira_front_test_gif.ps1`
- 根目录误生成的 `render.png`

删除理由：KIIRA 方案已被当前外观验收标准淘汰，且没有被新的运行时端到端测试读取。其历史评估结论保留在 Git 历史和候选评估文档中，不再让仓库继续携带这套容易误用的外观来源。

以下资源本次没有删除，因为当前默认回归测试或预览仍会读取它们：

- `prototype/assets/characters/chibi/`
- `prototype/assets/characters/chibi_compact/`
- `prototype/assets/characters/faces/`
- `prototype/assets/characters/base_features_v1/`
- `prototype/assets/characters/runtime/chibi_accurig_walk_test_v1/`
- `prototype/assets/characters/rebuild_*` 和 `generated/skeleton_walk_pipeline_v1/`

其中 `rebuild_*`、`skeleton_walk_pipeline_v1`、RGS 参考帧等只属于历史/兼容测试资源，不代表最终角色外观。等新的 3D 演员特征管线接替默认预览后，再单独删除这一批，并同步移除对应兼容开关和测试。

本地下载的 Koban 资源继续保留在被 Git 忽略的目录中：

`prototype/assets/external/koban_chibi_base_mesh/`

仓库只保留审计记录，不提交原始压缩包或外部模型文件。

## 验证标准

清理后必须通过：

```text
git diff --check
PIXEL_ASSET_END_TO_END_PASS package=1 godot=1 integration=1 appearance=1
```

本次清理后已实际通过上述端到端测试：四方向、32 帧资源包校验通过，Godot 资源导入、运行时切向、移动捕获和随机五官三种模式均通过。

## 明日继续位置

下一步不再回头修补已淘汰的 KIIRA 或临时 2D 拼接方案，直接在真实 3D 演员上做：

1. 依据目标画风重新设计眼睛、耳朵和未来装饰的 3D/2.5D 特征；
2. 将特征挂到演员的 `CC_Base_Head`，做正面、侧面、背面静态验收；
3. 通过后接入四方向 × 8 帧渲染和像素化管线；
4. 最后再扩展随机五官参数和跑步速度参数。
