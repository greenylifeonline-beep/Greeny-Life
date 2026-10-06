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
function Read-RaiosOwnerManifest {
    if (-not (Test-Path -LiteralPath $OwnerManifest)) { return $null }
    try { return Get-Content -LiteralPath $OwnerManifest -Raw | ConvertFrom-Json } catch { return $null }
}
function Get-RaiosProcessInfo([int]$ProcId) {
    try { return Get-CimInstance Win32_Process -Filter "ProcessId=$ProcId" -OperationTimeoutSec 8 } catch { return $null }
}
function Get-RaiosProcessStartUtc([int]$ProcId, $Info) {
    if ($Info -and $Info.CreationDate) {
        return ([DateTime]$Info.CreationDate).ToUniversalTime().ToString("o")
    }
    try {
        return (Get-Process -Id $ProcId -ErrorAction Stop).StartTime.ToUniversalTime().ToString("o")
    } catch { return $null }
}
function Test-RaiosSameInstant([string]$Left, [string]$Right) {
    try {
        $a = [DateTimeOffset]::Parse($Left)
        $b = [DateTimeOffset]::Parse($Right)
        return [Math]::Abs(($a.UtcDateTime - $b.UtcDateTime).TotalSeconds) -lt 2
    } catch { return $false }
}
function Get-RaiosC5GenerationId {
    $path = Join-Path $env:USERPROFILE ".raios\runtime\continuity\c5-service\current-generation.json"
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    try { $doc = Get-Content -LiteralPath $path -Raw -ErrorAction Stop | ConvertFrom-Json } catch { return $null }
    $id = [string]$doc.generation_id
    if ([string]$doc.schema -ne "raios.runtime-generation.v3") { return $null }
    if ([string]$doc.authority -ne "RAIOS-C5-SCM") { return $null }
    if ($id -notmatch '^[0-9a-f]{64}::\d{4}-\d{2}-\d{2}T') { return $null }
    return $id
}
function Get-RaiosLaunchSourceFingerprint {
    $serverPath = [IO.Path]::GetFullPath($Server)
    $gatewayPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "raios_mcp\gateway.py"))
    if (-not (Test-Path -LiteralPath $serverPath) -or -not (Test-Path -LiteralPath $gatewayPath)) { return $null }
    $serverSha = (Get-FileHash -LiteralPath $serverPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $gatewaySha = (Get-FileHash -LiteralPath $gatewayPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $material = "server.py`n$serverSha`ngateway.py`n$gatewaySha`n"
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $fingerprint = ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($material)))).Replace("-", "").ToLowerInvariant()
    } finally { $sha.Dispose() }
    return [pscustomobject]@{
        server_path = $serverPath
        gateway_path = $gatewayPath
        server_sha256 = $serverSha
        gateway_sha256 = $gatewaySha
        fingerprint = $fingerprint
    }
}
function Write-RaiosLaunchIdentity($Process, $Info, $Source, [string]$GenerationId) {
    if ($null -eq $Process -or $null -eq $Info -or $null -eq $Source) { throw "MCP_LAUNCH_IDENTITY_UNREADABLE" }
    $started = Get-RaiosProcessStartUtc $Process.Id $Info
    $command = [string]$Info.CommandLine
    $launcherInfo = Get-RaiosProcessInfo $PID
    $launcherStarted = Get-RaiosProcessStartUtc $PID $launcherInfo
    $serverPath = [string]$Source.server_path
    if (-not $started -or -not $command -or -not $launcherStarted) { throw "MCP_LAUNCH_IDENTITY_UNREADABLE::$($Process.Id)" }
    if ($command.IndexOf($serverPath, [StringComparison]::OrdinalIgnoreCase) -lt 0) { throw "MCP_LAUNCH_COMMAND_MISMATCH::$($Process.Id)" }
    if (-not $GenerationId) { throw "MCP_C5_GENERATION_UNREADABLE" }
    $parentId = 0
    if ($Info.ParentProcessId) { $parentId = [int]$Info.ParentProcessId }
    if ($parentId -ne $PID) { throw "MCP_LAUNCH_PARENT_MISMATCH::$($Process.Id)" }
    New-Item -ItemType Directory -Force -Path $OwnerDir | Out-Null
    $doc = [ordered]@{
        schema = "raios.universal-mcp-launch.v1"
        observation = "PROCESS_START"
        pid = [int]$Process.Id
        port = $Port
        started_at = $started
        command_line = $command
        launcher = [ordered]@{
            pid = $PID
            path = [IO.Path]::GetFullPath($PSCommandPath)
            started_at = $launcherStarted
        }
        c5_generation = $GenerationId
        launch_source_path = $serverPath
        launch_gateway_path = [string]$Source.gateway_path
        launch_source_sha256 = [string]$Source.fingerprint
        server_sha256 = [string]$Source.server_sha256
        gateway_sha256 = [string]$Source.gateway_sha256
        written_at = [DateTimeOffset]::UtcNow.ToString("o")
    }
    $tmp = "$OwnerManifest.tmp.$PID"
    [IO.File]::WriteAllText($tmp, (($doc | ConvertTo-Json -Depth 6) + [Environment]::NewLine), [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tmp -Destination $OwnerManifest -Force
}
function Test-RaiosLaunchIdentity($Info, [int]$ProcId, [int]$ListenPort) {
    $owner = Read-RaiosOwnerManifest
    if ($null -eq $owner -or $null -eq $Info) { return $false }
    if ([string]$owner.schema -ne "raios.universal-mcp-launch.v1") { return $false }
    if ([string]$owner.observation -ne "PROCESS_START") { return $false }
    if ([int]$owner.pid -ne $ProcId -or [int]$owner.port -ne $ListenPort) { return $false }
    $started = Get-RaiosProcessStartUtc $ProcId $Info
    if (-not (Test-RaiosSameInstant $started ([string]$owner.started_at))) { return $false }
    $command = [string]$Info.CommandLine
    if (-not $command -or $command -ne [string]$owner.command_line) { return $false }
    $launcherPath = [string]$owner.launcher.path
    if (-not $launcherPath -or $launcherPath -ne [IO.Path]::GetFullPath($PSCommandPath)) { return $false }
    if (-not $owner.launcher.pid -or -not $owner.launcher.started_at) { return $false }
    $parentId = 0
    if ($Info.ParentProcessId) { $parentId = [int]$Info.ParentProcessId }
    if ($parentId -ne [int]$owner.launcher.pid) { return $false }
    $launcherProc = Get-Process -Id ([int]$owner.launcher.pid) -ErrorAction SilentlyContinue
    if ($launcherProc -and -not (Test-RaiosSameInstant $launcherProc.StartTime.ToUniversalTime().ToString("o") ([string]$owner.launcher.started_at))) { return $false }
    $generation = Get-RaiosC5GenerationId
    if (-not $generation -or [string]$owner.c5_generation -ne $generation) { return $false }
    $source = Get-RaiosLaunchSourceFingerprint
    if ($null -eq $source) { return $false }
    if ([string]$owner.launch_source_path -ne [string]$source.server_path) { return $false }
    if ([string]$owner.launch_source_sha256 -ne [string]$source.fingerprint) { return $false }
    if ($command.IndexOf([string]$source.server_path, [StringComparison]::OrdinalIgnoreCase) -lt 0) { return $false }
    return $true
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
    if ($null -eq $Info) { throw "MCP_LAUNCH_IDENTITY_UNREADABLE port=$Port pid=$OwningPid" }
    if (-not (Test-RaiosLaunchIdentity $Info $OwningPid $Port)) {
        throw "MCP_LAUNCH_IDENTITY_MISMATCH port=$Port pid=$OwningPid"
    }
    if (Test-RaiosMcpHealthy $Health) {
        if (-not $Reload) {
            Write-Output "LOCAL_MCP_ALREADY_HEALTHY port=$Port pid=$OwningPid tools=$($Health.tools.Count) head_source=$($Health.head_source)"
            exit 0
        }
        Write-Output "LOCAL_MCP_RELOAD port=$Port pid=$OwningPid"
        Stop-RaiosListenPid $OwningPid
    } else {
        if ($NoRecover) { throw "Existing local MCP listener is unhealthy." }
        Write-Output "LOCAL_MCP_RECOVER_HUNG port=$Port pid=$OwningPid"
        Stop-RaiosListenPid $OwningPid
    }
}

$Shadow = Get-RaiosListenPid 8787
if ($Shadow) {
    $ShadowInfo = Get-RaiosProcessInfo $Shadow
    if (Test-RaiosLaunchIdentity $ShadowInfo $Shadow 8787) {
        Write-Output "LOCAL_MCP_STOP_SHADOW port=8787 pid=$Shadow"
        Stop-RaiosListenPid $Shadow
    } else {
        Write-Output "MCP_SHADOW_LISTENER_UNPROVEN port=8787 pid=$Shadow"
    }
}

$GenerationId = Get-RaiosC5GenerationId
if (-not $GenerationId) { throw "MCP_C5_GENERATION_UNREADABLE" }
$SourceFingerprint = Get-RaiosLaunchSourceFingerprint
if ($null -eq $SourceFingerprint) { throw "MCP_LAUNCH_SOURCE_MISSING" }

$Stdout = Join-Path $ReceiptDir "LOCAL-MCP-$Port.stdout.log"
$Stderr = Join-Path $ReceiptDir "LOCAL-MCP-$Port.stderr.log"
$Arguments = @($Server, "--http", "--host", "127.0.0.1", "--port", "$Port")
$Process = Start-Process -FilePath $Python -ArgumentList $Arguments -WorkingDirectory $Repo -RedirectStandardOutput $Stdout -RedirectStandardError $Stderr -WindowStyle Hidden -PassThru
try {
    $LaunchInfo = Get-RaiosProcessInfo $Process.Id
    Write-RaiosLaunchIdentity -Process $Process -Info $LaunchInfo -Source $SourceFingerprint -GenerationId $GenerationId
} catch {
    if (-not $Process.HasExited) { Stop-RaiosListenPid $Process.Id }
    throw
}

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
    if (-not $Process.HasExited) { Stop-RaiosListenPid $Process.Id }
    throw "Local MCP health validation failed."
}
$LivePid = Get-RaiosListenPid $Port
if ($LivePid -ne $Process.Id) {
    if (-not $Process.HasExited) { Stop-RaiosListenPid $Process.Id }
    throw "MCP_LISTENER_PID_NOT_LAUNCH_PID live=$LivePid launch=$($Process.Id)"
}
$LiveInfo = Get-RaiosProcessInfo $LivePid
if (-not (Test-RaiosLaunchIdentity $LiveInfo $LivePid $Port)) {
    if (-not $Process.HasExited) { Stop-RaiosListenPid $Process.Id }
    throw "MCP_LAUNCH_IDENTITY_MISMATCH port=$Port pid=$LivePid"
}

Write-Output "LOCAL_MCP_STARTED port=$Port pid=$($Process.Id) tools=$($Health.tools.Count) head_source=$($Health.head_source)"
Write-Output "HEALTH=$HealthUrl"
Write-Output "GL005_PROVEN=$($Health.gl005_proven)"
Write-Output "NINTH_TOOL=$($Health.ninth_tool)"
Write-Output "SECOND_GATEWAY=$($Health.second_gateway)"
Write-Output "LAUNCH_SOURCE_SHA256=$($SourceFingerprint.fingerprint)"
Write-Output "C5_GENERATION=$GenerationId"
