# Character Anchor 轮廓合同

## 当前概念基准

当前角色外观与轮廓以项目根目录的 `front-character-anchor.png` 为正面设计基准；女性表现变体使用 `front-character-anchor-female.png`。这些图片是美术目标，不是已经接入运行时的像素资源。

## 当前 3D 基线

`prototype/assets/characters/actor_v1/` 是唯一保留的 3D 演员基线。下一步不是继续寻找新的演员，而是检查 Actor V1 是否能在固定四向相机、头部锚点和脚底 y=60 合同下接近正面概念轮廓，并完成 3D→2D review。

## 轮廓验收重点

- 大头比例保留，但头部不能压扁或侵入肩颈；
- 发型、肩部/服装、衣摆和靴子形成连续剪影；
- 双臂和手掌与躯干保持可读分离；
- 四方向共享画布、脚底基线、头部锚点和碰撞占位；
- 64×64 下轮廓必须清晰，不能依靠细碎高光或抗锯齿维持形状。

## 运行时边界

Actor V1 的 Blend 只用于离线参考。Godot 最终使用处理后的分层 PNG，所有 Face、Hair、Clothing 和 Accessory 层必须遵守同一注册合同，不能逐层独立缩放或裁切。

## 下一步

1. 用 Actor V1 生成四向、8 帧透明参考和 silhouette/part-ID/depth pass；
2. 在 64×64 review 图上验收正面轮廓、脚底和头部稳定性；
3. 通过后再接入 Face 层、眨眼、发型和服装。
