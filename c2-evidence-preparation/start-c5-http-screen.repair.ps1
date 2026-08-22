# C2 helper for Repair: start C5 HTTP screen on THIS laptop loop.
# Requires a tree that already has scripts/ai-os/raios_c5_screen.py (v9).
# No WAL write. No tree copy. No train. Paste the whole block; do not split if/elseif.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Candidates = @(
    (Get-Location).Path,
    "C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair"
)
$Repo = $null
foreach ($Root in $Candidates) {
    $Screen = Join-Path $Root "scripts\ai-os\raios_c5_screen.py"
    if (Test-Path -LiteralPath $Screen) {
        $Repo = $Root
        break
    }
}
if (-not $Repo) {
    Write-Host "C5_SCREEN_MISSING: checkout v9-neurolingua-semantic-kernel so scripts/ai-os/raios_c5_screen.py exists."
    Write-Host "Laptop localhost:8765 is empty until this script runs ON Repair."
    exit 2
}

Set-Location $Repo
$Python = $null
foreach ($Name in @("python3", "python")) {
    $Cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $Cmd) { continue }
    if ($Cmd.Source) { $Python = [string]$Cmd.Source; break }
    if ($Cmd.Path) { $Python = [string]$Cmd.Path; break }
}
if (-not $Python) {
    Write-Host "PYTHON_MISSING"
    exit 2
}

Write-Host "C5_SCREEN_STARTING on Repair loop http://127.0.0.1:8765"
& $Python (Join-Path $Repo "scripts\ai-os\raios_c5_screen.py") --serve
exit $LASTEXITCODE
