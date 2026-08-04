param(
    [string]$GodotPath
)

$ErrorActionPreference = "Stop"
$assetsLabRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$prototypeRoot = Join-Path $assetsLabRoot "prototype"
. (Join-Path $PSScriptRoot "resolve_godot.ps1")
$godot = Resolve-GodotExecutable -RequestedPath $GodotPath -AssetsLabRoot $assetsLabRoot

Write-Output "PIXEL_RUNTIME_GODOT_TEST_BEGIN executable=$godot"

Write-Output "PIXEL_RUNTIME_IMPORT_BEGIN"
# Runtime sprite folders are intentionally replaced by the asset pipeline.  A
# generic .ctex existence check can therefore accept stale imports from an old
# folder while the new PNGs remain unavailable to ResourceLoader.  Force a
# project import pass before every validation run.
& $godot --headless --editor --path $prototypeRoot --import --quit-after 180
if($LASTEXITCODE -ne 0) {
    throw "Godot editor import scan failed"
}
Write-Output "PIXEL_RUNTIME_IMPORT_PASS"

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
