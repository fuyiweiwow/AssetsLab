# AssetsLab 当前预览工具

这里只保留当前眼睛校准、耳朵锚点校准和统一静态预览入口。旧的身体重建、骨骼分阶段和 Miku/Koban 页面已移除。

从仓库根目录启动静态预览服务器：

```powershell
.\tools\serve_preview.ps1 -Port 8000
```

手机查看时使用脚本输出的 Tailscale 地址。发型统一入口由以下命令生成：

```powershell
python .\tools\build_hair_gallery_index.py `
  --root .\prototype\test_output\hair_candidates_2026_08_04 `
  --catalog .\prototype\assets\hair\hair_gallery_catalog_v1.json
```

当前工具：

- `chibi_eye_calibrator.html`：眼睛与眉毛头部锚点；
- `ear_anchor_annotator.html`：耳朵连接点；
- `calibrate.html`：通用静态预览入口；
- `assets/chibi_eye_web_calibrator.glb`：校准器模型资源。
