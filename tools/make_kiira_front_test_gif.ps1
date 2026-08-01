param(
    [string]$PythonPath,
    [int]$Fps = 8
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$inputDir = Join-Path $root "prototype\assets\characters\generated\kiira_walk_front_test_v1"
$output = Join-Path $inputDir "front_walk_test.gif"

if (-not (Test-Path -LiteralPath $inputDir)) {
    throw "KIIRA front test frames not found: $inputDir"
}

if ($PythonPath) {
    $python = $PythonPath
} else {
    . (Join-Path $PSScriptRoot "resolve_python.ps1")
    $python = Resolve-PythonExecutable -AssetsLabRoot $root
}

& $python (Join-Path $root "tools\make_gif.py") --input $inputDir --output $output --fps $Fps
if ($LASTEXITCODE -ne 0) {
    throw "KIIRA front GIF conversion failed with exit code $LASTEXITCODE"
}
Write-Output "KIIRA_FRONT_GIF=$output"
