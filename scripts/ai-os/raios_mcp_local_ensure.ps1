param([int]$Port = 8788)

$ErrorActionPreference = "Stop"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$Server = Join-Path $Repo "scripts\ai-os\raios_mcp\server.py"
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
    $Health = Invoke-RestMethod $HealthUrl -TimeoutSec 5
    if ($Health.ok -and @($Health.tools).Count -eq 8) {
        Write-Output "LOCAL_MCP_ALREADY_HEALTHY port=$Port pid=$($Listener.OwningProcess) tools=8"
        exit 0
    }
    throw "Existing local MCP listener is unhealthy."
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
if (-not $Health.ok -or $Tools.Count -ne 8) {
    throw "Local MCP health validation failed."
}
if ($Tools -notcontains "send_packet" -or $Tools -notcontains "ack_packet") {
    throw "Required packet tools are missing."
}

Write-Output "LOCAL_MCP_STARTED port=$Port pid=$($Process.Id) tools=$($Tools.Count)"
Write-Output "HEALTH=$HealthUrl"
Write-Output "GL005_PROVEN=$($Health.gl005_proven)"
