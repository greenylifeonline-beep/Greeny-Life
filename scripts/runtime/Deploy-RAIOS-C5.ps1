param(
    [string]$RuntimeRoot = $(Join-Path ([Environment]::GetFolderPath("UserProfile")) ".raios\runtime\c5"),
    [int]$Port = 8766,
    [string]$Repo = $(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
)
$ErrorActionPreference = "Stop"
$StableUserProfile = [Environment]::GetFolderPath("UserProfile")
$Repo = (Resolve-Path $Repo).Path
$Head = (git -C $Repo rev-parse HEAD).Trim()
$AppRoot = Join-Path $RuntimeRoot "app"
$Venv = Join-Path $RuntimeRoot ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"
$PythonWindowless = Join-Path $Venv "Scripts\pythonw.exe"
$Logs = Join-Path $RuntimeRoot "logs"
$Manifest = Join-Path $RuntimeRoot "deployment.json"
$CognitiveStoreRoot = Join-Path $StableUserProfile ".raios\runtime\cognitive-store\v9"
$LearningRoot = Join-Path $CognitiveStoreRoot "learning"
$Requirements = Join-Path $Repo "requirements-c5.txt"
$PackageNames = @("c5_gateway","search_cortex","neuro_lingua")

New-Item -ItemType Directory -Force -Path $Logs,(Join-Path $AppRoot "raios"),$CognitiveStoreRoot,$LearningRoot | Out-Null
$Init = Join-Path $AppRoot "raios\__init__.py"
if (-not (Test-Path $Init)) { Set-Content -Path $Init -Value "" -Encoding UTF8 }
foreach ($PackageName in $PackageNames) {
    $PackageDest = Join-Path $AppRoot ("raios\" + $PackageName)
    New-Item -ItemType Directory -Force -Path $PackageDest | Out-Null
    Copy-Item -Path (Join-Path $Repo ("src\raios\" + $PackageName + "\*")) -Destination $PackageDest -Recurse -Force
}

if (-not (Test-Path $Python)) {
    & py -3.14 -m venv $Venv
}
if (-not (Test-Path $Requirements)) {
    throw "C5_REQUIREMENTS_MISSING::$Requirements"
}
if (-not (Test-Path $PythonWindowless)) {
    throw "C5_PYTHONW_MISSING::$PythonWindowless"
}
$RequiredModules = "fastapi,uvicorn,pydantic,httpx,yaml,orjson,rapidfuzz,langcodes,language_data,ddgs,pytest,pytest_asyncio,hypothesis"
$MissingModules = (& $Python -c "import importlib.util; mods='$RequiredModules'.split(','); print(','.join(x for x in mods if importlib.util.find_spec(x) is None))").Trim()
if ($MissingModules) {
    Write-Host "INSTALL C5 missing modules: $MissingModules"
    & $Python -m pip install --disable-pip-version-check -r $Requirements
    if ($LASTEXITCODE -ne 0) { throw "C5_DEPENDENCY_INSTALL_FAILED" }
}
& $Python -c "import importlib.util,sys; mods='$RequiredModules'.split(','); missing=[x for x in mods if importlib.util.find_spec(x) is None]; print('C5_DEPENDENCY_AUDIT=' + ('PASS' if not missing else 'FAIL:' + ','.join(missing))); sys.exit(0 if not missing else 1)"
if ($LASTEXITCODE -ne 0) { throw "C5_DEPENDENCY_AUDIT_FAILED" }
$DependencyFreeze = @(& $Python -m pip freeze)
$RequirementsHash = (Get-FileHash $Requirements -Algorithm SHA256).Hash

$hashes = @{}
foreach ($PackageName in $PackageNames) {
    $PackageDest = Join-Path $AppRoot ("raios\" + $PackageName)
    Get-ChildItem $PackageDest -File -Recurse | ForEach-Object {
        $relative = $_.FullName.Substring($AppRoot.Length + 1).Replace("\","/")
        $hashes[$relative] = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
    }
}
$deploy = [ordered]@{
    schema = "raios.c5-canonical-deployment.v2"
    canonical_head = $Head
    source_repo = $Repo
    runtime_root = $RuntimeRoot
    cognitive_store_root = $CognitiveStoreRoot
    learning_root = $LearningRoot
    app_root = $AppRoot
    packages = $PackageNames
    package_hashes = $hashes
    requirements_file = $Requirements
    requirements_sha256 = $RequirementsHash
    dependency_audit = "PASS"
    dependencies = $DependencyFreeze
    pytest_available = [bool]($DependencyFreeze | Where-Object { $_ -match "^pytest==" })
    deployed_at = [DateTimeOffset]::UtcNow.ToString("o")
}
$deploy | ConvertTo-Json -Depth 8 | Set-Content -Path $Manifest -Encoding UTF8

$old = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
$oldPid = if ($old) { $old.OwningProcess } else { $null }
$stagePort = $Port + 1000
if (Get-NetTCPConnection -LocalPort $stagePort -State Listen -ErrorAction SilentlyContinue) {
    throw "C5_STAGE_PORT_IN_USE::$stagePort"
}

$env:RAIOS_MAIN_CORTEX = "qwen3:0.6b"
$env:RAIOS_STUDENT_MODEL = "qwen3:0.6b"
$env:RAIOS_STUDENT_NUM_CTX = "2048"
$env:RAIOS_STUDENT_KEEP_ALIVE = "2m"
$env:RAIOS_RUNTIME_ROOT = $RuntimeRoot
$env:RAIOS_COGNITIVE_STORE_ROOT = $CognitiveStoreRoot
$env:RAIOS_LEARNING_ROOT = $LearningRoot
$env:RAIOS_CANONICAL_REPO = $Repo
$env:RAIOS_CANONICAL_HEAD = $Head
$env:PYTHONPATH = $AppRoot

function Start-C5Process([int]$ListenPort,[string]$Name) {
    $out = Join-Path $Logs "$Name.out.log"
    $err = Join-Path $Logs "$Name.err.log"
    $args = @(
        "-m","uvicorn",
        "raios.c5_gateway.gateway:app",
        "--app-dir",$AppRoot,
        "--host","127.0.0.1",
        "--port","$ListenPort"
    )
    return Start-Process -FilePath $PythonWindowless -ArgumentList $args -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
}

function Wait-C5Healthy([int]$ListenPort,[int]$ExpectedPid) {
    for ($i=0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        if (-not (Get-Process -Id $ExpectedPid -ErrorAction SilentlyContinue)) { return $null }
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$ListenPort/health" -TimeoutSec 3
            if ($health.status -eq "ONLINE" -and $health.runtime_source -eq "CANONICAL_DEPLOYMENT" -and $health.canonical_head -eq $Head) {
                return $health
            }
        } catch {}
    }
    return $null
}

$stage = Start-C5Process -ListenPort $stagePort -Name "gateway.stage"
$stageHealth = Wait-C5Healthy -ListenPort $stagePort -ExpectedPid $stage.Id
if (-not $stageHealth) {
    Stop-Process -Id $stage.Id -Force -ErrorAction SilentlyContinue
    throw "CANONICAL_C5_STAGE_VALIDATION_FAILED::$Logs\gateway.stage.err.log"
}
Stop-Process -Id $stage.Id -Force -ErrorAction Stop
Start-Sleep -Milliseconds 500

if ($oldPid) {
    Stop-Process -Id $oldPid -Force -ErrorAction Stop
    Start-Sleep -Milliseconds 500
}

$proc = Start-C5Process -ListenPort $Port -Name "gateway"
$r = Wait-C5Healthy -ListenPort $Port -ExpectedPid $proc.Id
if (-not $r) {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    throw "CANONICAL_C5_CUTOVER_FAILED::$Logs\gateway.err.log"
}

Write-Host "C5_CANONICAL_RUNTIME=true"
Write-Host "C5_STAGE_VALIDATION=true"
Write-Host "C5_HTTP=200"
Write-Host "C5_PID=$($proc.Id)"
Write-Host "C5_CANONICAL_HEAD=$($r.canonical_head)"
Write-Host "C5_RUNTIME_SOURCE=$($r.runtime_source)"
Write-Host "C5_MODEL=$($r.model)"
Write-Host "OLD_LISTENER_PID=$oldPid"
Write-Host "DEPLOYMENT_MANIFEST=$Manifest"
