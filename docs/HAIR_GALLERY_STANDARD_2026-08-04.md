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
- `tools/build_hair_workbench.py`：生成统一发型设计与随机池评审页面，支持每个槽位随机池随机/手选、保存设计并回链 Gallery。
- `tools/blender/generate_hair_component_variant.py`：以一个参考部件为种子生成独立几何变体，不自动拼接其它部件。
- `tools/build_hair_component_workbench.py`：生成单部件变体评审页面，与组合工作台共享正式部件池。
- `tools/generate_hair_pool_preview_cache.ps1`：按当前随机池静默生成可复用的组合预览缓存。
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

生成随机化工作台：

```powershell
python tools\build_hair_workbench.py `
  --root prototype\test_output\hair_candidates_2026_08_04 `
  --component-catalog prototype\assets\hair\hair_component_catalog_v1.json `
  --pool-catalog prototype\assets\hair\hair_random_pool_v1.json `
  --gallery-catalog prototype\assets\hair\hair_gallery_catalog_v1.json `
  --output prototype\test_output\hair_candidates_2026_08_04\workbench\index.html
```

生成随机池组合预览缓存：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\generate_hair_pool_preview_cache.ps1
```

生成单部件变体示例：

```powershell
& .\blender-4.5.10-windows-x64\blender.exe -b --python tools\blender\generate_hair_component_variant.py -- `
  --hair-source-blend prototype\assets\hair\Blender-Chloe_Hair.blend `
  --hair-object Chloe_hair_bangs_02 `
  --source-anchor-object Chloe_head_dummy `
  --actor-blend prototype\assets\characters\generated\chibi_eyes_ears_pixel_walk_source_v1.blend `
  --output-blend prototype\test_output\hair_component_variants_2026_08_04\variant_female_front_bangs_02_1001\actor.blend `
  --output-dir prototype\test_output\hair_component_variants_2026_08_04\variant_female_front_bangs_02_1001 `
  --variant-seed 1001
```

生成单部件评审页面：

```powershell
python tools\build_hair_component_workbench.py `
  --component-catalog prototype\assets\hair\hair_component_catalog_v1.json `
  --pool-catalog prototype\assets\hair\hair_random_pool_v1.json `
  --variant-root prototype\test_output\hair_component_variants_2026_08_04 `
  --output prototype\test_output\hair_component_variants_2026_08_04\workbench\index.html
```

单部件工作台在 `tools\serve_preview.ps1` 启动的预览服务下支持“生成并预览”：页面提交参考部件和 Seed 后，服务端验证共享部件池，静默执行 Blender `-b`，生成四方向图并自动重建工作台。该接口不会改写正式随机池，也不会打开 Blender GUI。

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
