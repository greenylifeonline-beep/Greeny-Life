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
function Set-RaiosGenerationTransition([int]$PreviousPid,[string]$Reason) {
    $script:TransitionPreviousPid = $PreviousPid
    $script:TransitionReason = $Reason
    $owner = Read-RaiosOwnerManifest
    $script:TransitionPreviousGeneration = $null
    $script:TransitionPreviousStartedAt = $null
    if ($owner) {
        if ($owner.generation_id) { $script:TransitionPreviousGeneration = [string]$owner.generation_id }
        if ($owner.listener_creation_time) { $script:TransitionPreviousStartedAt = [string]$owner.listener_creation_time }
        elseif ($owner.started_at) { $script:TransitionPreviousStartedAt = [string]$owner.started_at }
    }
}
function Test-RaiosPidAlive([int]$ProcId) {
    if ($ProcId -le 4) { return $false }
    return [bool](Get-Process -Id $ProcId -ErrorAction SilentlyContinue)
}
function Write-RaiosAtomicJson([string]$Path,$Value) {
    $tmp = "$Path.tmp.$PID.$([guid]::NewGuid().ToString('N'))"
    [IO.File]::WriteAllText(
        $tmp,
        (($Value | ConvertTo-Json -Depth 12) + [Environment]::NewLine),
        [Text.UTF8Encoding]::new($false)
    )
    Move-Item -LiteralPath $tmp -Destination $Path -Force
}
function Write-RaiosBoundedLifecycle($Value,[int]$Limit=128) {
    $line = $Value | ConvertTo-Json -Depth 12 -Compress
    $existing = @()
    if (Test-Path -LiteralPath $LifecycleLedger) {
        $existing = @(Get-Content -LiteralPath $LifecycleLedger -ErrorAction SilentlyContinue | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    }
    if ($existing.Count -ge $Limit) {
        $existing = @($existing | Select-Object -Last ($Limit - 1))
    }
    $all = @($existing) + @([string]$line)
    $tmp = "$LifecycleLedger.tmp.$PID.$([guid]::NewGuid().ToString('N'))"
    [IO.File]::WriteAllLines($tmp, [string[]]$all, [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tmp -Destination $LifecycleLedger -Force
}
function Write-RaiosGenerationHandoff([int]$CandidatePid,[int]$ActivePid,[string]$Reason) {
    $owner = Read-RaiosOwnerManifest
    $priorProjection = $null
    if (Test-Path -LiteralPath $LifecycleProjection) {
        try { $priorProjection = Get-Content -LiteralPath $LifecycleProjection -Raw | ConvertFrom-Json } catch { $priorProjection = $null }
    }
    $preserveTransition = [bool](
        $Reason -eq "STEADY_STATE_VERIFY" -and
        $priorProjection -and
        [string]$priorProjection.schema -eq "raios.mcp-generation-handoff.v1" -and
        [string]$priorProjection.transition_reason -ne "STEADY_STATE_VERIFY"
    )
    $previousPid = [int]$script:TransitionPreviousPid
    $previousAlive = Test-RaiosPidAlive $previousPid
    $candidateAlive = Test-RaiosPidAlive $CandidatePid
    $activeAlive = Test-RaiosPidAlive $ActivePid
    $listeners = @(Get-RaiosListenPids $Port)
    $orphanPids = New-Object System.Collections.Generic.List[int]
    if ($previousPid -gt 4 -and $previousPid -ne $ActivePid -and $previousAlive) { [void]$orphanPids.Add($previousPid) }
    if ($CandidatePid -gt 4 -and $CandidatePid -ne $ActivePid -and $candidateAlive -and -not $orphanPids.Contains($CandidatePid)) { [void]$orphanPids.Add($CandidatePid) }
    $ownerHead = $(if ($owner -and $owner.canonical_head) { [string]$owner.canonical_head } else { $null })
    $ownerGeneration = $(if ($owner -and $owner.generation_id) { [string]$owner.generation_id } else { $null })
    $ownerServiceGeneration = $(if ($owner -and $owner.service_generation) { [string]$owner.service_generation } else { $null })
    $serviceGeneration = Get-RaiosC5GenerationId
    $ownerHeadMatch = [bool]($ownerHead -and $ownerHead -eq [string]$env:RAIOS_CANONICAL_HEAD)
    $serviceGenerationMatch = [bool]($ownerServiceGeneration -and $serviceGeneration -and $ownerServiceGeneration -eq $serviceGeneration)
    $activeListenerMatch = [bool]($listeners.Count -eq 1 -and [int]$listeners[0] -eq $ActivePid)
    $duplicateMcp = [bool]($listeners.Count -gt 1)
    $handoffComplete = [bool](
        $activeAlive -and
        $activeListenerMatch -and
        -not $duplicateMcp -and
        $orphanPids.Count -eq 0 -and
        $ownerHeadMatch -and
        $serviceGenerationMatch
    )
    $previousState = $(if ($previousPid -le 4) { "NONE" } elseif ($previousPid -eq $ActivePid) { "ACTIVE" } elseif ($previousAlive) { "ORPHAN" } else { "RETIRED" })
    $candidateState = $(if ($CandidatePid -eq $ActivePid) { "ACTIVE" } elseif ($candidateAlive) { "ORPHAN" } else { "SUPERSEDED" })
    $reportedReason = $Reason
    $verificationReason = $null
    $reportedPreviousPid = $(if ($previousPid -gt 4) { $previousPid } else { $null })
    $reportedPreviousGeneration = $script:TransitionPreviousGeneration
    $reportedPreviousStartedAt = $script:TransitionPreviousStartedAt
    $reportedPreviousState = $previousState
    $reportedCandidatePid = $CandidatePid
    $reportedCandidateGeneration = $ownerGeneration
    $reportedCandidateState = $candidateState
    if ($preserveTransition) {
        $reportedReason = [string]$priorProjection.transition_reason
        $verificationReason = "STEADY_STATE_VERIFY"
        $reportedPreviousPid = $priorProjection.previous_pid
        $reportedPreviousGeneration = $priorProjection.previous_generation_id
        $reportedPreviousStartedAt = $priorProjection.previous_started_at
        $reportedPreviousState = [string]$priorProjection.previous_state
        $reportedCandidatePid = $priorProjection.candidate_pid
        $reportedCandidateGeneration = $priorProjection.candidate_generation_id
        $reportedCandidateState = [string]$priorProjection.candidate_state
    }
    $doc = [ordered]@{
        schema = "raios.mcp-generation-handoff.v1"
        observed_at = [DateTimeOffset]::UtcNow.ToString("o")
        authority = "RAIOS-C5-SCM"
        canonical_head = [string]$env:RAIOS_CANONICAL_HEAD
        port = $Port
        transition_reason = $reportedReason
        verification_reason = $verificationReason
        previous_pid = $reportedPreviousPid
        previous_generation_id = $reportedPreviousGeneration
        previous_started_at = $reportedPreviousStartedAt
        previous_state = $reportedPreviousState
        candidate_pid = $reportedCandidatePid
        candidate_generation_id = $reportedCandidateGeneration
        candidate_state = $reportedCandidateState
        active_pid = $ActivePid
        active_generation_id = $ownerGeneration
        active_state = "ACTIVE"
        active_listener_count = $listeners.Count
        active_listener_match = $activeListenerMatch
        duplicate_mcp = $duplicateMcp
        orphan_generation_count = $orphanPids.Count
        orphan_pids = @($orphanPids)
        owner_head_match = $ownerHeadMatch
        service_generation = $serviceGeneration
        service_generation_match = $serviceGenerationMatch
        handoff_complete = $handoffComplete
        singleton_verdict = $(if ($handoffComplete) { "PASS" } elseif ($duplicateMcp) { "FAIL_DUPLICATE_LISTENER" } elseif ($orphanPids.Count -gt 0) { "FAIL_ORPHAN_GENERATION" } else { "FAIL_INCOMPLETE_HANDOFF" })
    }
    Write-RaiosAtomicJson -Path $LifecycleProjection -Value $doc
    Write-RaiosBoundedLifecycle -Value $doc
    return [pscustomobject]$doc
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
$LifecycleProjection = Join-Path $OwnerDir "generation-handoff.json"
$LifecycleLedger = Join-Path $OwnerDir "generation-lifecycle.jsonl"
$script:TransitionPreviousPid = 0
$script:TransitionPreviousGeneration = $null
$script:TransitionPreviousStartedAt = $null
$script:TransitionReason = "INITIAL_START"
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
            Set-RaiosGenerationTransition -PreviousPid $OwningPid -Reason ([string]$script:RaiosIdentityReason)
            Stop-RaiosListenPid $OwningPid
        } else {
            $ownership_proven = $false
            throw "MCP_LIVE_BUT_UNOWNED port=$Port pid=$OwningPid reason=$script:RaiosIdentityReason"
        }
    } elseif (Test-RaiosMcpHealthy $Health) {
        if (-not $Reload) {
            Set-RaiosGenerationTransition -PreviousPid $OwningPid -Reason "STEADY_STATE_VERIFY"
            $Steady = Write-RaiosGenerationHandoff -CandidatePid $OwningPid -ActivePid $OwningPid -Reason "STEADY_STATE_VERIFY"
            Write-Output "LOCAL_MCP_ALREADY_HEALTHY port=$Port pid=$OwningPid tools=$($Health.tools.Count) head_source=$($Health.head_source)"
            Write-Output "GENERATION_ACTIVE_PID=$($Steady.active_pid)"
            Write-Output "GENERATION_HANDOFF_COMPLETE=$($Steady.handoff_complete)"
            Write-Output "GENERATION_SINGLETON_VERDICT=$($Steady.singleton_verdict)"
            Write-Output "GENERATION_ORPHAN_COUNT=$($Steady.orphan_generation_count)"
            Write-Output "GENERATION_DUPLICATE_MCP=$($Steady.duplicate_mcp)"
            exit 0
        }
        Write-Output "LOCAL_MCP_RELOAD port=$Port pid=$OwningPid"
        Set-RaiosGenerationTransition -PreviousPid $OwningPid -Reason "RELOAD"
        Stop-RaiosListenPid $OwningPid
    } else {
        $recordedContract = ""
        $ownerNow = Read-RaiosOwnerManifest
        if ($ownerNow -and $ownerNow.tool_contract_sha256) { $recordedContract = [string]$ownerNow.tool_contract_sha256 }
        if ($PromoteOwnedGeneration -and (Test-RaiosRecordedProcess $Info $OwningPid)) {
            Write-Output "LOCAL_MCP_PROMOTE_OWNED port=$Port pid=$OwningPid reason=CONTRACT_DRIFT"
            Set-RaiosGenerationTransition -PreviousPid $OwningPid -Reason "CONTRACT_DRIFT"
            Stop-RaiosListenPid $OwningPid
        } elseif ($recordedContract -ne (Get-RaiosToolContractSha)) {
            $ownership_proven = $false
            throw "MCP_LIVE_BUT_UNOWNED port=$Port pid=$OwningPid reason=CONTRACT_DRIFT"
        } elseif ($NoRecover) {
            throw "Existing local MCP listener is unhealthy."
        } else {
            Write-Output "LOCAL_MCP_RECOVER_HUNG port=$Port pid=$OwningPid"
            Set-RaiosGenerationTransition -PreviousPid $OwningPid -Reason "RECOVER_HUNG"
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
$Handoff = Write-RaiosGenerationHandoff -CandidatePid ([int]$Process.Id) -ActivePid $LivePid -Reason ([string]$script:TransitionReason)

Write-Output "LOCAL_MCP_STARTED port=$Port pid=$($Process.Id) tools=$($Health.tools.Count) head_source=$($Health.head_source)"
Write-Output "GENERATION_PREVIOUS_PID=$($Handoff.previous_pid)"
Write-Output "GENERATION_CANDIDATE_PID=$($Handoff.candidate_pid)"
Write-Output "GENERATION_ACTIVE_PID=$($Handoff.active_pid)"
Write-Output "GENERATION_PREVIOUS_STATE=$($Handoff.previous_state)"
Write-Output "GENERATION_CANDIDATE_STATE=$($Handoff.candidate_state)"
Write-Output "GENERATION_ACTIVE_STATE=$($Handoff.active_state)"
Write-Output "GENERATION_HANDOFF_COMPLETE=$($Handoff.handoff_complete)"
Write-Output "GENERATION_SINGLETON_VERDICT=$($Handoff.singleton_verdict)"
Write-Output "GENERATION_ORPHAN_COUNT=$($Handoff.orphan_generation_count)"
Write-Output "GENERATION_DUPLICATE_MCP=$($Handoff.duplicate_mcp)"
Write-Output "HEALTH=$HealthUrl"
Write-Output "GL005_PROVEN=$($Health.gl005_proven)"
Write-Output "NINTH_TOOL=$($Health.ninth_tool)"
Write-Output "SECOND_GATEWAY=$($Health.second_gateway)"
Write-Output "LAUNCH_SOURCE_SHA256=$($SourceFingerprint.fingerprint)"
Write-Output "C5_GENERATION=$GenerationId"
