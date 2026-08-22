# C3 NEXT_ACTION=RECOVER_ORIGINAL_C5_RUNTIME_ONLY
# NO_REBUILD / NO_SECOND_SERVER / NO_NEW_C5 / NO_MODEL_DOWNLOAD / NO_WEIGHT_MERGE
# Paste the whole block. Do not split if / elseif.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Port = 8765
$Tcp = $null
try {
    $Tcp = New-Object System.Net.Sockets.TcpClient
    $Tcp.Connect("127.0.0.1", $Port)
} catch {
    $Tcp = $null
}
if ($null -ne $Tcp -and $Tcp.Connected) {
    $Tcp.Close()
    Write-Host "C5_PORT_8765_LISTENING=true"
    Write-Host "NO_SECOND_SERVER: original already bound on this loop. Not starting another process."
    try {
        $Status = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8765/api/status"
        $Status | ConvertTo-Json -Compress
    } catch {
        Write-Host "PORT_OPEN_BUT_STATUS_FAILED"
    }
    exit 0
}

$Candidates = @(
    (Get-Location).Path,
    "C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair"
)
$Repo = $null
foreach ($Root in $Candidates) {
    $Screen = Join-Path $Root "scripts\ai-os\raios_c5_screen.py"
    $Launch = Join-Path $Root "scripts\ai-os\raios_c5_screen.ps1"
    if ((Test-Path -LiteralPath $Screen) -and (Test-Path -LiteralPath $Launch)) {
        $Repo = $Root
        break
    }
}
if (-not $Repo) {
    Write-Host "ORIGINAL_RUNTIME_ENV_OR_LAUNCH_BIND"
    Write-Host "C5_SOURCE_LOSS_NOT_PROVEN: need v9 tree with scripts/ai-os/raios_c5_screen.ps1"
    Write-Host "NO_REBUILD=true NO_NEW_C5=true"
    exit 2
}

Set-Location $Repo
Write-Host "RECOVER_ORIGINAL_C5_RUNTIME_ONLY $Repo"
Write-Host "NO_SECOND_SERVER launching original raios_c5_screen.ps1 because 8765 was closed on THIS loop"
& (Join-Path $Repo "scripts\ai-os\raios_c5_screen.ps1") --serve
exit $LASTEXITCODE
