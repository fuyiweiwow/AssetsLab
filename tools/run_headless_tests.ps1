param(
    [string]$GodotPath,
    [string]$PythonPath,
    [switch]$Female,
    [switch]$Compact,
    [switch]$BaseFeatures,
    [switch]$RebuildHead,
    [switch]$RebuildBody,
    [switch]$VerticalCandidate,
    [switch]$RgsBodyRight,
    [switch]$BomboBodyRight,
    [switch]$RgsWalkReference,
    [switch]$MilestoneBodyRight,
    [int]$AppearanceSeed
)

$ErrorActionPreference = "Stop"

$assetsLabRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$prototypeRoot = Join-Path $assetsLabRoot "prototype"
. (Join-Path $PSScriptRoot "resolve_godot.ps1")
$godotPath = Resolve-GodotExecutable -RequestedPath $GodotPath -AssetsLabRoot $assetsLabRoot
. (Join-Path $PSScriptRoot "resolve_python.ps1")
$pythonPath = Resolve-PythonExecutable -RequestedPath $PythonPath -AssetsLabRoot $assetsLabRoot
$pythonModules = Join-Path $assetsLabRoot ".tools\python"
$assetVariant = if ($Compact) { "chibi_compact" } else { "chibi" }
$previousGeneratorPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = $pythonModules
try {
    $baseValidationOutput = & $pythonPath (Join-Path $assetsLabRoot "tools\validate_base_features.py") 2>&1
    $baseValidationExitCode = $LASTEXITCODE
    $baseValidationOutput | ForEach-Object { Write-Output $_ }
    if ($baseValidationExitCode -ne 0) {
        throw "Base feature validation failed with exit code $baseValidationExitCode"
    }
}
finally {
    $env:PYTHONPATH = $previousGeneratorPythonPath
}

$importLogPath = Join-Path $assetsLabRoot "prototype\test_output\headless_import.log"
New-Item -ItemType Directory -Force -Path (Split-Path $importLogPath) | Out-Null
$previousImportErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$importOutput = & $godotPath --headless --editor --import --path $prototypeRoot --quit 2>&1
$importExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousImportErrorActionPreference
$importOutput | Out-File -LiteralPath $importLogPath -Encoding utf8
if ($importExitCode -ne 0) {
    throw "Godot headless asset import failed with exit code $importExitCode"
}

function Invoke-GodotScriptTest {
    param([string]$ScriptName)

    $scriptArguments = @(
        "--headless",
        "--path", $prototypeRoot,
        "--script", "res://tests/$ScriptName"
    )
    $scriptOutput = & $godotPath @scriptArguments 2>&1
    $scriptExitCode = $LASTEXITCODE
    $scriptOutput | ForEach-Object { Write-Output $_ }
    if ($scriptExitCode -ne 0) {
        throw "Godot test $ScriptName failed with exit code $scriptExitCode"
    }
}

$previousPythonPath = $env:PYTHONPATH
$previousChibiAssetRoot = $env:CHIBI_ASSET_ROOT
$env:PYTHONPATH = $pythonModules
$env:CHIBI_ASSET_ROOT = $assetVariant
try {
    if ($RebuildHead) {
        & $pythonPath (Join-Path $assetsLabRoot "tools\validate_rebuild_runtime_anchors.py")
        if ($LASTEXITCODE -ne 0) {
            throw "Rebuild runtime anchor validation failed with exit code $LASTEXITCODE"
        }
    }
	& $pythonPath (Join-Path $assetsLabRoot "tools\validate_chibi_frames.py")
	if ($LASTEXITCODE -ne 0) {
		throw "Chibi frame validation failed with exit code $LASTEXITCODE"
	}
	& $pythonPath (Join-Path $assetsLabRoot "tools\validate_limb_occlusion.py")
	if ($LASTEXITCODE -ne 0) {
		throw "Limb occlusion validation failed with exit code $LASTEXITCODE"
	}
}
finally {
    $env:PYTHONPATH = $previousPythonPath
    $env:CHIBI_ASSET_ROOT = $previousChibiAssetRoot
}

function Invoke-SmokeTest {
    param([switch]$UseFemale)

    $logDirectory = Join-Path $assetsLabRoot "prototype\test_output"
    New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
    $logPrefix = if ($Compact) { "headless_compact" } else { "headless" }
    $logName = if ($UseFemale) { "$logPrefix`_female.log" } else { "$logPrefix`_male.log" }
    $logPath = Join-Path $logDirectory $logName
    $arguments = @(
        "--headless",
        "--log-file", $logPath,
        "--path", $prototypeRoot,
        "--script", "res://tests/smoke_test.gd"
    )
    if ($UseFemale) {
        $arguments += @("--", "--female")
    }
    if ($Compact) {
        if ($arguments -contains "--") {
            $arguments += "--compact"
        } else {
            $arguments += @("--", "--compact")
        }
    }
    if ($BaseFeatures) {
        if ($arguments -contains "--") {
            $arguments += "--base-features"
        } else {
            $arguments += @("--", "--base-features")
        }
    } else {
        if ($arguments -contains "--") {
            $arguments += "--appearance-seed=$appearanceSeed"
        } else {
            $arguments += @("--", "--appearance-seed=$appearanceSeed")
        }
    }
    if ($RebuildHead) {
        if ($arguments -contains "--") {
            $arguments += "--rebuild-head"
        } else {
            $arguments += @("--", "--rebuild-head")
        }
    }
    if ($RebuildBody) {
        if ($arguments -contains "--") {
            $arguments += "--rebuild-body"
        } else {
            $arguments += @("--", "--rebuild-body")
        }
    }
    if ($RgsBodyRight) {
        if ($arguments -contains "--") {
            $arguments += "--rgs-body-right"
        } else {
            $arguments += @("--", "--rgs-body-right")
        }
    }
    if ($RgsWalkReference) {
        if ($arguments -contains "--") {
            $arguments += "--rgs-walk-reference"
        } else {
            $arguments += @("--", "--rgs-walk-reference")
        }
    }
    if ($BomboBodyRight) {
        if ($arguments -contains "--") {
            $arguments += "--bombo-body-right"
        } else {
            $arguments += @("--", "--bombo-body-right")
        }
    }
    if ($MilestoneBodyRight) {
        if ($arguments -contains "--") {
            $arguments += "--milestone-body-right"
        } else {
            $arguments += @("--", "--milestone-body-right")
        }
    }
	if ($VerticalCandidate) {
		if ($arguments -contains "--") {
			$arguments += "--vertical-body-candidate"
		} else {
			$arguments += @("--", "--vertical-body-candidate")
		}
	}

    Write-Output ("Running headless smoke test ({0}) with {1}" -f ($(if ($UseFemale) { "female" } else { "male" }), $godotPath))
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $output = & $godotPath @arguments 2>&1
    $nativeExitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorActionPreference
    $output | ForEach-Object { Write-Output $_ }
    if ($nativeExitCode -ne 0) {
        throw "Godot headless smoke test failed with exit code $nativeExitCode"
    }
    if (-not ($output -match "SMOKE_TEST_PASS")) {
        throw "Godot headless smoke test did not report SMOKE_TEST_PASS"
    }
}

Invoke-SmokeTest
if ($Female) {
    Invoke-SmokeTest -UseFemale
}

Write-Output "HEADLESS_TESTS_PASS"
