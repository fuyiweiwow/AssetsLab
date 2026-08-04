param(
    [Parameter(Mandatory = $false)]
    [int]$Port = 8000,

    [Parameter(Mandatory = $false)]
    [string]$PythonPath,

    [Parameter(Mandatory = $false)]
    [string]$UnusedSnapshotName,

    [Parameter(Mandatory = $false)]
    [int]$HairVariantCacheMaxCount = 40,

    [Parameter(Mandatory = $false)]
    [long]$HairVariantCacheMaxBytes = 536870912
)

$ErrorActionPreference = "Stop"
$assetsLabRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "resolve_python.ps1")
$python = Resolve-PythonExecutable -RequestedPath $PythonPath -AssetsLabRoot $assetsLabRoot

$previewRoot = Join-Path $assetsLabRoot "prototype"
$serverPython = Join-Path (Split-Path -Parent $python) "pythonw.exe"
if (-not (Test-Path -LiteralPath $serverPython -PathType Leaf)) {
    $serverPython = $python
}
$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    Write-Output "PREVIEW_SERVER_ALREADY_RUNNING port=$Port"
} else {
    $server = Start-Process -WindowStyle Hidden -WorkingDirectory $assetsLabRoot -PassThru -FilePath $serverPython -ArgumentList @(
        "tools\lan_preview_server.py", "--port", $Port.ToString(), "--directory", $previewRoot,
        "--hair-variant-cache-max-count", $HairVariantCacheMaxCount.ToString(),
        "--hair-variant-cache-max-bytes", $HairVariantCacheMaxBytes.ToString()
    )
    $server.Id | Set-Content -LiteralPath (Join-Path $assetsLabRoot "prototype\test_output\lan_preview.pid") -Encoding ascii
    Start-Sleep -Milliseconds 500
}

$addresses = Get-NetIPConfiguration |
    Where-Object { $_.IPv4Address -and $_.IPv4DefaultGateway -and $_.IPv4Address.IPAddress -notlike "127.*" -and $_.IPv4Address.IPAddress -notlike "169.254.*" -and $_.IPv4Address.IPAddress -notlike "198.18.*" } |
    ForEach-Object { $_.IPv4Address.IPAddress }
if (-not $addresses) {
    $addresses = @("127.0.0.1")
}

$tailscalePath = (Get-Command tailscale -ErrorAction SilentlyContinue).Source
if ([string]::IsNullOrWhiteSpace($tailscalePath) -and (Test-Path -LiteralPath "C:\Program Files\Tailscale\tailscale.exe")) {
    $tailscalePath = "C:\Program Files\Tailscale\tailscale.exe"
}
$tailscaleAddresses = @()
if (-not [string]::IsNullOrWhiteSpace($tailscalePath)) {
    $tailscaleAddresses = @(& $tailscalePath ip -4 2>$null | Where-Object { $_ -match "^\d+\.\d+\.\d+\.\d+$" })
}

$orderedAddresses = @($tailscaleAddresses + $addresses | Select-Object -Unique)
$urls = foreach ($address in $orderedAddresses) { "http://$address`:$Port/preview/" }
$urlText = $urls -join [Environment]::NewLine
$urlText | Set-Content -LiteralPath (Join-Path $assetsLabRoot "prototype\test_output\lan_preview_url.txt") -Encoding utf8
Write-Output "PREVIEW_SERVER_ROOT=$previewRoot"
Write-Output $urlText
