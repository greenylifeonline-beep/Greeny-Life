param(
    [string]$Repo = $(if ($env:RAIOS_CANONICAL_REPO) { $env:RAIOS_CANONICAL_REPO } else { (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path }),
    [switch]$InstallTask
)
$ErrorActionPreference = "Stop"
$env:RAIOS_CANONICAL_REPO = $Repo
$TaskName = "RAIOS-C5-Permanent"
$RuntimeRoot = Join-Path $env:USERPROFILE ".raios\runtime\continuity"
$StatusPath = Join-Path $RuntimeRoot "status.json"
$mutex = [Threading.Mutex]::new($false, "Local\RAIOS-Canonical-Continuity")
if (-not $mutex.WaitOne(0)) { Write-Host "RAIOS_CONTINUITY_ALREADY_RUNNING"; exit 0 }
try {
    New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
    if ($InstallTask) {
        $PowerShell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
        $Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Repo `"$Repo`""
        $Action = New-ScheduledTaskAction -Execute $PowerShell -Argument $Arguments -WorkingDirectory $Repo
        $Logon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
        $Pulse = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Days 3650)
        $Settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Minutes 15) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
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
        -not $loop -or $loop.manager.alive -ne $true
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
        $router = Get-Command 9router.cmd -ErrorAction SilentlyContinue
        if (-not $router) {
            $fallback = Join-Path $env:APPDATA "npm\9router.cmd"
            if (Test-Path -LiteralPath $fallback) { $router = [pscustomobject]@{ Source = $fallback } }
        }
        if ($router) {
            Start-Process -FilePath $router.Source -ArgumentList @("--host","127.0.0.1","--port","20128","--no-browser","--skip-update") -WindowStyle Hidden -RedirectStandardOutput (Join-Path $RuntimeRoot "9router.out.log") -RedirectStandardError (Join-Path $RuntimeRoot "9router.err.log") | Out-Null
            $actions.Add("START_EXISTING_9ROUTER")
            Start-Sleep -Seconds 5
        } else { $errors.Add("9ROUTER_COMMAND_MISSING") }
    }

    $c5 = Get-JsonHealth "http://127.0.0.1:8766/health"
    $loop = Get-JsonHealth "http://127.0.0.1:8766/v1/cognitive/status"
    $center = Get-JsonHealth "http://127.0.0.1:8770/health"
    $routerOnline = Test-Tcp 20128
    $services = [ordered]@{
        C5 = [bool]($c5 -and $c5.status -eq "ONLINE")
        MANAGER = [bool]($loop -and $loop.manager.alive -eq $true)
        COMMAND_CENTER = [bool]($center -and $center.status -eq "ONLINE")
        ROUTER_9 = $routerOnline
        NATS = [bool](Test-Tcp 4222)
        OLLAMA = [bool](Test-Tcp 11434)
    }
    $online = -not (@($services.Values) -contains $false) -and $errors.Count -eq 0
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
        auto_canonical_mutation = $false
    }
    Write-Host ("RAIOS_CONTINUITY=" + $(if ($online) { "ONLINE" } else { "DEGRADED" }))
    Write-Host ("ACTIONS=" + (@($actions) -join ","))
    if (-not $online) { exit 2 }
} finally {
    try { $mutex.ReleaseMutex() } catch {}
    $mutex.Dispose()
}
