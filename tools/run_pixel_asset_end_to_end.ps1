param(
    [string]$GodotPath,
    [string]$PythonPath
)

$ErrorActionPreference = "Stop"
$assetsLabRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeAssetRoot = Join-Path $assetsLabRoot "prototype\assets\characters\runtime\chibi_accurig_walk_test_v1"
. (Join-Path $PSScriptRoot "resolve_python.ps1")
$python = Resolve-PythonExecutable -RequestedPath $PythonPath -AssetsLabRoot $assetsLabRoot

Write-Output "PIXEL_ASSET_END_TO_END_BEGIN python=$python"
& $python (Join-Path $assetsLabRoot "tools\validate_pixel_runtime_package.py") --asset-dir $runtimeAssetRoot
if($LASTEXITCODE -ne 0) {
    throw "Pixel runtime package validation failed"
}

& (Join-Path $PSScriptRoot "run_pixel_runtime_godot_test.ps1") -GodotPath $GodotPath
if($LASTEXITCODE -ne 0) {
    throw "Godot runtime tests failed"
}

& (Join-Path $PSScriptRoot "run_pixel_runtime_pipeline_test.ps1") -GodotPath $GodotPath
if($LASTEXITCODE -ne 0) {
    throw "Prototype integration pipeline failed"
}

Write-Output "PIXEL_ASSET_END_TO_END_PASS package=1 godot=1 integration=1"
