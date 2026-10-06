param(
    [int]$Port = 8788,
    [switch]$NoRecover,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"
function Test-RaiosTcp([int]$ListenPort, [int]$TimeoutMs = 800) {
    try {
        $client = [Net.Sockets.TcpClient]::new()
        $pending = $client.BeginConnect("127.0.0.1", $ListenPort, $null, $null)
        $ok = $pending.AsyncWaitHandle.WaitOne($TimeoutMs) -and $client.Connected
        $client.Close()
        return [bool]$ok
    } catch { return $false }
}
function Get-RaiosListenPid([int]$ListenPort) {
    foreach ($line in (& netstat -ano -p tcp 2>$null)) {
        $parts = @($line.ToString().Trim() -split '\s+')
        if ($parts.Length -lt 5) { continue }
        if ($parts[-2] -ne 'LISTENING') { continue }
        if ($parts[1] -match (":$ListenPort$")) { return [int]$parts[-1] }
    }
    return $null
}
function Get-RaiosMcpHealth([string]$Url, [int]$TimeoutSec = 2) {
    try {
        return Invoke-RestMethod $Url -TimeoutSec $TimeoutSec
    } catch {
        return $null
    }
}
function Test-RaiosMcpToolContract($Health) {
    $tools = @($Health.tools)
    foreach ($banned in @("shell", "bash", "run_command", "run_sandboxed_command", "execute_scoped_task")) {
        if ($tools -contains $banned) { return $false }
    }
    foreach ($core in @("get_head", "read_board", "read_inbox", "read_receipt", "get_diff", "post_opinion", "send_packet", "ack_packet")) {
        if ($tools -notcontains $core) { return $false }
    }
    return ($tools.Count -eq 8 -and [int]$Health.tool_count -eq 8 -and $Health.second_gateway -ne $true)
}
function Test-RaiosMcpHealthy($Health) {
    if (-not $Health) { return $false }
    if ($Health.ok -ne $true) { return $false }
    if ($env:RAIOS_CANONICAL_HEAD -notmatch "^[0-9a-fA-F]{40}$") { return $false }
    if ($Health.head -ne $env:RAIOS_CANONICAL_HEAD -or $Health.head_source -ne "git-file") { return $false }
    return Test-RaiosMcpToolContract $Health
}
function Test-RaiosMcpIdentity($Health) {
    if (-not $Health -or $Health.ok -ne $true) { return $false }
    if ([string]$Health.service -ne "raios-universal-mcp") { return $false }
    if ($Health.second_gateway -eq $true) { return $false }
    return Test-RaiosMcpToolContract $Health
}
function Read-RaiosOwnerManifest {
    if (-not (Test-Path -LiteralPath $OwnerManifest)) { return $null }
    try { return Get-Content -LiteralPath $OwnerManifest -Raw | ConvertFrom-Json } catch { return $null }
}
function Test-RaiosOwnerManifest($Owner, [int]$ProcId, [int]$ListenPort) {
    if ($null -eq $Owner) { return $false }
    if ([int]$Owner.pid -ne $ProcId -or [int]$Owner.port -ne $ListenPort) { return $false }
    if ([string]$Owner.repo -ne [IO.Path]::GetFullPath($Repo)) { return $false }
    if ([string]$Owner.server -ne [IO.Path]::GetFullPath($Server)) { return $false }
    return $true
}
function Write-RaiosOwnerManifest([int]$ProcId, [string]$Generation) {
    New-Item -ItemType Directory -Force -Path $OwnerDir | Out-Null
    $doc = [ordered]@{
        schema = "raios.universal-mcp-owner.v1"; pid = $ProcId; port = $Port
        repo = [IO.Path]::GetFullPath($Repo); server = [IO.Path]::GetFullPath($Server)
        python = [IO.Path]::GetFullPath($Python); canonical_head = $env:RAIOS_CANONICAL_HEAD
        generation = $Generation; written_at = [DateTimeOffset]::UtcNow.ToString("o")
    }
    $tmp = "$OwnerManifest.tmp.$PID"
    [IO.File]::WriteAllText($tmp, (($doc | ConvertTo-Json -Depth 4) + [Environment]::NewLine), [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tmp -Destination $OwnerManifest -Force
}
function Get-RaiosProcessInfo([int]$ProcId) {
    try { return Get-CimInstance Win32_Process -Filter "ProcessId=$ProcId" -OperationTimeoutSec 8 } catch { return $null }
}
function Test-RaiosOurMcp([object]$Info, [int]$ProcId, [int]$ListenPort, $Health = $null) {
    $owner = Read-RaiosOwnerManifest
    if (Test-RaiosOwnerManifest $owner $ProcId $ListenPort) { return $true }
    if ($null -ne $Info -and $ListenPort -eq 8788) {
        $cmd = [string]$Info.CommandLine
        $expected = [IO.Path]::GetFullPath($Server)
        if (($cmd.IndexOf($expected, [StringComparison]::OrdinalIgnoreCase) -ge 0) -and ($cmd -match '--port\s+8788(?:\s|$)')) {
            Write-RaiosOwnerManifest $ProcId "CIM_ADOPTED"
            return $true
        }
    }
    if ($ListenPort -eq 8788 -and (Test-RaiosMcpIdentity $Health)) {
        try {
            $proc = Get-Process -Id $ProcId -ErrorAction Stop
            if ($proc.ProcessName -in @("python", "pythonw")) {
                Write-RaiosOwnerManifest $ProcId "LEGACY_HEALTH_ADOPTED"
                return $true
            }
        } catch {}
    }
    return $false
}
function Stop-RaiosListenPid([int]$ProcId) {
    Stop-Process -Id $ProcId -Force -ErrorAction Stop
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 250
        if (-not (Get-Process -Id $ProcId -ErrorAction SilentlyContinue)) { return }
    }
    throw "RAIOS_MCP_PROCESS_DID_NOT_STOP::$ProcId"
}

$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$PythonCandidates = @(
    (Join-Path $env:USERPROFILE ".raios\runtime\c5\.venv\Scripts\python.exe"),
    (Join-Path $Repo ".venv\Scripts\python.exe")
)
$Python = $PythonCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$Server = Join-Path $Repo "scripts\ai-os\raios_mcp\server.py"
$ReceiptDir = Join-Path $Repo ".ai-os\receipts\command-fabric"
$OwnerDir = Join-Path $env:USERPROFILE ".raios\runtime\mcp"
$OwnerManifest = Join-Path $OwnerDir "universal-mcp-owner.json"
$HealthUrl = "http://127.0.0.1:$Port/health"

if ($Port -ne 8788) { throw "MCP_CENSUS_PORT_IS_8788 refused port=$Port (no second gateway)" }
if (-not (Test-Path $Python)) { throw "Missing Python: $Python" }
if (-not (Test-Path $Server)) { throw "Missing MCP server: $Server" }
New-Item -ItemType Directory -Force -Path $ReceiptDir | Out-Null

$env:RAIOS_CANONICAL_HEAD = ""
$GitDir = Join-Path $Repo ".git"
$raw = (Get-Content -LiteralPath (Join-Path $GitDir "HEAD") -TotalCount 1 -ErrorAction Stop).Trim()
if ($raw -match '^ref:\s*(refs/[A-Za-z0-9_./-]+)$') {
    $ref = $Matches[1]
    if (@($ref -split '/') -contains '..') { throw "INVALID_CANONICAL_REF" }
    $refPath = Join-Path $GitDir ($ref -replace '/', '\')
    if (Test-Path -LiteralPath $refPath) {
        $env:RAIOS_CANONICAL_HEAD = (Get-Content -LiteralPath $refPath -TotalCount 1 -ErrorAction Stop).Trim()
    } else {
        foreach ($line in (Get-Content -LiteralPath (Join-Path $GitDir "packed-refs") -ErrorAction Stop)) {
            if ($line -match '^([0-9a-fA-F]{40}) (.+)$' -and $Matches[2] -eq $ref) {
                $env:RAIOS_CANONICAL_HEAD = $Matches[1]
                break
            }
        }
    }
} elseif ($raw -match '^[0-9a-fA-F]{40}$') {
    $env:RAIOS_CANONICAL_HEAD = $raw
}
if ($env:RAIOS_CANONICAL_HEAD -notmatch '^[0-9a-fA-F]{40}$') { throw "LIVE_CANONICAL_GIT_HEAD_REQUIRED" }

$OwningPid = Get-RaiosListenPid $Port
if ($OwningPid) {
    $Info = Get-RaiosProcessInfo $OwningPid
    $Health = Get-RaiosMcpHealth $HealthUrl 2
    if (-not (Test-RaiosOurMcp $Info $OwningPid $Port $Health)) {
        $who = if ($Info) { $Info.Name } else { "unknown" }
        throw "Port $Port is not proven RAIOS-owned: $who PID $OwningPid."
    }
    if (Test-RaiosMcpHealthy $Health) {
        if (-not $Reload) {
            Write-Output "LOCAL_MCP_ALREADY_HEALTHY port=$Port pid=$OwningPid tools=$($Health.tools.Count) head_source=$($Health.head_source)"
            exit 0
        }
        if (-not (Test-RaiosOurMcp $Info $OwningPid $Port $Health)) {
            throw "Port $Port is owned by another process, PID $OwningPid."
        }
        Write-Output "LOCAL_MCP_RELOAD port=$Port pid=$OwningPid"
        Stop-RaiosListenPid $OwningPid
    } else {
        if ($NoRecover) { throw "Existing local MCP listener is unhealthy." }
        if (-not (Test-RaiosOurMcp $Info $OwningPid $Port $Health)) {
            $who = if ($Info) { $Info.Name } else { "unknown" }
            throw "Port $Port is owned by $who, PID $OwningPid."
        }
        Write-Output "LOCAL_MCP_RECOVER_HUNG port=$Port pid=$OwningPid"
        Stop-RaiosListenPid $OwningPid
    }
}

$Shadow = Get-RaiosListenPid 8787
if ($Shadow) {
    $ShadowInfo = Get-RaiosProcessInfo $Shadow
    if (Test-RaiosOurMcp $ShadowInfo $Shadow 8787 $null) {
        Write-Output "LOCAL_MCP_STOP_SHADOW port=8787 pid=$Shadow"
        Stop-RaiosListenPid $Shadow
    }
}

$Stdout = Join-Path $ReceiptDir "LOCAL-MCP-$Port.stdout.log"
$Stderr = Join-Path $ReceiptDir "LOCAL-MCP-$Port.stderr.log"
$Arguments = @($Server, "--http", "--host", "127.0.0.1", "--port", "$Port")
$Process = Start-Process -FilePath $Python -ArgumentList $Arguments -WorkingDirectory $Repo -RedirectStandardOutput $Stdout -RedirectStandardError $Stderr -WindowStyle Hidden -PassThru

$Health = $null
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Milliseconds 400
    if ($Process.HasExited) { break }
    $Health = Get-RaiosMcpHealth $HealthUrl 2
    if (Test-RaiosMcpHealthy $Health) { break }
}
if ($Process.HasExited) {
    Get-Content $Stderr -ErrorAction SilentlyContinue
    throw "Local MCP failed to start."
}
if (-not (Test-RaiosMcpHealthy $Health)) {
    throw "Local MCP health validation failed."
}
$LivePid = Get-RaiosListenPid $Port
if (-not $LivePid) { throw "LOCAL_MCP_LISTENER_PID_MISSING_AFTER_START" }
Write-RaiosOwnerManifest $LivePid "STARTED_CANONICAL"

Write-Output "LOCAL_MCP_STARTED port=$Port pid=$($Process.Id) tools=$($Health.tools.Count) head_source=$($Health.head_source)"
Write-Output "HEALTH=$HealthUrl"
Write-Output "GL005_PROVEN=$($Health.gl005_proven)"
Write-Output "NINTH_TOOL=$($Health.ninth_tool)"
Write-Output "SECOND_GATEWAY=$($Health.second_gateway)"
