#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
# Fail-closed GL-004 atomic executor for Repair. Same children as the Python twin.
# Does not spawn or kill Next. Isolated build uses NODE_OPTIONS preload.

$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Repo

function Invoke-Child([string]$Name, [scriptblock]$Body) {
    $t0 = Get-Date
    $code = 2
    $out = ""
    try {
        $out = & $Body 2>&1 | Out-String
        if ($null -eq $LASTEXITCODE) { $code = 0 } else { $code = [int]$LASTEXITCODE }
    } catch {
        $code = 1
        $out = [string]$_
    }
    return [ordered]@{
        name = $Name
        exit = $code
        seconds = [math]::Round(((Get-Date) - $t0).TotalSeconds, 3)
        stdout_tail = if ($out.Length -gt 4000) { $out.Substring($out.Length - 4000) } else { $out }
    }
}

$bind = Invoke-Child "RUNTIME_TRACE" {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "gl004-runtime-bind.ps1")
}
$tc = Invoke-Child "TYPECHECK" { npm run type-check }
$env:GL004_ISOLATED_DIST = ".next-gl004-proof"
$env:NODE_ENV = "production"
$build = Invoke-Child "BUILD" { node (Join-Path $PSScriptRoot "gl004-isolated-build.cjs") }
$build["isolated_dist"] = ".next-gl004-proof"
$build["listened"] = $false
$canon = Invoke-Child "TEST_CANONICAL" { npx --no-install tsx tests/canonical_intelligence_check.ts }
$orch = Invoke-Child "TEST_TASK_ORCHESTRATION" { npx --no-install tsx tests/task_orchestration_check.ts }

$children = @($bind, $tc, $build, $canon, $orch)
$required = @("TYPECHECK", "BUILD", "TEST_CANONICAL", "TEST_TASK_ORCHESTRATION", "RUNTIME_TRACE")
$byName = @{}
foreach ($c in $children) { $byName[$c.name] = $c }
$codes = @()
foreach ($n in $required) {
    if (-not $byName.ContainsKey($n) -or $null -eq $byName[$n].exit) { $codes += 2 }
    else { $codes += [int]$byName[$n].exit }
}
$parent = 0
$nonzero = @($codes | Where-Object { $_ -ne 0 })
if ($nonzero.Count -gt 0) { $parent = ($nonzero | Measure-Object -Maximum).Maximum }
$proven = ($parent -eq 0)

$head = (git rev-parse HEAD).Trim()
$tag = "safety/pre-gl004-bind-" + (git rev-parse --short HEAD).Trim()
$existing = git tag --list $tag
if (-not $existing) { git tag $tag }

$receiptDir = Join-Path $Repo ".ai-os\receipts"
New-Item -ItemType Directory -Force -Path $receiptDir | Out-Null
$receiptPath = Join-Path $receiptDir "GL004-ATOMIC.json"
$payload = [ordered]@{
    schema = "raios.gl004-atomic.v1"
    HEAD = $head
    SAFETY_TAG = $tag
    children = $children
    PARENT_EXIT = $parent
    RECEIPT = $receiptPath
    GL004_PROVEN = $proven
    GL005_PROVEN = $false
}
$payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
$sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $receiptPath).Hash.ToLowerInvariant()

Write-Output "HEAD=$head"
Write-Output "SAFETY_TAG=$tag"
foreach ($c in $children) { Write-Output ("{0}_EXIT={1}" -f $c.name, $c.exit) }
Write-Output "PARENT_EXIT=$parent"
Write-Output "RECEIPT=$receiptPath"
Write-Output "RECEIPT_SHA256=$sha"
Write-Output "GL004_PROVEN=$($proven.ToString().ToLowerInvariant())"
Write-Output "GL005_PROVEN=false"
exit $parent
