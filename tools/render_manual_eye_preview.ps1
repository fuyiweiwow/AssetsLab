param(
    [string]$Blend = 'E:\WorkProject\AssetsLab\prototype\assets\characters\generated\procedural_anime_eye_manual_adjustment_final_v1.blend'
)

$blender = 'E:\Env\Blender\blender.exe'
$outputDir = 'E:\WorkProject\AssetsLab\prototype\test_output\manual_eye_preview'
$outputPrefix = Join-Path $outputDir 'frame_'

if (-not (Test-Path -LiteralPath $blender)) { throw "Blender not found: $blender" }
if (-not (Test-Path -LiteralPath $Blend)) { throw "Blend file not found: $Blend" }
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

& $blender --factory-startup --background $Blend -o $outputPrefix -F PNG -f 1
if ($LASTEXITCODE -ne 0) { throw "Blender render failed with exit code $LASTEXITCODE" }

Write-Host "Render complete: $outputDir\frame_0001.png"
