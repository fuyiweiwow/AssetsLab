param(
    [string]$BlenderPath = "E:\env\Blender\blender.exe",
    [string]$PythonPath,
    [string]$BlendPath = "prototype\assets\external\koban_chibi_base_mesh\Koban Chibi Base Mesh VRM export.blend",
    [string]$RenderOutput = "prototype\test_output\koban_walk_test_v1",
    [string]$PixelOutput = "prototype\test_output\koban_walk_pixels_v1",
    [double]$Amplitude = 1.3
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "resolve_python.ps1")
$python = Resolve-PythonExecutable -RequestedPath $PythonPath -AssetsLabRoot $root
$blend = if([System.IO.Path]::IsPathRooted($BlendPath)){ $BlendPath } else { Join-Path $root $BlendPath }
if(-not (Test-Path -LiteralPath $BlenderPath)){ throw "Blender executable not found: $BlenderPath" }
if(-not (Test-Path -LiteralPath $blend)){ throw "Koban blend not found: $blend" }

& $BlenderPath --background --python (Join-Path $root "tools\blender\render_koban_walk_test.py") -- `
    --blend $blend `
    --output $RenderOutput `
    --amplitude $Amplitude `
    --freestyle
if($LASTEXITCODE -ne 0){ throw "Koban render test failed" }

& $python (Join-Path $root "tools\validate_koban_walk_test.py") --render-dir $RenderOutput
if($LASTEXITCODE -ne 0){ throw "Koban render validation failed" }

& $python (Join-Path $root "tools\process_accurig_walk_pixels.py") --render-dir $RenderOutput --output-dir $PixelOutput --size 64
if($LASTEXITCODE -ne 0){ throw "Koban pixel conversion failed" }

& $python (Join-Path $root "tools\validate_pixel_asset_test.py") --pixel-dir $PixelOutput --expected-size 64 --expected-frames 8
if($LASTEXITCODE -ne 0){ throw "Koban pixel package validation failed" }

Write-Output "KOBAN_WALK_PIPELINE_PASS render=$RenderOutput pixels=$PixelOutput amplitude=$Amplitude"
