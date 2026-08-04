# AssetsLab 素体演员 AccuRIG 交接说明

当前用于 AccuRIG 的输入文件：

```text
prototype/assets/characters/generated/chibi_base_mesh_accurig_input_v3/chibi_base_mesh_accurig_input_v3.fbx
```

当前已标定的交接文件：

```text
prototype/assets/characters/generated/chibi_base_mesh_accurig_calibrated_v1.fbx
```

在 AccuRIG 中只导入 `chibi_base_mesh_accurig_input_v3.fbx` 做重新标定；不要把眼睛、眉毛、耳朵或头发合并进标定输入。它们由 Blender 后台装配到演员头骨，并在四视图渲染后进入像素化流程。

标定检查顺序：

1. Head / Neck 位于头部和身体连接处的体积中心；
2. Shoulder / Elbow / Wrist 位于手臂厚度中心；
3. Hip / Knee / Ankle 位于腿部实际弯曲轴心；
4. 关闭 Mirror，分别检查左右膝、肘和头部；
5. 先导出骨骼绑定文件，再单独检查动作，不要把收费动作导出作为当前流程前置条件。

项目内的演员源文件是：

```text
prototype/assets/characters/generated/chibi_eyes_ears_pixel_walk_source_v1.blend
```

完整的当前流程、无 GUI 命令和保留清单见 `docs/ACTIVE_ASSET_WORKFLOW.md`。
