# AssetsLab 发型 Gallery 规范

## 目的

发型评审统一使用静态 HTML gallery。页面必须能在手机浏览器中通过 Tailscale 打开，不能依赖 Blender GUI 或 Godot GUI。

统一入口生成于：

```text
prototype/test_output/hair_candidates_YYYY_MM_DD/index.html
```

当前入口：

```text
http://desktop-dk81254.tailf01571.ts.net:8000/hair_candidates_2026_08_04/index.html
```

## 目录约定

每个子 gallery 使用独立目录，并包含：

```text
<gallery-id>/
  gallery.html
  <seed-id>/
    front.png
    right.png
    back.png
    left.png
    manifest.json
    pixel/
      front_pixel.png
      right_pixel.png
      four_view_pixel_sheet.png
```

推荐候选和实验候选必须分开登记。存在露白、后脑缺失、严重穿插或方向错误的候选只能进入 experimental gallery，不能进入推荐池。

## 当前工具

- `tools/blender/fit_blend_hair_candidate.py`：后台追加、组装、贴合和四视图渲染；支持 Chloe 源网格归一化，也支持 male 的 `base/bangs/side/back` 展示网格重新组装。
- `tools/build_hair_randomization_gallery.py`：生成单个发型 gallery，支持 `--candidate` 精选候选和 `--output` 输出多个子页面。
- `tools/build_hair_gallery_index.py`：根据 catalog 生成统一入口。
- `prototype/assets/hair/hair_gallery_catalog_v1.json`：统一入口的可追踪登记表，新增 gallery 时只需增加一条记录。

## 侧视图像素补偿

64×64 最近邻缩放会把侧脸的前端轮廓压缩成过少的像素，造成侧面看起来偏扁。当前证据表明这主要是分辨率和采样造成的轮廓损失，不应先归因于眼睛贴图被删除。因此侧视图需要单独保留像素补偿步骤：

1. 保留 256×256 原始侧视图，作为 3D 轮廓基准；
2. 先生成 128×128 侧视诊断图，确认鼻尖、嘴部、下巴和发际线没有在降采样时整体消失；
3. 在输出 64×64 像素图时，只对左右侧视图的可见外轮廓进行最小补偿，优先补回连续的脸部前缘和发际线；
4. 不修改正面/背面，不扩大眼睛贴图，不添加黑色眼框，也不把补偿像素延伸到原始轮廓之外；
5. 补偿后的结果必须同时与原始侧视图、128×128 诊断图和 64×64 像素图对照验收。

该补偿属于 2D 像素输出阶段的轮廓修正，不改变演员 Blend、骨骼或发型几何。正式接入像素处理工具前，侧视补偿结果只能作为 review 输出，不能直接覆盖正式运行时资源。

## 生成示例

使用 Blender 后台生成一个候选：

```powershell
& .\blender-4.5.10-windows-x64\blender.exe -b --python tools\blender\fit_blend_hair_candidate.py -- `
  --hair-source-blend prototype\assets\hair\male_source\Blend_Hair.blend `
  --hair-objects Colin_hair_bangs_01 Colin_hair_side_01 Colin_hair_back_01 `
  --source-anchor-object Colin_head_dummy `
  --normalize-components-to-head `
  --actor-blend prototype\assets\characters\generated\chibi_eyes_ears_pixel_walk_source_v1.blend `
  --output-blend prototype\test_output\hair_candidates_2026_08_04\male_gallery\assembly_seed_01\actor.blend `
  --output-dir prototype\test_output\hair_candidates_2026_08_04\male_gallery\assembly_seed_01
```

生成单个 gallery：

```powershell
python tools\build_hair_randomization_gallery.py `
  --root prototype\test_output\hair_candidates_2026_08_04\male_gallery `
  --candidate assembly_seed_01 `
  --candidate assembly_seed_02 `
  --candidate assembly_seed_04 `
  --output prototype\test_output\hair_candidates_2026_08_04\male_gallery\assembly_gallery.html
```

生成统一入口：

```powershell
python tools\build_hair_gallery_index.py `
  --root prototype\test_output\hair_candidates_2026_08_04 `
  --catalog prototype\assets\hair\hair_gallery_catalog_v1.json
```

## 验收规则

每个推荐候选至少检查正面、右侧面、后面和左侧面，并在 64×64 最近邻像素预览中复核。重点检查：

1. 发型是否覆盖头顶和后脑；
2. 刘海是否位于额头而不是眼睛或脸颊；
3. 耳朵是否被正确露出或遮挡；
4. 侧面是否出现明显白缝、漂浮或穿插；
5. 后视是否存在大面积头皮缺失；
6. 是否可以作为独立随机种子，或必须依赖某个 base/bangs/side/back 组合。
7. 侧视 64×64 输出是否经过轮廓补偿，并且没有误伤眼睛、发型或正面像素。

生成结果属于可重建的预览产物，当前 `prototype/test_output/` 按项目规则忽略；源 Blend、组合清单、工具和 catalog 必须提交到 Git。
