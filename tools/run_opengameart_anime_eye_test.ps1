param(
    [string]$BlenderPath = "E:\env\Blender\blender.exe",
    [string]$FbxPath = "E:\comic\chibi_base_mesh_accurig_rigged_v1.fbx",
    [string]$SourceBlend = "prototype\assets\external\anime_eye_candidates\opengameart_generic_anime_face\animefaceshare.blend",
    [string]$Output = "prototype\test_output\opengameart_anime_eyes_on_accurig_v2",
    [double]$ScaleFactor = 0.82,
    [double]$EyeZRatio = 0.51,
    [double]$FrontSurfaceBias = -0.01,
    [double]$DepthScale = 0.35
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$fbx = if([System.IO.Path]::IsPathRooted($FbxPath)){ $FbxPath } else { Join-Path $root $FbxPath }
$source = if([System.IO.Path]::IsPathRooted($SourceBlend)){ $SourceBlend } else { Join-Path $root $SourceBlend }
if(-not (Test-Path -LiteralPath $BlenderPath)){ throw "Blender executable not found: $BlenderPath" }
if(-not (Test-Path -LiteralPath $fbx)){ throw "Original actor FBX not found: $fbx" }
if(-not (Test-Path -LiteralPath $source)){ throw "OpenGameArt source blend not found: $source" }

& $BlenderPath --background --python (Join-Path $root "tools\blender\render_opengameart_anime_eyes_on_accurig.py") -- `
    --fbx $fbx `
    --source $source `
    --output $Output `
    --scale-factor $ScaleFactor `
    --eye-z-ratio $EyeZRatio `
    --front-surface-bias $FrontSurfaceBias `
    --depth-scale $DepthScale `
    --freestyle
if($LASTEXITCODE -ne 0){ throw "OpenGameArt anime eye render failed" }

& python (Join-Path $root "tools\validate_opengameart_anime_eye_test.py") --render-dir $Output
if($LASTEXITCODE -ne 0){ throw "OpenGameArt anime eye validation failed" }

Write-Output "OPENGAMEART_ANIME_EYE_TEST_PASS output=$Output scale_factor=$ScaleFactor depth_scale=$DepthScale"
