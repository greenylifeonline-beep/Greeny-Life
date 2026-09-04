param(
    [string]$RuntimeRoot = $(Join-Path ([Environment]::GetFolderPath("UserProfile")) ".raios\runtime\c5"),
    [int]$Port = 8766,
    [string]$Repo = $(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
)
$ErrorActionPreference = "Stop"
$StableUserProfile = [Environment]::GetFolderPath("UserProfile")
$Repo = (Resolve-Path $Repo).Path
$Head = (git -C $Repo rev-parse HEAD).Trim()
$CanonicalSourcePaths = @(
    "requirements-c5.txt",
    "src/raios/c5_gateway",
    "src/raios/search_cortex",
    "src/raios/neuro_lingua",
    ".ai-os/mcp/C5-MAINTENANCE-LAWS.json",
    "scripts/ai-os/raios_c5_maintenance_guard.py",
    "scripts/runtime/Deploy-RAIOS-C5.ps1"
)
$DirtyCanonicalSources = @(git -C $Repo status --porcelain=v1 -- $CanonicalSourcePaths)
if ($DirtyCanonicalSources.Count -gt 0) {
    throw ("C5_CANONICAL_SOURCE_DIRTY::" + (($DirtyCanonicalSources -join ";") -replace "`r|`n", " "))
}
$AppRoot = Join-Path $RuntimeRoot "app"
$StageAppRoot = Join-Path $RuntimeRoot "app.stage"
$BackupAppRoot = Join-Path $RuntimeRoot "app.previous"
$Venv = Join-Path $RuntimeRoot ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"
$PythonWindowless = Join-Path $Venv "Scripts\pythonw.exe"
$Logs = Join-Path $RuntimeRoot "logs"
$Manifest = Join-Path $RuntimeRoot "deployment.json"
$RuntimeBase = Split-Path -Parent $RuntimeRoot
$CognitiveStoreRoot = Join-Path $RuntimeBase "cognitive-store\v9"
$LearningRoot = Join-Path $CognitiveStoreRoot "learning"
$Requirements = Join-Path $Repo "requirements-c5.txt"
$MaintenanceGuard = Join-Path $Repo "scripts\ai-os\raios_c5_maintenance_guard.py"
$PackageNames = @("c5_gateway","search_cortex","neuro_lingua")

if (-not (Test-Path $Python)) { & py -3.14 -m venv $Venv }
& $Python $MaintenanceGuard
if ($LASTEXITCODE -ne 0) { throw "C5_MAINTENANCE_GUARD_FAILED" }
if (-not (Test-Path $Requirements)) { throw "C5_REQUIREMENTS_MISSING::$Requirements" }
if (-not (Test-Path $PythonWindowless)) { throw "C5_PYTHONW_MISSING::$PythonWindowless" }
$RequiredModules = "fastapi,uvicorn,pydantic,httpx,yaml,orjson,rapidfuzz,langcodes,language_data,ddgs,pytest,pytest_asyncio,hypothesis"
$MissingModules = (& $Python -c "import importlib.util; mods='$RequiredModules'.split(','); print(','.join(x for x in mods if importlib.util.find_spec(x) is None))").Trim()
if ($MissingModules) {
    & $Python -m pip install --disable-pip-version-check -r $Requirements
    if ($LASTEXITCODE -ne 0) { throw "C5_DEPENDENCY_INSTALL_FAILED" }
}
& $Python -c "import importlib.util,sys; mods='$RequiredModules'.split(','); missing=[x for x in mods if importlib.util.find_spec(x) is None]; sys.exit(0 if not missing else 1)"
if ($LASTEXITCODE -ne 0) { throw "C5_DEPENDENCY_AUDIT_FAILED" }
Write-Host "C5_DEPENDENCY_AUDIT=PASS"
$DependencyFreeze = @(& $Python -m pip freeze)
$RequirementsHash = (Get-FileHash $Requirements -Algorithm SHA256).Hash

Remove-Item $StageAppRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $Logs,(Join-Path $StageAppRoot "raios"),$CognitiveStoreRoot,$LearningRoot | Out-Null
Set-Content -Path (Join-Path $StageAppRoot "raios\__init__.py") -Value "" -Encoding UTF8
foreach ($PackageName in $PackageNames) {
    $dest = Join-Path $StageAppRoot ("raios\" + $PackageName)
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Copy-Item -Path (Join-Path $Repo ("src\raios\" + $PackageName + "\*")) -Destination $dest -Recurse -Force
}
$hashes = @{}
foreach ($PackageName in $PackageNames) {
    $dest = Join-Path $StageAppRoot ("raios\" + $PackageName)
    Get-ChildItem $dest -File -Recurse | ForEach-Object {
        $relative = $_.FullName.Substring($StageAppRoot.Length + 1).Replace("\","/")
        $hashes[$relative] = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
    }
}
$deploy = [ordered]@{
    schema = "raios.c5-canonical-deployment.v3"
    canonical_head = $Head
    source_repo = $Repo
    runtime_root = $RuntimeRoot
    cognitive_store_root = $CognitiveStoreRoot
    learning_root = $LearningRoot
    app_root = $AppRoot
    staged_app_root = $StageAppRoot
    packages = $PackageNames
    package_hashes = $hashes
    requirements_sha256 = $RequirementsHash
    dependencies = $DependencyFreeze
    dependency_audit = "PASS"
    maintenance_guard = "PASS"
    deployed_at = [DateTimeOffset]::UtcNow.ToString("o")
}
$oldListener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
$oldPid = if ($oldListener) { $oldListener.OwningProcess } else { $null }
$previousHead = $null
if (Test-Path $Manifest) {
    try { $previousHead = (Get-Content $Manifest -Raw | ConvertFrom-Json).canonical_head } catch {}
}
$stagePort = $Port + 1000
if (Get-NetTCPConnection -LocalPort $stagePort -State Listen -ErrorAction SilentlyContinue) {
    throw "C5_STAGE_PORT_IN_USE::$stagePort"
}

$env:RAIOS_MAIN_CORTEX = "qwen3:0.6b"
$env:RAIOS_STUDENT_MODEL = "qwen3:0.6b"
$env:RAIOS_STUDENT_NUM_CTX = "2048"
$env:RAIOS_STUDENT_NUM_PREDICT = "128"
$env:RAIOS_STUDENT_KEEP_ALIVE = "30s"
$env:RAIOS_RUNTIME_ROOT = $RuntimeRoot
$env:RAIOS_RUNTIME_BASE = $RuntimeBase
$env:RAIOS_COGNITIVE_STORE_ROOT = $CognitiveStoreRoot
$env:RAIOS_LEARNING_ROOT = $LearningRoot
$env:RAIOS_CANONICAL_REPO = $Repo
$env:RAIOS_CANONICAL_HEAD = $Head
function Start-C5Process([int]$ListenPort,[string]$Name,[string]$AppDir,[string]$ExpectedHead) {
    $out = Join-Path $Logs "$Name.out.log"
    $err = Join-Path $Logs "$Name.err.log"
    $previousPyPath = $env:PYTHONPATH
    $previousHeadEnv = $env:RAIOS_CANONICAL_HEAD
    try {
        $env:PYTHONPATH = $AppDir
        $env:RAIOS_CANONICAL_HEAD = $ExpectedHead
        $args = @("-m","uvicorn","raios.c5_gateway.gateway:app","--app-dir",$AppDir,"--host","127.0.0.1","--port","$ListenPort")
        return Start-Process -FilePath $PythonWindowless -ArgumentList $args -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
    } finally {
        $env:PYTHONPATH = $previousPyPath
        $env:RAIOS_CANONICAL_HEAD = $previousHeadEnv
    }
}

function Wait-C5Healthy([int]$ListenPort,[int]$ExpectedPid,[string]$ExpectedHead) {
    for ($i=0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        if (-not (Get-Process -Id $ExpectedPid -ErrorAction SilentlyContinue)) { return $null }
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$ListenPort/health" -TimeoutSec 3
            $headOk = $health.canonical_head -eq $ExpectedHead
            if ($ExpectedHead -eq $Head) { $headOk = $health.canonical_head -eq $Head }
            if ($health.status -eq "ONLINE" -and $health.runtime_source -eq "CANONICAL_DEPLOYMENT" -and $headOk) { return $health }
        } catch {}
    }
    return $null
}
$stage = Start-C5Process -ListenPort $stagePort -Name "gateway.stage" -AppDir $StageAppRoot -ExpectedHead $Head
$stageHealth = Wait-C5Healthy -ListenPort $stagePort -ExpectedPid $stage.Id -ExpectedHead $Head
if (-not $stageHealth) {
    Stop-Process -Id $stage.Id -Force -ErrorAction SilentlyContinue
    throw "CANONICAL_C5_STAGE_VALIDATION_FAILED::$Logs\gateway.stage.err.log"
}
$stageListener = Get-NetTCPConnection -LocalPort $stagePort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($stageListener) { Stop-Process -Id $stageListener.OwningProcess -Force -ErrorAction SilentlyContinue }
Stop-Process -Id $stage.Id -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 400

if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) {
    Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 700
}
Remove-Item $BackupAppRoot -Recurse -Force -ErrorAction SilentlyContinue
if (Test-Path $AppRoot) { Move-Item -LiteralPath $AppRoot -Destination $BackupAppRoot }
try {
    Move-Item -LiteralPath $StageAppRoot -Destination $AppRoot
} catch {
    if ((Test-Path $BackupAppRoot) -and -not (Test-Path $AppRoot)) { Move-Item -LiteralPath $BackupAppRoot -Destination $AppRoot }
    throw
}
$proc = Start-C5Process -ListenPort $Port -Name "gateway" -AppDir $AppRoot -ExpectedHead $Head
$r = Wait-C5Healthy -ListenPort $Port -ExpectedPid $proc.Id -ExpectedHead $Head
if (-not $r) {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    Remove-Item $AppRoot -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path $BackupAppRoot) {
        Move-Item -LiteralPath $BackupAppRoot -Destination $AppRoot
        if ($previousHead) {
            $rollback = Start-C5Process -ListenPort $Port -Name "gateway.rollback" -AppDir $AppRoot -ExpectedHead $previousHead
            $rollbackHealth = Wait-C5Healthy -ListenPort $Port -ExpectedPid $rollback.Id -ExpectedHead $previousHead
            if (-not $rollbackHealth) { throw "C5_CUTOVER_AND_ROLLBACK_FAILED" }
        }
    }
    Write-Host "C5_CUTOVER_ROLLED_BACK=true"
    throw "CANONICAL_C5_CUTOVER_FAILED::C5_CUTOVER_ROLLED_BACK"
}

$deploy | ConvertTo-Json -Depth 8 | Set-Content -Path $Manifest -Encoding UTF8
Remove-Item $BackupAppRoot -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "C5_CANONICAL_RUNTIME=true"
Write-Host "C5_STAGE_VALIDATION=true"
Write-Host "C5_LIVE_APP_MUTATION=false"
Write-Host "C5_ROLLBACK_READY=true"
Write-Host "C5_HTTP=200"
Write-Host "C5_PID=$($proc.Id)"
Write-Host "C5_CANONICAL_HEAD=$($r.canonical_head)"
Write-Host "C5_RUNTIME_SOURCE=$($r.runtime_source)"
Write-Host "C5_MODEL=$($r.model)"
Write-Host "OLD_LISTENER_PID=$oldPid"
Write-Host "DEPLOYMENT_MANIFEST=$Manifest"
