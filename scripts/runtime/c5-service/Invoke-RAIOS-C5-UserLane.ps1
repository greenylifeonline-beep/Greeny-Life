$ErrorActionPreference='Continue'
$Root='C:\Users\Ghanam\.raios\runtime\continuity\c5-service'
$Repo='C:\Users\Ghanam\Documents\Codex\Greeny-Life'
$Python='C:\Users\Ghanam\AppData\Local\Programs\Python\Python314\python.exe'
$Dcr='C:\Users\Ghanam\.raios\runtime\continuity\reap_stale_rdc_sessions.py'
$Maintain=Join-Path $Repo 'scripts\runtime\Maintain-RAIOS-Online.ps1'
$State=Join-Path $Root 'user-lane-state.json'
$Out=Join-Path $Root 'user-lane.out.log'
$Err=Join-Path $Root 'user-lane.err.log'
$DcrOut=Join-Path $Root 'dcr-supervisor.out.log'
$DcrErr=Join-Path $Root 'dcr-supervisor.err.log'
$DcrState='C:\Users\Ghanam\.raios\runtime\remote-access\rdc-system-direct\rdc-supervisor-state.json'
$Transport=Join-Path (Split-Path $Root) 'rdc-transport-continuity.json'
$NativeTunnelHealthFile='C:\Users\Ghanam\.local\state\tunnel-client\health\raios-native.url'
$RepairCooldownSeconds=300
$RepairTimeoutSeconds=720
$CanonicalContinuityRoot=Join-Path $Repo 'scripts\runtime\continuity'
$RuntimeContinuityRoot=Split-Path $Root

function Sync-CanonicalContinuity {
 try {
  foreach($name in @('raios_reconnect_checkpoint.py','reap_stale_rdc_sessions.py')){
   $src=Join-Path $CanonicalContinuityRoot $name
   $dst=Join-Path $RuntimeContinuityRoot $name
   if(-not(Test-Path -LiteralPath $src)){continue}
   $copy=$true
   if(Test-Path -LiteralPath $dst){
    try{$copy=((Get-FileHash -Algorithm SHA256 -LiteralPath $src).Hash -ne (Get-FileHash -Algorithm SHA256 -LiteralPath $dst).Hash)}catch{$copy=$true}
   }
   if($copy){
    $tmp=$dst+'.tmp-'+[guid]::NewGuid().ToString('N')
    Copy-Item -LiteralPath $src -Destination $tmp -Force
    Move-Item -LiteralPath $tmp -Destination $dst -Force
   }
  }
 }catch{
  try{('CANONICAL_CONTINUITY_SYNC_FAIL|'+[DateTimeOffset]::UtcNow.ToString('o')+'|'+$_.Exception.Message)|Add-Content -LiteralPath $Err -Encoding UTF8}catch{}
 }
}
New-Item -ItemType Directory -Path $Root -Force | Out-Null
Sync-CanonicalContinuity
$mutex=[Threading.Mutex]::new($false,'Local\RAIOS-C5-UserLane-v2')
$owned=$false
try{$owned=$mutex.WaitOne(0)}catch [Threading.AbandonedMutexException]{$owned=$true}
if(-not $owned){exit 0}
$script:dcrProc=$null;$script:dcrProcOwned=$false;$script:maintProc=$null
$env:RAIOS_DCR_AUTHORITY='RAIOS-C5'
$env:RAIOS_DCR_OWNER_PID=[string]$PID
$script:lastRepairAttempt=[DateTimeOffset]::MinValue
$script:maintStartedAt=[DateTimeOffset]::MinValue

function Test-TcpFast([int]$Port){
 try{
  $c=[Net.Sockets.TcpClient]::new()
  $a=$c.BeginConnect('127.0.0.1',$Port,$null,$null)
  $ok=$a.AsyncWaitHandle.WaitOne(700)-and $c.Connected
  $c.Close()
  return [bool]$ok
 }catch{return $false}
}
function Test-NativeMcpTunnelReady {
 if(-not(Test-Path -LiteralPath $NativeTunnelHealthFile)){return $false}
 try{
  $base=(Get-Content -LiteralPath $NativeTunnelHealthFile -Raw).Trim()
  if($base -notmatch '^http://127\.0\.0\.1:\d+$'){return $false}
  $r=Invoke-WebRequest -UseBasicParsing -Uri ($base+'/readyz') -TimeoutSec 3
  return ($r.StatusCode -eq 200 -and $r.Content.Trim() -eq 'ready')
 }catch{return $false}
}
function Get-NativeHealth {
 $h=[ordered]@{
  C5=(Test-TcpFast 8766)
  COMMAND_CENTER=(Test-TcpFast 8770)
  UNIVERSAL_MCP=(Test-TcpFast 8788)
  NATIVE_MCP_TUNNEL=(Test-NativeMcpTunnelReady)
  NATS=(Test-TcpFast 4222)
  ROUTER=$(if($script:routerHttpHelperLoaded){Test-RaiosRouterHttpReady}else{$false})
 }
 $ready=-not (@($h.Values)-contains $false)
 return [pscustomobject]@{Ready=$ready;Ports=$h}
}
function Write-State([string]$status,$health){
 try{
  if($script:dcrProc){try{$script:dcrProc.Refresh()}catch{}}
  if($script:maintProc){try{$script:maintProc.Refresh()}catch{}}
  $transportState=$null
  try{$transportState=Get-Content -LiteralPath $Transport -Raw|ConvertFrom-Json}catch{}
  $obj=[ordered]@{
   schema='raios.c5.user-lane.state.v2'
   observed_at=[DateTimeOffset]::UtcNow.ToString('o')
   status=$status
   pid=$PID
   session_id=[Diagnostics.Process]::GetCurrentProcess().SessionId
   dcr_pid=$(if($script:dcrProc -and -not $script:dcrProc.HasExited){$script:dcrProc.Id}else{$null})
   maintain_pid=$(if($script:maintProc -and -not $script:maintProc.HasExited){$script:maintProc.Id}else{$null})
   native_ready=$(if($health){[bool]$health.Ready}else{$false})
   native_ports=$(if($health){$health.Ports}else{$null})
   last_repair_attempt=$(if($script:lastRepairAttempt -ne [DateTimeOffset]::MinValue){$script:lastRepairAttempt.ToString('o')}else{$null})
   repair_cooldown_seconds=$RepairCooldownSeconds
   transport_online=$(if($transportState){[bool]$transportState.transport_online}else{$false})
   remote_transport_execution_allowed=$(if($transportState -and $transportState.PSObject.Properties['transport_execution_allowed']){[bool]$transportState.transport_execution_allowed}else{$false})
   reconciliation_required=$(if($transportState){[bool]$transportState.reconciliation_required}else{$true})
   continuation_allowed=$(if($transportState){[bool]$transportState.continuation_allowed}else{$true})
   mutation_allowed=$(if($transportState -and $transportState.PSObject.Properties['mutation_allowed']){[bool]$transportState.mutation_allowed}else{$false})
   authority='RAIOS-C5'
   scheduler_authority=$false
  }
  $tmp=$State+'.tmp-'+[guid]::NewGuid().ToString('N')
  $obj|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $tmp -Encoding UTF8
  for($i=0;$i-lt 5;$i++){
   try{Move-Item -LiteralPath $tmp -Destination $State -Force;break}
   catch{if($i-eq 4){throw};Start-Sleep -Milliseconds (25*($i+1))}
  }
 }catch{}
}
function Get-ExistingDcrSupervisor {
 try {
  if(-not(Test-Path -LiteralPath $DcrState)){return $null}
  $st=Get-Content -LiteralPath $DcrState -Raw|ConvertFrom-Json
  # RAIOS_DCR_STATE_CONTRACT_V1
  $stateSup=[int]$(if($st.PSObject.Properties['supervisor_pid']){$st.supervisor_pid}else{0})
  $stateOwner=[int]$(if($st.PSObject.Properties['owner_pid']){$st.owner_pid}else{0})
  $stateAuthority=[string]$(if($st.PSObject.Properties['authority']){$st.authority}else{''})
  if($stateSup -gt 4 -and $stateAuthority -eq 'RAIOS-C5'){
   try{
    $sp=[Diagnostics.Process]::GetProcessById($stateSup)
    if(-not $sp.HasExited){
     return [pscustomobject]@{Pid=$stateSup;ParentPid=$stateOwner;OwnerPid=$stateOwner;SeedPid=0;Depth=0;Authority=$stateAuthority}
    }
   }catch{}
  }
  if([string]$st.status -ne 'ONLINE'){return $null}

  $seedPids=@()
  $seedPids+=@($st.owned_remote_pids|Where-Object{$_})
  $seedPids+=@($st.owned_local_mcp_pids|Where-Object{$_})

  foreach($seed in @($seedPids|Select-Object -Unique)){
   $current=[int]$seed
   for($depth=0;$depth -lt 8;$depth++){
    if($current -le 4){break}
    $child=Get-CimInstance Win32_Process -Filter ('ProcessId='+$current) -ErrorAction SilentlyContinue
    if(-not $child){break}
    $parentId=[int]$child.ParentProcessId
    if($parentId -le 4){break}
    $parent=Get-CimInstance Win32_Process -Filter ('ProcessId='+$parentId) -ErrorAction SilentlyContinue
    if(-not $parent){break}
    $name=[string]$parent.Name
    $cmd=[string]$parent.CommandLine
    if($name -match '^python(w)?\.exe$' -and $cmd -like ('*'+$Dcr+'*') -and $cmd -match '--supervise'){
     return [pscustomobject]@{Pid=$parentId;ParentPid=[int]$parent.ParentProcessId;OwnerPid=[int]$parent.ParentProcessId;SeedPid=[int]$seed;Depth=$depth+1;Authority='RAIOS-C5'}
    }
    $current=$parentId
   }
  }
  return $null
 } catch {
  try{('DCR_DISCOVERY_FAIL|'+[DateTimeOffset]::UtcNow.ToString('o')+'|'+$_.Exception.Message)|Add-Content -LiteralPath $Err -Encoding UTF8}catch{}
  return $null
 }
}
function Ensure-Dcr {
 try{
  if($script:dcrProc){
   try{$script:dcrProc.Refresh()}catch{}
   if(-not $script:dcrProc.HasExited){return}
   $script:dcrProc=$null
   $script:dcrProcOwned=$false
  }

  $existing=Get-ExistingDcrSupervisor
  if($existing){
   try{
    $script:dcrProc=[Diagnostics.Process]::GetProcessById([int]$existing.Pid)
    if(-not $script:dcrProc.HasExited){
     $script:dcrProcOwned=([int]$existing.ParentPid -eq $PID -or [int]$existing.OwnerPid -eq $PID)
     ('DCR_SUPERVISOR_ADOPT|'+[DateTimeOffset]::UtcNow.ToString('o')+'|PID='+$script:dcrProc.Id+'|OWNER='+$existing.OwnerPid+'|OWNED_BY_LANE='+$script:dcrProcOwned)|Add-Content -LiteralPath $Out -Encoding UTF8
     return
    }
   }catch{
    $script:dcrProc=$null
    $script:dcrProcOwned=$false
   }
  }

  $script:dcrProc=Start-Process -FilePath $Python -ArgumentList @($Dcr,'--supervise') -WorkingDirectory (Split-Path $Dcr) -WindowStyle Hidden -RedirectStandardOutput $DcrOut -RedirectStandardError $DcrErr -PassThru
  $script:dcrProcOwned=$true
  ('DCR_SUPERVISOR_START|'+[DateTimeOffset]::UtcNow.ToString('o')+'|PID='+$script:dcrProc.Id+'|PARENT='+$PID)|Add-Content -LiteralPath $Out -Encoding UTF8
 }catch{
  $script:dcrProc=$null
  $script:dcrProcOwned=$false
  try{('DCR_START_FAIL|'+[DateTimeOffset]::UtcNow.ToString('o')+'|'+$_.Exception.Message)|Add-Content -LiteralPath $Err -Encoding UTF8}catch{}
 }
}
function Ensure-NativeRecovery($health){
 try{
  if($script:maintProc){
   try{$script:maintProc.Refresh()}catch{}
   if(-not $script:maintProc.HasExited){
    if((([DateTimeOffset]::UtcNow-$script:maintStartedAt).TotalSeconds)-gt $RepairTimeoutSeconds){
     try{& "$env:SystemRoot\System32\taskkill.exe" /PID $script:maintProc.Id /T /F | Out-Null}catch{}
     ('NATIVE_REPAIR_TIMEOUT|'+[DateTimeOffset]::UtcNow.ToString('o')+'|PID='+$script:maintProc.Id)|Add-Content -LiteralPath $Err -Encoding UTF8
     $script:maintProc=$null
    }
    return
   } else {
    ('NATIVE_REPAIR_EXIT|'+[DateTimeOffset]::UtcNow.ToString('o')+'|CODE='+$script:maintProc.ExitCode)|Add-Content -LiteralPath $Out -Encoding UTF8
    $script:maintProc=$null
   }
  }
  if($health.Ready){return}
  if((([DateTimeOffset]::UtcNow-$script:lastRepairAttempt).TotalSeconds)-lt $RepairCooldownSeconds){return}
  $args=@('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$Maintain,'-Repo',$Repo)
  $script:maintProc=Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList $args -WorkingDirectory $Repo -WindowStyle Hidden -RedirectStandardOutput $Out -RedirectStandardError $Err -PassThru
  $script:lastRepairAttempt=[DateTimeOffset]::UtcNow
  $script:maintStartedAt=$script:lastRepairAttempt
  ('NATIVE_REPAIR_START|'+$script:lastRepairAttempt.ToString('o')+'|PID='+$script:maintProc.Id)|Add-Content -LiteralPath $Out -Encoding UTF8
 }catch{
  try{('NATIVE_REPAIR_FAIL|'+[DateTimeOffset]::UtcNow.ToString('o')+'|'+$_.Exception.Message)|Add-Content -LiteralPath $Err -Encoding UTF8}catch{}
 }
}

# Optional Hermes provider pulse; SCM remains the only control authority.
$script:hermesTick=$null
$script:hermesLast=[DateTimeOffset]::MinValue
function Ensure-HermesProvider {
 try {
  $now=[DateTimeOffset]::UtcNow
  if($script:hermesTick){
   $script:hermesTick.Refresh()
   if(-not $script:hermesTick.HasExited){
    if(($now-$script:hermesLast).TotalSeconds -gt 240){
     try{$script:hermesTick.Kill()}catch{}
    }
    return
   }
   $script:hermesTick.Dispose()
   $script:hermesTick=$null
  }
  if(($now-$script:hermesLast).TotalSeconds -lt 30){return}
  $script:hermesLast=$now
  $hp='C:\Users\Ghanam\.raios\runtime\c5\.venv\Scripts\pythonw.exe'
  $ha=Join-Path $Repo 'src\raios\knowledge\hermes_ingest.py'
  if(-not([IO.File]::Exists($hp)-and[IO.File]::Exists($ha))){return}
  $args=@(('"' + $ha + '"'),'tick','--repo',('"' + $Repo + '"'),'--authority','RAIOS-C5')
  $script:hermesTick=Start-Process -FilePath $hp -ArgumentList $args -WorkingDirectory $Repo -WindowStyle Hidden -PassThru
 }catch{$script:hermesTick=$null;$script:hermesLast=[DateTimeOffset]::UtcNow.AddSeconds(30)}
}


# Load the one canonical HTTP probe without executing continuity operations.
$script:routerHttpHelperLoaded=$false
try {
 $routerTokens=$null;$routerParseErrors=$null
 $routerAst=[Management.Automation.Language.Parser]::ParseFile($Maintain,[ref]$routerTokens,[ref]$routerParseErrors)
 if($routerParseErrors.Count -gt 0){throw 'ROUTER_HTTP_HELPER_SOURCE_INVALID'}
 $routerFunction=$routerAst.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Test-RaiosRouterHttpReady'},$true)
 if(-not $routerFunction){throw 'ROUTER_HTTP_HELPER_MISSING'}
 Invoke-Expression $routerFunction.Extent.Text
 $script:routerHttpHelperLoaded=$true
}catch{$script:routerHttpHelperLoaded=$false}

try{
 while($true){
  Ensure-HermesProvider
  Ensure-Dcr
  $health=Get-NativeHealth
  Ensure-NativeRecovery $health
  Write-State $(if($health.Ready){'ONLINE'}else{'DEGRADED'}) $health
  Start-Sleep -Seconds 2
 }
}finally{
 Write-State 'STOPPING' (Get-NativeHealth)
 try{if($script:dcrProcOwned -and $script:dcrProc -and -not $script:dcrProc.HasExited){Stop-Process -Id $script:dcrProc.Id -Force}}catch{}
 try{if($script:maintProc -and -not $script:maintProc.HasExited){& "$env:SystemRoot\System32\taskkill.exe" /PID $script:maintProc.Id /T /F | Out-Null}}catch{}
 if($owned){try{$mutex.ReleaseMutex()}catch{}}
 $mutex.Dispose()
}
