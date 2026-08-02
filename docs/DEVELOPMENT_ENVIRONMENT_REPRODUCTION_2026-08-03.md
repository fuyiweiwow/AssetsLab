# AssetsLab 开发环境与复现基准

更新时间：2026-08-03  
适用分支：`pixel_asset_test`  
用途：在另一台 Windows 机器上复现当前 3D 演员、眼部部件、耳朵部件、Blender 渲染和网页校准工具。

> 本文只记录 3D/图像资产开发所需环境。Godot 属于运行时验证环境，本次明确不纳入。

## 1. 目录约定

建议在其他机器上保持同样的目录层级；如果盘符不同，只需要修改环境变量，不要修改项目脚本中的相对路径。

```text
E:\WorkProject\AssetsLab\             # Git 项目根目录
E:\Env\Blender\blender.exe            # Blender 4.5.0 便携版
E:\Env\Python311\python.exe           # 项目图像处理 Python
E:\Env\blender-ai-mcp\                # Blender MCP 外部仓库
E:\Env\Assets\                        # 用户下载的外部模型/材质
```

推荐设置以下变量：

```powershell
$env:ASSETSLAB_ROOT = 'E:\WorkProject\AssetsLab'
$env:BLENDER_BIN = 'E:\Env\Blender\blender.exe'
$env:PYTHON_BIN = 'E:\Env\Python311\python.exe'
$env:BLENDER_MCP_ROOT = 'E:\Env\blender-ai-mcp'
$env:ASSETSLAB_EXTERNAL_ASSETS = 'E:\Env\Assets'
```

项目中的 PowerShell 脚本优先使用显式参数，其次读取 `PYTHON_BIN` 或本机 PATH；不要依赖某台机器上的固定 `E:` 盘符。

## 2. 已验证版本

当前机器的基线如下：

| 组件 | 版本/状态 | 用途 |
|---|---|---|
| Windows PowerShell | 5.1.19041.6456 | 运行 `.ps1` 构建、渲染和预览脚本 |
| Git | 2.32.0.windows.1 | 分支、提交、远程同步 |
| Blender | 4.5.0 | 导入 FBX/Blend、建模测试、正侧面渲染 |
| Python | 3.11.3 | 图像裁切、透明化、像素化、报告生成 |
| Pillow | 10.0.0 | PNG/GIF 处理 |
| NumPy | 1.26.4 | 图像和坐标计算 |
| OpenCV | 4.8.0 | 轮廓、掩码和参考图分析 |
| Requests | 2.34.2 | 少量网络/资源辅助脚本 |
| Node.js | v24.18.0 | 网页工具/浏览器控制的辅助运行时 |
| npm | 8.5.3 | Node 包管理；PowerShell 中建议调用 `npm.cmd` |

检查命令：

```powershell
& $env:BLENDER_BIN --version
& $env:PYTHON_BIN --version
& $env:PYTHON_BIN -c "import PIL,numpy,cv2,requests; print(PIL.__version__, numpy.__version__, cv2.__version__, requests.__version__)"
node --version
npm.cmd --version
git --version
```

项目 Python 最低依赖可以用下面的命令安装：

```powershell
& $env:PYTHON_BIN -m pip install Pillow==10.0.0 numpy==1.26.4 opencv-python==4.8.0 requests==2.34.2
```

Blender 内部脚本使用 Blender 自带 Python，不要把项目 Python 的第三方包复制到 Blender 的 Python 目录。

## 3. Blender 与项目脚本

Blender 4.5.0 是当前项目的主要兼容目标。当前使用的脚本类型包括：

- `tools/blender/`：Blender 内部建模、导入、绑定、分析和渲染脚本；
- `tools/run_*eye*.ps1`：眼睛/眉毛/眼窝的测试入口；
- `tools/serve_*tool.ps1`：启动网页校准工具的本地静态服务器；
- `prototype/preview/`：网页校准器及其浏览器加载资源；
- `prototype/test_output/`：测试渲染输出，原则上不作为生产输入。

典型命令：

```powershell
Set-Location $env:ASSETSLAB_ROOT
& $env:BLENDER_BIN --background --python tools\blender\audit_chibi_candidate.py -- ...
.\tools\run_eye_package_imagegen_v4.ps1 -BlenderPath $env:BLENDER_BIN -PythonPath $env:PYTHON_BIN
.\tools\serve_chibi_eye_calibrator.ps1
```

若 Blender GUI 闪退，先用 `--background` 验证 Blend 文件能否被读取；只有后台验证通过后，才进入 GUI 或浏览器预览排查。

## 4. 当前 Codex Skill 清单

这些 skill 是工作流说明，不是项目运行时依赖。另一台机器使用 Codex 时，需要安装同名 skill 或使用等价工作流；项目不能通过 Git 自动携带用户目录中的 skill。

### 4.1 Blender/参考图核心 skill

来自 `RobLe3/cc-blender-skill` 体系、当前已安装在 `C:\Users\Admin\.codex\skills` 的核心 skill：

1. `reference-to-3d`：根据概念图、参考表和模型做源锁定重建；
2. `reference-analysis-validator`：测量轮廓、边界、中心和多视图差异；
3. `contour-to-mesh`：从 2D 轮廓建立网格，而不是用近似基本体；
4. `orthographic-registration`：登记正面、侧面、背面和顶面坐标；
5. `multiview-fit-loop`：多视图渲染、比较和迭代修正；
6. `blender-uv-texturing`：UV、贴图、Alpha 部件和导出；
7. `atlas-uv-fitting`：贴图图集区域与模型 UV 一一对应；
8. `texture-driven-mesh-fitting`：依据贴图/轮廓调整网格边界；
9. `fit-repair-optimizer`：把多视图验证结果整理成修复队列；
10. `quality-refinement-autoloop`：连续失败时诊断技能缺口、修复和验证。

当前项目的使用顺序建议为：

```text
reference-analysis-validator
  -> orthographic-registration
  -> reference-to-3d / contour-to-mesh
  -> blender-uv-texturing / texture-driven-mesh-fitting
  -> multiview-fit-loop
  -> fit-repair-optimizer
```

### 4.2 图像和网页辅助 skill

- `imagegen`：只用于生成新的概念眼睛、眉毛或临时参考位图；生成结果必须经过透明化、尺寸检查和人工视觉确认。
- `generate2dsprite`：后续进入像素资源生成时使用；当前眼睛/耳朵几何验证阶段不是必需依赖。
- `browser:control-in-app-browser`：用于已登录网页资源下载、网页校准器操作和本地预览验证；不能用来绕过登录、验证码或下载权限。
- `visualize:visualize`：需要做交互式校准器、参数面板或可视化比较时使用。

Skill 的本地路径属于当前机器示例。复现时应安装同名 skill，而不是硬编码 `C:\Users\Admin`；如果 Codex 未暴露 Blender MCP 原生工具，应继续使用仓库内的 Blender/Python 脚本作为可重复后备方案。

## 5. Blender MCP 环境

### 5.1 当前采用的 MCP

项目研究和本地握手验证采用：

- 仓库：[PatrykIti/blender-ai-mcp](https://github.com/PatrykIti/blender-ai-mcp)；
- 当前仓库版本：`3.3.0`；
- 本机目录：`E:\Env\blender-ai-mcp`；
- Blender 插件包：`E:\Env\blender-ai-mcp\outputs\blender_ai_mcp.zip`；
- MCP 独立 Python 环境：`E:\Env\blender-ai-mcp\.venv`；
- Blender RPC：`127.0.0.1:8765`；
- 当前推荐配置：`ROUTER_ENABLED=true`、`MCP_SURFACE_PROFILE=llm-guided`；
- 当前会话验证过的受限 MCP 工具数量：11 个；
- 当前 Codex 会话不保证动态暴露 `mcp__blender__*`，所以脚本路径仍必须可以独立运行。

MCP 虚拟环境当前版本：Python 3.11.3、FastMCP 3.2.4、pydocket 0.19.2、uvicorn 0.38.0、Pillow 12.3.0、NumPy 2.4.6、pydantic-monty 0.0.11。它与项目 Python 环境分离，不能混用。

### 5.2 另一台机器的安装步骤

```powershell
Set-Location E:\Env
git clone https://github.com/PatrykIti/blender-ai-mcp.git
Set-Location .\blender-ai-mcp
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe scripts\build_addon.py
```

然后在 Blender 中：

1. `Edit > Preferences > Add-ons > Install...`；
2. 选择 `outputs\blender_ai_mcp.zip`；
3. 启用 Blender AI MCP 插件；
4. 确认本地 RPC 使用 `127.0.0.1:8765`；
5. 按 MCP 客户端的配置启动服务器，不要在后台留下孤立常驻进程。

本地 stdio 配置使用 MCP 仓库的 `.env.example` 作为模板。至少确认：

```text
BLENDER_RPC_HOST=127.0.0.1
BLENDER_RPC_PORT=8765
ROUTER_ENABLED=true
MCP_SURFACE_PROFILE=llm-guided
MCP_TRANSPORT_MODE=stdio
```

如果使用 Docker/HTTP 模式，必须根据操作系统调整 Blender RPC 主机：Windows/macOS 通常使用 `host.docker.internal`，Linux 通常使用 `127.0.0.1` 加 `--network host`。当前项目不要求 Docker，stdio 模式足够进行本地测试。

### 5.3 MCP 使用边界

- MCP 负责受控的场景读取、测量、参考图检查、局部贴合和验证；
- 不把任意 `bpy` 代码执行当成默认建模方式；
- 任何眼窝、眼球或耳朵变更都必须输出正面和右侧面渲染，并检查接触/悬浮状态；
- MCP 不可用时，使用 `tools/blender/` 中的确定性脚本，不阻塞普通渲染和像素化流程。

## 6. 外部资源清单

用户下载目录：`E:\Env\Assets`。

| 文件 | 内容 | SHA-256 | 当前状态 |
|---|---|---|---|
| `Procedural Anime Eye Shader.blend` | 程序化动漫眼睛候选 | `BB4987A1F492987AAB7AFE9BBB9051EC4083853ED3884290842360ED3D1BD2FF` | 已下载，待下一阶段评估 |
| `簡単アニメアイ_販売用ファイル_Gumroad_無料.blend` | Easy Anime Eye 候选 | `21B05E6D91C4951199855AEF5E2F343BCD4DC9BBCBB736DF36793633FCB5BAE8` | 已下载，已有历史评估记录 |
| `low-poly-cartoon-ear.zip` | 独立卡通耳朵候选 | `53970087A6652EF1AD96ED03BBE5C586AD85F2B874308BA13FA60E5BB1E2191D` | 已下载，尚未提取/绑定 |

耳朵压缩包结构为：

```text
low-poly-cartoon-ear.zip
└─ source/archive.zip
   ├─ sketchfab.zbrush
   └─ SubTool-0-8292957.OBJ
```

下一步处理耳朵时，应先把它复制到项目的外部资产目录并保留原始压缩包，例如：

```text
prototype/assets/external/chibi_ear_candidates/low_poly_cartoon_ear/source/
```

原始下载文件和授权信息必须保留；不要把个人下载目录作为项目脚本的唯一输入路径。

## 7. 可复现验证顺序

在另一台机器上，按以下顺序验证，不要直接开始修改演员：

1. `git clone` 项目并切换到 `pixel_asset_test`；
2. 验证 Blender 4.5.0、项目 Python 3.11 和四个 Python 图像包；
3. 运行一个现有 Blender 后台审计脚本，确认 Blender 可读项目文件；
4. 启动本地预览服务器，确认 `prototype/preview/` 可以通过浏览器打开；
5. 若需要受控 Blender 操作，再安装并启动 Blender MCP；
6. 复制 `E:\Env\Assets` 中的外部模型并校验 SHA-256；
7. 对外部模型做独立正面/侧面渲染，再接入演员；
8. 每次接入后更新 `docs/` 测试记录，并保留失败候选的明确标记。

## 8. 不纳入本基准的内容

- Godot 编辑器、Godot 导出模板和运行时测试；
- 用户个人登录状态、浏览器 Cookie、API Key、MCP 客户端私有配置；
- `prototype/test_output/` 下的临时渲染输出；
- MCP `.venv`、模型缓存和本地日志；
- 未经确认的下载授权文件。

这些内容不能通过 Git 安全复现，应在目标机器上按本文说明单独安装或配置。
