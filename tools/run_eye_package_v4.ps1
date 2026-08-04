param(
    [string]$BlenderPath = "E:\env\Blender\blender.exe",
    [string]$PythonPath,
    [string]$FbxPath = "E:\comic\chibi_base_mesh_accurig_rigged_v1.fbx",
    [string]$CalibrationPath = "prototype\assets\characters\generated\chibi_eye_calibration.json",
    [string]$Output = "prototype\test_output\eye_package_v5_flat_miku_style",
    [string]$SaveBlend = "prototype\assets\characters\generated\eye_package_v5_flat_miku_style.blend",
    [double]$IrisWidthScale = 1.0,
    [double]$IrisHeightScale = 0.92,
    [double]$PupilHeightScale = 1.35
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if(-not (Test-Path -LiteralPath $BlenderPath)) { throw "Blender executable not found: $BlenderPath" }
if(-not (Test-Path -LiteralPath $FbxPath)) { throw "Actor FBX not found: $FbxPath" }
. (Join-Path $PSScriptRoot "resolve_python.ps1")
$python = Resolve-PythonExecutable -RequestedPath $PythonPath -AssetsLabRoot $root

$mikuSource = Join-Path $root "prototype\assets\external\chibi_eye_model_candidates\miku_chibi\source\extracted\ctr_mikp001_eye.png"
$mikuDir = Join-Path $root "prototype\assets\generated\eye_package_v2"
$mikuFullDir = Join-Path $root "prototype\assets\generated\eye_package_v1"
$conceptSource = Join-Path $root "front-character-anchor.png"
$conceptDir = Join-Path $root "prototype\assets\generated\eye_package_v2"
& $python (Join-Path $root "tools\prepare_miku_eye_layers_v2.py") --source $mikuSource --output $mikuDir
& $python (Join-Path $root "tools\prepare_miku_eye_texture_crops.py") --source $mikuSource --output $mikuFullDir
& $python (Join-Path $root "tools\prepare_concept_eye_frames_v2.py") --source $conceptSource --output $conceptDir
if($LASTEXITCODE -ne 0) { throw "Miku/concept eye layer preparation failed" }

$outputPath = Join-Path $root $Output
$blendPath = Join-Path $root $SaveBlend
& $BlenderPath --background --python (Join-Path $root "tools\blender\build_eye_package_v1.py") -- `
    --fbx (Resolve-Path $FbxPath).Path `
    --calibration (Resolve-Path $CalibrationPath).Path `
    --left-texture (Join-Path $mikuFullDir "miku_eye_left.png") `
    --right-texture (Join-Path $mikuFullDir "miku_eye_right.png") `
    --left-iris (Join-Path $mikuDir "miku_iris_base_L.png") `
    --right-iris (Join-Path $mikuDir "miku_iris_base_R.png") `
    --left-pupil (Join-Path $mikuDir "anime_pupil_vertical_L.png") `
    --right-pupil (Join-Path $mikuDir "anime_pupil_vertical_R.png") `
    --left-frame (Join-Path $conceptDir "concept_eye_frame_v2_L.png") `
    --right-frame (Join-Path $conceptDir "concept_eye_frame_v2_R.png") `
    --front-clearance 0.03 `
    --width-scale 1.0 `
    --height-scale 1.35 `
    --eye-white-height-scale 0.68 `
    --iris-width-scale $IrisWidthScale `
    --iris-height-scale $IrisHeightScale `
    --pupil-height-scale $PupilHeightScale `
    --curvature 0.006 `
    --shrinkwrap-offset 0.0015 `
    --output $outputPath `
    --save-blend $blendPath
$blendExit = $LASTEXITCODE
if($blendExit -ne 0) { throw "EyePackage v5 Blender build failed with exit code $blendExit" }

Write-Output "EYE_PACKAGE_V5_WRAPPER_PASS output=$outputPath blend=$blendPath"
