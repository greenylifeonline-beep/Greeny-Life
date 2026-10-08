param(
    [int]$Port = 8788,
    [switch]$NoRecover,
    [switch]$Reload,
    [switch]$PromoteOwnedGeneration,
    [ValidateSet("8", "9")]
    [string]$ExpectedToolContract = "9"
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
function Get-RaiosListenPids([int]$ListenPort) {
    $found = New-Object System.Collections.Generic.List[int]
    foreach ($line in (& netstat -ano -p tcp 2>$null)) {
        $parts = @($line.ToString().Trim() -split '\s+')
        if ($parts.Length -lt 5) { continue }
        if ($parts[-2] -ne 'LISTENING') { continue }
        if ($parts[1] -match (":$ListenPort$")) {
            $listenPid = [int]$parts[-1]
            if (-not $found.Contains($listenPid)) { [void]$found.Add($listenPid) }
        }
    }
    return @($found)
}
function Get-RaiosListenPid([int]$ListenPort) {
    $all = @(Get-RaiosListenPids $ListenPort)
    if ($all.Count -eq 1) { return [int]$all[0] }
    return $null
}
function Get-RaiosMcpHealth([string]$Url, [int]$TimeoutSec = 2) {
    try {
        return Invoke-RestMethod $Url -TimeoutSec $TimeoutSec
    } catch {
        return $null
    }
}
function Get-RaiosExpectedToolNames {
    $names = @("get_head", "read_board", "read_inbox", "read_receipt", "get_diff", "post_opinion", "send_packet", "ack_packet")
    if ($ExpectedToolContract -eq "9") { $names += "execute_scoped_task" }
    return $names
}
function Get-RaiosToolContractSha {
    return Get-RaiosSha256Text ((Get-RaiosExpectedToolNames) -join "`n")
}
function Test-RaiosMcpToolContract($Health) {
    $tools = @($Health.tools)
    foreach ($banned in @("shell", "bash", "run_command", "run_sandboxed_command")) {
        if ($tools -contains $banned) { return $false }
    }
    foreach ($core in (Get-RaiosExpectedToolNames)) {
        if ($tools -notcontains $core) { return $false }
    }
    $count = [int]$ExpectedToolContract
    if ($tools.Count -ne $count -or [int]$Health.tool_count -ne $count -or $Health.second_gateway -eq $true) { return $false }
    if ($count -eq 9 -and ($Health.execute_scoped_task -ne $true -or $Health.raw_shell -eq $true)) { return $false }
    if ($Health.duplicate_mcp -eq $true -or $Health.second_gateway -eq $true) { return $false }
    return $true
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
function Test-RaiosRecordedProcess($Info, [int]$ProcId) {
    # Promotion may stop only the process bound by the launch receipt. PID reuse and a different command are not that process.
    $owner = Read-RaiosOwnerManifest
    if (-not $owner -or -not $Info) { return $false }
    $recordedPid = 0
    if ($owner.listener_pid) { $recordedPid = [int]$owner.listener_pid }
    elseif ($owner.pid) { $recordedPid = [int]$owner.pid }
    if ($recordedPid -ne $ProcId) { return $false }
    $started = Get-RaiosProcessStartUtc $ProcId $Info
    $expectedStart = if ($owner.listener_creation_time) { [string]$owner.listener_creation_time } else { [string]$owner.started_at }
    if (-not (Test-RaiosSameInstant $started $expectedStart)) { return $false }
    $expectedCmd = if ($owner.listener_command_line) { [string]$owner.listener_command_line } else { [string]$owner.command_line }
    $liveCmd = [string]$Info.CommandLine
    if ([string]::IsNullOrWhiteSpace($liveCmd)) {
        # Session isolation can hide CommandLine. PID plus creation time already matched the receipt.
        $name = [string]$Info.Name
        return ($name -match '(?i)^python(w)?\.exe$') -and ($expectedCmd -match 'raios_mcp[\\/]server\.py')
    }
    return $liveCmd.Trim() -eq $expectedCmd.Trim()
}
function Get-RaiosProfileRoot {
    $stable = "C:\Users\Ghanam"
    $marker = Join-Path $stable ".raios\runtime\continuity\c5-service\current-generation.json"
    if (Test-Path -LiteralPath $marker) { return $stable }
    return $env:USERPROFILE
}
function Set-RaiosLaunchEnvironment {
    # A SYSTEM rollback inherits a profile whose PATH has neither Git nor the npm shim.
    $profile = Get-RaiosProfileRoot
    $marker = Join-Path $profile ".raios\runtime\continuity\c5-service\current-generation.json"
    if (Test-Path -LiteralPath $marker) {
        $env:RAIOS_STABLE_USER_PROFILE = $profile
        $currentMarker = Join-Path $env:USERPROFILE ".raios\runtime\continuity\c5-service\current-generation.json"
        if (-not (Test-Path -LiteralPath $currentMarker)) {
            $env:USERPROFILE = $profile
            $env:HOME = $profile
        }
    }
    $prefix = New-Object System.Collections.Generic.List[string]
    $npm = Join-Path $profile "AppData\Roaming\npm"
    $gitCmd = "C:\Program Files\Git\cmd"
    if ((Test-Path -LiteralPath $npm) -and ($env:PATH -notlike "*${npm}*")) { [void]$prefix.Add($npm) }
    if ((Test-Path -LiteralPath $gitCmd) -and ($env:PATH -notlike "*\Git\cmd*")) { [void]$prefix.Add($gitCmd) }
    if ($prefix.Count -gt 0) { $env:PATH = (($prefix -join ";") + ";" + $env:PATH) }
}
function Get-RaiosC5GenerationId {
    $path = Join-Path (Get-RaiosProfileRoot) ".raios\runtime\continuity\c5-service\current-generation.json"
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
function Get-RaiosSha256Text([string]$Text) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Text)))).Replace("-", "").ToLowerInvariant()
    } finally { $sha.Dispose() }
}
function Get-RaiosParentChain([int]$ProcId) {
    $chain = @()
    $current = $ProcId
    for ($depth = 0; $depth -lt 8; $depth++) {
        $info = Get-RaiosProcessInfo $current
        if ($null -eq $info) { break }
        $parentId = 0
        if ($info.ParentProcessId) { $parentId = [int]$info.ParentProcessId }
        if ($parentId -le 4) { break }
        $parent = Get-RaiosProcessInfo $parentId
        if ($null -eq $parent) { break }
        $chain += [ordered]@{
            pid = $parentId
            creation_time = (Get-RaiosProcessStartUtc $parentId $parent)
            command_line = [string]$parent.CommandLine
            executable = [string]$parent.Name
        }
        $current = $parentId
    }
    return @($chain)
}
function Invoke-RaiosGenerationJudge($Record, $Observation) {
    $judgeDir = Join-Path $env:TEMP ("raios-mcp-judge-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $judgeDir | Out-Null
    try {
        $recordPath = Join-Path $judgeDir "record.json"
        $observationPath = Join-Path $judgeDir "observation.json"
        [IO.File]::WriteAllText($recordPath, (($Record | ConvertTo-Json -Depth 8 -Compress) + ""), [Text.UTF8Encoding]::new($false))
        [IO.File]::WriteAllText($observationPath, (($Observation | ConvertTo-Json -Depth 8 -Compress) + ""), [Text.UTF8Encoding]::new($false))
        $module = Join-Path $PSScriptRoot "raios_mcp_generation_identity.py"
        $output = & $Python $module --record $recordPath --observation $observationPath 2>&1
        $text = ((@($output) | Out-String).Trim())
        $accepted = $text.StartsWith("ACCEPT ")
        return [pscustomobject]@{ accept = $accepted; reason = $(if ($accepted) { $text.Substring(7).Trim() } else { $text }) }
    } catch {
        return [pscustomobject]@{ accept = $false; reason = "REJECT_NO_GENERATION_PROVENANCE" }
    } finally {
        Remove-Item -LiteralPath $judgeDir -Recurse -Force -ErrorAction SilentlyContinue
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
    $policyPath = Join-Path $Repo ".ai-os\mcp\POLICY.json"
    $policySha = $null
    if (Test-Path -LiteralPath $policyPath) {
        $policySha = (Get-FileHash -LiteralPath $policyPath -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $toolContractSha = Get-RaiosToolContractSha
    $servicePid = $null
    $generationPath = Join-Path (Get-RaiosProfileRoot) ".raios\runtime\continuity\c5-service\current-generation.json"
    if (Test-Path -LiteralPath $generationPath) {
        try {
            $generationDoc = Get-Content -LiteralPath $generationPath -Raw | ConvertFrom-Json
            if ($generationDoc.service_pid) { $servicePid = [int]$generationDoc.service_pid }
        } catch {}
    }
    $mcpGeneration = Get-RaiosSha256Text ("$GenerationId|$($Process.Id)|$started|$($Source.server_sha256)")
    $doc = [ordered]@{
        schema = "raios.universal-mcp-launch.v1"
        observation = "PROCESS_START"
        generation_id = $mcpGeneration
        launcher_pid = [int]$Process.Id
        launcher_creation_time = $started
        launcher_command_line = $command
        launcher_executable = [string]$Info.Name
        service_pid = $servicePid
        service_generation = $GenerationId
        canonical_head = [string]$env:RAIOS_CANONICAL_HEAD
        policy_sha256 = $policySha
        tool_contract_sha256 = $toolContractSha
        expected_service = "raios-universal-mcp"
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
        superseded = $false
        written_at = [DateTimeOffset]::UtcNow.ToString("o")
    }
    $tmp = "$OwnerManifest.tmp.$PID"
    [IO.File]::WriteAllText($tmp, (($doc | ConvertTo-Json -Depth 6) + [Environment]::NewLine), [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tmp -Destination $OwnerManifest -Force
}
function Test-RaiosLaunchIdentity($Info, [int]$ProcId, [int]$ListenPort) {
    # PID_NE_PROCESS_IDENTITY. HEALTH_NE_OWNERSHIP. DESCENDANT_NE_OWNED_UNLESS_GENERATION_BOUND.
    # C1_EXPLICIT_QUARANTINE_RETIREMENT is the only retirement authority and is not invoked here.
    $script:RaiosIdentityReason = "REJECT_NO_GENERATION_PROVENANCE"
    $owner = Read-RaiosOwnerManifest
    if ($null -eq $owner -or $null -eq $Info) { return $false }
    $source = Get-RaiosLaunchSourceFingerprint
    $listenPids = @(Get-RaiosListenPids $ListenPort)
    $policyPath = Join-Path $Repo ".ai-os\mcp\POLICY.json"
    $policySha = $null
    if (Test-Path -LiteralPath $policyPath) {
        $policySha = (Get-FileHash -LiteralPath $policyPath -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $observation = [ordered]@{
        listener_pid = $ProcId
        listener_creation_time = (Get-RaiosProcessStartUtc $ProcId $Info)
        listener_command_line = [string]$Info.CommandLine
        listener_executable = [string]$Info.Name
        parent_chain = @(Get-RaiosParentChain $ProcId)
        port = $ListenPort
        listener_count = $listenPids.Count
        server_sha256 = $(if ($source) { [string]$source.server_sha256 } else { $null })
        gateway_sha256 = $(if ($source) { [string]$source.gateway_sha256 } else { $null })
        policy_sha256 = $policySha
        tool_contract_sha256 = (Get-RaiosToolContractSha)
        canonical_head = [string]$env:RAIOS_CANONICAL_HEAD
        service_generation = (Get-RaiosC5GenerationId)
        current_generation_id = $(if ($owner.generation_id) { [string]$owner.generation_id } else { $null })
    }
    $decision = Invoke-RaiosGenerationJudge $owner $observation
    $script:RaiosIdentityReason = [string]$decision.reason
    return [bool]$decision.accept
}
function Write-RaiosListenerBinding($Info, [int]$ProcId) {
    $owner = Read-RaiosOwnerManifest
    if ($null -eq $owner) { return }
    $owner | Add-Member -NotePropertyName listener_pid -NotePropertyValue $ProcId -Force
    $owner | Add-Member -NotePropertyName listener_creation_time -NotePropertyValue (Get-RaiosProcessStartUtc $ProcId $Info) -Force
    $owner | Add-Member -NotePropertyName listener_command_line -NotePropertyValue ([string]$Info.CommandLine) -Force
    $owner | Add-Member -NotePropertyName listener_executable -NotePropertyValue ([string]$Info.Name) -Force
    $owner | Add-Member -NotePropertyName listener_parent_chain -NotePropertyValue @(Get-RaiosParentChain $ProcId) -Force
    $owner | Add-Member -NotePropertyName bound_at -NotePropertyValue ([DateTimeOffset]::UtcNow.ToString("o")) -Force
    $tmp = "$OwnerManifest.tmp.$PID"
    [IO.File]::WriteAllText($tmp, (($owner | ConvertTo-Json -Depth 8) + [Environment]::NewLine), [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tmp -Destination $OwnerManifest -Force
}
function Stop-RaiosListenPid([int]$ProcId) {
    if ($ProcId -le 4) { throw "Refusing unsafe listener PID $ProcId." }
    Stop-Process -Id $ProcId -Force -ErrorAction Stop
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 250
        if (-not (Get-Process -Id $ProcId -ErrorAction SilentlyContinue)) { return }
    }
    throw "RAIOS_MCP_PROCESS_DID_NOT_STOP::$ProcId"
}

$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$PythonCandidates = @(
    (Join-Path (Get-RaiosProfileRoot) ".raios\runtime\c5\.venv\Scripts\python.exe"),
    (Join-Path $Repo ".venv\Scripts\python.exe")
)
$Python = $PythonCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$Server = Join-Path $Repo "scripts\ai-os\raios_mcp\server.py"
$ReceiptDir = Join-Path $Repo ".ai-os\receipts\command-fabric"
$OwnerDir = Join-Path (Get-RaiosProfileRoot) ".raios\runtime\mcp"
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

$ListenPids = @(Get-RaiosListenPids $Port)
if ($ListenPids.Count -gt 1) {
    $ownership_proven = $false
    throw "MCP_LIVE_BUT_UNOWNED port=$Port reason=REJECT_COMPETING_LISTENER"
}
$OwningPid = if ($ListenPids.Count -eq 1) { [int]$ListenPids[0] } else { $null }
if ($OwningPid) {
    $Info = Get-RaiosProcessInfo $OwningPid
    $Health = Get-RaiosMcpHealth $HealthUrl 2
    if ($null -eq $Info) { throw "MCP_LAUNCH_IDENTITY_UNREADABLE port=$Port pid=$OwningPid" }
    if (-not (Test-RaiosLaunchIdentity $Info $OwningPid $Port)) {
        if ($PromoteOwnedGeneration -and (Test-RaiosRecordedProcess $Info $OwningPid)) {
            Write-Output "LOCAL_MCP_PROMOTE_OWNED port=$Port pid=$OwningPid reason=$script:RaiosIdentityReason"
            Stop-RaiosListenPid $OwningPid
        } else {
            $ownership_proven = $false
            throw "MCP_LIVE_BUT_UNOWNED port=$Port pid=$OwningPid reason=$script:RaiosIdentityReason"
        }
    } elseif (Test-RaiosMcpHealthy $Health) {
        if (-not $Reload) {
            Write-Output "LOCAL_MCP_ALREADY_HEALTHY port=$Port pid=$OwningPid tools=$($Health.tools.Count) head_source=$($Health.head_source)"
            exit 0
        }
        Write-Output "LOCAL_MCP_RELOAD port=$Port pid=$OwningPid"
        Stop-RaiosListenPid $OwningPid
    } else {
        $recordedContract = ""
        $ownerNow = Read-RaiosOwnerManifest
        if ($ownerNow -and $ownerNow.tool_contract_sha256) { $recordedContract = [string]$ownerNow.tool_contract_sha256 }
        if ($PromoteOwnedGeneration -and (Test-RaiosRecordedProcess $Info $OwningPid)) {
            Write-Output "LOCAL_MCP_PROMOTE_OWNED port=$Port pid=$OwningPid reason=CONTRACT_DRIFT"
            Stop-RaiosListenPid $OwningPid
        } elseif ($recordedContract -ne (Get-RaiosToolContractSha)) {
            $ownership_proven = $false
            throw "MCP_LIVE_BUT_UNOWNED port=$Port pid=$OwningPid reason=CONTRACT_DRIFT"
        } elseif ($NoRecover) {
            throw "Existing local MCP listener is unhealthy."
        } else {
            Write-Output "LOCAL_MCP_RECOVER_HUNG port=$Port pid=$OwningPid"
            Stop-RaiosListenPid $OwningPid
        }
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
Set-RaiosLaunchEnvironment
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
if ($Process.HasExited -and -not (Test-RaiosMcpHealthy $Health)) {
    Get-Content $Stderr -ErrorAction SilentlyContinue
    throw "Local MCP failed to start."
}
if (-not (Test-RaiosMcpHealthy $Health)) {
    if (-not $Process.HasExited) { Stop-RaiosListenPid $Process.Id }
    throw "Local MCP health validation failed."
}
$StartedPids = @(Get-RaiosListenPids $Port)
if ($StartedPids.Count -ne 1) {
    if (-not $Process.HasExited) { Stop-RaiosListenPid $Process.Id }
    $ownership_proven = $false
    throw "MCP_GENERATION_REJECTED port=$Port reason=REJECT_COMPETING_LISTENER"
}
$LivePid = [int]$StartedPids[0]
$LiveInfo = Get-RaiosProcessInfo $LivePid
if (-not (Test-RaiosLaunchIdentity $LiveInfo $LivePid $Port)) {
    if (-not $Process.HasExited -and [int]$Process.Id -ne $LivePid) { Stop-RaiosListenPid $Process.Id }
    $ownership_proven = $false
    throw "MCP_GENERATION_REJECTED port=$Port pid=$LivePid reason=$script:RaiosIdentityReason"
}
Write-RaiosListenerBinding -Info $LiveInfo -ProcId $LivePid

Write-Output "LOCAL_MCP_STARTED port=$Port pid=$($Process.Id) tools=$($Health.tools.Count) head_source=$($Health.head_source)"
Write-Output "HEALTH=$HealthUrl"
Write-Output "GL005_PROVEN=$($Health.gl005_proven)"
Write-Output "NINTH_TOOL=$($Health.ninth_tool)"
Write-Output "SECOND_GATEWAY=$($Health.second_gateway)"
Write-Output "LAUNCH_SOURCE_SHA256=$($SourceFingerprint.fingerprint)"
Write-Output "C5_GENERATION=$GenerationId"
