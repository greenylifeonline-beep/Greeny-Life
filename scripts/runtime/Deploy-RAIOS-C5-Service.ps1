param([string]$Repo='C:\Users\Ghanam\Documents\Codex\Greeny-Life')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$Root='C:\Users\Ghanam\.raios\runtime\continuity\c5-service'
$RuntimeContinuity='C:\Users\Ghanam\.raios\runtime\continuity'
$RuntimeTunnel='C:\Users\Ghanam\.raios\runtime\mcp-tunnel'
$Source=Join-Path $Repo 'scripts\runtime\RAIOS.C5.ServiceHost.cs'
$Maintain=Join-Path $Repo 'scripts\runtime\Maintain-RAIOS-Online.ps1'
$UserLane=Join-Path $Repo 'scripts\runtime\c5-service\Invoke-RAIOS-C5-UserLane.ps1'
$Dcr=Join-Path $Repo 'scripts\runtime\continuity\reap_stale_rdc_sessions.py'
$Checkpoint=Join-Path $Repo 'scripts\runtime\continuity\raios_reconnect_checkpoint.py'
$NativeLauncher=Join-Path $Repo 'scripts\runtime\Start-RAIOS-Native-MCP-System.ps1'
$RuntimeUserLane=Join-Path $Root 'Invoke-RAIOS-C5-UserLane.ps1'
$RuntimeDcr=Join-Path $RuntimeContinuity 'reap_stale_rdc_sessions.py'
$RuntimeCheckpoint=Join-Path $RuntimeContinuity 'raios_reconnect_checkpoint.py'
$RuntimeNativeLauncher=Join-Path $RuntimeTunnel 'Start-RAIOS-Native-MCP-System.ps1'
$Live=Join-Path $Root 'RAIOS-C5-Service.exe'
$Stage=Join-Path $Root 'RAIOS-C5-Service.stage.exe'
$Previous=Join-Path $Root 'RAIOS-C5-Service.previous.exe'
$Receipt=Join-Path $Root 'service-deploy-receipt.json'
$GenerationState=Join-Path $Root 'current-generation.json'
$Csc='C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$Python='C:\Users\Ghanam\AppData\Local\Programs\Python\Python314\python.exe'
$RollbackRoot=Join-Path $env:LOCALAPPDATA ('Temp\raios-c5-deploy-rollback-'+[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss'))
$PhasePath=Join-Path $Root 'service-deploy-phase.json'
$FailurePath=Join-Path $Root 'service-deploy-failure.json'
$script:CurrentDeployPhase='BOOTSTRAP'

function Write-DeployPhase([string]$Name,[hashtable]$Extra=$null){
 $script:CurrentDeployPhase=$Name
 try{
  $o=[ordered]@{schema='raios.c5.service-deploy.phase.v1';observed_at=[DateTimeOffset]::UtcNow.ToString('o');phase=$Name;pid=$PID}
  if($Extra){foreach($k in $Extra.Keys){$o[$k]=$Extra[$k]}}
  $tmp=$PhasePath+'.tmp-'+[guid]::NewGuid().ToString('N')
  $o|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $tmp -Encoding UTF8
  Move-Item -LiteralPath $tmp -Destination $PhasePath -Force
 }catch{}
}

function Assert-File([string]$Path){
 if(-not [IO.File]::Exists($Path)){throw "MISSING::$Path"}
}

function Test-PowerShellSource([string]$Path,[int]$TimeoutSeconds=15){
 try{
  $text=[IO.File]::ReadAllText($Path)
  [scriptblock]::Create($text) | Out-Null
 }catch{
  throw ('POWERSHELL_SYNTAX_FAILED::'+$Path+'::'+$_.Exception.Message)
 }
}

function Read-JsonObjectSafe([string]$Path){
 try{
  if(-not(Test-Path -LiteralPath $Path)){return $null}
  $raw=Get-Content -LiteralPath $Path -Raw
  if([string]::IsNullOrWhiteSpace($raw)){return $null}
  $obj=$raw|ConvertFrom-Json
  if($null -eq $obj){return $null}
  if($obj -is [System.Collections.IDictionary]){
   $copy=[pscustomobject]@{}
   foreach($k in @($obj.Keys)){
    $copy|Add-Member -MemberType NoteProperty -Name ([string]$k) -Value $obj[$k] -Force
   }
   return $copy
  }
  return $obj
 }catch{return $null}
}

function Get-JsonProp($Object,[string]$Name,$Default=$null){
 if($null -eq $Object){return $Default}
 try{
  $p=$Object.PSObject.Properties[$Name]
  if($null -eq $p){return $Default}
  return $p.Value
 }catch{return $Default}
}

function Copy-Atomic([string]$SourcePath,[string]$TargetPath){
 $dir=Split-Path $TargetPath
 [IO.Directory]::CreateDirectory($dir)|Out-Null
 $tmp=$TargetPath+'.tmp-'+[guid]::NewGuid().ToString('N')
 try{
  Copy-Item -LiteralPath $SourcePath -Destination $tmp -Force
  if((Get-FileHash -LiteralPath $SourcePath -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $tmp -Algorithm SHA256).Hash){
   throw "ATOMIC_COPY_HASH_MISMATCH::$TargetPath"
  }
  Move-Item -LiteralPath $tmp -Destination $TargetPath -Force
 }finally{
  if(Test-Path -LiteralPath $tmp){Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue}
 }
}

function Test-LocalMcpReady {
 try{
  $m=Invoke-RestMethod -Uri 'http://127.0.0.1:8788/health' -TimeoutSec 3
  return ($m.ok -eq $true -and [int]$m.tool_count -eq 9 -and $m.execute_scoped_task -eq $true -and $m.second_gateway -eq $false)
 }catch{return $false}
}

function Test-NativeMcpTunnelReady {
 if(-not(Test-LocalMcpReady)){return $false}
 $healthFile='C:\Users\Ghanam\.local\state\tunnel-client\health\raios-native.url'
 if(-not(Test-Path -LiteralPath $healthFile)){return $false}
 try{
  $base=(Get-Content -LiteralPath $healthFile -Raw).Trim()
  if($base -notmatch '^http://127\.0\.0\.1:\d+$'){return $false}
 }catch{return $false}
 try{
  $r=Invoke-WebRequest -UseBasicParsing -Uri ($base+'/readyz') -TimeoutSec 3
  if($r.StatusCode -eq 200 -and $r.Content.Trim().StartsWith('ready',[StringComparison]::OrdinalIgnoreCase)){return $true}
 }catch{}
 try{
  $r=Invoke-WebRequest -UseBasicParsing -Uri ($base+'/metrics') -TimeoutSec 3
  return ($r.StatusCode -eq 200)
 }catch{return $false}
}

function Get-NativeShape {
 $all=@(Get-Process -Name 'tunnel-client' -ErrorAction SilentlyContinue)
 return [pscustomobject]@{
  System=@($all|Where-Object{$_.SessionId -eq 0})
  Console=@($all|Where-Object{$_.SessionId -ne 0})
 }
}

function Restore-RuntimeFiles {
 param([hashtable]$Backups)
 foreach($target in @($Backups.Keys)){
  $backup=[string]$Backups[$target]
  try{
   if($backup -and (Test-Path -LiteralPath $backup)){Copy-Item -LiteralPath $backup -Destination $target -Force}
  }catch{}
 }
}

function Retire-LegacyArtifacts([string]$CurrentServicePath){
 $retiredTasks=[System.Collections.Generic.List[string]]::new()
 foreach($name in @('RAIOS-C5-Permanent','RAIOS-RemoteDesktopCommander')){
  try{
   & "$env:SystemRoot\System32\schtasks.exe" /Query /TN $name *> $null
   if($LASTEXITCODE -eq 0){
    & "$env:SystemRoot\System32\schtasks.exe" /Delete /TN $name /F *> $null
    if($LASTEXITCODE -eq 0){$retiredTasks.Add($name)}
   }
  }catch{}
 }
 $removedBins=[System.Collections.Generic.List[string]]::new()
 foreach($f in @(Get-ChildItem -LiteralPath $Root -File -ErrorAction SilentlyContinue)){
  if($f.FullName -eq $CurrentServicePath -or $f.FullName -eq $Previous){continue}
  if($f.Name -match '^RAIOS-C5-Service\.v\d+[a-z]*\.exe$' -or $f.Name -in @('RAIOS-C5-Service.next.exe','RAIOS-C5-Service.stage.exe')){
   try{Remove-Item -LiteralPath $f.FullName -Force; $removedBins.Add($f.Name)}catch{}
  }
 }
 return [pscustomobject]@{tasks=@($retiredTasks);binaries=@($removedBins)}
}

# ---------- PRE-FLIGHT: no live mutation before all source gates pass ----------
Write-DeployPhase 'PRECHECK_START'
Write-DeployPhase 'ASSERT_FILES_START'
foreach($p in @($Source,$Maintain,$UserLane,$Dcr,$Checkpoint,$NativeLauncher,$Csc,$Python)){Assert-File $p}
Write-DeployPhase 'ASSERT_FILES_PASS'
Write-DeployPhase 'PARSE_MAINTAIN'
Test-PowerShellSource $Maintain
Write-DeployPhase 'PARSE_USERLANE'
Test-PowerShellSource $UserLane
Write-DeployPhase 'PARSE_NATIVE_LAUNCHER'
Test-PowerShellSource $NativeLauncher
Write-DeployPhase 'PARSE_DEPLOYER'
Test-PowerShellSource $PSCommandPath
Write-DeployPhase 'POWERSHELL_SYNTAX_PASS'
$serviceText=[IO.File]::ReadAllText($Source)
Write-DeployPhase 'SERVICE_STATIC_CONTRACT'
if($serviceText.Contains([char]9)){throw 'SERVICE_SOURCE_TAB_CONTROL_CHARACTER'}
if(([regex]::Matches($serviceText,[regex]::Escape('C:\Windows\System32\taskkill.exe'))).Count -ne 1){throw 'SERVICE_PROCESS_TERMINATOR_SINGLETON_CONTRACT_FAILED'}
Write-DeployPhase 'SOURCE_SYNTAX_PASS'

$pySyntax='import sys;[compile(open(p,chr(114)+chr(98)).read(),p,chr(101)+chr(120)+chr(101)+chr(99)) for p in sys.argv[1:]]'
& $Python -c $pySyntax $Dcr $Checkpoint
if($LASTEXITCODE -ne 0){throw "PY_SYNTAX_FAILED::$LASTEXITCODE"}
Write-DeployPhase 'PYTHON_SYNTAX_PASS'

[IO.Directory]::CreateDirectory($Root)|Out-Null
& $Csc /nologo /target:exe /out:$Stage /reference:System.ServiceProcess.dll /reference:System.Web.Extensions.dll $Source
if($LASTEXITCODE -ne 0){throw "SERVICE_COMPILE_FAILED::$LASTEXITCODE"}
Write-DeployPhase 'SERVICE_COMPILE_PASS'
$self=@(& $Stage --selftest 2>&1)
if($LASTEXITCODE -ne 0 -or -not($self -contains 'SELFTEST=PASS')){
 throw ('SERVICE_SELFTEST_FAILED::'+($self -join ';'))
}
Write-DeployPhase 'SELFTEST_PASS'

$before=Get-CimInstance Win32_Service -Filter "Name='RAIOS-C5'"
if(-not $before){throw 'RAIOS_C5_SERVICE_NOT_INSTALLED'}
$beforePid=[int]$before.ProcessId
$beforeState=[string]$before.State
$beforePath=[string]$before.PathName
$beforeStartMode=[string]$before.StartMode

[IO.Directory]::CreateDirectory($RollbackRoot)|Out-Null
$runtimeBackups=@{}
foreach($pair in @(
 @($RuntimeUserLane,$UserLane),
 @($RuntimeDcr,$Dcr),
 @($RuntimeCheckpoint,$Checkpoint),
 @($RuntimeNativeLauncher,$NativeLauncher)
)){
 $target=[string]$pair[0]
 if(Test-Path -LiteralPath $target){
  $bak=Join-Path $RollbackRoot ([IO.Path]::GetFileName($target)+'.bak')
  Copy-Item -LiteralPath $target -Destination $bak -Force
  $runtimeBackups[$target]=$bak
 }
}
if(Test-Path -LiteralPath $Live){
 Copy-Item -LiteralPath $Live -Destination (Join-Path $RollbackRoot 'RAIOS-C5-Service.exe.bak') -Force
}
if(Test-Path -LiteralPath $beforePath){
 Copy-Item -LiteralPath $beforePath -Destination $Previous -Force
}

$deploymentStarted=$false
try{
 Write-DeployPhase 'CUTOVER_BEGIN'
 if((Get-Service RAIOS-C5).Status -ne 'Stopped'){
  Write-DeployPhase 'SERVICE_STOP_BEGIN'
  Stop-Service RAIOS-C5 -Force
  (Get-Service RAIOS-C5).WaitForStatus('Stopped',[TimeSpan]::FromSeconds(30))
  Write-DeployPhase 'SERVICE_STOP_PASS'
 }

 Write-DeployPhase 'COPY_SERVICE_BINARY'
 Copy-Atomic $Stage $Live
 Write-DeployPhase 'COPY_USER_LANE'
 Copy-Atomic $UserLane $RuntimeUserLane
 Write-DeployPhase 'COPY_DCR_SUPERVISOR'
 Copy-Atomic $Dcr $RuntimeDcr
 Write-DeployPhase 'COPY_RECONNECT_CHECKPOINT'
 Copy-Atomic $Checkpoint $RuntimeCheckpoint
 Write-DeployPhase 'COPY_NATIVE_LAUNCHER'
 Copy-Atomic $NativeLauncher $RuntimeNativeLauncher
 Write-DeployPhase 'RUNTIME_COPY_PASS'

 Write-DeployPhase 'SC_CONFIG_BEGIN'
 & sc.exe config RAIOS-C5 binPath= $Live start= auto | Out-Null
 if($LASTEXITCODE -ne 0){throw 'SC_CONFIG_FAILED'}
 Write-DeployPhase 'SC_FAILURE_POLICY_BEGIN'
 & sc.exe failure RAIOS-C5 reset= 86400 actions= restart/5000/restart/15000/restart/30000 | Out-Null
 if($LASTEXITCODE -ne 0){throw 'SC_FAILURE_CONFIG_FAILED'}
 Write-DeployPhase 'SC_FAILUREFLAG_BEGIN'
 & sc.exe failureflag RAIOS-C5 1 | Out-Null
 if($LASTEXITCODE -ne 0){throw 'SC_FAILUREFLAG_CONFIG_FAILED'}
 Write-DeployPhase 'SC_CONFIG_PASS'

 Write-DeployPhase 'SERVICE_START_BEGIN'
 Start-Service RAIOS-C5
 (Get-Service RAIOS-C5).WaitForStatus('Running',[TimeSpan]::FromSeconds(30))
 $deploymentStarted=$true
 Write-DeployPhase 'SERVICE_STARTED'

 $deadline=[DateTimeOffset]::UtcNow.AddSeconds(180)
 $state=$null;$dcrState=$null;$laneState=$null;$generation=$null;$shape=$null;$nativeReady=$false;$svc=$null
 do{
  Start-Sleep -Seconds 2
  $state=Read-JsonObjectSafe (Join-Path $Root 'state.json')
  $dcrState=Read-JsonObjectSafe 'C:\Users\Ghanam\.raios\runtime\remote-access\rdc-system-direct\rdc-supervisor-state.json'
  $laneState=Read-JsonObjectSafe (Join-Path $Root 'user-lane-state.json')
  $generation=Read-JsonObjectSafe $GenerationState
  $svc=Get-CimInstance Win32_Service -Filter "Name='RAIOS-C5'"
  $nativeReady=Test-NativeMcpTunnelReady
  $shape=Get-NativeShape
  $svcPid=[int]$(if($svc){$svc.ProcessId}else{0})
  $dcrOwnerPid=[int](Get-JsonProp $dcrState 'owner_pid' 0)
  $dcrOwnedRemote=@(Get-JsonProp $dcrState 'owned_remote_pids' @())
  $dcrOwnedLocal=@(Get-JsonProp $dcrState 'owned_local_mcp_pids' @())
  $dcrLegacyRemote=@(Get-JsonProp $dcrState 'legacy_remote_pids' @())
  $dcrOwned=[bool]($null -ne $dcrState -and $dcrOwnerPid -eq $svcPid)
  $dcrShapeOk=[bool]($null -ne $dcrState -and $dcrOwnedRemote.Count -eq 1 -and $dcrOwnedLocal.Count -eq 1 -and $dcrLegacyRemote.Count -eq 0)
  $imageOk=[bool]($svc -and ([string]$svc.PathName).Trim('"') -eq $Live)
  $runtimeAligned=[bool](
    (Get-FileHash $UserLane -Algorithm SHA256).Hash -eq (Get-FileHash $RuntimeUserLane -Algorithm SHA256).Hash -and
    (Get-FileHash $Dcr -Algorithm SHA256).Hash -eq (Get-FileHash $RuntimeDcr -Algorithm SHA256).Hash -and
    (Get-FileHash $Checkpoint -Algorithm SHA256).Hash -eq (Get-FileHash $RuntimeCheckpoint -Algorithm SHA256).Hash -and
    (Get-FileHash $NativeLauncher -Algorithm SHA256).Hash -eq (Get-FileHash $RuntimeNativeLauncher -Algorithm SHA256).Hash
  )
  $laneOk=[bool](
    $null -ne $laneState -and
    [string](Get-JsonProp $laneState 'role' '') -eq 'INTERACTIVE_SESSION_ADAPTER' -and
    [string](Get-JsonProp $laneState 'control_authority' '') -eq 'RAIOS-C5-SCM' -and
    [bool](Get-JsonProp $laneState 'can_start_dcr_supervisor' $true) -eq $false -and
    [bool](Get-JsonProp $laneState 'can_start_native_tunnel' $true) -eq $false -and
    [bool](Get-JsonProp $laneState 'can_promote_source' $true) -eq $false
  )
  $generationOk=[bool](
    $null -ne $generation -and
    [string](Get-JsonProp $generation 'role' '') -eq 'LEADER' -and
    [string](Get-JsonProp $generation 'authority' '') -eq 'RAIOS-C5-SCM' -and
    [int](Get-JsonProp $generation 'service_pid' 0) -eq $svcPid -and
    [string](Get-JsonProp $generation 'acceptance' '') -eq 'PASS' -and
    [bool](Get-JsonProp $generation 'ok' $false) -eq $true
  )
  $ok=[bool](
    $svc -and [string]$svc.State -eq 'Running' -and $svcPid -gt 4 -and $imageOk -and $runtimeAligned -and
    $null -ne $state -and
    [string](Get-JsonProp $state 'status' '') -eq 'ONLINE' -and
    [string](Get-JsonProp $state 'control_authority' '') -eq 'RAIOS-C5-SCM' -and
    [bool](Get-JsonProp $state 'single_control_authority' $false) -eq $true -and
    [bool](Get-JsonProp $state 'scheduler_authority' $true) -eq $false -and
    [int](Get-JsonProp $state 'dcr_supervisor_pid' 0) -gt 4 -and
    [bool](Get-JsonProp $state 'dcr_ready' $false) -eq $true -and
    [bool](Get-JsonProp $state 'dcr_owned_by_service' $false) -eq $true -and
    [int](Get-JsonProp $state 'native_tunnel_owner_pid' 0) -gt 4 -and
    [bool](Get-JsonProp $state 'native_tunnel_ready' $false) -eq $true -and
    [bool](Get-JsonProp $state 'native_tunnel_owned_by_service' $false) -eq $true -and
    $null -ne $dcrState -and
    [string](Get-JsonProp $dcrState 'authority' '') -eq 'RAIOS-C5' -and
    [string](Get-JsonProp $dcrState 'status' '') -eq 'ONLINE' -and
    $dcrOwned -and $dcrShapeOk -and $laneOk -and $generationOk -and
    $nativeReady -and @($shape.System).Count -eq 1 -and @($shape.Console).Count -eq 0
  )
 }until($ok -or [DateTimeOffset]::UtcNow -ge $deadline)

 if(-not $ok){
  $acceptanceSnapshot=[ordered]@{
   service_running=[bool]($svc -and [string]$svc.State -eq 'Running')
   service_pid=$svcPid
   image_ok=$imageOk
   runtime_aligned=$runtimeAligned
   state_status=[string](Get-JsonProp $state 'status' '')
   state_control_authority=[string](Get-JsonProp $state 'control_authority' '')
   state_single_control_authority=[bool](Get-JsonProp $state 'single_control_authority' $false)
   state_scheduler_authority=[bool](Get-JsonProp $state 'scheduler_authority' $true)
   dcr_supervisor_pid=[int](Get-JsonProp $state 'dcr_supervisor_pid' 0)
   dcr_ready=[bool](Get-JsonProp $state 'dcr_ready' $false)
   dcr_owned_by_service=[bool](Get-JsonProp $state 'dcr_owned_by_service' $false)
   native_tunnel_owner_pid=[int](Get-JsonProp $state 'native_tunnel_owner_pid' 0)
   native_tunnel_ready=[bool](Get-JsonProp $state 'native_tunnel_ready' $false)
   native_tunnel_owned_by_service=[bool](Get-JsonProp $state 'native_tunnel_owned_by_service' $false)
   dcr_authority=[string](Get-JsonProp $dcrState 'authority' '')
   dcr_status=[string](Get-JsonProp $dcrState 'status' '')
   dcr_owned=$dcrOwned
   dcr_shape_ok=$dcrShapeOk
   lane_ok=$laneOk
   generation_ok=$generationOk
   native_ready=$nativeReady
   native_system_count=@($shape.System).Count
   native_console_count=@($shape.Console).Count
  }
  Write-DeployPhase 'ACCEPTANCE_FAILED' $acceptanceSnapshot
  throw 'C5_ACCEPTANCE_FAILED'
 }
 Write-DeployPhase 'ACCEPTANCE_PASS' @{
  service_pid=$svcPid
  dcr_pid=[int](Get-JsonProp $state 'dcr_supervisor_pid' 0)
  native_pid=[int](Get-JsonProp $state 'native_tunnel_owner_pid' 0)
  generation_id=[string](Get-JsonProp $generation 'generation_id' '')
 }

 $after=Get-CimInstance Win32_Service -Filter "Name='RAIOS-C5'"
 $cleanup=Retire-LegacyArtifacts -CurrentServicePath $Live

 $receipt=[ordered]@{
  schema='raios.c5.service-deploy.v3'
  observed_at=[DateTimeOffset]::UtcNow.ToString('o')
  repo=$Repo
  control_authority='RAIOS-C5-SCM'
  single_control_authority=$true
  source_sha256=(Get-FileHash $Source -Algorithm SHA256).Hash.ToLower()
  binary_sha256=(Get-FileHash $Live -Algorithm SHA256).Hash.ToLower()
  before_pid=$beforePid
  before_state=$beforeState
  before_image_path=$beforePath
  after_pid=[int]$after.ProcessId
  after_state=[string]$after.State
  after_image_path=[string]$after.PathName
  dcr_supervisor_pid=[int](Get-JsonProp $state 'dcr_supervisor_pid' 0)
  dcr_status=[string](Get-JsonProp $dcrState 'status' '')
  dcr_provider_role='REMOTE_CAPABILITY_PROVIDER'
  dcr_control_authority=$false
  dcr_owner_pid=[int](Get-JsonProp $dcrState 'owner_pid' 0)
  native_tunnel_authority='RAIOS-C5-SCM'
  native_channel_role='SINGLE_EXTERNAL_RAIOS_CHANNEL'
  native_tunnel_ready=[bool]$nativeReady
  native_tunnel_system_count=@($shape.System).Count
  native_tunnel_console_count=@($shape.Console).Count
  user_lane_role='INTERACTIVE_SESSION_ADAPTER'
  user_lane_control_authority=$false
  scheduler_authority=$false
  generation_id=[string](Get-JsonProp $generation 'generation_id' '')
  generation_role=[string](Get-JsonProp $generation 'role' '')
  generation_acceptance=[string](Get-JsonProp $generation 'acceptance' '')
  legacy_tasks_removed=@($cleanup.tasks)
  obsolete_service_binaries_removed=@($cleanup.binaries)
  rollback_available=(Test-Path -LiteralPath $Previous)
  source_preflight='PASS'
  acceptance='PASS'
  ok=$true
 }
 $tmp=$Receipt+'.tmp-'+[guid]::NewGuid().ToString('N')
 $receipt|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $tmp -Encoding UTF8
 Move-Item -LiteralPath $tmp -Destination $Receipt -Force
 Remove-Item -LiteralPath $RollbackRoot -Recurse -Force -ErrorAction SilentlyContinue
 $receipt|ConvertTo-Json -Compress
 exit 0
}
catch{
 $err=$_
 $failure=[string]$err.Exception.Message
 $failureType=[string]$err.Exception.GetType().FullName
 $failureId=[string]$err.FullyQualifiedErrorId
 $failureStack=[string]$err.ScriptStackTrace
 $failurePosition=[string]$err.InvocationInfo.PositionMessage
 $failureCommand=[string]$err.InvocationInfo.MyCommand
 $failurePhase=[string]$script:CurrentDeployPhase
 try{
  $svcFailure=Get-CimInstance Win32_Service -Filter "Name='RAIOS-C5'" -ErrorAction SilentlyContinue
  $diag=[ordered]@{
   schema='raios.c5.service-deploy.failure.v1'
   observed_at=[DateTimeOffset]::UtcNow.ToString('o')
   phase=$failurePhase
   exception_type=$failureType
   message=$failure
   fully_qualified_error_id=$failureId
   script_stack_trace=$failureStack
   invocation_position=$failurePosition
   invocation_command=$failureCommand
   deployment_started=[bool]$deploymentStarted
   rollback_root=$RollbackRoot
   before_pid=$beforePid
   before_state=$beforeState
   service_state=$(if($svcFailure){[string]$svcFailure.State}else{'MISSING'})
   service_pid=$(if($svcFailure){[int]$svcFailure.ProcessId}else{0})
  }
  $failureTmp=$FailurePath+'.tmp-'+[guid]::NewGuid().ToString('N')
  $diag|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $failureTmp -Encoding UTF8
  Move-Item -LiteralPath $failureTmp -Destination $FailurePath -Force
 }catch{}
 Write-DeployPhase 'ROLLBACK_BEGIN' @{
  failure=$failure
  failed_phase=$failurePhase
  exception_type=$failureType
  fully_qualified_error_id=$failureId
 }
 try{
  Stop-Service RAIOS-C5 -Force -ErrorAction SilentlyContinue
  (Get-Service RAIOS-C5).WaitForStatus('Stopped',[TimeSpan]::FromSeconds(20))
 }catch{}
 try{
  $liveBak=Join-Path $RollbackRoot 'RAIOS-C5-Service.exe.bak'
  if(Test-Path -LiteralPath $liveBak){Copy-Item -LiteralPath $liveBak -Destination $Live -Force}
  Restore-RuntimeFiles -Backups $runtimeBackups
  & sc.exe config RAIOS-C5 binPath= $beforePath start= auto | Out-Null
  if($beforeState -eq 'Running'){
   Start-Service RAIOS-C5
   (Get-Service RAIOS-C5).WaitForStatus('Running',[TimeSpan]::FromSeconds(30))
  }
 }catch{}
 throw ('C5_DEPLOY_ROLLED_BACK::'+$failurePhase+'::'+$failureType+'::'+$failure)
}