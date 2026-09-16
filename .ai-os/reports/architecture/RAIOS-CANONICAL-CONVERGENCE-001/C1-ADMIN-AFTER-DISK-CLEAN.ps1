# C1 elevated restore after disk clean. Existing services only. No LOCKS.json mutation.
# Paste into an Administrator PowerShell on AG.
$ErrorActionPreference = "Stop"
$Repo = "C:\Users\Ghanam\Documents\Codex\Greeny-Life"
$UserHome = "C:\Users\Ghanam"
$PyW = Join-Path $UserHome ".raios\runtime\c5\.venv\Scripts\pythonw.exe"
$Py = Join-Path $UserHome ".raios\runtime\c5\.venv\Scripts\python.exe"
$CcRuntime = Join-Path $UserHome ".raios\runtime\command-center"
$CcLogs = Join-Path $CcRuntime "logs"
$Ops = Join-Path $UserHome ".raios\runtime\council-ops"
New-Item -ItemType Directory -Force -Path $CcLogs | Out-Null

function Test-Tcp([int]$Port) {
  $c = [Net.Sockets.TcpClient]::new()
  $ok = $c.BeginConnect("127.0.0.1", $Port, $null, $null).AsyncWaitHandle.WaitOne(800) -and $c.Connected
  $c.Close()
  return [bool]$ok
}

Write-Host "=== KILL_HUNG_COMMAND_CENTER ==="
& taskkill.exe /F /PID 56712
for ($i = 0; $i -lt 40; $i++) { if (-not (Test-Tcp 8770)) { break }; Start-Sleep -Milliseconds 250 }
if (Test-Tcp 8770) { throw "COMMAND_CENTER_OLD_LISTENER_NOT_RELEASED" }

$Head = (git -C $Repo rev-parse HEAD).Trim()
$env:RAIOS_CANONICAL_REPO = $Repo
$env:RAIOS_CANONICAL_HEAD = $Head
$env:RAIOS_MCP_ROOT = $Repo
$env:RAIOS_COMMAND_CENTER_RUNTIME = $CcRuntime
$env:PYTHONPATH = Join-Path $Repo "src"
$stamp = Get-Date -Format "yyyyMMddHHmmss"
$cc = Start-Process -FilePath $PyW -ArgumentList @("-m", "uvicorn", "raios.command_center.app:app", "--host", "127.0.0.1", "--port", "8770") -WorkingDirectory $Repo -WindowStyle Hidden -RedirectStandardOutput (Join-Path $CcLogs "center.src.$stamp.out.log") -RedirectStandardError (Join-Path $CcLogs "center.src.$stamp.err.log") -PassThru
Write-Host "NEW_CC_PID=$($cc.Id) HEAD=$Head"
for ($i = 0; $i -lt 30; $i++) {
  Start-Sleep -Seconds 1
  try {
    $h = Invoke-RestMethod "http://127.0.0.1:8770/health" -TimeoutSec 3
    if ($h.status -eq "ONLINE") {
      Write-Host "CC_HEALTH=ONLINE worker=$($h.message_worker.state) reported_head=$($h.canonical_head)"
      break
    }
  } catch {}
}

Write-Host "=== OPTIONAL_C5_IF_HTTP_DEAD ==="
try {
  $null = Invoke-RestMethod "http://127.0.0.1:8766/health" -TimeoutSec 4
  Write-Host "C5_HTTP=ALREADY_OK"
} catch {
  Write-Host "C5_HTTP_DEAD — kill PID 32796 then existing HeadOnlyRecovery if C1 confirms"
}

Write-Host "=== SEAT_SESSIONS C2 C8 ==="
$start = Join-Path $Repo "scripts\runtime\Start-RAIOS-Seat-Session.ps1"
foreach ($seat in @("C2", "C8")) {
  $lock = Join-Path $Ops "consumers\$seat.agent.lock"
  if (Test-Path $lock) {
    $raw = ([IO.File]::ReadAllText($lock)).Trim()
    if ($raw -match "(\d+)") { & taskkill.exe /F /PID ([int]$Matches[1]) 2>$null | Out-Null }
  }
}
& $start -Seat C2 -AuthEvidence (Join-Path $Ops "auth\C2-CURSOR-AUTH.json") -ActorId C2-CURSOR -OriginInstance C2-CURSOR-AG -DeviceId AG -SessionId ([guid]::NewGuid().ToString()) -Repo $Repo -RuntimeRoot $Ops
& $start -Seat C8 -AuthEvidence (Join-Path $Ops "auth\C8-DESKTOP-COMMANDER-AUTH.json") -ActorId "DESKTOP-COMMANDER-CLIENT-20dab21d-bcd9-41c8-a028-ecb2235564db" -OriginInstance DESKTOP-COMMANDER-AG -DeviceId AG -SessionId ([guid]::NewGuid().ToString()) -Repo $Repo -RuntimeRoot $Ops

Write-Host "=== BOARD_PROOF ==="
$b = Invoke-RestMethod "http://127.0.0.1:8770/api/bootstrap" -TimeoutSec 8
$t = Invoke-RestMethod "http://127.0.0.1:8770/api/tasks" -TimeoutSec 8
$p = Invoke-RestMethod "http://127.0.0.1:8770/api/plane" -TimeoutSec 8
Write-Host "BOOT_MODE=$($b.boot_mode) PLANE_9ROUTER=$(($p.services | Where-Object name -eq '9Router').state)"
Write-Host "TASK_IN_RECENT=$([bool]($t.recent | Where-Object id -eq 'RAIOS-CANONICAL-CONVERGENCE-001')) IN_PROGRESS=$($t.in_progress)"
Write-Host "OPEN http://127.0.0.1:8770"
Write-Host "C1_ADMIN_RESTORE_DONE"
