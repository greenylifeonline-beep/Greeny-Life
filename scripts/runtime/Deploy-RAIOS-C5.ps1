param(
    [string]$RuntimeRoot = "$HOME\.raios\runtime\c5",
    [int]$Port = 8766
)
$ErrorActionPreference = "Stop"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Head = (git -C $Repo rev-parse HEAD).Trim()
$AppRoot = Join-Path $RuntimeRoot "app"
$PkgDest = Join-Path $AppRoot "raios\c5_gateway"
$Venv = Join-Path $RuntimeRoot ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"
$Logs = Join-Path $RuntimeRoot "logs"
$Manifest = Join-Path $RuntimeRoot "deployment.json"

New-Item -ItemType Directory -Force -Path $PkgDest,$Logs | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppRoot "raios") | Out-Null
$Init = Join-Path $AppRoot "raios\__init__.py"
if (-not (Test-Path $Init)) { Set-Content -Path $Init -Value "" -Encoding UTF8 }
Copy-Item -Path (Join-Path $Repo "src\raios\c5_gateway\*") -Destination $PkgDest -Recurse -Force

if (-not (Test-Path $Python)) {
    & py -3.14 -m venv $Venv
}
& $Python -c "import importlib.util as u,sys; sys.exit(0 if all(u.find_spec(x) for x in ('fastapi','uvicorn','pydantic')) else 1)"
if ($LASTEXITCODE -ne 0) {
    & $Python -m pip install --disable-pip-version-check "fastapi>=0.115,<1" "uvicorn>=0.30,<1" "pydantic>=2,<3"
}

$hashes = @{}
Get-ChildItem $PkgDest -File | ForEach-Object {
    $hashes[$_.Name] = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
}
$deploy = [ordered]@{
    schema = "raios.c5-canonical-deployment.v1"
    canonical_head = $Head
    source_repo = $Repo
    runtime_root = $RuntimeRoot
    app_root = $AppRoot
    package_hashes = $hashes
    deployed_at = [DateTimeOffset]::UtcNow.ToString("o")
}
$deploy | ConvertTo-Json -Depth 8 | Set-Content -Path $Manifest -Encoding UTF8

$old = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
$oldPid = if ($old) { $old.OwningProcess } else { $null }
if ($oldPid) {
    Stop-Process -Id $oldPid -Force -ErrorAction Stop
    Start-Sleep -Seconds 2
}
$env:RAIOS_MAIN_CORTEX = "qwen3:0.6b"
$env:RAIOS_RUNTIME_ROOT = $RuntimeRoot
$env:RAIOS_CANONICAL_HEAD = $Head
$env:PYTHONPATH = $AppRoot
$out = Join-Path $Logs "gateway.out.log"
$err = Join-Path $Logs "gateway.err.log"
$args = @(
    "-m","uvicorn",
    "raios.c5_gateway.gateway:app",
    "--app-dir",$AppRoot,
    "--host","127.0.0.1",
    "--port","$Port"
)
$proc = Start-Process -FilePath $Python -ArgumentList $args -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru

$healthy = $false
for ($i=0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3
        if ($r.status -eq "ONLINE" -and $r.runtime_source -eq "CANONICAL_DEPLOYMENT" -and $r.canonical_head -eq $Head) {
            $healthy = $true
            break
        }
    } catch {}
}
if (-not $healthy) {
    if (-not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    throw "CANONICAL_C5_CUTOVER_FAILED::$err"
}

$r = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 5
Write-Host "C5_CANONICAL_RUNTIME=true"
Write-Host "C5_HTTP=200"
Write-Host "C5_PID=$($proc.Id)"
Write-Host "C5_CANONICAL_HEAD=$($r.canonical_head)"
Write-Host "C5_RUNTIME_SOURCE=$($r.runtime_source)"
Write-Host "C5_MODEL=$($r.model)"
Write-Host "OLD_LISTENER_PID=$oldPid"
Write-Host "DEPLOYMENT_MANIFEST=$Manifest"
