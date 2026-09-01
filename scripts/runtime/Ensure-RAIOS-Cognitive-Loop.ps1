param(
    [string]$Repo = $(if ($env:RAIOS_CANONICAL_REPO) { $env:RAIOS_CANONICAL_REPO } else { (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path })
)
$ErrorActionPreference = "Stop"
$env:RAIOS_CANONICAL_REPO = $Repo
$Python = Join-Path $env:USERPROFILE ".raios\runtime\c5\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) { throw "C5_PYTHON_MISSING::$Python" }
$Head = (git -C $Repo rev-parse HEAD).Trim()
$StatusRoot = Join-Path $env:USERPROFILE ".raios\runtime\cognitive-loop"
$StatusPath = Join-Path $StatusRoot "ensure-status.json"
New-Item -ItemType Directory -Force -Path $StatusRoot | Out-Null

function Get-C5Health {
    try { return Invoke-RestMethod -Uri "http://127.0.0.1:8766/health" -TimeoutSec 5 }
    catch { return $null }
}
function Get-LoopStatus {
    try { return Invoke-RestMethod -Uri "http://127.0.0.1:8766/v1/cognitive/status" -TimeoutSec 5 }
    catch { return $null }
}
function Write-AtomicJson([hashtable]$Value) {
    $Value["generated_at"] = [DateTimeOffset]::UtcNow.ToString("o")
    $tmp = Join-Path $StatusRoot ("ensure-status.json.tmp-" + [guid]::NewGuid().ToString("N"))
    try {
        $Value | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $tmp -Encoding UTF8
        Get-Content -LiteralPath $tmp -Raw | ConvertFrom-Json | Out-Null
        for ($i=0; $i -lt 5; $i++) {
            try { Move-Item -LiteralPath $tmp -Destination $StatusPath -Force; return }
            catch [System.UnauthorizedAccessException] {
                if ($i -eq 4) { throw }
                Start-Sleep -Milliseconds (25 * ($i + 1))
            }
        }
    } finally { Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue }
}

$actions = [System.Collections.Generic.List[string]]::new()
$health = Get-C5Health
$environment = if ($health) { $health.environment } else { $null }
$needsDeploy = (
    -not $health -or
    $health.status -ne "ONLINE" -or
    $health.canonical_head -ne $Head -or
    -not $environment -or
    $environment.dependency_audit -ne "PASS" -or
    $environment.pytest_available -ne $true
)
if ($needsDeploy) {
    & (Join-Path $PSScriptRoot "Deploy-RAIOS-C5.ps1")
    $actions.Add("DEPLOY_EXISTING_C5")
    $health = Get-C5Health
    if (-not $health -or $health.status -ne "ONLINE") { throw "C5_RESTORE_FAILED" }
}

$loop = Get-LoopStatus
$managerAlive = $loop -and $loop.manager.alive -eq $true
if (-not $managerAlive) {
    $mgrPy = Join-Path $Repo "src\raios\manager\live_manager.py"
    $matching = @(
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -match "^python" -and
            $_.CommandLine -like ("*" + $mgrPy + "*") -and
            $_.CommandLine -match "--daemon"
        }
    )
    foreach ($process in $matching) {
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
        $actions.Add("STOP_STALE_MANAGER_PID_" + $process.ProcessId)
    }
    $env:PYTHONPATH = Join-Path $Repo "src"
    $managerRoot = Join-Path $env:USERPROFILE ".raios\runtime\manager"
    New-Item -ItemType Directory -Force -Path $managerRoot | Out-Null
    Start-Process -FilePath $Python -ArgumentList @($mgrPy, "--daemon", "--no-task-write") -WindowStyle Hidden -WorkingDirectory $Repo -RedirectStandardOutput (Join-Path $managerRoot "daemon.out.log") -RedirectStandardError (Join-Path $managerRoot "daemon.err.log") | Out-Null
    $actions.Add("START_EXISTING_MANAGER")
    for ($i=0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 1
        $loop = Get-LoopStatus
        if ($loop -and $loop.manager.alive -eq $true) { break }
    }
}
$loop = Get-LoopStatus
$closed = $health -and $health.status -eq "ONLINE" -and $loop -and $loop.manager.alive -eq $true
Write-AtomicJson @{
    schema = "raios.cognitive-loop.ensure.v2"
    status = $(if ($closed) { "ONLINE" } else { "DEGRADED" })
    canonical_head = $Head
    c5 = $(if ($health) { $health.status } else { "OFFLINE" })
    dependency_audit = $(if ($health) { $health.environment.dependency_audit } else { "UNPROVEN" })
    pytest_available = $(if ($health) { $health.environment.pytest_available } else { $false })
    manager = $(if ($loop) { $loop.manager } else { @{ alive = $false; reason = "STATUS_UNAVAILABLE" } })
    actions = @($actions)
    second_runtime = $false
}
if (-not $closed) { throw "COGNITIVE_LOOP_NOT_CLOSED" }
Write-Host "RAIOS_COGNITIVE_LOOP=ONLINE"
Write-Host ("ACTIONS=" + (@($actions) -join ","))
