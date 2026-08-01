param(
    [string]$BlenderPath = "E:\env\Blender\blender.exe",
    [string]$WalkFbxPath = "E:\env\temp\opencode\kiira_anim_pack\Walk.fbx",
    [string]$OutputName = "chibi_base_mesh_actor_v2",
    [double]$HeadSplitZ = 1.3,
    [string]$BindingLinesPath = ""
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (!(Test-Path -LiteralPath $BlenderPath)) { throw "Blender executable not found: $BlenderPath" }
if (!(Test-Path -LiteralPath $WalkFbxPath)) { throw "Walk FBX not found: $WalkFbxPath" }
. (Join-Path $PSScriptRoot "resolve_python.ps1")
$pythonPath = Resolve-PythonExecutable -RequestedPath $null -AssetsLabRoot $root
$actorRoot = Join-Path $root "prototype\assets\characters\generated\$OutputName"
$pixelRoot = Join-Path $root "prototype\assets\characters\generated\${OutputName}_pixels"
$renderRoot = Join-Path $root "prototype\test_output\${OutputName}_3d"
$blend = Join-Path $actorRoot "$OutputName.blend"
$manifest = Join-Path $renderRoot "manifest.json"
$report = Join-Path $actorRoot "${OutputName}_validation.json"
$source = Join-Path $root "third_party\chibi-base-meshblender.zip"
$bindingLineArgs = @()
if ($BindingLinesPath -ne "") {
    if (!(Test-Path -LiteralPath $BindingLinesPath)) { throw "Binding lines JSON not found: $BindingLinesPath" }
    $bindingLineArgs = @("--binding-lines", $BindingLinesPath)
}

& $BlenderPath --background --python (Join-Path $root "tools\blender\render_chibi_base_mesh_actor.py") -- --source-blend $source --walk-fbx $WalkFbxPath --render-dir $renderRoot --blend $blend --preserve-source-transform --rigid-head --head-split-z $HeadSplitZ @bindingLineArgs
if ($LASTEXITCODE -ne 0) { throw "chibi base mesh Blender build failed: $LASTEXITCODE" }
& $pythonPath (Join-Path $root "tools\process_chibi_base_mesh_actor_pixels.py") --render-dir $renderRoot --output-dir $pixelRoot --actor-blend $blend --source-archive $source
if ($LASTEXITCODE -ne 0) { throw "chibi base mesh pixelization failed: $LASTEXITCODE" }
& $pythonPath (Join-Path $root "tools\validate_chibi_base_mesh_actor.py") --render-dir $renderRoot --pixel-dir $pixelRoot --blend $blend --manifest $manifest --report $report
if ($LASTEXITCODE -ne 0) { throw "chibi base mesh validation failed: $LASTEXITCODE" }
Write-Output "CHIBI_BASE_MESH_ACTOR_BUILD_PASS=$actorRoot"
Write-Output "CHIBI_BASE_MESH_ACTOR_PIXEL_OUTPUT=$pixelRoot"
Write-Output "CHIBI_BASE_MESH_ACTOR_REPORT=$report"
