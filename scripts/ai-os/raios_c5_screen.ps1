# C5 professional system screen on the local Windows control-plane host.
# Not this Cursor session. Open source. Local. No WAL. No extra MCP tools.
# Same C5 process, two lanes:
#   http://127.0.0.1:8765  PUBLIC — for everyone
#   http://127.0.0.1:8876  C1 only — founder console
#
# Paste in PowerShell (from the Greeny-Life repo, or it will try to find it):
#   Set-ExecutionPolicy -Scope Process Bypass
#   powershell -File scripts/ai-os/raios_c5_screen.ps1 -Go
#
# Switches:
#   -Install   register logon tasks + start
#   -Ensure    start if down
#   -Status    print ports/tasks
#   -Open      open both screens in the browser
#   -Go        Install + Ensure + Status + Open
#   -Uninstall remove scheduled tasks
# No switches: launch raios_c5_screen.py
param(
    [switch]$Install,
    [switch]$Ensure,
    [switch]$Status,
    [switch]$Uninstall,
    [switch]$Open,
    [switch]$Go
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Resolve-RaiosRepo {
    if ($env:RAIOS_REPO -and (Test-Path (Join-Path $env:RAIOS_REPO "scripts\ai-os\raios_c5_screen.ps1"))) {
        return (Resolve-Path $env:RAIOS_REPO).Path
    }
    $here = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
    if (Test-Path (Join-Path $here "scripts\ai-os\raios_c5_screen.ps1")) {
        return $here
    }
    try {
        $top = (git rev-parse --show-toplevel 2>$null)
        if ($top -and (Test-Path (Join-Path $top "scripts\ai-os\raios_c5_screen.ps1"))) {
            return $top
        }
    } catch {}
    return $null
}

$Repo = Resolve-RaiosRepo
if (-not $Repo) {
    Write-Host "RAIOS_REPO_MISSING"
    Write-Host "cd to the Greeny-Life folder, or set `$env:RAIOS_REPO, then rerun."
    exit 2
}
Set-Location $Repo
Write-Host "REPO=$Repo"

$TaskScreen = "RAIOS-C5-SCREEN"
$TaskMcp = "RAIOS-MCP"
$ScreenPort = 8765
$C1Port = 8876
$McpPort = 8787
$BindHost = "127.0.0.1"
if ($env:RAIOS_C5_SCREEN_HOST) { $BindHost = [string]$env:RAIOS_C5_SCREEN_HOST }
$McpHost = $BindHost
if ($env:RAIOS_MCP_HOST) { $McpHost = [string]$env:RAIOS_MCP_HOST }

$Python = $null
foreach ($Name in @("python3", "python")) {
    $Cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $Cmd) { continue }
    if ($Cmd.Source) { $Python = [string]$Cmd.Source; break }
    if ($Cmd.Path) { $Python = [string]$Cmd.Path; break }
}
if (-not $Python) {
    Write-Host "PYTHON_MISSING"
    Write-Host "Install Python 3, then rerun. Do not use this script to download models."
    exit 2
}

function Test-RaiosLoopbackPort {
    param([int]$Port)
    try {
        $Client = New-Object System.Net.Sockets.TcpClient
        $Async = $Client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $Ok = $Async.AsyncWaitHandle.WaitOne(400)
        if (-not $Ok) {
            $Client.Close()
            return $false
        }
        $Client.EndConnect($Async)
        $Client.Close()
        return $true
    } catch {
        return $false
    }
}

function Start-RaiosC5ScreenIfDown {
    if ((Test-RaiosLoopbackPort -Port $ScreenPort) -and (Test-RaiosLoopbackPort -Port $C1Port)) {
        Write-Host "SCREEN_UP :$ScreenPort PUBLIC"
        Write-Host "SCREEN_UP :$C1Port C1"
        return
    }
    $ScreenPy = Join-Path $PSScriptRoot "raios_c5_screen.py"
    Start-Process -FilePath $Python -ArgumentList @($ScreenPy, "--host", $BindHost) -WorkingDirectory $Repo -WindowStyle Hidden | Out-Null
    Write-Host "SCREEN_STARTED PUBLIC=http://127.0.0.1:$ScreenPort C1=http://127.0.0.1:$C1Port"
}

function Start-RaiosMcpIfDown {
    if (Test-RaiosLoopbackPort -Port $McpPort) {
        Write-Host "MCP_UP :$McpPort"
        return
    }
    $McpPy = Join-Path $PSScriptRoot "raios_mcp\server.py"
    Start-Process -FilePath $Python -ArgumentList @($McpPy, "--http", "--host", $McpHost, "--port", "$McpPort") -WorkingDirectory $Repo -WindowStyle Hidden | Out-Null
    Write-Host "MCP_STARTED"
}

function Open-RaiosScreens {
    Start-Process "http://127.0.0.1:$ScreenPort"
    Start-Process "http://127.0.0.1:$C1Port"
    Write-Host "OPENED PUBLIC=http://127.0.0.1:$ScreenPort"
    Write-Host "OPENED C1=http://127.0.0.1:$C1Port"
}

function Write-RaiosScreenStatus {
    foreach ($Name in @($TaskScreen, $TaskMcp)) {
        $Existing = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
        if ($null -eq $Existing) {
            Write-Host "TASK_ABSENT $Name"
        } else {
            Write-Host ("TASK {0} {1}" -f $Name, $Existing.State)
        }
    }
    Write-Host ("PUBLIC_PORT={0} up={1} lane=PUBLIC" -f $ScreenPort, (Test-RaiosLoopbackPort -Port $ScreenPort))
    Write-Host ("C1_PORT={0} up={1} lane=C1" -f $C1Port, (Test-RaiosLoopbackPort -Port $C1Port))
    Write-Host ("MCP_PORT={0} up={1}" -f $McpPort, (Test-RaiosLoopbackPort -Port $McpPort))
    Write-Host "PUBLIC=http://127.0.0.1:8765"
    Write-Host "C1=http://127.0.0.1:8876"
    Write-Host "MCP=http://127.0.0.1:8787/mcp"
    Write-Host "DUPLICATE_C5=false"
    Write-Host "CURSOR_SESSION_NE_C5=true"
    Write-Host "NEW_MCP_TOOLS=false"
    Write-Host "GL005_PROVEN=false"
}

function Register-RaiosForeverTask {
    param(
        [string]$Name,
        [string]$Argument
    )
    $Action = New-ScheduledTaskAction -Execute $Python -Argument $Argument -WorkingDirectory $Repo
    $Trigger = New-ScheduledTaskTrigger -AtLogOn
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1)
    $Settings.ExecutionTimeLimit = [TimeSpan]::Zero
    $Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $Name -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force | Out-Null
    Write-Host "TASK_REGISTERED $Name"
}

if ($Uninstall) {
    foreach ($Name in @($TaskScreen, $TaskMcp)) {
        $Existing = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
        if ($null -ne $Existing) {
            Unregister-ScheduledTask -TaskName $Name -Confirm:$false
            Write-Host "TASK_REMOVED $Name"
        } else {
            Write-Host "TASK_ABSENT $Name"
        }
    }
    Write-Host "CURSOR_SESSION_NE_C5=true"
    Write-Host "GL005_PROVEN=false"
    exit 0
}

if ($Go) {
    $Install = $true
    $Ensure = $true
    $Status = $true
    $Open = $true
}

if ($Install) {
    $ScreenPy = Join-Path $PSScriptRoot "raios_c5_screen.py"
    $McpPy = Join-Path $PSScriptRoot "raios_mcp\server.py"
    $ScreenArg = '"{0}" --host {1}' -f $ScreenPy, $BindHost
    $McpArg = '"{0}" --http --host {1} --port {2}' -f $McpPy, $McpHost, $McpPort
    Register-RaiosForeverTask -Name $TaskScreen -Argument $ScreenArg
    Register-RaiosForeverTask -Name $TaskMcp -Argument $McpArg
    Start-RaiosC5ScreenIfDown
    Start-RaiosMcpIfDown
    Write-Host "SCREEN_HOME=CONTROL_PLANE"
    Write-Host "PUBLIC=http://127.0.0.1:8765"
    Write-Host "C1=http://127.0.0.1:8876"
    Write-Host "MCP=http://127.0.0.1:8787/mcp"
    Write-Host "CURSOR_SESSION_NE_C5=true"
    Write-Host "NEW_MCP_TOOLS=false"
    Write-Host "DUPLICATE_C5=false"
    Write-Host "GL005_PROVEN=false"
}

if ($Ensure) {
    Start-RaiosC5ScreenIfDown
    Start-RaiosMcpIfDown
    Write-Host "PUBLIC=http://127.0.0.1:8765"
    Write-Host "C1=http://127.0.0.1:8876"
    Write-Host "MCP=http://127.0.0.1:8787/mcp"
    Write-Host "CURSOR_SESSION_NE_C5=true"
    Write-Host "NEW_MCP_TOOLS=false"
    Write-Host "GL005_PROVEN=false"
}

if ($Open) {
    Open-RaiosScreens
}

if ($Status) {
    Write-RaiosScreenStatus
}

if ($Install -or $Ensure -or $Status -or $Open -or $Go) {
    exit 0
}

& $Python (Join-Path $PSScriptRoot "raios_c5_screen.py") @args
exit $LASTEXITCODE
