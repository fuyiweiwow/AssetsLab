param(
    [string]$BlenderPath = "E:\env\Blender\blender.exe",
    [string]$FbxPath = "E:\comic\chibi_base_mesh_accurig_rigged_v1.fbx",
    [string]$FeatureBlend = "prototype\test_output\koban_feature_extraction_v1\koban_feature_base_v1.blend",
    [string]$Output = "prototype\test_output\koban_features_on_accurig_v3",
    [double]$FrontOffset = 0.18,
    [double]$EarOutward = 0.10,
    [double]$EyeInset = 0.09,
    [ValidateSet("source", "anime_plate_v2")]
    [string]$EyeStyle = "anime_plate_v2"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$fbx = if([System.IO.Path]::IsPathRooted($FbxPath)){ $FbxPath } else { Join-Path $root $FbxPath }
$features = if([System.IO.Path]::IsPathRooted($FeatureBlend)){ $FeatureBlend } else { Join-Path $root $FeatureBlend }
if(-not (Test-Path -LiteralPath $BlenderPath)){ throw "Blender executable not found: $BlenderPath" }
if(-not (Test-Path -LiteralPath $fbx)){ throw "Original actor FBX not found: $fbx" }
if(-not (Test-Path -LiteralPath $features)){ throw "Feature blend not found: $features" }

& $BlenderPath --background --python (Join-Path $root "tools\blender\render_koban_features_on_accurig.py") -- `
    --fbx $fbx `
    --features $features `
    --output $Output `
    --front-offset $FrontOffset `
    --ear-outward $EarOutward `
    --eye-inset $EyeInset `
    --eye-style $EyeStyle
if($LASTEXITCODE -ne 0){ throw "Koban feature attachment render failed" }

& python (Join-Path $root "tools\validate_koban_feature_attachment.py") --render-dir $Output
if($LASTEXITCODE -ne 0){ throw "Koban feature attachment validation failed" }

Write-Output "KOBAN_FEATURE_ATTACHMENT_TEST_PASS output=$Output eye_style=$EyeStyle eye_inset=$EyeInset"
