param(
  [string]$Repo = "C:\Users\Ghanam\Documents\Codex\Greeny-Life"
)
$ErrorActionPreference = "Continue"
$UserHome = $HOME
$Py = Join-Path $UserHome ".raios\runtime\c5\.venv\Scripts\python.exe"
$PyW = Join-Path $UserHome ".raios\runtime\c5\.venv\Scripts\pythonw.exe"
$Continuity = Join-Path $UserHome ".raios\runtime\continuity"
$CcRuntime = Join-Path $UserHome ".raios\runtime\command-center"
$CcLogs = Join-Path $CcRuntime "logs"
$Ops = Join-Path $UserHome ".raios\runtime\council-ops"
New-Item -ItemType Directory -Force -Path $Continuity, $CcLogs | Out-Null

function Test-Tcp([int]$Port) {
  try {
    $c = [Net.Sockets.TcpClient]::new()
    $ok = $c.BeginConnect("127.0.0.1", $Port, $null, $null).AsyncWaitHandle.WaitOne(400) -and $c.Connected
    $c.Close()
    return [bool]$ok
  } catch { return $false }
}

function Get-ListenPid([int]$Port) {
  $line = netstat -ano | Select-String -Pattern (":$Port\s+.*?LISTENING\s+(\d+)") | Select-Object -Last 1
  if (-not $line) { return $null }
  if ($line.Line -match "\s(\d+)\s*$") { return [int]$Matches[1] }
  return $null
}

function Wait-Tcp([int]$Port, [int]$Seconds, [bool]$WantOpen) {
  for ($i = 0; $i -lt $Seconds; $i++) {
    $open = Test-Tcp $Port
    if ($open -eq $WantOpen) { return $true }
    Start-Sleep -Milliseconds 400
  }
  return $false
}

Write-Host "=== PIDS ==="
foreach ($p in 20128, 4222, 8766, 8770, 8788) {
  $listenPid = Get-ListenPid $p
  Write-Host "PORT $p TCP=$(Test-Tcp $p) PID=$listenPid"
}

Write-Host "=== NATS ==="
try {
  $nats = Get-ScheduledTask -TaskName "RAIOS-NATS-Local" -ErrorAction Stop
  Write-Host "NATS_TASK_STATE=$($nats.State)"
  if (-not (Test-Tcp 4222)) {
    Start-ScheduledTask -TaskName "RAIOS-NATS-Local"
    Write-Host "NATS_START_ISSUED=true"
    [void](Wait-Tcp 4222 20 $true)
  }
} catch { Write-Host "NATS_ERR=$($_.Exception.Message)" }
Write-Host "NATS_TCP=$(Test-Tcp 4222)"

Write-Host "=== 9ROUTER ==="
if (-not (Test-Tcp 20128)) {
  $cli = Join-Path $env:APPDATA "npm\node_modules\9router\cli.js"
  $node = (Get-Command node.exe -ErrorAction SilentlyContinue).Source
  Write-Host "NODE=$node"
  Write-Host "CLI_EXISTS=$(Test-Path -LiteralPath $cli)"
  if ($node -and (Test-Path -LiteralPath $cli)) {
    $stamp = Get-Date -Format "yyyyMMddHHmmss"
    $out = Join-Path $Continuity "9router.$stamp.out.log"
    $err = Join-Path $Continuity "9router.$stamp.err.log"
    $proc = Start-Process -FilePath $node -ArgumentList @($cli, "--tray", "--host", "127.0.0.1", "--port", "20128", "--no-browser", "--skip-update") -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
    Write-Host "9ROUTER_START_PID=$($proc.Id)"
    [void](Wait-Tcp 20128 15 $true)
  } else {
    Write-Host "9ROUTER_WINDOWLESS_ENTRY_MISSING"
  }
}
Write-Host "9ROUTER_TCP=$(Test-Tcp 20128) PID=$(Get-ListenPid 20128)"

Write-Host "=== CC_RESTART_FROM_SRC ==="
$oldCc = Get-ListenPid 8770
Write-Host "OLD_CC_PID=$oldCc"
if ($oldCc) {
  & taskkill.exe /F /PID $oldCc 2>&1 | ForEach-Object { Write-Host $_ }
  [void](Wait-Tcp 8770 20 $false)
}
Write-Host "CC_TCP_AFTER_KILL=$(Test-Tcp 8770)"
if (-not (Test-Tcp 8770)) {
  $head = (git -C $Repo rev-parse HEAD).Trim()
  $env:RAIOS_CANONICAL_REPO = $Repo
  $env:RAIOS_CANONICAL_HEAD = $head
  $env:RAIOS_MCP_ROOT = $Repo
  $env:RAIOS_COMMAND_CENTER_RUNTIME = $CcRuntime
  $env:PYTHONPATH = Join-Path $Repo "src"
  $stamp = Get-Date -Format "yyyyMMddHHmmss"
  $out = Join-Path $CcLogs "center.src.$stamp.out.log"
  $err = Join-Path $CcLogs "center.src.$stamp.err.log"
  $cc = Start-Process -FilePath $PyW -ArgumentList @("-m", "uvicorn", "raios.command_center.app:app", "--host", "127.0.0.1", "--port", "8770") -WorkingDirectory $Repo -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
  Write-Host "NEW_CC_PID=$($cc.Id) HEAD=$head LOG=$err"
  [void](Wait-Tcp 8770 20 $true)
} else {
  Write-Host "CC_KILL_FAILED_STILL_LISTENING"
}
Write-Host "CC_TCP=$(Test-Tcp 8770) PID=$(Get-ListenPid 8770)"

Write-Host "=== STALE_SEAT_LOCKS ==="
foreach ($seat in @("C2", "C8")) {
  $lock = Join-Path $Ops "consumers\$seat.agent.lock"
  if (Test-Path -LiteralPath $lock) {
    $raw = ([IO.File]::ReadAllText($lock)).Trim()
    Write-Host "$seat LOCK_RAW=$raw"
    if ($raw -match "(\d+)") {
      $lp = [int]$Matches[1]
      $alive = Get-Process -Id $lp -ErrorAction SilentlyContinue
      Write-Host "$seat LOCK_PID_ALIVE=$([bool]$alive) NAME=$($alive.ProcessName)"
      if ($alive) {
        & taskkill.exe /F /PID $lp 2>&1 | ForEach-Object { Write-Host $_ }
      }
    }
  }
}

Write-Host "=== SEAT_SESSIONS ==="
$c2Auth = Join-Path $Ops "auth\C2-CURSOR-AUTH.json"
$c8Auth = Join-Path $Ops "auth\C8-DESKTOP-COMMANDER-AUTH.json"
$startSeat = Join-Path $Repo "scripts\runtime\Start-RAIOS-Seat-Session.ps1"
$c2Sid = [guid]::NewGuid().ToString()
$c8Sid = [guid]::NewGuid().ToString()
try {
  & $startSeat -Seat C2 -AuthEvidence $c2Auth -ActorId C2-CURSOR -OriginInstance C2-CURSOR-AG -DeviceId AG -SessionId $c2Sid -Repo $Repo -RuntimeRoot $Ops
} catch { Write-Host "C2_SESSION_ERR=$($_.Exception.Message)" }
try {
  & $startSeat -Seat C8 -AuthEvidence $c8Auth -ActorId "DESKTOP-COMMANDER-CLIENT-20dab21d-bcd9-41c8-a028-ecb2235564db" -OriginInstance DESKTOP-COMMANDER-AG -DeviceId AG -SessionId $c8Sid -Repo $Repo -RuntimeRoot $Ops
} catch { Write-Host "C8_SESSION_ERR=$($_.Exception.Message)" }

Write-Host "=== FINAL_TCP ==="
foreach ($p in 20128, 4222, 8766, 8770, 8788, 11434) {
  Write-Host "PORT $p TCP=$(Test-Tcp $p) PID=$(Get-ListenPid $p)"
}
Write-Host "RESTORE_SCRIPT_DONE"
