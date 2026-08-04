param([string]$GodotPath,[string]$BlenderPath,[string]$PythonPath)
$ErrorActionPreference="Stop"; $assetsLabRoot=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path; $prototypeRoot=Join-Path $assetsLabRoot "prototype"
. (Join-Path $PSScriptRoot "resolve_godot.ps1"); $godotPath=Resolve-GodotExecutable -RequestedPath $GodotPath -AssetsLabRoot $assetsLabRoot
$blenderPath=if($BlenderPath){$BlenderPath}else{'E:\env\Blender\blender.exe'}; if(!(Test-Path -LiteralPath $blenderPath)){throw "Blender executable not found: $blenderPath"}
. (Join-Path $PSScriptRoot "resolve_python.ps1"); $pythonPath=Resolve-PythonExecutable -RequestedPath $PythonPath -AssetsLabRoot $assetsLabRoot
$guideRoot=Join-Path $prototypeRoot "assets\characters\generated\skeleton_walk_pipeline_v1\3d_guide_v1"; $contract=Join-Path $guideRoot "camera_contract.json"; $poseContract=Join-Path $guideRoot "g1_pose_contract.json"; $blend=Join-Path $guideRoot "mannequin_g1.blend"; $pose3d=Join-Path $guideRoot "g1_pose_3d.json"; $renderDir=Join-Path $prototypeRoot "test_output\3d_guide_g1"; $sheet=Join-Path $renderDir "contact_sheet.png"
$arguments = @("--headless","--rendering-driver","opengl3","--rendering-method","gl_compatibility","--audio-driver","Dummy","--path",$prototypeRoot,"--script","res://tests/pose_contract_export_test.gd")
$process=Start-Process -FilePath $godotPath -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait
if($process.ExitCode -ne 0){throw "G1 pose contract export failed with exit code $($process.ExitCode)"}
& $blenderPath --background --python (Join-Path $assetsLabRoot "tools\blender\create_g1_guide_scene.py") -- --contract $contract --pose-contract $poseContract --blend $blend --render-dir $renderDir --pose-3d $pose3d
if($LASTEXITCODE -ne 0){throw "G1 Blender scene build failed with exit code $LASTEXITCODE"}
& $pythonPath (Join-Path $assetsLabRoot "tools\blender\validate_g1_guide.py") --pose-3d $pose3d --blend $blend --render-dir $renderDir --contact-sheet $sheet
if($LASTEXITCODE -ne 0){throw "G1 guide validation failed with exit code $LASTEXITCODE"}; Write-Output "G1_3D_GUIDE_CAPTURE_PASS=$sheet"
