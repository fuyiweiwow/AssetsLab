# AssetsLab Project

当前项目保留一条最小可重建流程：

```text
素体演员/骨骼标定
  -> 眼睛、眉毛、耳朵挂载与随机化
  -> 当前发型候选与 Gallery
  -> 四方向渲染和最近邻像素化
  -> Godot 无 GUI 运行时验证
```

所有项目文件必须位于当前仓库目录内；Blender 和 Godot 验证使用后台/console 模式，不打开 GUI。手机查看视觉结果时使用预览服务器提供的完整 Tailscale URL。

当前开发入口：

- [当前保留流程](docs/ACTIVE_ASSET_WORKFLOW.md)
- [五官与随机化管线](docs/FACE_FEATURE_PIPELINE.md)
- [发型 Gallery 规范](docs/HAIR_GALLERY_STANDARD_2026-08-04.md)
- [环境复现说明](docs/DEVELOPMENT_ENVIRONMENT_REPRODUCTION_2026-08-03.md)

主运行时和像素资源位于 `prototype/`；生成的测试输出位于
`prototype/test_output/`，原则上不提交 Git。源 Blend、骨骼标定文件、贴图源、
随机化配置和生成工具必须提交。
