# The Goal / TOC on live canonical JSON. No simulated minutes. Calls the Python keeper.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Repo

$py = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $py) {
    $py = Get-Command python -ErrorAction Stop
}

& $py.Source (Join-Path $PSScriptRoot "raios_c5_toc.py") @args
exit $LASTEXITCODE
