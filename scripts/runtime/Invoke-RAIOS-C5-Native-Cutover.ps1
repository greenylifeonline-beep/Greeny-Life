param(
 [Parameter(Mandatory=$true)][string]$RequestId,
 [Parameter(Mandatory=$true)][string]$ExpectedSourceSha256
)
$ErrorActionPreference='Stop'
$Repo='C:\Users\Ghanam\Documents\Codex\Greeny-Life'
$Root='C:\Users\Ghanam\.raios\runtime\continuity\c5-service'
$Priv='C:\Users\Ghanam\.raios\runtime\continuity\privileged-exec'
$Source=Join-Path $Repo 'scripts\runtime\RAIOS.C5.ServiceHost.cs'
$NativeSource=Join-Path $Repo 'scripts\runtime\Start-RAIOS-Native-MCP-System.ps1'
$NativeLive='C:\Users\Ghanam\.raios\runtime\mcp-tunnel\Start-RAIOS-Native-MCP-System.ps1'
$Live=Join-Path $Root 'RAIOS-C5-Service.exe'
$Stage=Join-Path $Root ('RAIOS-C5-Service.native-close-'+$RequestId+'.stage.exe')
$Backup=Join-Path $Root ('RAIOS-C5-Service.before-'+$RequestId+'.exe')
$Failed=Join-Path $Root ('RAIOS-C5-Service.failed-'+$RequestId+'.exe')
$State=Join-Path $Root 'state.json'
$DcrState='C:\Users\Ghanam\.raios\runtime\remote-access\rdc-system-direct\rdc-supervisor-state.json'
$Receipt=Join-Path (Join-Path $Priv 'receipts') ($RequestId+'.cutover.json')
$Csc='C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'

function Write-Receipt($obj){
 $tmp=$Receipt+'.tmp-'+[guid]::NewGuid().ToString('N')
 $obj|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $tmp -Encoding UTF8
 Move-Item -LiteralPath $tmp -Destination $Receipt -Force
}
function Get-PortListenPids([int]$Port){
 $ids=New-Object System.Collections.Generic.List[int]
 foreach($line in (& netstat -ano -p tcp 2>$null)){
  $parts=@($line.ToString().Trim() -split '\s+')
  if($parts.Length -lt 5){continue}
  if($parts[-2] -ne 'LISTENING'){continue}
  if($parts[1] -match (":${Port}$")){
   $listenPid=[int]$parts[-1]
   if(-not $ids.Contains($listenPid)){[void]$ids.Add($listenPid)}
  }
 }
 return @($ids)
}
function Get-FirstFailingGate($g){
 foreach($name in @('SERVICE_RUNNING','MCP_CHILD_LAUNCHED','GENERATION_BOUND','LISTENER_CREATED','LISTENER_IDENTITY_VALID','PORT_8788_SINGLETON','HEALTH_REACHED','TOOL_COUNT_9','EXECUTE_SCOPED_TASK_PRESENT','TUNNEL_READY','DCR_ONLINE')){
  if(-not $g[$name]){return $name}
 }
 return $null
}
function Invoke-ScmCrashHandoff([string]$TargetImage,[string]$Phase,[int]$TimeoutSeconds=90){
 if(-not(Test-Path -LiteralPath $TargetImage -PathType Leaf)){throw "SCM_HANDOFF_TARGET_MISSING::$TargetImage"}
 $quoted='"'+$TargetImage+'"'
 & sc.exe config RAIOS-C5 binPath= $quoted start= auto | Out-Null
 if($LASTEXITCODE -ne 0){throw "SCM_HANDOFF_CONFIG_FAILED::$Phase"}
 & sc.exe failure RAIOS-C5 reset= 86400 actions= restart/5000/restart/15000/restart/30000 | Out-Null
 if($LASTEXITCODE -ne 0){throw "SCM_HANDOFF_FAILURE_POLICY_FAILED::$Phase"}
 & sc.exe failureflag RAIOS-C5 1 | Out-Null
 $svc=Get-CimInstance Win32_Service -Filter "Name='RAIOS-C5'"
 if(-not $svc){throw "SCM_HANDOFF_SERVICE_MISSING::$Phase"}
 if([string]$svc.State -eq 'Running' -and [int]$svc.ProcessId -gt 4){
  Stop-Process -Id ([int]$svc.ProcessId) -Force -ErrorAction Stop
 }else{
  Start-Service RAIOS-C5
 }
 $deadline=[DateTimeOffset]::UtcNow.AddSeconds($TimeoutSeconds)
 do{
  Start-Sleep -Milliseconds 500
  $svc=Get-CimInstance Win32_Service -Filter "Name='RAIOS-C5'"
  $path=if($svc){([string]$svc.PathName).Trim('"')}else{''}
  if($svc -and [string]$svc.State -eq 'Running' -and [int]$svc.ProcessId -gt 4 -and $path -eq $TargetImage){return $svc}
 }until([DateTimeOffset]::UtcNow -ge $deadline)
 throw "SCM_HANDOFF_TIMEOUT::$Phase::$TargetImage"
}

$started=[DateTimeOffset]::UtcNow
$beforeHash=$null
$stageHash=$null
$cutoverStarted=$false
$promotionRequested=$false
$gates=$null
$MaintenanceIntent=Join-Path $Root 'maintenance-stop.intent.json'
$GenFile=Join-Path $Root 'current-generation.json'
$EightHold=Join-Path $Root 'hold-8tool-rollback-20261006'
$Lane=Join-Path $Root 'Invoke-RAIOS-C5-UserLane.ps1'
$LaneBackup=Join-Path $Root ('Invoke-RAIOS-C5-UserLane.before-'+$RequestId+'.ps1')
$NativeBackup=Join-Path $Root ('Start-RAIOS-Native-MCP-System.before-'+$RequestId+'.ps1')
$PromoteIntent=Join-Path $Root 'mcp-promote-owned.intent.json'
$beforeGen=$null
try{
 $id=[Security.Principal.WindowsIdentity]::GetCurrent()
 if($id.User.Value -ne 'S-1-5-18'){throw ('NOT_SYSTEM:'+ $id.User.Value)}
 if($ExpectedSourceSha256 -notmatch '^[0-9a-fA-F]{64}$'){throw 'EXPECTED_SOURCE_SHA256_INVALID'}
 if(-not(Test-Path -LiteralPath $Source)){throw 'SERVICE_SOURCE_MISSING'}
 if(-not(Test-Path -LiteralPath $NativeSource)){throw 'NATIVE_LAUNCHER_SOURCE_MISSING'}
 $actualSource=(Get-FileHash -Algorithm SHA256 -LiteralPath $Source).Hash.ToLowerInvariant()
 if($actualSource -ne $ExpectedSourceSha256.ToLowerInvariant()){throw ('SOURCE_HASH_MISMATCH:'+ $actualSource)}

 Remove-Item -LiteralPath $Stage -Force -ErrorAction SilentlyContinue
 & $Csc /nologo /target:exe /out:$Stage /reference:System.ServiceProcess.dll /reference:System.Web.Extensions.dll $Source
 if($LASTEXITCODE -ne 0){throw ('SERVICE_COMPILE_FAILED:'+ $LASTEXITCODE)}
 $self=@(& $Stage --selftest 2>&1)
 if($LASTEXITCODE -ne 0 -or -not($self -contains 'SELFTEST=PASS')){throw ('SERVICE_SELFTEST_FAILED:'+($self -join ';'))}
 $stageHash=(Get-FileHash -Algorithm SHA256 -LiteralPath $Stage).Hash.ToLowerInvariant()

 # Canonical Native launcher is deployed before service restart.
 Copy-Item -LiteralPath $NativeLive -Destination $NativeBackup -Force
 Copy-Item -LiteralPath $Lane -Destination $LaneBackup -Force
 $laneText=[IO.File]::ReadAllText($Lane)
 if($laneText.Contains('[int]$m.tool_count -eq 8')){
  [IO.File]::WriteAllText($Lane, $laneText.Replace('[int]$m.tool_count -eq 8','[int]$m.tool_count -eq 9'))
 }
 # The current listener is a SYSTEM process. The user lane cannot stop it.
 # This SYSTEM helper promotes after the new service generation exists.
 Remove-Item -LiteralPath $PromoteIntent -Force -ErrorAction SilentlyContinue
 $promotionRequested=$true
 Copy-Item -LiteralPath $NativeSource -Destination $NativeLive -Force

 $beforeHash=(Get-FileHash -Algorithm SHA256 -LiteralPath $Live).Hash.ToLowerInvariant()
 $beforeState=$null
 try{$beforeState=Get-Content -LiteralPath $State -Raw|ConvertFrom-Json}catch{}
 $beforePid=if($beforeState){[int]$beforeState.service_pid}else{0}

 # Give the broker time to return its acceptance receipt before the SCM handoff.
 Start-Sleep -Seconds 3
 [ordered]@{schema='raios.c5.maintenance-stop.v1';authority='RAIOS_SYSTEM';reason='NATIVE_CHANNEL_CUTOVER';request_id=$RequestId;issued_utc=[DateTimeOffset]::UtcNow.ToString('o');expires_utc=[DateTimeOffset]::UtcNow.AddMinutes(5).ToString('o')}|ConvertTo-Json -Compress|Set-Content -LiteralPath $MaintenanceIntent -Encoding UTF8
 $cutoverStarted=$true

 if(Test-Path -LiteralPath $Backup){Remove-Item -LiteralPath $Backup -Force}
 Copy-Item -LiteralPath $Live -Destination $Backup -Force

 try{$beforeGen=[string](Get-Content -LiteralPath $GenFile -Raw|ConvertFrom-Json).generation_id}catch{$beforeGen=$null}

 # Zero-dead-zone cutover: stage first, then canonical live. No clean Stop-Service.
 [void](Invoke-ScmCrashHandoff $Stage 'NATIVE_CUTOVER_STAGE')
 Copy-Item -LiteralPath $Stage -Destination $Live -Force
 [void](Invoke-ScmCrashHandoff $Live 'NATIVE_CUTOVER_LIVE')
 Remove-Item -LiteralPath $MaintenanceIntent -Force -ErrorAction SilentlyContinue
 Remove-Item -LiteralPath $PromoteIntent -Force -ErrorAction SilentlyContinue

 $genDeadline=[DateTimeOffset]::UtcNow.AddSeconds(45)
 $genReady=$false
 do{
  Start-Sleep -Seconds 1
  $svcNow=Get-Service -Name 'RAIOS-C5' -ErrorAction SilentlyContinue
  try{$genNow=[string](Get-Content -LiteralPath $GenFile -Raw|ConvertFrom-Json).generation_id}catch{$genNow=$null}
  $genReady=[bool]($svcNow -and $svcNow.Status -eq 'Running' -and $genNow -and $beforeGen -and $genNow -ne $beforeGen)
 }until($genReady -or [DateTimeOffset]::UtcNow -ge $genDeadline)
 if(-not ($svcNow -and $svcNow.Status -eq 'Running')){throw 'SERVICE_RUNNING'}
 if(-not $genReady){throw 'GENERATION_BOUND'}
 $ensure=Join-Path $Repo 'scripts\ai-os\raios_mcp_local_ensure.ps1'
 $promoteOut=& powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $ensure -Port 8788 -PromoteOwnedGeneration -ExpectedToolContract 9 2>&1
 if($LASTEXITCODE -ne 0){
  $tail=((@($promoteOut) | Select-Object -Last 4) -join ' | ')
  throw ('MCP_CHILD_LAUNCHED '+$tail)
 }

 $ownerPath='C:\Users\Ghanam\.raios\runtime\mcp\universal-mcp-owner.json'
 $laneOut=Join-Path $Root 'user-lane.out.log'
 $expectedTools=@('get_head','read_board','read_inbox','read_receipt','get_diff','post_opinion','send_packet','ack_packet','execute_scoped_task')
 $last=$null
 $deadline=[DateTimeOffset]::UtcNow.AddSeconds(150)
 do{
  Start-Sleep -Seconds 2
  $svc=Get-Service -Name 'RAIOS-C5' -ErrorAction SilentlyContinue
  try{$st=Get-Content -LiteralPath $State -Raw|ConvertFrom-Json}catch{$st=$null}
  try{$ds=Get-Content -LiteralPath $DcrState -Raw|ConvertFrom-Json}catch{$ds=$null}
  try{$genNow=[string](Get-Content -LiteralPath $GenFile -Raw|ConvertFrom-Json).generation_id}catch{$genNow=$null}
  try{$owner=Get-Content -LiteralPath $ownerPath -Raw|ConvertFrom-Json}catch{$owner=$null}
  $tunnels=@(Get-Process -Name 'tunnel-client' -ErrorAction SilentlyContinue)
  $sys=@($tunnels|Where-Object{$_.SessionId -eq 0})
  $usr=@($tunnels|Where-Object{$_.SessionId -ne 0})
  $listen=@(Get-PortListenPids 8788)
  $mh=$null
  try{$mh=Invoke-RestMethod -Uri 'http://127.0.0.1:8788/health' -TimeoutSec 3}catch{$mh=$null}
  $names=@()
  if($mh){$names=@($mh.tools)}
  $exact=($names.Count -eq 9)
  foreach($name in $expectedTools){ if($names -notcontains $name){$exact=$false} }
  foreach($banned in @('shell','bash','run_command','run_sandboxed_command')){ if($names -contains $banned){$exact=$false} }
  $promoteOk=$false
  if(Test-Path -LiteralPath $laneOut){
   $hit=Select-String -LiteralPath $laneOut -Pattern 'MCP_PROMOTE_EXIT\|' | Select-Object -Last 1
   if($hit -and [string]$hit.Line -match 'CODE=0'){$promoteOk=$true}
  }
  $writtenAfter=$false
  if($owner -and $owner.written_at){
   try{$writtenAfter=[DateTimeOffset]::Parse([string]$owner.written_at) -gt $started}catch{$writtenAfter=$false}
  }
  $recordedPid=0
  if($owner -and $owner.listener_pid){$recordedPid=[int]$owner.listener_pid}
  elseif($owner -and $owner.pid){$recordedPid=[int]$owner.pid}
  $gates=[ordered]@{
   SERVICE_RUNNING=[bool]($svc -and $svc.Status -eq 'Running' -and $st -and [string]$st.authority -eq 'RAIOS-C5')
   MCP_CHILD_LAUNCHED=[bool]($promoteOk -or ($listen.Count -ge 1 -and $writtenAfter))
   GENERATION_BOUND=[bool]($owner -and $genNow -and $beforeGen -and $genNow -ne $beforeGen -and [string]$owner.service_generation -eq $genNow -and [string]$owner.generation_id -and [string]$owner.superseded -ne 'True')
   LISTENER_CREATED=[bool]($listen.Count -ge 1)
   LISTENER_IDENTITY_VALID=[bool]($listen.Count -eq 1 -and $recordedPid -eq [int]$listen[0] -and $owner -and [string]$owner.service_generation -eq $genNow)
   PORT_8788_SINGLETON=[bool]($listen.Count -eq 1)
   HEALTH_REACHED=[bool]($mh -and $mh.ok -eq $true -and [string]$mh.head_source -eq 'git-file')
   TOOL_COUNT_9=[bool]($mh -and [int]$mh.tool_count -eq 9 -and $exact -and $mh.second_gateway -eq $false -and $mh.raw_shell -eq $false)
   EXECUTE_SCOPED_TASK_PRESENT=[bool]($names -contains 'execute_scoped_task' -and $mh -and $mh.execute_scoped_task -eq $true)
   TUNNEL_READY=[bool]($st -and [bool]$st.native_tunnel_ready -and [string]$st.native_tunnel_authority -eq 'RAIOS-C5-SCM' -and [int]$st.native_tunnel_owner_pid -gt 4 -and $sys.Count -eq 1 -and $usr.Count -eq 0)
   DCR_ONLINE=[bool]($ds -and [string]$ds.status -eq 'ONLINE' -and [string]$ds.authority -eq 'RAIOS-C5')
   EXTERNAL_CHANNEL_REACHED=$false
  }
  $last=[ordered]@{
   service=$(if($svc){[string]$svc.Status}else{'MISSING'})
   service_pid=$(if($st){$st.service_pid}else{$null})
   authority=$(if($st){$st.authority}else{$null})
   native_ready=$(if($st){$st.native_tunnel_ready}else{$false})
   native_owner=$(if($st){$st.native_tunnel_owner_pid}else{$null})
   native_authority=$(if($st){$st.native_tunnel_authority}else{$null})
   tunnel_system_count=$sys.Count
   tunnel_user_count=$usr.Count
   universal_mcp_ready=[bool]$gates.TOOL_COUNT_9
   dcr_status=$(if($ds){$ds.status}else{$null})
   dcr_supervisor_pid=$(if($ds){$ds.supervisor_pid}else{$null})
   gates=$gates
  }
 }until((-not (Get-FirstFailingGate $gates)) -or [DateTimeOffset]::UtcNow -ge $deadline)

 $firstFail=Get-FirstFailingGate $gates
 if($firstFail){throw $firstFail}

 $rec=[ordered]@{
  schema='raios.c5.native-channel-cutover.v1';request_id=$RequestId;status='LOCAL_9_PASS';rolled_back=$false
  started_at=$started.ToString('o');finished_at=[DateTimeOffset]::UtcNow.ToString('o')
  source_sha256=$actualSource;stage_sha256=$stageHash;before_binary_sha256=$beforeHash
  live_binary_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $Live).Hash.ToLowerInvariant()
  before_pid=$beforePid;after_pid=[int]$last.service_pid
  native_authority=$last.native_authority;native_owner_pid=$last.native_owner
  tunnel_system_count=$last.tunnel_system_count;tunnel_user_count=$last.tunnel_user_count
  universal_mcp_ready=$last.universal_mcp_ready;dcr_status=$last.dcr_status;dcr_supervisor_pid=$last.dcr_supervisor_pid
  gates=$gates;external_channel_reached=$false;external_note='C1_EXTERNAL_PENDING'
 }
 Write-Receipt $rec
 exit 0
}catch{
 $err=[string]$_.Exception.Message
 Remove-Item -LiteralPath $MaintenanceIntent -Force -ErrorAction SilentlyContinue
 Remove-Item -LiteralPath $PromoteIntent -Force -ErrorAction SilentlyContinue
 try{
  if(Test-Path -LiteralPath $LaneBackup){Copy-Item -LiteralPath $LaneBackup -Destination $Lane -Force}
  if(Test-Path -LiteralPath $NativeBackup){Copy-Item -LiteralPath $NativeBackup -Destination $NativeLive -Force}
  $server=Join-Path $Repo 'scripts\ai-os\raios_mcp\server.py'
  $gateway=Join-Path $Repo 'scripts\ai-os\raios_mcp\gateway.py'
  if(Test-Path -LiteralPath (Join-Path $EightHold 'server.py')){Copy-Item -LiteralPath (Join-Path $EightHold 'server.py') -Destination $server -Force}
  if(Test-Path -LiteralPath (Join-Path $EightHold 'gateway.py')){Copy-Item -LiteralPath (Join-Path $EightHold 'gateway.py') -Destination $gateway -Force}
 }catch{$err+=';SOURCE_RESTORE_ERROR='+[string]$_.Exception.Message}
 if($cutoverStarted){
  try{
   if(Test-Path -LiteralPath $Backup){
    [void](Invoke-ScmCrashHandoff $Backup 'NATIVE_ROLLBACK_BACKUP')
    Copy-Item -LiteralPath $Backup -Destination $Live -Force
    [void](Invoke-ScmCrashHandoff $Live 'NATIVE_ROLLBACK_LIVE')
   }
  }catch{$err+=';ROLLBACK_ERROR='+[string]$_.Exception.Message}
 }
 try{
  if($promotionRequested){
   $ensure=Join-Path $Repo 'scripts\ai-os\raios_mcp_local_ensure.ps1'
   & powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $ensure -Port 8788 -PromoteOwnedGeneration -ExpectedToolContract 8
   if($LASTEXITCODE -ne 0){throw ('EIGHT_TOOL_RESTORE_FAILED:'+$LASTEXITCODE)}
  }
 }catch{$err+=';MCP_RESTORE_ERROR='+[string]$_.Exception.Message}
 $rec=[ordered]@{
  schema='raios.c5.native-channel-cutover.v1';request_id=$RequestId;status='FAIL'
  rolled_back=[bool]$cutoverStarted;started_at=$started.ToString('o');finished_at=[DateTimeOffset]::UtcNow.ToString('o')
  error=$err;first_failing_gate=$err;before_binary_sha256=$beforeHash;stage_sha256=$stageHash;gates=$gates
 }
 try{Write-Receipt $rec}catch{}
 exit 31
}
