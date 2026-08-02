param(
    [string]$BlenderPath = "E:\env\Blender\blender.exe",
    [string]$FbxPath = "E:\comic\chibi_base_mesh_accurig_rigged_v1.fbx",
    [string]$CalibrationPath = "prototype\assets\characters\generated\chibi_eye_calibration.json",
    [string]$Output = "prototype\test_output\eye_package_imagegen_v1",
    [string]$SaveBlend = "prototype\assets\characters\generated\eye_package_imagegen_v1.blend"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$left = Join-Path $root "prototype\assets\generated\eye_package_v3\imagegen_eye_v2_crops\imagegen_eye_L.png"
$right = Join-Path $root "prototype\assets\generated\eye_package_v3\imagegen_eye_v2_crops\imagegen_eye_R.png"
if(-not (Test-Path -LiteralPath $BlenderPath)) { throw "Blender executable not found: $BlenderPath" }
if(-not (Test-Path -LiteralPath $FbxPath)) { throw "Actor FBX not found: $FbxPath" }
if(-not (Test-Path -LiteralPath $left) -or -not (Test-Path -LiteralPath $right)) { throw "ImageGen eye crops not found" }

$outputPath = Join-Path $root $Output
$blendPath = Join-Path $root $SaveBlend
& $BlenderPath --background --python (Join-Path $root "tools\blender\build_eye_package_v1.py") -- `
    --fbx (Resolve-Path $FbxPath).Path `
    --calibration (Resolve-Path $CalibrationPath).Path `
    --left-texture $left `
    --right-texture $right `
    --front-clearance 0.03 `
    --width-scale 0.95 `
    --height-scale 1.0 `
    --curvature 0.004 `
    --shrinkwrap-offset 0.001 `
    --no-upper-line `
    --output $outputPath `
    --save-blend $blendPath
$blendExit = $LASTEXITCODE
if($blendExit -ne 0) { throw "ImageGen EyePackage Blender build failed with exit code $blendExit" }
Write-Output "EYE_PACKAGE_IMAGEGEN_V1_PASS output=$outputPath blend=$blendPath"
