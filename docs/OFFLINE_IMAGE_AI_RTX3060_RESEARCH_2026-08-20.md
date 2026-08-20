# RTX 3060 12GB 离线图像 AI 与生成式穿戴工作流调研（2026-08-20）

## 决策结论

项目将 `RTX 3060 12GB` 作为本地图像生成/编辑阶段的目标显存规格。当前最值得验证的主模型是 `Qwen-Image-Edit-2511`；`Qwen-Image-Layered` 作为穿衣图分层实验；`Z-Image-Turbo` 作为快速文生图候选；`Stable Diffusion 3.5 Medium NF4` 作为显存可控的保底路线。

没有任何一个开放权重图像模型能够单独完成“Actor 三视图 -> 合身且一致的服装三视图 -> 可动画 3D 穿戴资产”。图像模型只负责原型设计和多视图一致性；Hunyuan3D-2MV 负责生成 3D 来源网格；ActorProfile、Slot Compiler、骨骼绑定和动作门禁仍由确定性脚本负责。

## 候选模型

| 模型 | 官方能力与显存信息 | 本项目定位 | 当前结论 |
| --- | --- | --- | --- |
| `Qwen-Image-Edit-2511` | 支持多图输入并强调一致性；Qwen-Image 官方仓库记录 DiffSynth-Studio 可逐层卸载、FP8 量化，并可在约 4GB 显存内推理；Apache 2.0 | 读取同一 Actor 的 front/right/back/left 校准图，生成同步的穿衣或局部饰品视图 | **首选验证**；3060 12GB 需要量化/CPU offload，速度与系统内存占用必须实测 |
| `Qwen-Image-Layered` | 20B，可把输入图分解为多个 RGBA 层，支持 640/1024 分辨率和递归分层；Apache 2.0 | 从 Actor 穿衣图中分离衣服、人物与背景，验证能否补全手臂遮挡后的衣摆/袖管 | **第二阶段验证**；权重与缓存很大，不能预先承诺 12GB 上的速度或遮挡补全质量 |
| `Z-Image-Turbo` | 6B、8 NFE；官方称可在 16GB 消费卡运行，stable-diffusion.cpp 路线最低约 4GB 显存；Apache 2.0 | 快速生成服装概念和提示词 A/B | **可用辅助模型**；当前官方模型表中的 `Z-Image-Edit` 仍为待发布，不能承担 Actor 多图编辑主线 |
| `Stable Diffusion 3.5 Medium` | 官方提供 NF4 四比特量化和 CPU offload 示例 | 低显存保底文生图、已有生态对照组 | **保底**；不是当前多视图 Actor 一致性的首选 |
| `FLUX.1-schnell` | 1-4 步生成，Apache 2.0 | 快速文生图对照 | **不作为主线**；缺少本项目需要的原生多参考图编辑合同 |

官方来源：

- [Qwen-Image / Qwen-Image-Edit-2511](https://github.com/QwenLM/Qwen-Image)
- [Qwen-Image-Layered](https://huggingface.co/Qwen/Qwen-Image-Layered)
- [Z-Image](https://github.com/Tongyi-MAI/Z-Image)
- [Stable Diffusion 3.5 Medium](https://huggingface.co/stabilityai/stable-diffusion-3.5-medium)
- [FLUX.1-schnell](https://github.com/black-forest-labs/flux/blob/main/model_cards/FLUX.1-schnell.md)

## 目标闭环

暂定目标流水线如下：

1. 本地图像 AI 生成或编辑素体 front/right/back 三视图；生产合同仍建议同时保留 left，以便发现非对称错误。
2. 本地 Hunyuan3D-2MV 根据多视图生成素体来源模型。
3. 为该素体建立新的 `ActorClass`：规范单位/轴向、生成 canonical scene，并提取 ActorProfile。需要动画时必须具备骨骼、蒙皮、bind/rest pose 和语义骨骼映射；没有骨骼时只能进入 `static_only`。
4. 由 canonical Actor 的固定正交相机重新拍摄 front/right/back/left、轮廓、深度、法线、部件 ID 和槽位遮罩。这一组图是后续生成的几何约束，不复用最初概念图的相机误差。
5. `Qwen-Image-Edit-2511` 读取同一 Actor 的多视图与槽位说明，在保持人物比例、姿势和相机不变的前提下生成完整套装或指定 Slot 的穿衣视图。
6. 优先直接生成每个 Slot 的独立白底/纯色背景图；同时用 `Qwen-Image-Layered` 验证从穿衣图分离 RGBA 服装层。分层失败或遮挡后部件缺失时，候选不得直接进入 Hunyuan。
7. Hunyuan3D-2MV 为每个 Slot 单独生成来源 GLB；禁止把整套穿衣 Actor 作为不可拆分模型送入饰品系统。
8. Slot Compiler 根据 ActorProfile 自动完成尺度、锚点、局部变形笼、身体遮挡、骨骼白名单和权重编译；生成网格继续作为可见风格资产，脚本辅助几何不替代服装设计。
9. QA Compiler 运行静态、四视图、动作、自相交、Actor 穿插、袖窿、鞋底接地和槽位间干涉门禁。
10. 人工批准后才进入 AssetsStudio milestone、组合预览和最终 3D -> 2D 渲染。

## 3060 12GB 执行策略

- 第一个离线图像实验使用 640 或 768 分辨率，不从 2K 开始。
- 采用 FP8/NF4、模型逐层卸载和 CPU offload；记录峰值显存、系统内存、单张耗时和输出一致性。
- 同一套多视图必须使用确定性 seed、同一提示词合同和固定相机标签；不接受四张独立文生图拼接。
- 图像阶段先评估轮廓、比例、槽位完整性、手臂/下摆遮挡和跨视图对应关系；纹理生成、UV 烘焙和最终材质质量暂不列入本轮目标。
- 模型权重保存在本地模型缓存，不进入 Git。仓库只保存版本、来源、校验值、运行配置和批准后的轻量参考输入。

## 首个离线验证门禁

以当前 `ChibiActorV1` 和冒险者 `torso_outer` 为基准，比较现有 ImageGen 输入与 Qwen 本地输入：

- Actor 身高、肩宽、胸腰轮廓和固定相机投影不发生不可接受漂移；
- front/right/back/left 的领口、袖长、下摆和主色块能对应；
- 侧视图不因抹除手臂产生下摆缺口或双袖；
- 分离后的 Slot 图不含明显皮肤、脸或背景残片；
- Hunyuan3D-2MV 输出能够通过现有 Source Intake，并由同一 Slot Compiler 编译；
- 图像质量提升不能替代袖窿变形和鞋底接地的 3D 门禁。

通过该验证后，再把本地图像模型包装为 AssetsStudio 的本地作业阶段；在此之前只登记为 `planned`，不伪装成可用按钮。
