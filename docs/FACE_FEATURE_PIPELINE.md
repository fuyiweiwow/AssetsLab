# 五官、眉毛、耳朵与随机化管线

## 当前基线

- 真实素体演员：`prototype/assets/characters/generated/chibi_eyes_ears_pixel_walk_source_v1.blend`
- 眼睛/眉毛/耳朵像素层：`prototype/assets/characters/base_features_v1/`
- 眼睛/耳朵随机化渲染入口：`tools/run_chibi_face_randomization_preview.ps1`
- 随机化验证：`tools/validate_chibi_face_randomization.py`
- 固定资源验证：`tools/validate_base_features.py`

五官必须挂到真实演员的 `CC_Base_Head`，并通过正面、右侧、背面、左侧四方向检查。鼻子和嘴巴不属于当前资源合同。耳朵作为独立层保留，随机化时必须维持已验证的耳朵锚点和方向策略。

## 可复现随机化

随机化通过 `appearance_seed` 选择样式，同一个 seed 必须得到同一组眼睛/眉毛/耳朵结果。生成 preview：

```powershell
.\tools\run_chibi_face_randomization_preview.ps1
```

验证固定层：

```powershell
python .\tools\validate_base_features.py
```

验证随机化 review 输出：

```powershell
python .\tools\validate_chibi_face_randomization.py `
  --root .\test_output\face_randomization_v2
```

## 验收规则

1. 五官和眉毛不脱离头部，也不因像素化出现黑色贴纸框；
2. 侧面轮廓按发型规范执行 128px 诊断和最小像素补偿；
3. 耳朵方向、左右关系和头部锚点保持稳定；
4. 64×64 输出全部有可见像素，四方向和帧数完整；
5. 生成结果属于 review 输出，未通过人工视觉确认前不覆盖正式运行时包。
