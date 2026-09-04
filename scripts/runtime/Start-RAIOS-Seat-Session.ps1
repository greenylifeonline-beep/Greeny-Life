param(
 [Parameter(Mandatory=$true)][string]$Seat,
 [Parameter(Mandatory=$true)][string]$AuthEvidence,
 [Parameter(Mandatory=$true)][string]$ActorId,
 [Parameter(Mandatory=$true)][string]$OriginInstance,
 [Parameter(Mandatory=$true)][string]$DeviceId,
 [Parameter(Mandatory=$true)][string]$SessionId,
 [string]$Repo="",
 [string]$RuntimeRoot=""
)
$ErrorActionPreference="Stop"
if(-not $Repo){$Repo=(Resolve-Path(Join-Path $PSScriptRoot "..\..")).Path}
$Repo=(Resolve-Path $Repo).Path
$UserHome=$HOME
if($Repo -match '^(?<h>[A-Za-z]:\\Users\\[^\\]+)\\'){$UserHome=$Matches.h}
if(-not $RuntimeRoot){$RuntimeRoot=Join-Path $UserHome '.raios\runtime\council-ops'}
if($Seat -notmatch '^C(?:[1-9]|1[0-2])$'){throw "INVALID_COUNCIL_SEAT"}
if(-not(Test-Path $AuthEvidence)){throw "AUTH_EVIDENCE_MISSING"}
$Python=Join-Path $UserHome ".raios\runtime\c5\.venv\Scripts\pythonw.exe"
if(-not(Test-Path $Python)){throw "CANONICAL_PYTHONW_MISSING"}
$Heartbeat=Join-Path $RuntimeRoot "consumers\$Seat.json"
if(Test-Path $Heartbeat){
 try{$h=Get-Content $Heartbeat -Raw|ConvertFrom-Json;$expiry=[DateTimeOffset]::Parse($h.lease_expires_at)
  if($h.state -eq 'ONLINE' -and $h.session_id -eq $SessionId -and $expiry -gt [DateTimeOffset]::UtcNow){
   Write-Host "SEAT_SESSION_ALREADY_ONLINE=true";Write-Host "SEAT=$Seat";Write-Host "SESSION_ID=$SessionId";exit 0}}
 catch{}
}
$env:PYTHONPATH=Join-Path $Repo "src"
$args=@('-m','raios.council_ops.session_agent','--repo',$Repo,'--runtime',$RuntimeRoot,'--seat',$Seat,
 '--auth-evidence',$AuthEvidence,'--actor-id',$ActorId,'--origin-instance',$OriginInstance,
 '--device-id',$DeviceId,'--session-id',$SessionId)
$p=Start-Process $Python -ArgumentList $args -WindowStyle Hidden -PassThru
for($i=0;$i-lt 20;$i++){Start-Sleep -Milliseconds 500;if(Test-Path $Heartbeat){try{$h=Get-Content $Heartbeat -Raw|ConvertFrom-Json
 if($h.state -eq 'ONLINE' -and $h.session_id -eq $SessionId){Write-Host "SEAT_SESSION_ONLINE=true";Write-Host "SEAT=$Seat";Write-Host "PID=$($p.Id)";Write-Host "ACTOR_ID=$ActorId";Write-Host "SESSION_ID=$SessionId";exit 0}}catch{}}}
Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
throw "SEAT_SESSION_START_FAILED"
