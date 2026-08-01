param(
    [string]$GodotPath
)

$ErrorActionPreference = "Stop"
$assetsLabRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$prototypeRoot = Join-Path $assetsLabRoot "prototype"
. (Join-Path $PSScriptRoot "resolve_godot.ps1")
$godot = Resolve-GodotExecutable -RequestedPath $GodotPath -AssetsLabRoot $assetsLabRoot

Write-Output "PIXEL_RUNTIME_GODOT_TEST_BEGIN executable=$godot"

$importedRoot = Join-Path $prototypeRoot ".godot\imported"
$pixelImport = Get-ChildItem $importedRoot -Filter "pixel.png-*.ctex" -File -ErrorAction SilentlyContinue | Select-Object -First 1
if($null -eq $pixelImport) {
    Write-Output "PIXEL_RUNTIME_IMPORT_CACHE_BEGIN"
    & $godot --headless --editor --path $prototypeRoot --quit-after 30
    if($LASTEXITCODE -ne 0) {
        throw "Godot editor import scan failed"
    }
    $pixelImport = Get-ChildItem $importedRoot -Filter "pixel.png-*.ctex" -File -ErrorAction SilentlyContinue | Select-Object -First 1
    if($null -eq $pixelImport) {
        throw "Godot import scan finished without importing pixel runtime PNGs"
    }
    Write-Output "PIXEL_RUNTIME_IMPORT_CACHE_PASS"
}

$tests = @(
    @("--script", "res://tests/pixel_runtime_import_test.gd"),
    @("--scene", "res://tests/pixel_runtime_scene_test.tscn"),
    @("--scene", "res://tests/pixel_runtime_actor_loader_test.tscn"),
    @("--scene", "res://tests/pixel_runtime_visual_capture.tscn"),
    @("--scene", "res://pixel_runtime_preview.tscn", "--", "--validate-only")
)

foreach($test in $tests) {
    $arguments = @(
        "--headless",
        "--rendering-method", "gl_compatibility",
        "--path", $prototypeRoot,
        "--quit-after", "5"
    ) + $test
    & $godot @arguments
    if($LASTEXITCODE -ne 0) {
        throw "Godot pixel runtime test failed: $($test -join ' ')"
    }
}

Write-Output "PIXEL_RUNTIME_GODOT_TEST_PASS tests=$($tests.Count)"
