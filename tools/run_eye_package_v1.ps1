param(
    [string]$BlenderPath = "E:\env\Blender\blender.exe",
    [string]$PythonPath,
    [string]$FbxPath = "E:\comic\chibi_base_mesh_accurig_rigged_v1.fbx",
    [string]$CalibrationPath = "prototype\assets\characters\generated\chibi_eye_calibration.json",
    [string]$Output = "prototype\test_output\eye_package_v8",
    [string]$SaveBlend = "prototype\assets\characters\generated\eye_package_v8.blend",
    [switch]$NoUpperLine
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if(-not (Test-Path -LiteralPath $BlenderPath)) { throw "Blender executable not found: $BlenderPath" }
if(-not (Test-Path -LiteralPath $FbxPath)) { throw "Actor FBX not found: $FbxPath" }
. (Join-Path $PSScriptRoot "resolve_python.ps1")
$python = Resolve-PythonExecutable -RequestedPath $PythonPath -AssetsLabRoot $root

$textureSource = Join-Path $root "prototype\assets\external\chibi_eye_model_candidates\miku_chibi\source\extracted\ctr_mikp001_eye.png"
$textureDir = Join-Path $root "prototype\assets\generated\eye_package_v1"
& $python (Join-Path $root "tools\prepare_miku_eye_texture_crops.py") --source $textureSource --output $textureDir
if($LASTEXITCODE -ne 0) { throw "Miku eye crop generation failed" }

$outputPath = Join-Path $root $Output
$blendPath = Join-Path $root $SaveBlend
$optionalArgs = @()
if($NoUpperLine) { $optionalArgs += "--no-upper-line" }
& $BlenderPath --background --python (Join-Path $root "tools\blender\build_eye_package_v1.py") -- `
    --fbx (Resolve-Path $FbxPath).Path `
    --calibration (Resolve-Path $CalibrationPath).Path `
    --left-texture (Join-Path $textureDir "miku_eye_left.png") `
    --right-texture (Join-Path $textureDir "miku_eye_right.png") `
    --left-iris (Join-Path $textureDir "miku_iris_left.png") `
    --right-iris (Join-Path $textureDir "miku_iris_right.png") `
    --front-clearance 0.03 `
    --width-scale 1.2 `
    --height-scale 1.0 `
    --curvature 0.012 `
    --upper-line-width 0.008 `
    --shrinkwrap-offset 0.002 `
    --output $outputPath `
    --save-blend $blendPath @optionalArgs
if($LASTEXITCODE -ne 0) { throw "EyePackage v1 Blender build failed" }

Write-Output "EYE_PACKAGE_V1_WRAPPER_PASS output=$outputPath blend=$blendPath"
