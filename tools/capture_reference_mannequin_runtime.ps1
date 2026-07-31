[CmdletBinding()]
param(
    [string]$GodotPath = ""
)

$assetsLabRoot = Split-Path -Parent $PSScriptRoot
$prototypeRoot = Join-Path $assetsLabRoot "prototype"
$logPath = Join-Path $prototypeRoot "test_output\reference_mannequin_capture.log"

if ([string]::IsNullOrWhiteSpace($GodotPath)) {
    $GodotPath = $env:GODOT_BIN
}
if ([string]::IsNullOrWhiteSpace($GodotPath)) {
    $GodotPath = $env:GODOT_PATH
}
if ([string]::IsNullOrWhiteSpace($GodotPath)) {
    $GodotPath = Join-Path (Split-Path -Parent $assetsLabRoot) "Godot-4.6.2\unpacked\Godot_v4.6.2-stable_win64_console.exe"
}
if (-not (Test-Path -LiteralPath $GodotPath)) {
    throw "Godot executable not found: $GodotPath"
}

$arguments = @(
    "--headless",
    "--display-driver", "windows",
    "--rendering-driver", "opengl3",
    "--rendering-method", "gl_compatibility",
    "--audio-driver", "Dummy",
    "--path", $prototypeRoot,
    "--script", "res://tests/reference_mannequin_runtime_capture.gd"
)

& $GodotPath @arguments *> $logPath
$exitCode = $LASTEXITCODE
Get-Content -LiteralPath $logPath
if ($exitCode -ne 0) {
    throw "Reference mannequin capture failed with exit code $exitCode"
}
if (-not (Select-String -LiteralPath $logPath -Pattern "REFERENCE_MANNEQUIN_RUNTIME_CAPTURE_PASS" -Quiet)) {
    throw "Reference mannequin capture did not report PASS"
}
Write-Output "REFERENCE_MANNEQUIN_CAPTURE_SCRIPT_PASS"
