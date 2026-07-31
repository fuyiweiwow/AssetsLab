param([string]$GodotPath,[string]$PythonPath)
$ErrorActionPreference="Stop"; $assetsLabRoot=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path; $prototypeRoot=Join-Path $assetsLabRoot "prototype"
. (Join-Path $PSScriptRoot "resolve_godot.ps1"); $godotPath=Resolve-GodotExecutable -RequestedPath $GodotPath -AssetsLabRoot $assetsLabRoot
. (Join-Path $PSScriptRoot "resolve_python.ps1"); $pythonPath=Resolve-PythonExecutable -RequestedPath $PythonPath -AssetsLabRoot $assetsLabRoot
$args=@("--headless","--display-driver","windows","--rendering-driver","opengl3","--rendering-method","gl_compatibility","--audio-driver","Dummy","--path",$prototypeRoot,"--script","res://tests/calibrated_head_attachment_stage_test.gd")
$process=Start-Process -FilePath $godotPath -ArgumentList $args -WindowStyle Hidden -PassThru -Wait
if($process.ExitCode -ne 0){throw "Calibrated head attachment stage failed with exit code $($process.ExitCode)"}
$frames=Join-Path $prototypeRoot "test_output\skeleton_pipeline\calibrated_head_attachment"; $gif=Join-Path $prototypeRoot "test_output\skeleton_pipeline\calibrated_head_attachment.gif"
if((Get-ChildItem -LiteralPath $frames -Filter "frame_*.png" -File | Measure-Object).Count -ne 8){throw "Calibrated head attachment stage did not produce eight frames"}
& $pythonPath (Join-Path $assetsLabRoot "tools\make_gif.py") --input $frames --output $gif --fps 8
if($LASTEXITCODE -ne 0){throw "Calibrated head attachment GIF conversion failed with exit code $LASTEXITCODE"}; Write-Output "CALIBRATED_HEAD_ATTACHMENT_STAGE_CAPTURE_PASS=$gif"
