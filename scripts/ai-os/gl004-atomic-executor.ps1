#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
# Wave2 isolated proof for Repair. Same contract as gl004-atomic-executor.py.
# NEVER set NEXT_CONFIG_FILE. NEVER write next.config.*. NEVER create _raios-* proof forests.
# NEVER spawn or kill Next. Isolated compile: node scripts/ai-os/gl004-isolated-build.cjs

$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Repo
$ReceiptDir = Join-Path $Repo ".ai-os\receipts"
New-Item -ItemType Directory -Force -Path $ReceiptDir | Out-Null

function Invoke-Child([string]$Name, [scriptblock]$Body) {
    $t0 = Get-Date
    $code = 2
    $out = ""
    $epistemic = "FAILED"
    try {
        $out = & $Body 2>&1 | Out-String
        if ($null -eq $LASTEXITCODE) { $code = 0 } else { $code = [int]$LASTEXITCODE }
    } catch {
        $code = 1
        $out = [string]$_
    }
    if ($code -eq 0) { $epistemic = "PASS" }
    return [ordered]@{
        name = $Name
        exit = $code
        epistemic = $epistemic
        seconds = [math]::Round(((Get-Date) - $t0).TotalSeconds, 3)
        stdout_tail = if ($out.Length -gt 4000) { $out.Substring($out.Length - 4000) } else { $out }
    }
}

function Get-Parent([object[]]$Children, [string[]]$Required) {
    $by = @{}
    foreach ($c in $Children) { $by[$c.name] = $c }
    $codes = @()
    foreach ($n in $Required) {
        if (-not $by.ContainsKey($n) -or $null -eq $by[$n].exit) { $codes += 2 }
        else { $codes += [int]$by[$n].exit }
    }
    $nz = @($codes | Where-Object { $_ -ne 0 })
    if ($nz.Count -eq 0) { return 0 }
    return [int]($nz | Measure-Object -Maximum).Maximum
}

$bind = Invoke-Child "RUNTIME_TRACE" {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "gl004-runtime-bind.ps1")
}
$tc = Invoke-Child "TYPECHECK" { npm run type-check }
$canon = Invoke-Child "TEST_CANONICAL" { npx --no-install tsx tests/canonical_intelligence_check.ts }
$orch = Invoke-Child "TEST_TASK_ORCHESTRATION" { npx --no-install tsx tests/task_orchestration_check.ts }
$env:NODE_ENV = "production"
$Work = Join-Path $env:TEMP "gl004-isolated-build"
if (Test-Path $Work) {
    git worktree remove --force $Work 2>$null
    Remove-Item -LiteralPath $Work -Recurse -Force -ErrorAction SilentlyContinue
}
git worktree add --detach $Work HEAD
$nm = Join-Path $Work "node_modules"
if (Test-Path $nm) { Remove-Item -LiteralPath $nm -Force -ErrorAction SilentlyContinue }
cmd /c mklink /J "$nm" (Join-Path $Repo "node_modules") | Out-Null
$build = Invoke-Child "BUILD" {
    Push-Location $Work
    try { npx --no-install next build --webpack } finally { Pop-Location }
}
$build["isolation"] = "git_worktree_default_distDir"
$build["listened"] = $false
$build["worktree"] = $Work
$aios = Invoke-Child "AIOS_STATUS" { python .\scripts\ai-os\aios.py status }
$controlOk = (Test-Path ".\.ai-os\state\TASKS.json") -and (Test-Path ".\.ai-os\state\LOCKS.json") -and (Test-Path ".\.ai-os\handoffs")
$control = [ordered]@{ name = "GL005_CONTROL_PLANE"; exit = $(if ($controlOk) { 0 } else { 97 }); epistemic = $(if ($controlOk) { "PASS" } else { "UNAVAILABLE" }) }

$demoExit = 100
$apiStatus = $null
$apiHash = $null
$apiDetails = $null
$bodyPath = Join-Path $ReceiptDir "api-tasks-body.txt"
try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:3000/api/tasks" -UseBasicParsing -TimeoutSec 15
    $apiStatus = [int]$resp.StatusCode
    [IO.File]::WriteAllText($bodyPath, [string]$resp.Content, [Text.UTF8Encoding]::new($false))
} catch {
    if ($_.Exception.Response) {
        try { $apiStatus = [int]$_.Exception.Response.StatusCode.value__ } catch {}
        try {
            $reader = New-Object IO.StreamReader($_.Exception.Response.GetResponseStream())
            $content = $reader.ReadToEnd()
            [IO.File]::WriteAllText($bodyPath, $content, [Text.UTF8Encoding]::new($false))
        } catch {}
    }
}
if (Test-Path $bodyPath) {
    $apiHash = (Get-FileHash $bodyPath -Algorithm SHA256).Hash.ToLowerInvariant()
    try { $apiDetails = (Get-Content $bodyPath -Raw | ConvertFrom-Json).details } catch {}
}
if ($apiStatus -ge 200 -and $apiStatus -lt 300) { $demoExit = 0 } else { $demoExit = 99 }
$demo = [ordered]@{
    name = "GL005_ORCHESTRATION_DEMO"
    exit = $demoExit
    epistemic = $(if ($demoExit -eq 0) { "PASS" } else { "FAILED" })
    status = $apiStatus
    body_sha256 = $apiHash
    details = $apiDetails
}

$children = @($bind, $tc, $canon, $orch, $build, $aios, $control, $demo)
$gl004 = Get-Parent $children @("TYPECHECK","BUILD","TEST_CANONICAL","TEST_TASK_ORCHESTRATION","RUNTIME_TRACE")
$gl005 = Get-Parent $children @("AIOS_STATUS","GL005_CONTROL_PLANE","TEST_TASK_ORCHESTRATION","GL005_ORCHESTRATION_DEMO")
$combined = Get-Parent $children @("TYPECHECK","BUILD","TEST_CANONICAL","TEST_TASK_ORCHESTRATION","RUNTIME_TRACE","AIOS_STATUS","GL005_CONTROL_PLANE","GL005_ORCHESTRATION_DEMO")

$head = (git rev-parse HEAD).Trim()
$tag = "safety/pre-gl004-bind-" + (git rev-parse --short HEAD).Trim()
if (-not (git tag --list $tag)) { git tag $tag }

$receiptPath = Join-Path $ReceiptDir "GL004-ATOMIC.json"
$payload = [ordered]@{
    schema = "raios.wave2.isolated-proof.v1"
    HEAD = $head
    SAFETY_TAG = $tag
    children = $children
    GL004_PARENT_EXIT = $gl004
    GL005_PARENT_EXIT = $gl005
    PARENT_EXIT = $combined
    RECEIPT = $receiptPath
    GL004_PROVEN = ($gl004 -eq 0)
    GL005_PROVEN = ($gl005 -eq 0)
    rejected = @{
        NEXT_CONFIG_FILE = "not a Next 16 contract; would risk live .next"
        "_raios-wave2-proof-isolated" = "proof forest rejected; use .ai-os/receipts"
    }
}
$payload | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
$sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $receiptPath).Hash.ToLowerInvariant()

Write-Output "HEAD=$head"
Write-Output "SAFETY_TAG=$tag"
foreach ($c in $children) { Write-Output ("CHILD::{0}::{1}::{2}" -f $c.name, $c.exit, $c.epistemic) }
Write-Output "GL004_PARENT_EXIT=$gl004"
Write-Output "GL005_PARENT_EXIT=$gl005"
Write-Output "PARENT_EXIT=$combined"
Write-Output "RECEIPT=$receiptPath"
Write-Output "RECEIPT_SHA256=$sha"
Write-Output "GL004_PROVEN=$(($gl004 -eq 0).ToString().ToLowerInvariant())"
Write-Output "GL005_PROVEN=$(($gl005 -eq 0).ToString().ToLowerInvariant())"
exit $combined
