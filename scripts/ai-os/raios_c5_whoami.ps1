# C5 introduces himself from git. Repair Windows and pwsh-on-Linux.
# Calls the live Python keeper. No WAL. No V9. Not this Cursor session.
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

& $Python (Join-Path $PSScriptRoot "raios_c5_whoami.py") @args
exit $LASTEXITCODE
