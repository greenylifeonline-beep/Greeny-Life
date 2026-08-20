# GL-004 / GL-005 atomic executor for Repair (Windows).
# Do NOT write ._raios-wave2-atomic-proof.ps1 or _raios-wave2-atomic-proof\ at repo root.
# Preferred: python .\scripts\ai-os\gl004-atomic-executor.py
# Native PowerShell path below is the same contract, not a forest bootstrap.

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Repo

$Head = (git rev-parse HEAD).Trim()
$Branch = (git branch --show-current).Trim()
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"

$ProofRoot = Join-Path $Repo ".ai-os\receipts"
New-Item -ItemType Directory -Force $ProofRoot | Out-Null
$Receipt = Join-Path $ProofRoot "GL004-ATOMIC.json"
$ApiBodyFile = Join-Path $ProofRoot "api-tasks-body.txt"
$BindSidecar = Join-Path $ProofRoot "GL004-RUNTIME-BIND.json"

$ProductPaths = @(
    "app", "lib", "tests", "prisma", "canonical",
    "package.json", "package-lock.json", "tsconfig.json",
    "next.config.ts", "next.config.js", "next.config.mjs",
    "next-env.d.ts", "scripts\ai-os"
)

function Test-ProductScopedDirty {
    foreach ($Rel in $ProductPaths) {
        $Full = Join-Path $Repo $Rel
        if (-not (Test-Path $Full)) { continue }
        git diff --quiet -- $Rel
        if ($LASTEXITCODE -ne 0) { return $true }
        git diff --cached --quiet -- $Rel
        if ($LASTEXITCODE -ne 0) { return $true }
    }
    return $false
}

$Children = [ordered]@{}

function Run-Child {
    param(
        [string]$Name,
        [scriptblock]$Action
    )
    Write-Host ""
    Write-Host "RUN=$Name"
    try {
        & $Action
        $Code = $LASTEXITCODE
        if ($null -eq $Code) { $Code = 0 }
    }
    catch {
        Write-Host "CHILD_EXCEPTION::$Name::$($_.Exception.Message)"
        $Code = 90
    }
    $Children[$Name] = [int]$Code
    Write-Host "CHILD::$Name::$Code"
}

Write-Host "############################################################"
Write-Host "# RAIOS WAVE2 ATOMIC PROOF (Repair native)"
Write-Host "############################################################"
Write-Host "REPOSITORY=$Repo"
Write-Host "BRANCH=$Branch"
Write-Host "HEAD=$Head"
Write-Host "RECEIPT_PATH=$Receipt"

Run-Child "TYPECHECK" { & npm run type-check }

if (Test-Path ".\tests\canonical_intelligence_check.ts") {
    Run-Child "TEST_CANONICAL" { & npx tsx ".\tests\canonical_intelligence_check.ts" }
} else {
    $Children.TEST_CANONICAL = 91
    Write-Host "CHILD::TEST_CANONICAL::91"
}

if (Test-Path ".\tests\task_orchestration_check.ts") {
    Run-Child "TEST_TASK_ORCHESTRATION" { & npx tsx ".\tests\task_orchestration_check.ts" }
} else {
    $Children.TEST_TASK_ORCHESTRATION = 92
    Write-Host "CHILD::TEST_TASK_ORCHESTRATION::92"
}

$TrackedDirty = Test-ProductScopedDirty
$BuildWT = Join-Path $env:TEMP "gl004-isolated-build"

if ($TrackedDirty) {
    $Children.BUILD = 102
    Write-Host "BUILD_STATE=BLOCKED"
    Write-Host "BUILD_REASON=PRODUCT_SCOPED_WORKTREE_DIFFERS_FROM_HEAD"
    Write-Host "CHILD::BUILD::102"
} else {
    if (Test-Path $BuildWT) {
        git worktree remove --force $BuildWT 2>$null
        Remove-Item -LiteralPath $BuildWT -Recurse -Force -ErrorAction SilentlyContinue
    }
    git worktree add --detach $BuildWT $Head
    if ($LASTEXITCODE -ne 0) {
        $Children.BUILD = 103
        Write-Host "CHILD::BUILD::103"
    } else {
        $MainNodeModules = Join-Path $Repo "node_modules"
        $BuildNodeModules = Join-Path $BuildWT "node_modules"
        if (!(Test-Path $MainNodeModules)) {
            $Children.BUILD = 104
            Write-Host "CHILD::BUILD::104"
        } else {
            if (!(Test-Path $BuildNodeModules)) {
                cmd /c "mklink /J `"$BuildNodeModules`" `"$MainNodeModules`"" | Out-Null
            }
            Push-Location $BuildWT
            try {
                Write-Host "BUILD_CMD=npx next build --webpack"
                & npx next build --webpack
                $Children.BUILD = [int]$LASTEXITCODE
            }
            catch {
                $Children.BUILD = 105
                Write-Host "BUILD_EXCEPTION=$($_.Exception.Message)"
            }
            finally {
                Pop-Location
            }
            Write-Host "CHILD::BUILD::$($Children.BUILD)"
        }
    }
}

# Bind live Next — no spawn, no kill. Invoke the binder (uses -ProcessId, not $PID).
Write-Host ""
Write-Host "RUN=RUNTIME_TRACE"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "gl004-runtime-bind.ps1")
$Children.RUNTIME_TRACE = [int]$LASTEXITCODE
Write-Host "CHILD::RUNTIME_TRACE::$($Children.RUNTIME_TRACE)"

$Bound = $null
if (Test-Path $BindSidecar) {
    try {
        $Bound = Get-Content -LiteralPath $BindSidecar -Raw | ConvertFrom-Json
    } catch {}
}

if (Test-Path ".\scripts\ai-os\aios.py") {
    Run-Child "AIOS_STATUS" { & python ".\scripts\ai-os\aios.py" status }
} else {
    $Children.AIOS_STATUS = 109
}

$TasksExists = Test-Path ".\.ai-os\state\TASKS.json"
$LocksExists = Test-Path ".\.ai-os\state\LOCKS.json"
$HandoffsExists = Test-Path ".\.ai-os\handoffs"
if ($TasksExists -and $LocksExists -and $HandoffsExists) {
    $Children.GL005_CONTROL_PLANE = 0
} else {
    $Children.GL005_CONTROL_PLANE = 110
}
Write-Host "CHILD::GL005_CONTROL_PLANE::$($Children.GL005_CONTROL_PLANE)"

$ApiStatus = $null
$ApiError = $null
$ApiBodyHash = $null
$Port = 3000
if ($Bound -and $Bound.port) { $Port = [int]$Bound.port }

try {
    $Response = Invoke-WebRequest `
        -Uri "http://127.0.0.1:$Port/api/tasks" `
        -UseBasicParsing `
        -TimeoutSec 15
    $ApiStatus = [int]$Response.StatusCode
    [IO.File]::WriteAllText($ApiBodyFile, [string]$Response.Content, [Text.UTF8Encoding]::new($false))
    $ApiBodyHash = (Get-FileHash -LiteralPath $ApiBodyFile -Algorithm SHA256).Hash.ToLower()
    if ($ApiStatus -ge 200 -and $ApiStatus -lt 300) {
        $Children.GL005_API_TASKS = 0
    } else {
        $Children.GL005_API_TASKS = 112
    }
}
catch {
    $ApiError = $_.Exception.Message
    try { $ApiStatus = [int]$_.Exception.Response.StatusCode.value__ } catch {}
    try {
        if ($_.ErrorDetails.Message) {
            [IO.File]::WriteAllText($ApiBodyFile, [string]$_.ErrorDetails.Message, [Text.UTF8Encoding]::new($false))
            $ApiBodyHash = (Get-FileHash -LiteralPath $ApiBodyFile -Algorithm SHA256).Hash.ToLower()
        }
    } catch {}
    $Children.GL005_API_TASKS = 113
}
Write-Host "API_TASKS_STATUS=$ApiStatus"
Write-Host "API_TASKS_ERROR=$ApiError"
Write-Host "API_TASKS_BODY_SHA256=$ApiBodyHash"
Write-Host "CHILD::GL005_API_TASKS::$($Children.GL005_API_TASKS)"

# Live path ≠ orchestration demo. Keep demo fail-closed until a live OrchestrationTask exists.
$GL005LivePath =
    $Children.AIOS_STATUS -eq 0 -and
    $Children.GL005_CONTROL_PLANE -eq 0 -and
    $Children.TEST_TASK_ORCHESTRATION -eq 0 -and
    $Children.GL005_API_TASKS -eq 0

$Children.GL005_ORCHESTRATION_DEMO = 114
Write-Host "CHILD::GL005_ORCHESTRATION_DEMO::114"
Write-Host "GL005_LIVE_PATH_PROVEN=$GL005LivePath"

$GL004 =
    $Children.TYPECHECK -eq 0 -and
    $Children.BUILD -eq 0 -and
    $Children.TEST_CANONICAL -eq 0 -and
    $Children.TEST_TASK_ORCHESTRATION -eq 0 -and
    $Children.RUNTIME_TRACE -eq 0

$GL005 = $false

$RequiredNames = @(
    "TYPECHECK", "BUILD", "TEST_CANONICAL", "TEST_TASK_ORCHESTRATION",
    "RUNTIME_TRACE", "AIOS_STATUS", "GL005_CONTROL_PLANE",
    "GL005_API_TASKS", "GL005_ORCHESTRATION_DEMO"
)
$FailureCodes = @()
foreach ($Name in $RequiredNames) {
    if (!$Children.Contains($Name)) { $FailureCodes += 120; continue }
    if ([int]$Children[$Name] -ne 0) { $FailureCodes += [int]$Children[$Name] }
}
$ParentExit = if ($FailureCodes.Count -eq 0) { 0 } else { [int]($FailureCodes | Measure-Object -Maximum).Maximum }

$Proof = [ordered]@{
    schema = "raios.wave2.atomic-proof.v2"
    repository = [ordered]@{ root = $Repo; branch = $Branch; head = $Head }
    children = $Children
    runtime = $Bound
    orchestration_http = [ordered]@{
        status = $ApiStatus
        body_sha256 = $ApiBodyHash
        error = $ApiError
    }
    verdict = [ordered]@{
        gl004_proven = $GL004
        gl005_live_path_proven = $GL005LivePath
        gl005_proven = $GL005
        parent_exit = $ParentExit
    }
    laws_observed = @(
        "BIND_EXISTING_NE_SPAWN",
        "NOT_RUN_NE_FAILED",
        "LIVENESS_NE_READINESS_NE_CORRECTNESS",
        "PARENT_SUCCESS_REQUIRES_ALL_REQUIRED_CHILDREN_SUCCESS",
        "SUPPORTING_TEST_NE_ORCHESTRATION_DEMONSTRATION",
        "PROOF_FOREST_NE_RECEIPT"
    )
    safety = [ordered]@{
        new_server_spawned = $false
        existing_server_killed = $false
        second_wal_created = $false
        second_bus_created = $false
        census_created = $false
        canonical_promotion = $false
        proof_forest_created = $false
    }
    created_at = (Get-Date).ToUniversalTime().ToString("o")
}

[IO.File]::WriteAllText($Receipt, ($Proof | ConvertTo-Json -Depth 30), [Text.UTF8Encoding]::new($false))
$ReceiptHash = (Get-FileHash -LiteralPath $Receipt -Algorithm SHA256).Hash.ToLower()

if (Test-Path $BuildWT) {
    git worktree remove --force $BuildWT 2>$null
    if (Test-Path $BuildWT) {
        Remove-Item -LiteralPath $BuildWT -Recurse -Force -ErrorAction SilentlyContinue
    }
}
git worktree prune

Write-Host ""
Write-Host "############################################################"
Write-Host "# ATOMIC RESULT"
Write-Host "############################################################"
foreach ($Name in $Children.Keys) {
    Write-Host "CHILD::$Name::$($Children[$Name])"
}
Write-Host "GL004_PROVEN=$($GL004.ToString().ToUpper())"
Write-Host "GL005_LIVE_PATH_PROVEN=$($GL005LivePath.ToString().ToUpper())"
Write-Host "GL005_PROVEN=FALSE"
Write-Host "PARENT_EXIT=$ParentExit"
Write-Host "RECEIPT=$Receipt"
Write-Host "RECEIPT_SHA256=$ReceiptHash"
Write-Host "SERVER_KILLED=FALSE"
Write-Host "SECOND_SERVER_STARTED=FALSE"
if ($ParentExit -eq 0) {
    Write-Host "STATUS=ATOMIC_PROOF_PASS"
} else {
    Write-Host "STATUS=ATOMIC_PROOF_NOT_PROVEN"
}
Write-Host "############################################################"
exit $ParentExit
