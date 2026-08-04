param(
    [string]$BlenderPath = "E:\env\Blender\blender.exe",
    [string]$PythonPath,
    [string]$FbxPath = "E:\comic\chibi_base_mesh_accurig_rigged_v1.fbx",
    [string]$CalibrationPath = "prototype\assets\characters\generated\chibi_eye_calibration.json",
    [string]$Output = "prototype\test_output\eye_package_v12_miku_structure",
    [string]$SaveBlend = "prototype\assets\characters\generated\eye_package_v12_miku_structure.blend"
)

$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "run_eye_package_v6.ps1") `
    -BlenderPath $BlenderPath `
    -PythonPath $PythonPath `
    -FbxPath $FbxPath `
    -CalibrationPath $CalibrationPath `
    -Output $Output `
    -SaveBlend $SaveBlend `
    -IrisWidthScale 0.96 `
    -IrisHeightScale 1.25 `
    -PupilHeightScale 1.45
if($LASTEXITCODE -ne 0) { throw "EyePackage v12 wrapper failed with exit code $LASTEXITCODE" }
Write-Output "EYE_PACKAGE_V12_WRAPPER_PASS output=$Output blend=$SaveBlend"
