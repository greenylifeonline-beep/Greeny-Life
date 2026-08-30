# GL-004 runtime binder for Repair (Windows). BIND_EXISTING_NE_SPAWN.
# Do not use param([int]$Pid) — $PID is an automatic variable in PowerShell.
# Do not write _raios-* proof forests. Do not spawn next. Do not kill listeners.

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($args -contains "--spawn" -or $args -contains "--start") {
    Write-Host "BIND_SPAWN_FORBIDDEN"
    exit 7
}

$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

$AllProcesses = @(Get-CimInstance Win32_Process)

function Get-ProcessById {
    param([int]$ProcessId)
    return $AllProcesses |
        Where-Object { $_.ProcessId -eq $ProcessId } |
        Select-Object -First 1
}

function Test-ProcessChainBelongsToRepo {
    param(
        [int]$ProcessId,
        [string]$RepoPath
    )

    $Seen = @{}
    $Current = $ProcessId

    for ($i = 0; $i -lt 10; $i++) {
        if ($Seen.ContainsKey($Current)) { break }
        $Seen[$Current] = $true

        $P = Get-ProcessById -ProcessId $Current
        if ($null -eq $P) { break }

        $Cmd = [string]$P.CommandLine
        if (
            $Cmd -and
            $Cmd.IndexOf($RepoPath, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -and
            $Cmd -match 'next'
        ) {
            return $true
        }

        if ($P.ParentProcessId -le 0) { break }
        $Current = [int]$P.ParentProcessId
    }

    return $false
}

$Listeners = @(
    Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.OwningProcess -gt 0 }
)

$Bound = $null
foreach ($L in $Listeners) {
    if (Test-ProcessChainBelongsToRepo -ProcessId ([int]$L.OwningProcess) -RepoPath $Repo) {
        $P = Get-ProcessById -ProcessId ([int]$L.OwningProcess)
        $Bound = [ordered]@{
            pid = [int]$L.OwningProcess
            ppid = if ($P) { [int]$P.ParentProcessId } else { $null }
            command = if ($P) { [string]$P.CommandLine } else { $null }
            address = [string]$L.LocalAddress
            port = [int]$L.LocalPort
        }
        break
    }
}

if ($null -eq $Bound) {
    Write-Host "RUNTIME_BOUND=FALSE"
    exit 106
}

Write-Host "RUNTIME_BOUND=TRUE"
Write-Host "RUNTIME_PID=$($Bound.pid)"
Write-Host "RUNTIME_PPID=$($Bound.ppid)"
Write-Host "RUNTIME_PORT=$($Bound.port)"
Write-Host "RUNTIME_COMMAND=$($Bound.command)"

try {
    $RootResponse = Invoke-WebRequest `
        -Uri "http://127.0.0.1:$($Bound.port)/" `
        -UseBasicParsing `
        -TimeoutSec 15
    $RootStatus = [int]$RootResponse.StatusCode
    $RootBody = [string]$RootResponse.Content
}
catch {
    Write-Host "ROOT_HTTP_ERROR=$($_.Exception.Message)"
    exit 108
}

$LooksNext = ($RootBody -match 'Next.js' -or $RootBody -match '/_next/')
Write-Host "ROOT_HTTP_STATUS=$RootStatus"
Write-Host "ROOT_LOOKS_NEXT=$LooksNext"

$ReceiptDir = Join-Path $Repo ".ai-os\receipts"
New-Item -ItemType Directory -Force $ReceiptDir | Out-Null
$ReceiptPath = Join-Path $ReceiptDir "GL004-RUNTIME-BIND.json"
$BindReceipt = [ordered]@{
    schema = "raios.gl004-runtime-bind.v1"
    ok = $false
    pid = $Bound.pid
    ppid = $Bound.ppid
    listen_port = $Bound.port
    port = $Bound.port
    cmdline = $Bound.command
    spawned = $false
    killed = $false
    http_root_status = $RootStatus
    looks_next = $LooksNext
}
if ($RootStatus -eq 200 -and $LooksNext) {
    $BindReceipt.ok = $true
    $BindReceipt.exit = 0
    [IO.File]::WriteAllText($ReceiptPath, ($BindReceipt | ConvertTo-Json -Depth 10), [Text.UTF8Encoding]::new($false))
    Write-Host "RUNTIME_CLASS=PROVEN_AS_DEV_LIVENESS"
    exit 0
}

Write-Host "RUNTIME_CLASS=HTTP_NOT_FRAMEWORK_LIVENESS"
exit 107
