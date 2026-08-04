param(
    [Parameter(Mandatory = $false)]
    [int]$Port = 8766
)

$ErrorActionPreference = "Stop"
$assetsLabRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "resolve_python.ps1")
$python = Resolve-PythonExecutable -RequestedPath $null -AssetsLabRoot $assetsLabRoot
$previewRoot = Join-Path $assetsLabRoot "prototype\preview"

Write-Output "CHIBI_EYE_CALIBRATOR_URL=http://127.0.0.1:$Port/chibi_eye_calibrator.html"
Write-Output "Press Ctrl+C to stop the local web server."
& $python -m http.server $Port --bind 127.0.0.1 --directory $previewRoot
