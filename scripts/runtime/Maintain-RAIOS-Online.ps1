param(
    [string]$Repo = $(if ($env:RAIOS_CANONICAL_REPO) { $env:RAIOS_CANONICAL_REPO } else { (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path }),
    [switch]$InstallTask
)
$ErrorActionPreference = "Stop"
$StableUserProfile = [Environment]::GetFolderPath("UserProfile")
$env:RAIOS_CANONICAL_REPO = $Repo
$TaskName = "RAIOS-C5-Permanent"
$RuntimeRoot = Join-Path $StableUserProfile ".raios\runtime\continuity"
$StatusPath = Join-Path $RuntimeRoot "status.json"
$NetworkStatePath = Join-Path $RuntimeRoot "network-resume.json"
$NetworkResumeCooldownSeconds = 300
$NetworkRequiredSuccesses = 2
$mutex = [Threading.Mutex]::new($false, "Local\RAIOS-Canonical-Continuity")
if (-not $mutex.WaitOne(0)) { Write-Host "RAIOS_CONTINUITY_ALREADY_RUNNING"; exit 0 }
try {
    New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
    if ($InstallTask) {
        $WScript = "$env:SystemRoot\System32\wscript.exe"
        $Launcher = Join-Path $PSScriptRoot "Run-RAIOS-Continuity-Hidden.vbs"
        if (-not (Test-Path -LiteralPath $Launcher)) { throw "WINDOWLESS_LAUNCHER_MISSING" }
        $Arguments = "`"$Launcher`" `"$Repo`""
        $Action = New-ScheduledTaskAction -Execute $WScript -Argument $Arguments -WorkingDirectory $Repo
        $Logon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
        $Pulse = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Days 3650)
        $Settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -Hidden -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Minutes 15) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
        Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger @($Logon,$Pulse) -Settings $Settings -Description "Canonical RAIOS continuity guard: C5, manager, Command Center, 9Router, NATS and Ollama." -Force | Out-Null
    }

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
            $pending = $client.BeginConnect("github.com",443,$null,$null)
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
    $actions = [System.Collections.Generic.List[string]]::new()
    $errors = [System.Collections.Generic.List[string]]::new()

    # Internet is required only for remote observation. C5 and Ollama remain local.
    # Two consecutive successes debounce a reconnect; the persisted cooldown makes
    # the pulse idempotent across scheduled-task invocations.
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

    if (-not (Test-Tcp 11434)) {
        $ollama = Get-Command ollama.exe -ErrorAction SilentlyContinue
        if ($ollama) {
            Start-Process -FilePath $ollama.Source -ArgumentList @("serve") -WindowStyle Hidden -RedirectStandardOutput (Join-Path $RuntimeRoot "ollama.out.log") -RedirectStandardError (Join-Path $RuntimeRoot "ollama.err.log") | Out-Null
            $actions.Add("START_EXISTING_OLLAMA")
            Start-Sleep -Seconds 3
        } else { $errors.Add("OLLAMA_COMMAND_MISSING") }
    }

    if (-not (Test-Tcp 4222)) {
        try {
            Start-ScheduledTask -TaskName "RAIOS-NATS-Local"
            $actions.Add("START_EXISTING_NATS_TASK")
            Start-Sleep -Seconds 2
        } catch { $errors.Add("NATS_RESTORE_FAILED:" + $_.Exception.GetType().Name) }
    }

    $c5 = Get-JsonHealth "http://127.0.0.1:8766/health"
    $loop = Get-JsonHealth "http://127.0.0.1:8766/v1/cognitive/status"
    $c5NeedsRepair = (
        -not $c5 -or $c5.status -ne "ONLINE" -or $c5.canonical_head -ne $Head -or
        $c5.environment.dependency_audit -ne "PASS" -or $c5.environment.pytest_available -ne $true -or
        -not $loop -or $loop.manager.alive -ne $true -or $loop.evolution.alive -ne $true
    )
    if ($c5NeedsRepair) {
        try {
            & (Join-Path $PSScriptRoot "Ensure-RAIOS-Cognitive-Loop.ps1") -Repo $Repo
            $actions.Add("ENSURE_EXISTING_COGNITIVE_LOOP")
        } catch { $errors.Add("COGNITIVE_LOOP_RESTORE_FAILED:" + $_.Exception.GetType().Name) }
    }

    $center = Get-JsonHealth "http://127.0.0.1:8770/health"
    if (-not $center -or $center.status -ne "ONLINE" -or $center.canonical_head -ne $Head) {
        try {
            & (Join-Path $PSScriptRoot "Deploy-RAIOS-Command-Center.ps1")
            $actions.Add("DEPLOY_EXISTING_COMMAND_CENTER")
        } catch { $errors.Add("COMMAND_CENTER_RESTORE_FAILED:" + $_.Exception.GetType().Name) }
    }

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

    $c5 = Get-JsonHealth "http://127.0.0.1:8766/health"
    $loop = Get-JsonHealth "http://127.0.0.1:8766/v1/cognitive/status"
    $center = Get-JsonHealth "http://127.0.0.1:8770/health"
    $routerOnline = Test-Tcp 20128
    $services = [ordered]@{
        C5 = [bool]($c5 -and $c5.status -eq "ONLINE")
        MANAGER = [bool]($loop -and $loop.manager.alive -eq $true)
        EVOLUTION = [bool]($loop -and $loop.evolution.alive -eq $true)
        COMMAND_CENTER = [bool]($center -and $center.status -eq "ONLINE")
        ROUTER_9 = $routerOnline
        NATS = [bool](Test-Tcp 4222)
        OLLAMA = [bool](Test-Tcp 11434)
    }
    $localReady = -not (@($services.Values) -contains $false)
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
    $online = $localReady -and $errors.Count -eq 0
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
    Write-Host ("RAIOS_CONTINUITY=" + $(if ($online) { "ONLINE" } else { "DEGRADED" }))
    Write-Host ("ACTIONS=" + (@($actions) -join ","))
    if (-not $online) { exit 2 }
} finally {
    try { $mutex.ReleaseMutex() } catch {}
    $mutex.Dispose()
}
