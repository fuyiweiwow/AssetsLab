param(
    [string]$GodotPath
)

$ErrorActionPreference = "Stop"
$assetsLabRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$prototypeRoot = Join-Path $assetsLabRoot "prototype"
. (Join-Path $PSScriptRoot "resolve_godot.ps1")
$godot = Resolve-GodotExecutable -RequestedPath $GodotPath -AssetsLabRoot $assetsLabRoot

Write-Output "FACE_VARIANT_TEST_BEGIN executable=$godot"

$baseArguments = @(
    "--headless",
    "--rendering-method", "gl_compatibility",
    "--path", $prototypeRoot,
    "--script", "res://tests/appearance_variant_test.gd"
)
& $godot @baseArguments
if($LASTEXITCODE -ne 0) {
    throw "Generated appearance variant test failed"
}

$fixedArguments = $baseArguments + @("--", "--base-features")
& $godot @fixedArguments
if($LASTEXITCODE -ne 0) {
    throw "Fixed base feature test failed"
}

$overrideArguments = $baseArguments + @("--", "--appearance-variant=3")
& $godot @overrideArguments
if($LASTEXITCODE -ne 0) {
    throw "Appearance variant override test failed"
}

Write-Output "FACE_VARIANT_TEST_PASS modes=3"
