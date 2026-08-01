param([string]$BlenderPath,[string]$PythonPath)
$ErrorActionPreference="Stop"; $assetsLabRoot=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path; $prototypeRoot=Join-Path $assetsLabRoot "prototype"
$blenderPath=if($BlenderPath){$BlenderPath}else{'E:\env\Blender\blender.exe'}; if(!(Test-Path -LiteralPath $blenderPath)){throw "Blender executable not found: $blenderPath"}
. (Join-Path $PSScriptRoot "resolve_python.ps1"); $pythonPath=Resolve-PythonExecutable -RequestedPath $PythonPath -AssetsLabRoot $assetsLabRoot
$guideRoot=Join-Path $prototypeRoot "assets\characters\generated\skeleton_walk_pipeline_v1\3d_guide_v1"; $contract=Join-Path $guideRoot "camera_contract.json"; $blend=Join-Path $guideRoot "mannequin_g0.blend"; $renderDir=Join-Path $prototypeRoot "test_output\3d_guide_g0"; $sheet=Join-Path $renderDir "contact_sheet.png"
& $blenderPath --background --python (Join-Path $assetsLabRoot "tools\blender\create_g0_guide_scene.py") -- --contract $contract --blend $blend --render-dir $renderDir
if($LASTEXITCODE -ne 0){throw "G0 Blender scene build failed with exit code $LASTEXITCODE"}
& $pythonPath (Join-Path $assetsLabRoot "tools\blender\validate_g0_guide.py") --contract $contract --blend $blend --render-dir $renderDir --contact-sheet $sheet
if($LASTEXITCODE -ne 0){throw "G0 guide validation failed with exit code $LASTEXITCODE"}; Write-Output "G0_3D_GUIDE_CAPTURE_PASS=$sheet"
