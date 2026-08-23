# C5 professional system screen on the local control-plane host.
# Not this Cursor session. Open source. Local. No WAL. No extra MCP tools.
#   powershell -File scripts/ai-os/raios_c5_screen.ps1 -Install
#   powershell -File scripts/ai-os/raios_c5_screen.ps1 -Ensure
#   powershell -File scripts/ai-os/raios_c5_screen.ps1 -Status
#   powershell -File scripts/ai-os/raios_c5_screen.ps1 -Uninstall
# No switches: launch raios_c5_screen.py (same as before).
param(
    [switch]$Install,
    [switch]$Ensure,
    [switch]$Status,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Repo

$TaskScreen = "RAIOS-C5-SCREEN"
$TaskMcp = "RAIOS-MCP"
$ScreenPort = 8765
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
    if (Test-RaiosLoopbackPort -Port $ScreenPort) {
        Write-Host "SCREEN_UP :$ScreenPort"
        return
    }
    $ScreenPy = Join-Path $PSScriptRoot "raios_c5_screen.py"
    Start-Process -FilePath $Python -ArgumentList @($ScreenPy, "--host", $BindHost) -WorkingDirectory $Repo -WindowStyle Hidden | Out-Null
    Write-Host "SCREEN_STARTED"
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

if ($Status) {
    foreach ($Name in @($TaskScreen, $TaskMcp)) {
        $Existing = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
        if ($null -eq $Existing) {
            Write-Host "TASK_ABSENT $Name"
        } else {
            Write-Host ("TASK {0} {1}" -f $Name, $Existing.State)
        }
    }
    Write-Host ("SCREEN_PORT={0} up={1}" -f $ScreenPort, (Test-RaiosLoopbackPort -Port $ScreenPort))
    Write-Host ("MCP_PORT={0} up={1}" -f $McpPort, (Test-RaiosLoopbackPort -Port $McpPort))
    Write-Host "OPEN=http://127.0.0.1:8765"
    Write-Host "MCP=http://127.0.0.1:8787/mcp"
    Write-Host "CURSOR_SESSION_NE_C5=true"
    Write-Host "NEW_MCP_TOOLS=false"
    Write-Host "GL005_PROVEN=false"
    exit 0
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
    Write-Host "OPEN=http://127.0.0.1:8765"
    Write-Host "MCP=http://127.0.0.1:8787/mcp"
    Write-Host "CURSOR_SESSION_NE_C5=true"
    Write-Host "NEW_MCP_TOOLS=false"
    Write-Host "DUPLICATE_C5=false"
    Write-Host "GL005_PROVEN=false"
    exit 0
}

if ($Ensure) {
    Start-RaiosC5ScreenIfDown
    Start-RaiosMcpIfDown
    Write-Host "OPEN=http://127.0.0.1:8765"
    Write-Host "MCP=http://127.0.0.1:8787/mcp"
    Write-Host "CURSOR_SESSION_NE_C5=true"
    Write-Host "NEW_MCP_TOOLS=false"
    Write-Host "GL005_PROVEN=false"
    exit 0
}

& $Python (Join-Path $PSScriptRoot "raios_c5_screen.py") @args
exit $LASTEXITCODE
