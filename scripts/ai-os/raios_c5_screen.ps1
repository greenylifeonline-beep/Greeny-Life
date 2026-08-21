# C5 professional system screen. Open source. Local. No WAL.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
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

& $Python (Join-Path $PSScriptRoot "raios_c5_screen.py") @args
exit $LASTEXITCODE
