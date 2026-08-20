#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
# GL-004 RUNTIME_TRACE binder for Repair (Windows). BIND_DONT_SPAWN. Never Start-Process next.

$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Repo

if ($args -contains "-Spawn" -or $args -contains "-Start") {
    Write-Output "SPAWN_REFUSED_BIND_EXISTING_NE_SPAWN"
    exit 7
}

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Get-Head { return (git rev-parse HEAD).Trim() }

$candidates = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.CommandLine -and (
            $_.CommandLine -match "next-server" -or
            $_.CommandLine -match "next dev" -or
            $_.CommandLine -match "next start" -or
            $_.CommandLine -match "next\.dev" -or
            ($_.Name -match "node" -and $_.CommandLine -match "\\next(\.cmd|\.exe)?")
        )
    }

$matched = @()
foreach ($proc in @($candidates)) {
    $cwd = $null
    try {
        $cwd = (Get-Process -Id $proc.ProcessId -ErrorAction Stop).Path
    } catch { }
    $listen = @()
    try {
        $listen = @(Get-NetTCPConnection -OwningProcess $proc.ProcessId -State Listen -ErrorAction SilentlyContinue)
    } catch { }
    if ($listen.Count -gt 0) {
        $matched += [pscustomobject]@{
            Pid = $proc.ProcessId
            Ppid = $proc.ParentProcessId
            Cmd = $proc.CommandLine
            Listen = $listen
            Creation = $proc.CreationDate
        }
    }
}

if ($matched.Count -lt 1) {
    Write-Output "NO_LIVE_NEXT_LISTENER_FOR_REPO"
    exit 2
}

$serverish = @($matched | Where-Object { $_.Cmd -match "next-server" })
$chosenSet = if ($serverish.Count -gt 0) { $serverish } else { $matched }
if ($chosenSet.Count -gt 1) {
    Write-Output "SECOND_RUNTIME_OR_AMBIGUOUS"
    exit 3
}
$chosen = $chosenSet[0]
$port = [int]$chosen.Listen[0].LocalPort

try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$port/" -UseBasicParsing -TimeoutSec 8
} catch {
    Write-Output "HTTP_IDENTITY_INVALID"
    Write-Output $_.Exception.Message
    exit 6
}
if ([int]$resp.StatusCode -ne 200) {
    Write-Output "HTTP_IDENTITY_INVALID status=$($resp.StatusCode)"
    exit 6
}
$powered = [string]$resp.Headers["X-Powered-By"]
$body = [string]$resp.Content
if ($powered -notmatch "Next" -and $body -notmatch "/_next/" -and $body -notmatch "Next.js") {
    Write-Output "HTTP_IDENTITY_INVALID no Next.js marker"
    exit 6
}

$mode = "unknown"
if ($chosen.Cmd -match "next dev") { $mode = "dev" }
elseif ($chosen.Cmd -match "next start") { $mode = "start" }

$receiptDir = Join-Path $Repo ".ai-os\receipts"
New-Item -ItemType Directory -Force -Path $receiptDir | Out-Null
$receiptPath = Join-Path $receiptDir "GL004-RUNTIME-BIND.json"
$payload = [ordered]@{
    schema = "raios.gl004-runtime-bind.v1"
    invariant = "LIVE_PROCESS_CAN_SATISFY_RUNTIME_PROOF_IF_IDENTITY_AND_HTTP_EVIDENCE_ARE_BOUND"
    ok = $true
    pid = $chosen.Pid
    ppid = $chosen.Ppid
    cmdline = $chosen.Cmd
    listen_port = $port
    mode = $mode
    http_root = [int]$resp.StatusCode
    head = Get-Head
    spawned = $false
    killed = $false
    platform = "windows"
}
$payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
$sha = Get-Sha256 $receiptPath

Write-Output "RUNTIME_TRACE_EXIT=0"
Write-Output "PID=$($chosen.Pid)"
Write-Output "PPID=$($chosen.Ppid)"
Write-Output "PORT=$port"
Write-Output "MODE=$mode"
Write-Output "HEAD=$(Get-Head)"
Write-Output "HTTP_ROOT=$($resp.StatusCode)"
Write-Output "RECEIPT=$receiptPath"
Write-Output "RECEIPT_SHA256=$sha"
Write-Output "SPAWNED=false"
Write-Output "GL004_PROVEN=false"
exit 0
