param(
    [string]$BlenderPath,
    [string]$PythonPath,
    [string]$OutputName = "neutral_chibi_actor_v1",
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
$assetsLabRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$prototypeRoot = Join-Path $assetsLabRoot "prototype"
$blenderPath = if ($BlenderPath) { $BlenderPath } else { "E:\env\Blender\blender.exe" }
if (!(Test-Path -LiteralPath $blenderPath)) { throw "Blender executable not found: $blenderPath" }

. (Join-Path $PSScriptRoot "resolve_python.ps1")
$pythonPath = Resolve-PythonExecutable -RequestedPath $PythonPath -AssetsLabRoot $assetsLabRoot

$guideRoot = Join-Path $prototypeRoot "assets\characters\generated\skeleton_walk_pipeline_v1\3d_guide_v1"
$actorRoot = Join-Path $prototypeRoot "assets\characters\generated\$OutputName"
$pixelRoot = Join-Path $prototypeRoot "assets\characters\generated\${OutputName}_pixels"
$renderRoot = Join-Path $prototypeRoot "test_output\${OutputName}_3d"
$contract = Join-Path $guideRoot "camera_contract.json"
$poseContract = Join-Path $guideRoot "g1_pose_contract.json"
$blend = Join-Path $actorRoot "$OutputName.blend"
$pose3d = Join-Path $actorRoot "${OutputName}_pose_3d.json"
$report = Join-Path $actorRoot "${OutputName}_validation.json"
$strictArgs = @()
if ($Strict) { $strictArgs = @("--strict") }

& $blenderPath --background --python (Join-Path $assetsLabRoot "tools\blender\create_q_guide_scene.py") -- --contract $contract --pose-contract $poseContract --blend $blend --render-dir $renderRoot --pose-3d $pose3d
if ($LASTEXITCODE -ne 0) { throw "neutral chibi Blender build failed with exit code $LASTEXITCODE" }

& $pythonPath (Join-Path $assetsLabRoot "tools\process_q_guide_pixels.py") --render-dir $renderRoot --output-dir $pixelRoot --blend $blend --pose-3d $pose3d
if ($LASTEXITCODE -ne 0) { throw "neutral chibi pixel processing failed with exit code $LASTEXITCODE" }

& $pythonPath (Join-Path $assetsLabRoot "tools\validate_neutral_chibi_actor.py") --render-dir $renderRoot --pixel-dir $pixelRoot --blend $blend --pose-3d $pose3d --report $report @strictArgs
if ($LASTEXITCODE -ne 0) { throw "neutral chibi validation failed with exit code $LASTEXITCODE" }

Write-Output "NEUTRAL_CHIBI_ACTOR_BUILD_PASS=$actorRoot"
Write-Output "NEUTRAL_CHIBI_ACTOR_PIXEL_OUTPUT=$pixelRoot"
Write-Output "NEUTRAL_CHIBI_ACTOR_REPORT=$report"
Write-Output "NEUTRAL_CHIBI_ACTOR_STATUS=REJECTED_GUIDERIG_FROM_SCRATCH_PROTOTYPE"
