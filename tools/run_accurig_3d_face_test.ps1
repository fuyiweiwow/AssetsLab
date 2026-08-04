param(
    [string]$BlenderPath = "E:\env\Blender\blender.exe",
    [string]$FbxPath = "E:\comic\chibi_base_mesh_accurig_rigged_v1.fbx",
    [string]$Output = "prototype\test_output\accurig_3d_face_test_v1",
    [int]$Variant = 0
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if(-not (Test-Path -LiteralPath $BlenderPath)) {
    throw "Blender executable not found: $BlenderPath"
}
if(-not (Test-Path -LiteralPath $FbxPath)) {
    throw "AccuRIG FBX not found: $FbxPath"
}

& $BlenderPath --background --python (Join-Path $root "tools\blender\render_accurig_3d_facial_feature_test.py") -- `
    --fbx $FbxPath `
    --output $Output `
    --variant $Variant `
    --freestyle
if($LASTEXITCODE -ne 0) {
    throw "3D facial feature diagnostic render failed"
}

Write-Output "ACCURIG_3D_FACE_TEST_WRAPPER_PASS output=$Output variant=$Variant"
