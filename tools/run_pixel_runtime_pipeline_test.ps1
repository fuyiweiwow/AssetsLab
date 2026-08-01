param(
    [string]$GodotPath
)

$ErrorActionPreference = "Stop"
$assetsLabRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$prototypeRoot = Join-Path $assetsLabRoot "prototype"
. (Join-Path $PSScriptRoot "resolve_godot.ps1")
$godot = Resolve-GodotExecutable -RequestedPath $GodotPath -AssetsLabRoot $assetsLabRoot

Write-Output "PIXEL_RUNTIME_PIPELINE_TEST_BEGIN executable=$godot"

$legacyArguments = @(
    "--headless",
    "--rendering-method", "gl_compatibility",
    "--path", $prototypeRoot,
    "--script", "res://tests/smoke_test.gd"
)
& $godot @legacyArguments
if($LASTEXITCODE -ne 0) {
    throw "Legacy prototype smoke test failed"
}

$runtimeArguments = @(
    "--headless",
    "--rendering-method", "gl_compatibility",
    "--path", $prototypeRoot,
    "--script", "res://tests/capture_test.gd",
    "--",
    "--pixel-runtime-actor"
)
& $godot @runtimeArguments
if($LASTEXITCODE -ne 0) {
    throw "Pixel runtime actor pipeline capture failed"
}

Write-Output "PIXEL_RUNTIME_PIPELINE_TEST_PASS legacy_smoke=1 runtime_capture=1"
