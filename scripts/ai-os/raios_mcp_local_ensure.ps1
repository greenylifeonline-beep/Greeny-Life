param([int]$Port = 8788, [switch]$Reload)

$ErrorActionPreference = "Stop"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$Server = Join-Path $Repo "scripts\ai-os\raios_mcp\server.py"
$PolicyPath = Join-Path $Repo '.ai-os\mcp\POLICY.json'
. (Join-Path $Repo 'scripts\ai-os\raios_mcp\Readiness.ps1')
$ReceiptDir = Join-Path $Repo ".ai-os\receipts\command-fabric"
$HealthUrl = "http://127.0.0.1:$Port/health"

if (-not (Test-Path $Python)) { throw "Missing Python: $Python" }
if (-not (Test-Path $Server)) { throw "Missing MCP server: $Server" }
New-Item -ItemType Directory -Force -Path $ReceiptDir | Out-Null

$Listener = Get-NetTCPConnection -LocalAddress "127.0.0.1" -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($Listener) {
    $Info = Get-CimInstance Win32_Process -Filter "ProcessId=$($Listener.OwningProcess)"
    if ($Info.CommandLine -notmatch "raios_mcp[\\/]server\.py") {
        throw "Port $Port is owned by $($Info.Name), PID $($Listener.OwningProcess)."
    }
    $Health = $null
    try { $Health = Invoke-RestMethod $HealthUrl -TimeoutSec 5 } catch {}
    if (-not $Reload -and (Test-RaiosMcpHealth -Health $Health -PolicyPath $PolicyPath)) {
        Write-Output "LOCAL_MCP_ALREADY_HEALTHY port=$Port pid=$($Listener.OwningProcess) tools=$(@($Health.tools).Count)"
        exit 0
    }
    if (-not $Reload) {
        throw "Existing local MCP listener needs reload or is unhealthy."
    }
    if ([int]$Listener.OwningProcess -le 4) { throw "Refusing unsafe listener PID $($Listener.OwningProcess)." }
    Stop-Process -Id ([int]$Listener.OwningProcess) -Force
    for ($i = 0; $i -lt 40; $i++) {
        if (-not (Get-Process -Id ([int]$Listener.OwningProcess) -ErrorAction SilentlyContinue)) { break }
        Start-Sleep -Milliseconds 250
    }
}
$Stdout = Join-Path $ReceiptDir "LOCAL-MCP-$Port.stdout.log"
$Stderr = Join-Path $ReceiptDir "LOCAL-MCP-$Port.stderr.log"
$Arguments = @($Server, "--http", "--host", "127.0.0.1", "--port", "$Port")
$Process = Start-Process -FilePath $Python -ArgumentList $Arguments -WorkingDirectory $Repo -RedirectStandardOutput $Stdout -RedirectStandardError $Stderr -WindowStyle Hidden -PassThru

Start-Sleep -Seconds 2
if ($Process.HasExited) {
    Get-Content $Stderr -ErrorAction SilentlyContinue
    throw "Local MCP failed to start."
}

$Health = Invoke-RestMethod $HealthUrl -TimeoutSec 5
$Tools = @($Health.tools)
if (-not (Test-RaiosMcpHealth -Health $Health -PolicyPath $PolicyPath)) {
    throw "Local MCP health does not match the repository tool and transport contract."
}

Write-Output "LOCAL_MCP_STARTED port=$Port pid=$($Process.Id) tools=$($Tools.Count)"
Write-Output "HEALTH=$HealthUrl"
Write-Output "GL005_PROVEN=$($Health.gl005_proven)"
