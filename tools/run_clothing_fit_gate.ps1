param(
    [Parameter(Mandatory = $true)]
    [string]$BlenderPath,

    [Parameter(Mandatory = $true)]
    [string]$Blend,

    [Parameter(Mandatory = $true)]
    [string]$Output,

    [Parameter(Mandatory = $false)]
    [string]$GarmentName = "GarmentCodeShirt_ActorTransfer",

    [Parameter(Mandatory = $false)]
    [string]$GarmentNames = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$detector = Join-Path $root "tools\blender\check_garment_actor_fit.py"

if (-not (Test-Path -LiteralPath $BlenderPath -PathType Leaf)) {
    throw "Blender executable was not found: $BlenderPath"
}
if (-not (Test-Path -LiteralPath $Blend -PathType Leaf)) {
    throw "Candidate blend was not found: $Blend"
}

$outputParent = Split-Path -Parent $Output
if (-not [string]::IsNullOrWhiteSpace($outputParent)) {
    New-Item -ItemType Directory -Force -Path $outputParent | Out-Null
}

Write-Output "CLOTHING_FIT_GATE_BEGIN blend=$Blend garment=$GarmentName"
$detectorArguments = @(
    "--blend", $Blend,
    "--output", $Output,
    "--garment-name", $GarmentName
)
if (-not [string]::IsNullOrWhiteSpace($GarmentNames)) {
    $detectorArguments += @("--garment-names", $GarmentNames)
}
& $BlenderPath --background --python $detector -- @detectorArguments
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Output "CLOTHING_FIT_GATE_PASS report=$Output"
} else {
    Write-Output "CLOTHING_FIT_GATE_FAIL report=$Output exit_code=$exitCode"
}
exit $exitCode
