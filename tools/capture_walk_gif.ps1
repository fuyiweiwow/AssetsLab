param(
    [switch]$Female,
    [switch]$Compact,
    [switch]$BaseFeatures,
    [switch]$PixelRuntimeActor,
    [switch]$RebuildHead,
    [switch]$LatestGeneratedBody,
    [switch]$VerticalCandidate,
	[switch]$VerticalOnly,
    [switch]$RgsBodyRight,
	[switch]$BomboBodyRight,
	[switch]$RgsWalkReference,
	[switch]$MilestoneBodyRight,
	[switch]$RightOnly,
    [string]$GodotPath,
    [string]$PythonPath,
    [int]$AppearanceSeed
)

$ErrorActionPreference = "Stop"

# The milestone currently contains only the right-facing direction. Force a
# single-direction capture so its preview can never mix in another body set.
if ($MilestoneBodyRight) {
	$RightOnly = $true
}
if ($VerticalOnly) {
	$VerticalCandidate = $true
}

$assetsLabRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$prototypeRoot = Join-Path $assetsLabRoot "prototype"
. (Join-Path $PSScriptRoot "resolve_godot.ps1")
$godotPath = Resolve-GodotExecutable -RequestedPath $GodotPath -AssetsLabRoot $assetsLabRoot
. (Join-Path $PSScriptRoot "resolve_python.ps1")
$pythonPath = Resolve-PythonExecutable -RequestedPath $PythonPath -AssetsLabRoot $assetsLabRoot
$pythonModules = Join-Path $assetsLabRoot ".tools\python"
$frameDirectory = if ($PixelRuntimeActor) {
    Join-Path $prototypeRoot "test_output\pixel_runtime_capture_frames"
} else {
    Join-Path $prototypeRoot "test_output\capture_frames"
}
$gifName = if ($PixelRuntimeActor) {
    "movement_3d_eyes_ears_pixel_walk_v1.gif"
} elseif ($BomboBodyRight) {
    "movement_bombo_body_candidate.gif"
} elseif ($RgsBodyRight) {
    "movement_rgs_body_candidate.gif"
} elseif ($RgsWalkReference) {
    "movement_rgs_reference.gif"
} elseif ($LatestGeneratedBody) {
    "movement_latest_generated_body.gif"
} elseif ($VerticalCandidate) {
    "movement_vertical_body_candidate.gif"
} elseif ($RebuildHead -and $RightOnly) {
    "movement_rebuild_head_right_only.gif"
} elseif ($RebuildHead) {
    "movement_rebuild_head.gif"
} elseif ($MilestoneBodyRight) {
    if ($RightOnly) { "movement_milestone_body_right_only.gif" } else { "movement_milestone_body.gif" }
} elseif ($BaseFeatures) {
    "movement_walk_base_features_v1.gif"
} elseif ($Compact) {
	"movement_walk_compact.gif"
} else {
    "movement_walk.gif"
}
$gifPath = Join-Path $prototypeRoot "test_output\$gifName"
$logPath = Join-Path $prototypeRoot "test_output\capture.log"

$previousGeneratorPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = $pythonModules
try {
    if ($BaseFeatures) {
        $baseValidationOutput = & $pythonPath (Join-Path $assetsLabRoot "tools\validate_base_features.py") 2>&1
        $baseValidationExitCode = $LASTEXITCODE
        $baseValidationOutput | ForEach-Object { Write-Output $_ }
        if ($baseValidationExitCode -ne 0) {
            throw "Base feature validation failed with exit code $baseValidationExitCode"
        }
    }
}
finally {
    $env:PYTHONPATH = $previousGeneratorPythonPath
}

$godotArguments = @(
    "--headless",
    "--rendering-driver", "opengl3",
    "--rendering-method", "gl_compatibility",
    "--audio-driver", "Dummy",
    "--fixed-fps", "12",
    "--path", $prototypeRoot,
    "--script", "res://tests/capture_test.gd",
    "--log-file", $logPath
)
# Everything after this separator is forwarded to OS.get_cmdline_user_args()
# and is consumed by player.gd as a test-only runtime mode.
$godotArguments += "--"
if ($Female) {
    $godotArguments += "--female"
}
if ($Compact) {
    $godotArguments += "--compact"
}
if ($PixelRuntimeActor) {
    $godotArguments += "--pixel-runtime-actor"
} else {
    $godotArguments += "--base-features"
}
if ($RebuildHead) {
    $godotArguments += "--rebuild-head"
}
if ($LatestGeneratedBody) {
    $godotArguments += "--latest-generated-body"
}
if ($VerticalCandidate) {
	$godotArguments += "--vertical-body-candidate"
}
if ($VerticalOnly) {
	$godotArguments += "--vertical-only"
}
if ($RgsWalkReference) {
	$godotArguments += "--rgs-walk-reference"
}
if ($RgsBodyRight) {
    $godotArguments += "--rgs-body-right"
}
if ($BomboBodyRight) {
    $godotArguments += "--bombo-body-right"
}
if ($MilestoneBodyRight) {
	$godotArguments += "--milestone-body-right"
}
if ($RightOnly) {
	$godotArguments += "--right-only"
}
$godotProcess = Start-Process -FilePath $godotPath -ArgumentList $godotArguments -WindowStyle Hidden -PassThru -Wait
if (Test-Path -LiteralPath $logPath) {
    Get-Content -LiteralPath $logPath
}
if ($godotProcess.ExitCode -ne 0) {
    throw "Godot capture test failed with exit code $($godotProcess.ExitCode)"
}
$capturePassMarker = if ($PixelRuntimeActor) { "PIXEL_RUNTIME_CAPTURE_PASS" } else { "CAPTURE_TEST_PASS" }
if (-not (Select-String -LiteralPath $logPath -Pattern $capturePassMarker -Quiet)) {
    throw "Godot capture test did not report $capturePassMarker"
}

$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = $pythonModules
try {
    & $pythonPath (Join-Path $assetsLabRoot "tools\make_gif.py") --input $frameDirectory --output $gifPath --fps 12
    if ($LASTEXITCODE -ne 0) {
        throw "GIF conversion failed with exit code $LASTEXITCODE"
    }
    if ($RgsWalkReference) {
        Copy-Item -LiteralPath $gifPath -Destination (Join-Path $assetsLabRoot "prototype\preview\assets\movement_rgs_reference.gif") -Force
    }
    if ($RgsBodyRight) {
        Copy-Item -LiteralPath $gifPath -Destination (Join-Path $assetsLabRoot "prototype\preview\assets\movement_rgs_body_candidate.gif") -Force
    }
	if ($BomboBodyRight) {
		Copy-Item -LiteralPath $gifPath -Destination (Join-Path $assetsLabRoot "prototype\preview\assets\movement_bombo_body_candidate.gif") -Force
	}
	if ($MilestoneBodyRight) {
		$milestoneDestination = if ($RightOnly) { "movement_milestone_body_right_only.gif" } else { "movement_milestone_body.gif" }
		Copy-Item -LiteralPath $gifPath -Destination (Join-Path $assetsLabRoot "prototype\preview\assets\$milestoneDestination") -Force
	}
	if ($VerticalOnly) {
		Copy-Item -LiteralPath $gifPath -Destination (Join-Path $assetsLabRoot "prototype\preview\assets\movement_vertical_body_candidate.gif") -Force
	}
	if ($RebuildHead -and $RightOnly) {
		Copy-Item -LiteralPath $gifPath -Destination (Join-Path $assetsLabRoot "prototype\preview\assets\movement_rebuild_head_right_only.gif") -Force
	}
}
finally {
    $env:PYTHONPATH = $previousPythonPath
}

Write-Output "CAPTURE_COMPLETE=$gifPath"
