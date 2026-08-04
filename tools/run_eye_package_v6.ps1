param(
    [string]$BlenderPath = "E:\env\Blender\blender.exe",
    [string]$PythonPath,
    [string]$FbxPath = "E:\comic\chibi_base_mesh_accurig_rigged_v1.fbx",
    [string]$CalibrationPath = "prototype\assets\characters\generated\chibi_eye_calibration.json",
    [string]$Output = "prototype\test_output\eye_package_v6_short_corner",
    [string]$SaveBlend = "prototype\assets\characters\generated\eye_package_v6_short_corner.blend",
    [double]$IrisWidthScale = 1.0,
    [double]$IrisHeightScale = 0.92,
    [double]$PupilHeightScale = 1.35
)

$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "run_eye_package_v4.ps1") `
    -BlenderPath $BlenderPath `
    -PythonPath $PythonPath `
    -FbxPath $FbxPath `
    -CalibrationPath $CalibrationPath `
    -Output $Output `
    -SaveBlend $SaveBlend `
    -IrisWidthScale $IrisWidthScale `
    -IrisHeightScale $IrisHeightScale `
    -PupilHeightScale $PupilHeightScale
if($LASTEXITCODE -ne 0) { throw "EyePackage v6 wrapper failed with exit code $LASTEXITCODE" }
Write-Output "EYE_PACKAGE_V6_WRAPPER_PASS output=$Output blend=$SaveBlend"
