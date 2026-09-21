param(
    [string]$Repo = $(if ($env:RAIOS_CANONICAL_REPO) { $env:RAIOS_CANONICAL_REPO } else { (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path }),
    [switch]$InstallTask
)
$ErrorActionPreference = "Stop"
$StableUserProfile = [Environment]::GetFolderPath("UserProfile")
if ([string]::IsNullOrWhiteSpace($StableUserProfile)) { $StableUserProfile = $env:USERPROFILE }
if ([string]::IsNullOrWhiteSpace($StableUserProfile)) { throw "RAIOS_USER_PROFILE_UNAVAILABLE" }
$env:RAIOS_CANONICAL_REPO = $Repo
$TaskName = "RAIOS-C5-Permanent"
$RuntimeRoot = Join-Path $StableUserProfile ".raios\runtime\continuity"
$StatusPath = Join-Path $RuntimeRoot "status.json"
$NetworkStatePath = Join-Path $RuntimeRoot "network-resume.json"
$NetworkResumeCooldownSeconds = 300
$NetworkRequiredSuccesses = 2

# Task registration must not be blocked by a stale continuity instance.
# This repairs the one canonical task without creating a second watchdog.
New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
$TracePath = Join-Path $RuntimeRoot "phase.log"
$RunId = [guid]::NewGuid().ToString("N")
function Mark-Phase([string]$Name) {
    try { Add-Content -LiteralPath $TracePath -Value (([DateTimeOffset]::UtcNow.ToString("o")) + "|RUN=" + $RunId + "|PID=" + $PID + "|" + $Name) } catch {}
}
if ($InstallTask) {
    $ScriptPath = Join-Path $PSScriptRoot "Maintain-RAIOS-Online.ps1"
    $Arguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -Repo "{1}"' -f $ScriptPath, $Repo
    $Action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument $Arguments -WorkingDirectory $Repo
    $Logon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $Pulse = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Days 3650)
    $Settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -Hidden -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger @($Logon,$Pulse) -Settings $Settings -Description "Canonical RAIOS continuity guard: C5, manager, Universal MCP, Command Center, 9Router, NATS and Ollama." -Force | Out-Null
    Write-Host "RAIOS_CONTINUITY_TASK_REGISTERED_WINDOWLESS"
    exit 0
}
Mark-Phase "RUN_START"

$mutex = [Threading.Mutex]::new($false, "Local\RAIOS-Canonical-Continuity")
if (-not $mutex.WaitOne(0)) { Mark-Phase "MUTEX_BUSY"; Write-Host "RAIOS_CONTINUITY_ALREADY_RUNNING"; exit 0 }
Mark-Phase "MUTEX_ACQUIRED"
try {
    function Get-JsonHealth([string]$Url,[int]$Timeout=4) {
        try { return Invoke-RestMethod -Uri $Url -TimeoutSec $Timeout }
        catch { return $null }
    }
    function Test-Tcp([int]$Port) {
        try {
            $client = [Net.Sockets.TcpClient]::new()
            $pending = $client.BeginConnect("127.0.0.1",$Port,$null,$null)
            $ok = $pending.AsyncWaitHandle.WaitOne(800) -and $client.Connected
            $client.Close()
            return $ok
        } catch { return $false }
    }
    function Test-Internet {
        try {
            $client = [Net.Sockets.TcpClient]::new()
            $pending = $client.BeginConnect("1.1.1.1",443,$null,$null)
            $ok = $pending.AsyncWaitHandle.WaitOne(1500) -and $client.Connected
            $client.Close()
            return $ok
        } catch { return $false }
    }
    function Read-NetworkState {
        try { return Get-Content -LiteralPath $NetworkStatePath -Raw | ConvertFrom-Json }
        catch { return [pscustomobject]@{ online = $false; success_streak = 0; last_resume_at = $null } }
    }
    function Write-JsonFileAtomic([string]$Path,[hashtable]$Value) {
        $Value["generated_at"] = [DateTimeOffset]::UtcNow.ToString("o")
        $tmp = $Path + ".tmp-" + [guid]::NewGuid().ToString("N")
        try {
            $Value | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $tmp -Encoding UTF8
            Get-Content -LiteralPath $tmp -Raw | ConvertFrom-Json | Out-Null
            Move-Item -LiteralPath $tmp -Destination $Path -Force
        } finally { Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue }
    }
    function Write-AtomicJson([hashtable]$Value) {
        $Value["generated_at"] = [DateTimeOffset]::UtcNow.ToString("o")
        $tmp = Join-Path $RuntimeRoot ("status.json.tmp-" + [guid]::NewGuid().ToString("N"))
        try {
            $Value | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $tmp -Encoding UTF8
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

    $Head = (git -C $Repo rev-parse HEAD).Trim()
    Mark-Phase "HEAD_OK"
    $C5CanonicalSourcePaths = @("requirements-c5.txt","src/raios/c5_gateway","src/raios/search_cortex","src/raios/neuro_lingua",".ai-os/mcp/C5-MAINTENANCE-LAWS.json","scripts/ai-os/raios_c5_maintenance_guard.py","scripts/runtime/Deploy-RAIOS-C5.ps1")
    function Test-C5DeploymentCurrent([string]$DeployedHead) {
        if (-not $DeployedHead -or $DeployedHead -eq "UNKNOWN") { return $false }
        if ($DeployedHead -eq $Head) { return $true }
        try {
            & git -C $Repo cat-file -e ($DeployedHead + "^{commit}") 2>$null
            if ($LASTEXITCODE -ne 0) { return $false }
            & git -C $Repo diff --quiet $DeployedHead $Head -- $C5CanonicalSourcePaths
            return ($LASTEXITCODE -eq 0)
        } catch { return $false }
    }
    $CommandCenterCanonicalSourcePaths = @("src/raios/command_center","src/raios/goals","src/raios/search_cortex","src/raios/resource_fabric","src/raios/ai_gateway","src/raios/council_ops","src/raios/a2a","scripts/ai-os/raios_mcp","scripts/runtime/Deploy-RAIOS-Command-Center.ps1")
    function Test-CommandCenterDeploymentCurrent([string]$DeployedHead) {
        if (-not $DeployedHead -or $DeployedHead -eq "UNKNOWN") { return $false }
        if ($DeployedHead -eq $Head) { return $true }
        try {
            & git -C $Repo cat-file -e ($DeployedHead + "^{commit}") 2>$null
            if ($LASTEXITCODE -ne 0) { return $false }
            & git -C $Repo diff --quiet $DeployedHead $Head -- $CommandCenterCanonicalSourcePaths
            return ($LASTEXITCODE -eq 0)
        } catch { return $false }
    }
    $actions = [System.Collections.Generic.List[string]]::new()
    $errors = [System.Collections.Generic.List[string]]::new()

    # Internet affects remote observers only. Two successes debounce reconnect;
    # persisted pending/cooldown state makes each one-minute pulse idempotent.
    $networkPrevious = Read-NetworkState
    $internetProbe = [bool](Test-Internet)
    $successStreak = if ($internetProbe) { [int]$networkPrevious.success_streak + 1 } else { 0 }
    $internetOnline = $internetProbe -and $successStreak -ge $NetworkRequiredSuccesses
    $lastResume = $null
    if ($networkPrevious.last_resume_at) {
        try { $lastResume = [DateTimeOffset]::Parse([string]$networkPrevious.last_resume_at) } catch {}
    }
    $cooldownElapsed = -not $lastResume -or (([DateTimeOffset]::UtcNow - $lastResume).TotalSeconds -ge $NetworkResumeCooldownSeconds)
    $reconnected = $internetOnline -and -not [bool]$networkPrevious.online
    $resumePending = $reconnected -or [bool]$networkPrevious.resume_pending
    $resumeTriggered = $false
    $resumeAt = if ($lastResume) { $lastResume.ToString("o") } else { $null }
    $resumeEligible = $internetOnline -and $resumePending -and $cooldownElapsed
    Mark-Phase "NETWORK_OK"

    $ollamaHealth = Get-JsonHealth "http://127.0.0.1:11434/api/tags" 3
    if (-not $ollamaHealth) {
        $ollama = Get-Command ollama.exe -ErrorAction SilentlyContinue
        $portOpen = Test-Tcp 11434
        $ollamaProc = Get-Process -Name ollama -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($portOpen -and $ollamaProc) {
            try {
                Stop-Process -Id $ollamaProc.Id -Force -ErrorAction Stop
                $actions.Add("RECYCLE_UNRESPONSIVE_OLLAMA")
                Start-Sleep -Milliseconds 750
            } catch {
                $errors.Add("OLLAMA_RECYCLE_FAILED:" + $_.Exception.GetType().Name)
            }
        } elseif ($portOpen -and -not $ollamaProc) {
            $errors.Add("PORT_11434_NON_OLLAMA_OWNER")
        }
        if ($ollama -and -not (Test-Tcp 11434)) {
            Start-Process -FilePath $ollama.Source -ArgumentList @("serve") -WindowStyle Hidden -RedirectStandardOutput (Join-Path $RuntimeRoot "ollama.out.log") -RedirectStandardError (Join-Path $RuntimeRoot "ollama.err.log") | Out-Null
            $actions.Add("START_EXISTING_OLLAMA")
            for ($i=0; $i -lt 6; $i++) {
                Start-Sleep -Seconds 1
                $ollamaHealth = Get-JsonHealth "http://127.0.0.1:11434/api/tags" 3
                if ($ollamaHealth) { break }
            }
        } elseif (-not $ollama) {
            $errors.Add("OLLAMA_COMMAND_MISSING")
        }
        if (-not $ollamaHealth) { $errors.Add("OLLAMA_HTTP_NOT_READY") }
    }
    $ollamaHttpReady = [bool]$ollamaHealth
    if (Test-Tcp 11434) { Mark-Phase "OLLAMA_PORT_UP" }
    if ($ollamaHttpReady) { Mark-Phase "OLLAMA_HTTP_READY" }
    # Fast continuity proof: installation/readiness only; semantic inference is certified separately.
    $ollamaModelReady = $false
    if ($ollamaHttpReady) {
        try {
            $ollamaModelReady = [bool](@($ollamaHealth.models | Where-Object {
                [string]$_.name -eq "qwen3:0.6b" -or [string]$_.model -eq "qwen3:0.6b"
            }).Count -gt 0)
        } catch { $ollamaModelReady = $false }
    }
    if ($ollamaModelReady) { Mark-Phase "OLLAMA_MODEL_READY" }
    if (-not $ollamaHttpReady) { $errors.Add("OLLAMA_HTTP_NOT_READY") }
    if ($ollamaHttpReady -and -not $ollamaModelReady) { $errors.Add("OLLAMA_MODEL_NOT_READY") }
    if ($ollamaHttpReady -and $ollamaModelReady) { Mark-Phase "OLLAMA_OK" }

    if (-not (Test-Tcp 4222)) {
        try {
            $natsTask = Get-ScheduledTask -TaskName "RAIOS-NATS-Local" -ErrorAction Stop
            if ($natsTask.State -ne "Running") {
                Start-ScheduledTask -TaskName "RAIOS-NATS-Local"
                $actions.Add("START_EXISTING_NATS_TASK")
            } else {
                $actions.Add("WAIT_EXISTING_NATS_TASK")
            }
            for ($i=0; $i -lt 20; $i++) {
                if (Test-Tcp 4222) { break }
                Start-Sleep -Seconds 1
            }
            if (-not (Test-Tcp 4222)) { $errors.Add("NATS_NOT_READY_AFTER_WAIT") }
        } catch { $errors.Add("NATS_RESTORE_FAILED:" + $_.Exception.GetType().Name) }
    }
    Mark-Phase "NATS_OK"

    $c5 = Get-JsonHealth "http://127.0.0.1:8766/health" 12
    $loop = if ($c5 -and $c5.cognitive_loop) { $c5.cognitive_loop } else { Get-JsonHealth "http://127.0.0.1:8766/v1/cognitive/status" 6 }
    $c5NeedsRepair = (
        -not $c5 -or $c5.status -ne "ONLINE" -or -not (Test-C5DeploymentCurrent ([string]$c5.canonical_head)) -or
        $c5.environment.dependency_audit -ne "PASS" -or $c5.environment.pytest_available -ne $true -or
        -not $loop -or $loop.manager.alive -ne $true -or $loop.evolution.alive -ne $true
    )
    if ($c5NeedsRepair) {
        Mark-Phase "C5_REPAIR_ATTEMPT"
        try {
            & (Join-Path $PSScriptRoot "Ensure-RAIOS-Cognitive-Loop.ps1") -Repo $Repo
            $actions.Add("ENSURE_EXISTING_COGNITIVE_LOOP")
        } catch {
            $msg = ([string]$_.Exception.Message -replace '[\r\n]+',' ')
            if ($msg.Length -gt 240) { $msg = $msg.Substring(0,240) }
            $errors.Add("COGNITIVE_LOOP_RESTORE_FAILED:" + $_.Exception.GetType().Name + ":" + $msg)
        }
    }
    $c5 = Get-JsonHealth "http://127.0.0.1:8766/health" 12
    $loop = if ($c5 -and $c5.cognitive_loop) { $c5.cognitive_loop } else { Get-JsonHealth "http://127.0.0.1:8766/v1/cognitive/status" 6 }
    $c5Ready = [bool]($c5 -and $c5.status -eq "ONLINE" -and (Test-C5DeploymentCurrent ([string]$c5.canonical_head)) -and $loop -and $loop.manager.alive -eq $true -and $loop.evolution.alive -eq $true)
    if ($c5Ready) { Mark-Phase "C5_LOOP_OK" } else { Mark-Phase "C5_REPAIR_FAILED" }

    $center = Get-JsonHealth "http://127.0.0.1:8770/health" 12
    $centerReady = [bool]($center -and $center.status -eq "ONLINE" -and (Test-CommandCenterDeploymentCurrent ([string]$center.canonical_head)))
    if (-not $centerReady) {
        Mark-Phase "CC_REPAIR_ATTEMPT"
        try {
            & (Join-Path $PSScriptRoot "Deploy-RAIOS-Command-Center.ps1") -HeadOnlyRecovery
            $actions.Add("DEPLOY_COMMAND_CENTER_HEAD_ONLY_RECOVERY")
        } catch {
            $msg = ([string]$_.Exception.Message -replace '[\r\n]+',' ')
            if ($msg.Length -gt 240) { $msg = $msg.Substring(0,240) }
            $errors.Add("COMMAND_CENTER_RESTORE_FAILED:" + $_.Exception.GetType().Name + ":" + $msg)
        }
        $center = Get-JsonHealth "http://127.0.0.1:8770/health" 12
        $centerReady = [bool]($center -and $center.status -eq "ONLINE" -and (Test-CommandCenterDeploymentCurrent ([string]$center.canonical_head)))
    }
    if ($centerReady) { Mark-Phase "CC_OK" } else { Mark-Phase "CC_REPAIR_FAILED" }

    # Universal MCP is part of the same canonical continuity fabric; never create a second watchdog.
    $mcp = Get-JsonHealth "http://127.0.0.1:8788/health" 4
    $mcpReady = [bool]($mcp -and $mcp.ok -eq $true -and $mcp.tool_count -eq 8 -and $mcp.second_gateway -eq $false)
    if (-not $mcpReady) {
        try {
            & (Join-Path $PSScriptRoot "Deploy-RAIOS-MCP.ps1")
            $actions.Add("DEPLOY_EXISTING_UNIVERSAL_MCP")
            $mcp = Get-JsonHealth "http://127.0.0.1:8788/health" 4
            $mcpReady = [bool]($mcp -and $mcp.ok -eq $true -and $mcp.tool_count -eq 8 -and $mcp.second_gateway -eq $false)
            if (-not $mcpReady) { $errors.Add("UNIVERSAL_MCP_NOT_READY_AFTER_DEPLOY") }
        } catch { $errors.Add("UNIVERSAL_MCP_RESTORE_FAILED:" + $_.Exception.GetType().Name) }
    }
    Mark-Phase "MCP_OK"

    try {
        & (Join-Path $PSScriptRoot "Ensure-RAIOS-Seat-Sessions.ps1") -Repo $Repo
        $actions.Add("ENSURE_RAIOS_SEAT_SESSIONS")
    } catch { $errors.Add("SEAT_SESSION_RESTORE_FAILED:" + $_.Exception.GetType().Name) }
    Mark-Phase "SEAT_SESSIONS_OK"

    # The installed 9Router dashboard may keep HTTP/1.1 responses open.
    # Continuity must never block on page rendering; detailed HTTP truth remains
    # in Command Center while this guard uses the bounded local listener proof.
    $routerOnline = Test-Tcp 20128
    if (-not $routerOnline) {
        # Resolve the installed package but never execute its console .cmd shim.
        # Direct Node + cli.js + tray is the package's own canonical windowless path.
        $routerCommand = Get-Command 9router.cmd -ErrorAction SilentlyContinue
        $routerRoot = if ($routerCommand) {
            Split-Path -Parent $routerCommand.Source
        } else {
            Join-Path $env:APPDATA "npm"
        }
        $routerCli = Join-Path $routerRoot "node_modules\9router\cli.js"
        $node = Get-Command node.exe -ErrorAction SilentlyContinue
        if ($node -and (Test-Path -LiteralPath $routerCli)) {
            Start-Process -FilePath $node.Source -ArgumentList @($routerCli,"--tray","--host","127.0.0.1","--port","20128","--no-browser","--skip-update") -WindowStyle Hidden -RedirectStandardOutput (Join-Path $RuntimeRoot "9router.out.log") -RedirectStandardError (Join-Path $RuntimeRoot "9router.err.log") | Out-Null
            $actions.Add("START_EXISTING_9ROUTER_WINDOWLESS")
            Start-Sleep -Seconds 5
        } else { $errors.Add("9ROUTER_WINDOWLESS_ENTRY_MISSING") }
    }
    Mark-Phase "ROUTER_OK"

    $c5 = Get-JsonHealth "http://127.0.0.1:8766/health" 12
    $loop = if ($c5 -and $c5.cognitive_loop) { $c5.cognitive_loop } else { Get-JsonHealth "http://127.0.0.1:8766/v1/cognitive/status" 6 }
    $center = Get-JsonHealth "http://127.0.0.1:8770/health" 12
    $routerOnline = Test-Tcp 20128
    $services = [ordered]@{
        C5 = [bool]($c5 -and $c5.status -eq "ONLINE")
        MANAGER = [bool]($loop -and $loop.manager.alive -eq $true)
        EVOLUTION = [bool]($loop -and $loop.evolution.alive -eq $true)
        COMMAND_CENTER = [bool]($center -and $center.status -eq "ONLINE")
        UNIVERSAL_MCP = [bool]$mcpReady
        ROUTER_9 = $routerOnline
        NATS = [bool](Test-Tcp 4222)
        OLLAMA = [bool](Get-JsonHealth "http://127.0.0.1:11434/api/tags" 3)
    }
    $localReady = -not (@($services.Values) -contains $false)
    Mark-Phase "SERVICES_OK"
    if ($resumeEligible -and $localReady -and $errors.Count -eq 0) {
        $PythonWindowless = Join-Path $StableUserProfile ".raios\runtime\c5\.venv\Scripts\pythonw.exe"
        if (Test-Path -LiteralPath $PythonWindowless) {
            $env:PYTHONPATH = Join-Path $Repo "src"
            Start-Process -FilePath $PythonWindowless -ArgumentList @("-m","raios.manager.live_manager","--refresh-resources") -WorkingDirectory $Repo -WindowStyle Hidden | Out-Null
            $actions.Add("NETWORK_RESUME_RESOURCES")
            $resumeTriggered = $true
            $resumeAt = [DateTimeOffset]::UtcNow.ToString("o")
        } else { $errors.Add("NETWORK_RESUME_PYTHONW_MISSING") }
    }
    Mark-Phase "BEFORE_NETWORK_STATE_WRITE"
    Write-JsonFileAtomic -Path $NetworkStatePath -Value @{
        schema = "raios.network-resume.v1"
        online = $internetOnline
        probe_ok = $internetProbe
        success_streak = $successStreak
        reconnect_detected = $reconnected
        resume_pending = [bool]($resumePending -and -not $resumeTriggered)
        resume_triggered = $resumeTriggered
        last_resume_at = $resumeAt
        cooldown_seconds = $NetworkResumeCooldownSeconds
        safe_jobs = @("RESOURCES")
        local_services_required = $true
        paid_resource_created = $false
        gpu_session_started = $false
        model_download_executed = $false
        canonical_mutation = $false
    }
    Mark-Phase "NETWORK_STATE_WRITTEN"
    $online = $localReady -and $errors.Count -eq 0
    Mark-Phase "BEFORE_STATUS_WRITE"
    Write-AtomicJson @{
        schema = "raios.continuity.status.v2"
        status = $(if ($online) { "ONLINE" } else { "DEGRADED" })
        canonical_head = $Head
        services = $services
        actions = @($actions)
        errors = @($errors)
        task_name = $TaskName
        task_reused = $true
        interval_seconds = 60
        self_healing = $true
        internet_online = $internetOnline
        network_resume_triggered = $resumeTriggered
        network_state_path = $NetworkStatePath
        auto_canonical_mutation = $false
    }
    Mark-Phase "STATUS_WRITTEN"
    Write-Host ("RAIOS_CONTINUITY=" + $(if ($online) { "ONLINE" } else { "DEGRADED" }))
    Write-Host ("ACTIONS=" + (@($actions) -join ","))
    if (-not $online) { exit 2 }
} finally {
    Mark-Phase "FINALLY_ENTER"
    try { $mutex.ReleaseMutex() } catch {}
    $mutex.Dispose()
    Mark-Phase "MUTEX_RELEASED"
}
Mark-Phase "SCRIPT_EXIT"
exit 0
