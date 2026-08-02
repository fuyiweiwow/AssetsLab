# Miku 眼眶复刻测试记录（2026-08-02）

## 网页工具修复

- `miku_lash_overlay_tool.html` 的“完成圈选”现在会自动闭合、抠出部件、清除左侧多边形并生成右侧部件。
- “重新抠取当前圈选”保留为重复生成入口。

## 眼眶测试

### v1：完整眼眶环

- 输出：`prototype/test_output/miku_eye_socket_on_accurig_v1/`
- 结果：正面过厚，像圆形眼镜；侧面出现明显板状黑边。
- 结论：淘汰。

### v2：薄眼眶环

- 输出：`prototype/test_output/miku_eye_socket_on_accurig_v2_thin_conformed/`
- 结果：侧面板状黑边消失，但正面仍有眼镜框感。
- 结论：仅保留作深度对照，不作为最终方案。

### v3：上下眼睑弧线

- 脚本：`tools/blender/create_miku_eye_socket_arc_on_accurig.py`
- 输出：`prototype/test_output/miku_eye_socket_arc_on_accurig_v2_directionfix/`
- Blender 场景：`prototype/assets/characters/generated/miku_eye_socket_arc_on_accurig_v2_directionfix.blend`
- 结果：上眼睑使用较粗弧线，下眼睑使用较细弧线；正面更接近动漫眼轮廓，侧面没有完整圆环的板状横条；64 像素预览中轮廓仍然可读。
- 当前状态：可供用户观察的候选，不代表最终眼眶拓扑。

## 下一步判断

如果 v3 的轮廓方向可接受，再继续把弧线调整为 Miku 的眼角形状，并制作真正的“眼眶开口/遮挡层”；如果 v3 仍然像外贴线条，则转向从 Miku `eye_007_22_0_node` 的 UV/轮廓中提取黑色眼线，再投射到演员头部。
