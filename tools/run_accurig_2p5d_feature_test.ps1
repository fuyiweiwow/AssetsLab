param(
    [string]$BlenderPath = "E:\env\Blender\blender.exe",
    [string]$PythonPath,
    [string]$FbxPath = "E:\comic\chibi_base_mesh_accurig_rigged_v1.fbx",
    [string]$Output = "prototype\test_output\accurig_2p5d_feature_test_v1",
    [ValidateSet("soft_anime_v1", "compact_v1")]
    [string]$Profile = "soft_anime_v1"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if(-not (Test-Path -LiteralPath $BlenderPath)) { throw "Blender executable not found: $BlenderPath" }
if(-not (Test-Path -LiteralPath $FbxPath)) { throw "AccuRIG FBX not found: $FbxPath" }
. (Join-Path $PSScriptRoot "resolve_python.ps1")
$python = Resolve-PythonExecutable -RequestedPath $PythonPath -AssetsLabRoot $root

& $BlenderPath --background --python (Join-Path $root "tools\blender\render_accurig_2p5d_feature_test.py") -- `
    --fbx $FbxPath `
    --output $Output `
    --profile $Profile `
    --freestyle
if($LASTEXITCODE -ne 0) { throw "2.5D feature render failed" }

& $python (Join-Path $root "tools\validate_accurig_2p5d_feature_test.py") --output $Output
if($LASTEXITCODE -ne 0) { throw "2.5D feature contract validation failed" }

Write-Output "ACCURIG_2P5D_FEATURE_WRAPPER_PASS output=$Output profile=$Profile"
