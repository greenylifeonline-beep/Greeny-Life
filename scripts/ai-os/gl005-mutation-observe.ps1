# Observe POST /api/tasks on the already-bound Next process. Does not grant GL-005 PASS.
# Does not spawn, kill, provision Postgres, mint secrets, or forge gl_session.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Repo

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "gl004-runtime-bind.ps1")
if ($LASTEXITCODE -ne 0) {
    Write-Host "BIND_FAILED=$LASTEXITCODE"
}

python (Join-Path $PSScriptRoot "gl005-mutation-observe.py")
exit $LASTEXITCODE
