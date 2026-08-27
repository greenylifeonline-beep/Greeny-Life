$ErrorActionPreference = "Stop"
$Root = "C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair"
$Channel = Join-Path $Root ".ai-os\control\RAIOS-C1-C5-CHANNEL.py"
$StartC5 = Join-Path $Root ".ai-os\control\START-RAIOS-C5.ps1"
$Python = Join-Path $Root ".venv\Scripts\python.exe"

function Test-C5 {
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8766/health" -TimeoutSec 4
        return ($r.StatusCode -eq 200)
    } catch { return $false }
}

if (-not (Test-C5)) {
    if (Test-Path $StartC5) {
        & $StartC5 -GatewayOnly
    }
}
if (-not (Test-C5)) {
    Write-Host "C5_RUNTIME_LIVE=false"
    Write-Host "BLOCKER=C5_LOCAL_8766_OFFLINE"
    exit 2
}

if (-not (Test-Path $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
Set-Location -LiteralPath $Root
& $Python $Channel @args
exit $LASTEXITCODE
