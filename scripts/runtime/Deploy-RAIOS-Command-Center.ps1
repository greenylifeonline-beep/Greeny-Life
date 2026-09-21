param(
 [string]$RuntimeRoot="$HOME\.raios\runtime\command-center",
 [int]$Port=8770,
 [string]$McpRoot="",
 [string]$ManifestPath="",
 [switch]$ValidateOnly,
 [switch]$FaultInjectCutoverFailure,
 [switch]$C1AuthorizeWorkingTree,
 [switch]$HeadOnlyRecovery
)
$ErrorActionPreference="Stop"
function Test-RaiosTcp([int]$Port,[int]$TimeoutMs=800){
 try{$client=[Net.Sockets.TcpClient]::new();$pending=$client.BeginConnect("127.0.0.1",$Port,$null,$null);$ok=$pending.AsyncWaitHandle.WaitOne($TimeoutMs) -and $client.Connected;$client.Close();return [bool]$ok}catch{return $false}
}
function Get-RaiosListenPid([int]$Port){
 foreach($line in (& netstat -ano -p tcp 2>$null)){
  $parts=@($line.ToString().Trim() -split '\s+')
  if($parts.Length -lt 5){continue}
  if($parts[-2] -ne 'LISTENING'){continue}
  if($parts[1] -match (":$Port$")){return [int]$parts[-1]}
 }
 return $null
}
if($FaultInjectCutoverFailure -and ($Port -eq 8770 -or $env:RAIOS_DEPLOYMENT_TEST_MODE -ne "1")){throw "FAULT_INJECTION_FORBIDDEN_ON_PRODUCTION"}
$Repo=(Resolve-Path(Join-Path $PSScriptRoot "..\..")).Path
$Head=(git -C $Repo rev-parse HEAD).Trim()
$DeployBasePaths=@(
 "src/raios/command_center","src/raios/goals","src/raios/search_cortex","src/raios/resource_fabric",
 "src/raios/ai_gateway","src/raios/council_ops","src/raios/a2a","src/raios/command_fabric","src/raios/c1c5","src/raios/neuro_lingua","RAIOS/V9/runtime/cognitive_event_bus.py","RAIOS/V9/runtime/git_history_search.py","scripts/ai-os/raios_mcp"
)
$DeployGatePaths=@($DeployBasePaths+"scripts/runtime/Deploy-RAIOS-Command-Center.ps1")
function Normalize-RepoPath([string]$PathValue){
 $v=($PathValue -replace '\\','/').TrimStart('./')
 if([string]::IsNullOrWhiteSpace($v) -or $v.Contains('..')){throw "DEPLOY_PATH_INVALID::$PathValue"}
 return $v
}
function Sha256([string]$PathValue){ return (Get-FileHash -LiteralPath $PathValue -Algorithm SHA256).Hash.ToLowerInvariant() }
function Scope-Overlap([string]$A,[string]$B){
 $a=(Normalize-RepoPath $A).TrimEnd('/','*');$b=(Normalize-RepoPath $B).TrimEnd('/','*')
 return ($a -eq $b -or $a.StartsWith($b+'/') -or $b.StartsWith($a+'/'))
}
function Map-ToApp([string]$Relative,[string]$AppRoot){
 $r=Normalize-RepoPath $Relative
 if($r.StartsWith('src/raios/')){return Join-Path $AppRoot ('raios\'+$r.Substring(10).Replace('/','\'))}
 if($r.StartsWith('scripts/ai-os/raios_mcp/')){return Join-Path $AppRoot ('raios_mcp\'+$r.Substring(25).Replace('/','\'))}
 throw "OVERLAY_NOT_RUNTIME_MAPPABLE::$r"
}
function Load-Json([string]$PathValue){ return Get-Content -LiteralPath $PathValue -Raw -Encoding UTF8 | ConvertFrom-Json }
function Require-CommandFabricLease($Grant,$Tasks){
 $path=Normalize-RepoPath ([string]$Grant.path);$leaseId=[string]$Grant.lease_id
 if([string]::IsNullOrWhiteSpace($leaseId)){throw "CF_LEASE_ID_REQUIRED::$path"}
 $leasePath=Join-Path $Repo (".ai-os/state/command-fabric/leases/"+$leaseId+".json")
 if(-not(Test-Path -LiteralPath $leasePath -PathType Leaf)){throw "CF_LEASE_NOT_FOUND::$path"}
 $lease=Load-Json $leasePath
 if([string]$lease.schema -ne 'raios.write-lease.v2' -or [string]$lease.state -ne 'ACTIVE'){throw "CF_LEASE_NOT_ACTIVE::$path"}
 if([string]$lease.owner -ne 'RAIOS_SYSTEM' -or [string]$Grant.lease_holder -ne 'RAIOS_SYSTEM'){throw "CF_LEASE_OWNER_INVALID::$path"}
 if((Normalize-RepoPath ([string]$lease.scope)) -ne $path -or [string]$lease.task_id -ne [string]$Grant.task_id){throw "CF_LEASE_BINDING_MISMATCH::$path"}
 if([Int64]$lease.fence_token -ne [Int64]$Grant.fence_token){throw "CF_LEASE_FENCE_MISMATCH::$path"}
 if([DateTimeOffset]::Parse([string]$lease.expires_at) -le [DateTimeOffset]::UtcNow){throw "CF_LEASE_EXPIRED::$path"}
 $task=$Tasks.tasks|Where-Object{$_.id -eq [string]$Grant.task_id}|Select-Object -First 1
 if(-not $task -or [string]$task.authorized_by -ne 'C1'){throw "CF_LEASE_TASK_NOT_C1_AUTHORIZED::$path"}
 $active=@(Get-ChildItem -LiteralPath (Join-Path $Repo '.ai-os/state/command-fabric/leases') -Filter '*.json' -File|ForEach-Object{try{Load-Json $_.FullName}catch{$null}}|Where-Object{[string]$_.state -eq 'ACTIVE' -and [string]$_.scope -eq $path -and [DateTimeOffset]::Parse([string]$_.expires_at) -gt [DateTimeOffset]::UtcNow})
 if($active.Count -ne 1 -or [string]$active[0].lease_id -ne $leaseId){throw "CF_LEASE_NOT_CURRENT::$path"}
 return $lease
}
function Require-TaskLease($Overlay,$Locks,$Tasks){
 $path=Normalize-RepoPath ([string]$Overlay.path)
 $lock=$Locks.locks|Where-Object{$_.id -eq [string]$Overlay.lock_id}|Select-Object -First 1
 if(-not $lock){throw "OVERLAY_LOCK_NOT_FOUND::$path"}
 if($lock.status -ne 'ACTIVE'){throw "OVERLAY_LOCK_NOT_ACTIVE::$path"}
 if((Normalize-RepoPath ([string]$lock.scope)) -ne $path){throw "OVERLAY_LOCK_SCOPE_MISMATCH::$path"}
 if([string]$lock.lease_holder -ne [string]$Overlay.lease_holder){throw "OVERLAY_LOCK_HOLDER_MISMATCH::$path"}
 if([string]$lock.task_id -ne [string]$Overlay.task_id){throw "OVERLAY_LOCK_TASK_MISMATCH::$path"}
 $task=$Tasks.tasks|Where-Object{$_.id -eq [string]$Overlay.task_id}|Select-Object -First 1
 if(-not $task){throw "OVERLAY_TASK_NOT_IN_CANONICAL_LEDGER::$path"}
 if([string]$task.authorized_by -ne 'C1'){throw "OVERLAY_TASK_NOT_C1_AUTHORIZED::$path"}
 $others=@($Locks.locks|Where-Object{$_.status -eq 'ACTIVE' -and $_.id -ne $lock.id -and (Scope-Overlap ([string]$_.scope) $path)})
 if($others.Count -gt 0){throw "OVERLAY_OVERLAPPING_ACTIVE_LEASE::$path"}
 return $lock
}
function Require-EngineLease($Engine,$Locks,$Tasks){
 $expected='scripts/runtime/Deploy-RAIOS-Command-Center.ps1'
 if((Normalize-RepoPath ([string]$Engine.path)) -ne $expected){throw 'DEPLOY_ENGINE_PATH_INVALID'}
 $actual=Sha256 (Join-Path $Repo $expected)
 if($actual -ne ([string]$Engine.expected_sha256).ToLowerInvariant()){throw 'DEPLOY_ENGINE_HASH_MISMATCH'}
 if($Engine.lease_id){[void](Require-CommandFabricLease $Engine $Tasks)}else{[void](Require-TaskLease $Engine $Locks $Tasks)}
}
if(-not $McpRoot){$McpRoot=$Repo}
$McpRoot=(Resolve-Path $McpRoot).Path
if($McpRoot -ne $Repo){throw "MCP_ROOT_MUST_EQUAL_CANONICAL_REPO"}
$Transactional=-not [string]::IsNullOrWhiteSpace($ManifestPath)
if($HeadOnlyRecovery -and $Transactional){throw 'HEAD_ONLY_RECOVERY_MANIFEST_FORBIDDEN'}
if($HeadOnlyRecovery -and $C1AuthorizeWorkingTree){throw 'HEAD_ONLY_RECOVERY_WORKING_TREE_FORBIDDEN'}
$Manifest=$null;$ManifestHash=$null;$TransactionId=$null;$App=$null;$Logs=Join-Path $RuntimeRoot 'logs'
if($HeadOnlyRecovery){
 $TransactionId='HEAD-RECOVERY-'+([guid]::NewGuid().ToString('N'))
 $TxRoot=Join-Path $RuntimeRoot ('transactions\'+$TransactionId);$Raw=Join-Path $TxRoot 'head';$App=Join-Path $TxRoot 'app'
 New-Item -ItemType Directory -Force -Path $Raw,$App,$Logs|Out-Null;$Archive=Join-Path $TxRoot 'head.tar';$DeployArchivePaths=@()
 foreach($basePath in $DeployBasePaths){$headMatch=@(& git -C $Repo ls-tree --name-only $Head -- $basePath);if($LASTEXITCODE -ne 0){throw "HEAD_PATH_PROBE_FAILED::$basePath"};if($headMatch.Count -gt 0){$DeployArchivePaths+=$basePath}}
 if($DeployArchivePaths.Count -eq 0){throw 'HEAD_ARCHIVE_NO_DEPLOY_PATHS'}
 & git -C $Repo archive --format=tar "--output=$Archive" $Head -- @DeployArchivePaths;if($LASTEXITCODE -ne 0){throw 'HEAD_ARCHIVE_MATERIALIZATION_FAILED'}
 & tar -xf $Archive -C $Raw;if($LASTEXITCODE -ne 0){throw 'HEAD_ARCHIVE_EXTRACTION_FAILED'}
 $map=@{'src/raios/command_center'='raios/command_center';'src/raios/goals'='raios/goals';'src/raios/search_cortex'='raios/search_cortex';'src/raios/resource_fabric'='raios/resource_fabric';'src/raios/ai_gateway'='raios/ai_gateway';'src/raios/council_ops'='raios/council_ops';'src/raios/a2a'='raios/a2a';'src/raios/command_fabric'='raios/command_fabric';'src/raios/c1c5'='raios/c1c5';'src/raios/neuro_lingua'='raios/neuro_lingua';'RAIOS/V9/runtime/cognitive_event_bus.py'='cognitive_event_bus.py';'RAIOS/V9/runtime/git_history_search.py'='git_history_search.py';'scripts/ai-os/raios_mcp'='raios_mcp'}
 foreach($k in $map.Keys){$src=Join-Path $Raw $k.Replace('/','\');if(Test-Path $src){$dst=Join-Path $App $map[$k].Replace('/','\');if((Get-Item -LiteralPath $src).PSIsContainer){New-Item -ItemType Directory -Force -Path $dst|Out-Null;Copy-Item (Join-Path $src '*') $dst -Recurse -Force}else{New-Item -ItemType Directory -Force -Path (Split-Path $dst -Parent)|Out-Null;Copy-Item -LiteralPath $src -Destination $dst -Force}}}
 New-Item -ItemType Directory -Force -Path (Join-Path $App 'raios')|Out-Null;if(-not(Test-Path(Join-Path $App 'raios\__init__.py'))){Set-Content(Join-Path $App 'raios\__init__.py')'' -Encoding UTF8}
 $DirtyAll=@(git -C $Repo status --porcelain -- @DeployGatePaths)
 ([ordered]@{schema='raios.command-center-head-recovery.v1';transaction_id=$TransactionId;canonical_head=$Head;base_source='GIT_OBJECT_DATABASE';working_tree_base_allowed=$false;unlisted_dirty_behavior='NEVER_DEPLOY';unlisted_dirty=@($DirtyAll);app_root=$App;materialized_at=[DateTimeOffset]::UtcNow.ToString('o')})|ConvertTo-Json -Depth 8|Set-Content(Join-Path $TxRoot 'materialization.json') -Encoding UTF8
 if($ValidateOnly){Write-Host 'HEAD_ONLY_RECOVERY_VALIDATION=PASS';Write-Host "TRANSACTION_ID=$TransactionId";Write-Host "APP_ROOT=$App";exit 0}
}elseif(-not $Transactional){
 $Dirty=@(git -C $Repo status --porcelain -- @DeployGatePaths)
 if($Dirty.Count -gt 0 -and -not $C1AuthorizeWorkingTree){throw "COMMAND_CENTER_CANONICAL_SOURCE_DIRTY::$($Dirty -join ';')"}
 $App=Join-Path $RuntimeRoot 'app'
}else{
 $ManifestPath=(Resolve-Path $ManifestPath).Path;$Manifest=Load-Json $ManifestPath
 if([string]$Manifest.schema -ne 'raios.command-center-deployment-manifest.v1'){throw 'DEPLOY_MANIFEST_SCHEMA_INVALID'}
 if([string]$Manifest.authorized_by -ne 'C1'){throw 'DEPLOY_MANIFEST_AUTHORITY_INVALID'}
 if([string]$Manifest.canonical_head -ne $Head){throw 'DEPLOY_MANIFEST_HEAD_MISMATCH'}
 if([string]$Manifest.base_source -ne 'GIT_OBJECT_DATABASE'){throw 'DEPLOY_BASE_SOURCE_INVALID'}
 if($Manifest.working_tree_base_allowed -ne $false){throw 'WORKING_TREE_BASE_FORBIDDEN'}
 $TransactionId=[string]$Manifest.transaction_id
 if([string]::IsNullOrWhiteSpace($TransactionId)){throw 'DEPLOY_TRANSACTION_ID_REQUIRED'}
 $ManifestHash=Sha256 $ManifestPath
 $Locks=Load-Json (Join-Path $Repo '.ai-os/state/LOCKS.json')
 $Tasks=Load-Json (Join-Path $Repo '.ai-os/state/TASKS.json')
 Require-EngineLease $Manifest.deployment_engine $Locks $Tasks
 $seen=@{}
 foreach($o in @($Manifest.overlays)){
  $rel=Normalize-RepoPath ([string]$o.path)
  if($seen.ContainsKey($rel)){throw "DUPLICATE_OVERLAY::$rel"};$seen[$rel]=$true
  $allowed=$false;foreach($root in $DeployBasePaths){if(Scope-Overlap $root $rel){$allowed=$true;break}}
  if(-not $allowed){throw "OVERLAY_OUTSIDE_DEPLOY_DOMAIN::$rel"}
  if($o.lease_id){[void](Require-CommandFabricLease $o $Tasks)}else{[void](Require-TaskLease $o $Locks $Tasks)}
  $src=Join-Path $Repo $rel
  if(-not(Test-Path -LiteralPath $src -PathType Leaf)){throw "OVERLAY_SOURCE_MISSING::$rel"}
  if((Sha256 $src) -ne ([string]$o.expected_sha256).ToLowerInvariant()){throw "OVERLAY_SOURCE_HASH_MISMATCH::$rel"}
 }
 $TxRoot=Join-Path $RuntimeRoot ('transactions\'+$TransactionId)
 if(Test-Path $TxRoot){Remove-Item -LiteralPath $TxRoot -Recurse -Force}
 $Raw=Join-Path $TxRoot 'head';$App=Join-Path $TxRoot 'app';New-Item -ItemType Directory -Force -Path $Raw,$App,$Logs|Out-Null
 $Archive=Join-Path $TxRoot 'head.tar'
 $DeployArchivePaths=@()
 foreach($basePath in $DeployBasePaths){
  $headMatch=@(& git -C $Repo ls-tree --name-only $Head -- $basePath)
  if($LASTEXITCODE -ne 0){throw "HEAD_PATH_PROBE_FAILED::$basePath"}
  if($headMatch.Count -gt 0){$DeployArchivePaths+=$basePath}
 }
 if($DeployArchivePaths.Count -eq 0){throw 'HEAD_ARCHIVE_NO_DEPLOY_PATHS'}
 & git -C $Repo archive --format=tar "--output=$Archive" $Head -- @DeployArchivePaths
 if($LASTEXITCODE -ne 0){throw 'HEAD_ARCHIVE_MATERIALIZATION_FAILED'}
 & tar -xf $Archive -C $Raw
 if($LASTEXITCODE -ne 0){throw 'HEAD_ARCHIVE_EXTRACTION_FAILED'}
 $map=@{
  'src/raios/command_center'='raios/command_center';'src/raios/goals'='raios/goals';'src/raios/search_cortex'='raios/search_cortex';
  'src/raios/resource_fabric'='raios/resource_fabric';'src/raios/ai_gateway'='raios/ai_gateway';
  'src/raios/council_ops'='raios/council_ops';'src/raios/a2a'='raios/a2a';'src/raios/command_fabric'='raios/command_fabric';'src/raios/c1c5'='raios/c1c5';'src/raios/neuro_lingua'='raios/neuro_lingua';'RAIOS/V9/runtime/cognitive_event_bus.py'='cognitive_event_bus.py';'RAIOS/V9/runtime/git_history_search.py'='git_history_search.py';'scripts/ai-os/raios_mcp'='raios_mcp'
 }
 foreach($k in $map.Keys){
  $src=Join-Path $Raw $k.Replace('/','\')
  if(Test-Path $src){
   $dst=Join-Path $App $map[$k].Replace('/','\')
   if((Get-Item -LiteralPath $src).PSIsContainer){New-Item -ItemType Directory -Force -Path $dst|Out-Null;Copy-Item (Join-Path $src '*') $dst -Recurse -Force}
   else{New-Item -ItemType Directory -Force -Path (Split-Path $dst -Parent)|Out-Null;Copy-Item -LiteralPath $src -Destination $dst -Force}
  }
 }
 New-Item -ItemType Directory -Force -Path (Join-Path $App 'raios')|Out-Null
 if(-not(Test-Path(Join-Path $App 'raios\__init__.py'))){Set-Content(Join-Path $App 'raios\__init__.py')'' -Encoding UTF8}
 foreach($o in @($Manifest.overlays)){
  $rel=Normalize-RepoPath ([string]$o.path);$src=Join-Path $Repo $rel;$dst=Map-ToApp $rel $App
  New-Item -ItemType Directory -Force -Path (Split-Path $dst -Parent)|Out-Null;Copy-Item -LiteralPath $src -Destination $dst -Force
  if((Sha256 $dst) -ne ([string]$o.expected_sha256).ToLowerInvariant()){throw "STAGED_OVERLAY_HASH_MISMATCH::$rel"}
 }
 $DirtyAll=@(git -C $Repo status --porcelain -- @DeployGatePaths)
 $Receipt=[ordered]@{schema='raios.command-center-deployment-transaction.v1';transaction_id=$TransactionId;canonical_head=$Head;manifest_sha256=$ManifestHash;base_source='GIT_OBJECT_DATABASE';working_tree_base_allowed=$false;unlisted_dirty_behavior='NEVER_DEPLOY';unlisted_dirty=@($DirtyAll);app_root=$App;materialized_at=[DateTimeOffset]::UtcNow.ToString('o');overlays=@($Manifest.overlays)}
 $Receipt|ConvertTo-Json -Depth 12|Set-Content(Join-Path $TxRoot 'materialization.json') -Encoding UTF8
 # Revalidate manifest, engine and overlay sources after staging.
 if((Sha256 $ManifestPath) -ne $ManifestHash){throw 'DEPLOY_MANIFEST_CHANGED_AFTER_FREEZE'}
 $Locks=Load-Json (Join-Path $Repo '.ai-os/state/LOCKS.json');$Tasks=Load-Json (Join-Path $Repo '.ai-os/state/TASKS.json')
 Require-EngineLease $Manifest.deployment_engine $Locks $Tasks
 foreach($o in @($Manifest.overlays)){if($o.lease_id){[void](Require-CommandFabricLease $o $Tasks)}else{[void](Require-TaskLease $o $Locks $Tasks)};$src=Join-Path $Repo (Normalize-RepoPath ([string]$o.path));if((Sha256 $src) -ne ([string]$o.expected_sha256).ToLowerInvariant()){throw "OVERLAY_CHANGED_AFTER_FREEZE::$($o.path)"}}
 if($ValidateOnly){Write-Host 'TRANSACTIONAL_DEPLOYMENT_VALIDATION=PASS';Write-Host "TRANSACTION_ID=$TransactionId";Write-Host "MANIFEST_SHA256=$ManifestHash";Write-Host "APP_ROOT=$App";exit 0}
}
$Pkg=Join-Path $App 'raios\command_center';$GoalsPkg=Join-Path $App 'raios\goals';$SearchPkg=Join-Path $App 'raios\search_cortex';$ResourcePkg=Join-Path $App 'raios\resource_fabric';$GatewayPkg=Join-Path $App 'raios\ai_gateway';$CouncilOpsPkg=Join-Path $App 'raios\council_ops';$A2APkg=Join-Path $App 'raios\a2a';$FabricPkg=Join-Path $App 'raios\command_fabric';$Mcp=Join-Path $App 'raios_mcp'
$Python=Join-Path $HOME '.raios\runtime\c5\.venv\Scripts\python.exe';if(-not(Test-Path $Python)){throw 'CANONICAL_C5_PYTHON_MISSING'}
$PythonWindowless=Join-Path $HOME '.raios\runtime\c5\.venv\Scripts\pythonw.exe';if(-not(Test-Path $PythonWindowless)){throw 'CANONICAL_C5_PYTHONW_MISSING'}
if(-not $Transactional -and -not $HeadOnlyRecovery){
 New-Item -ItemType Directory -Force -Path $Pkg,$GoalsPkg,$SearchPkg,$ResourcePkg,$GatewayPkg,$CouncilOpsPkg,$A2APkg,$FabricPkg,$Mcp,$Logs,(Join-Path $App 'raios')|Out-Null
 if(-not(Test-Path(Join-Path $App 'raios\__init__.py'))){Set-Content(Join-Path $App 'raios\__init__.py')'' -Encoding UTF8}
 Copy-Item(Join-Path $Repo 'src\raios\command_center\*')$Pkg -Recurse -Force;Copy-Item(Join-Path $Repo 'src\raios\goals\*')$GoalsPkg -Recurse -Force;Copy-Item(Join-Path $Repo 'src\raios\search_cortex\*')$SearchPkg -Recurse -Force
 Copy-Item(Join-Path $Repo 'src\raios\resource_fabric\*')$ResourcePkg -Recurse -Force;Copy-Item(Join-Path $Repo 'src\raios\ai_gateway\*')$GatewayPkg -Recurse -Force
 Copy-Item(Join-Path $Repo 'src\raios\council_ops\*')$CouncilOpsPkg -Recurse -Force;Copy-Item(Join-Path $Repo 'src\raios\a2a\*')$A2APkg -Recurse -Force;Copy-Item(Join-Path $Repo 'src\raios\command_fabric\*')$FabricPkg -Recurse -Force;Copy-Item(Join-Path $Repo 'scripts\ai-os\raios_mcp\*')$Mcp -Recurse -Force
}
$env:RAIOS_CANONICAL_REPO=$Repo;$env:RAIOS_CANONICAL_HEAD=$Head;$env:RAIOS_MCP_ROOT=$McpRoot;$env:RAIOS_COMMAND_CENTER_RUNTIME=$RuntimeRoot;$env:PYTHONPATH=$App
if($Transactional){$env:RAIOS_DEPLOYMENT_TRANSACTION_ID=$TransactionId;$env:RAIOS_DEPLOYMENT_MANIFEST_SHA256=$ManifestHash}
function Start-CenterAt([int]$Listen,[string]$Name,[string]$AppRoot,[string]$ExpectedHead){
 $out=Join-Path $Logs "$Name.out.log";$err=Join-Path $Logs "$Name.err.log"
 $savedPy=$env:PYTHONPATH;$savedHead=$env:RAIOS_CANONICAL_HEAD
 try{$env:PYTHONPATH=$AppRoot;$env:RAIOS_CANONICAL_HEAD=$ExpectedHead;return Start-Process $PythonWindowless -ArgumentList @('-m','uvicorn','raios.command_center.app:app','--app-dir',$AppRoot,'--host','127.0.0.1','--port',$Listen) -WorkingDirectory $Repo -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru}
 finally{$env:PYTHONPATH=$savedPy;$env:RAIOS_CANONICAL_HEAD=$savedHead}
}
function Wait-HealthyExpected([int]$Listen,[int]$ProcessId,[string]$ExpectedHead){$deadlineSeconds=if($env:RAIOS_CC_READINESS_DEADLINE_SECONDS){[int]$env:RAIOS_CC_READINESS_DEADLINE_SECONDS}else{180};$deadline=[DateTime]::UtcNow.AddSeconds($deadlineSeconds);while([DateTime]::UtcNow-lt$deadline){Start-Sleep -Milliseconds 500;if(-not(Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)){return $null};try{$r=Invoke-RestMethod "http://127.0.0.1:$Listen/health" -TimeoutSec 1;if($r.status-eq'ONLINE'-and$r.canonical_head-eq$ExpectedHead){return $r}}catch{}};return $null}
function Start-Center([int]$Listen,[string]$Name){return Start-CenterAt $Listen $Name $App $Head}
function Wait-Healthy([int]$Listen,[int]$ProcessId){return Wait-HealthyExpected $Listen $ProcessId $Head}
function Invoke-Rollback([string]$Reason,[object]$PreviousDeployment){
 if(-not $PreviousDeployment){throw "ROLLBACK_UNAVAILABLE_NO_PREVIOUS_DEPLOYMENT::$Reason"}
 $previousApp=[string]$PreviousDeployment.app_root;if(-not $previousApp){$previousApp=Join-Path $RuntimeRoot 'app'}
 $previousHead=[string]$PreviousDeployment.canonical_head
 if(-not $previousHead -or -not(Test-Path $previousApp)){throw "ROLLBACK_UNAVAILABLE_INVALID_PREVIOUS_DEPLOYMENT::$Reason"}
 $existingPid=Get-RaiosListenPid $Port
 if($existingPid){Stop-Process $existingPid -Force -ErrorAction SilentlyContinue;Start-Sleep -Milliseconds 300}
 $rollback=Start-CenterAt $Port 'center.rollback' $previousApp $previousHead
 $rollbackHealth=Wait-HealthyExpected $Port $rollback.Id $previousHead
 if(-not $rollbackHealth){Stop-Process $rollback.Id -Force -ErrorAction SilentlyContinue;throw "ROLLBACK_FAILED::$Reason"}
 $receipt=[ordered]@{schema='raios.command-center-rollback.v1';reason=$Reason;restored_head=$previousHead;restored_app_root=$previousApp;pid=$rollback.Id;rolled_back_at=[DateTimeOffset]::UtcNow.ToString('o');transaction_id=$TransactionId;manifest_sha256=$ManifestHash}
 $receipt|ConvertTo-Json -Depth 8|Set-Content(Join-Path $RuntimeRoot 'rollback-last.json') -Encoding UTF8
 return $rollbackHealth
}
$stagePort=$Port+1000;if(Test-RaiosTcp $stagePort){throw 'STAGE_PORT_IN_USE'}
$stage=Start-Center $stagePort 'center.stage';$proof=Wait-Healthy $stagePort $stage.Id
if(-not$proof){Stop-Process $stage.Id -Force -ErrorAction SilentlyContinue;throw 'COMMAND_CENTER_STAGE_FAILED'}
if($Transactional){
 if((Sha256 $ManifestPath) -ne $ManifestHash){Stop-Process $stage.Id -Force -ErrorAction SilentlyContinue;throw 'DEPLOY_MANIFEST_CHANGED_BEFORE_CUTOVER'}
 $Locks=Load-Json (Join-Path $Repo '.ai-os/state/LOCKS.json');$Tasks=Load-Json (Join-Path $Repo '.ai-os/state/TASKS.json');Require-EngineLease $Manifest.deployment_engine $Locks $Tasks
 foreach($o in @($Manifest.overlays)){if($o.lease_id){[void](Require-CommandFabricLease $o $Tasks)}else{[void](Require-TaskLease $o $Locks $Tasks)};$src=Join-Path $Repo (Normalize-RepoPath ([string]$o.path));if((Sha256 $src) -ne ([string]$o.expected_sha256).ToLowerInvariant()){Stop-Process $stage.Id -Force -ErrorAction SilentlyContinue;throw "OVERLAY_CHANGED_BEFORE_CUTOVER::$($o.path)"}}
}
Stop-Process $stage.Id -Force;Start-Sleep -Milliseconds 400
$PreviousDeployment=$null;$previousDeploymentPath=Join-Path $RuntimeRoot 'deployment.json';if(Test-Path $previousDeploymentPath){$PreviousDeployment=Load-Json $previousDeploymentPath}
$oldPid=Get-RaiosListenPid $Port
if($oldPid){Stop-Process $oldPid -Force -ErrorAction SilentlyContinue;for($i=0;$i-lt 40;$i++){Start-Sleep -Milliseconds 250;if(-not(Test-RaiosTcp $Port)){break}};if(Test-RaiosTcp $Port){throw 'COMMAND_CENTER_OLD_LISTENER_NOT_RELEASED'}}
if($FaultInjectCutoverFailure){[void](Invoke-Rollback 'FAULT_INJECTED_AFTER_OLD_STOP' $PreviousDeployment);throw 'FAULT_INJECTED_CUTOVER_FAILURE'}
$live=Start-Center $Port 'center';$health=Wait-Healthy $Port $live.Id
if(-not$health){Stop-Process $live.Id -Force -ErrorAction SilentlyContinue;[void](Invoke-Rollback 'COMMAND_CENTER_CUTOVER_FAILED' $PreviousDeployment);throw 'COMMAND_CENTER_CUTOVER_FAILED_ROLLED_BACK'}
$runtimePid=Get-RaiosListenPid $Port;if(-not$runtimePid){Stop-Process $live.Id -Force -ErrorAction SilentlyContinue;[void](Invoke-Rollback 'COMMAND_CENTER_LISTENER_MISSING' $PreviousDeployment);throw 'COMMAND_CENTER_LISTENER_MISSING_ROLLED_BACK'}
$deployment=[ordered]@{schema='raios.command-center-deployment.v2';canonical_head=$Head;canonical_repo=$Repo;mcp_root=$McpRoot;runtime_root=$RuntimeRoot;app_root=$App;port=$Port;pid=$runtimePid;launcher_pid=$live.Id;deployed_at=[DateTimeOffset]::UtcNow.ToString('o');auto_canonical_mutation=$false;transactional=$Transactional;head_only_recovery=[bool]$HeadOnlyRecovery;transaction_id=$TransactionId;manifest_sha256=$ManifestHash;base_source=($(if($Transactional -or $HeadOnlyRecovery){'GIT_OBJECT_DATABASE'}else{'WORKING_TREE_CLEAN_ONLY'}))}
$deployment|ConvertTo-Json -Depth 8|Set-Content(Join-Path $RuntimeRoot 'deployment.json') -Encoding UTF8
$launcher=@"
`$env:RAIOS_CANONICAL_REPO="$Repo"
`$env:RAIOS_CANONICAL_HEAD="$Head"
`$env:RAIOS_MCP_ROOT="$McpRoot"
`$env:RAIOS_COMMAND_CENTER_RUNTIME="$RuntimeRoot"
`$env:PYTHONPATH="$App"
`$ok=$false;try{`$c=[Net.Sockets.TcpClient]::new();`$p=`$c.BeginConnect("127.0.0.1",$Port,$null,$null);`$ok=`$p.AsyncWaitHandle.WaitOne(800) -and `$c.Connected;`$c.Close()}catch{}
if(-not `$ok){Start-Process "$PythonWindowless" -ArgumentList @("-m","uvicorn","raios.command_center.app:app","--app-dir","$App","--host","127.0.0.1","--port","$Port") -WorkingDirectory "$Repo" -WindowStyle Hidden -RedirectStandardOutput "$Logs\center.out.log" -RedirectStandardError "$Logs\center.err.log";for(`$i=0;`$i-lt 20;`$i++){Start-Sleep -Milliseconds 500;try{`$h=Invoke-RestMethod "http://127.0.0.1:$Port/health" -TimeoutSec 2;if(`$h.status-eq"ONLINE"){break}}catch{}}}
Start-Process "`$env:SystemRoot\explorer.exe" "http://127.0.0.1:$Port/"
"@
$launcherPath=Join-Path $RuntimeRoot 'Open-RAIOS-Command-Center.ps1';[IO.File]::WriteAllText($launcherPath,$launcher,[Text.UTF8Encoding]::new($false))
$desktop=[Environment]::GetFolderPath('Desktop');$shortcut=Join-Path $desktop 'RAIOS Command Center.lnk';$ws=New-Object -ComObject WScript.Shell;$lnk=$ws.CreateShortcut($shortcut);$lnk.TargetPath="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe";$lnk.Arguments="-NoProfile -ExecutionPolicy Bypass -File `"$RuntimeRoot\Open-RAIOS-Command-Center.ps1`"";$lnk.WorkingDirectory=$RuntimeRoot;$lnk.Save()
Write-Host 'COMMAND_CENTER_CANONICAL=true';Write-Host 'COMMAND_CENTER_STAGE_PASS=true';Write-Host 'COMMAND_CENTER_HTTP=200';Write-Host "COMMAND_CENTER_PID=$runtimePid";Write-Host "COMMAND_CENTER_LAUNCHER_PID=$($live.Id)";Write-Host "COMMAND_CENTER_HEAD=$Head";Write-Host "TRANSACTIONAL_DEPLOYMENT=$Transactional";if($Transactional){Write-Host "TRANSACTION_ID=$TransactionId";Write-Host "MANIFEST_SHA256=$ManifestHash"};Write-Host "SHORTCUT=$shortcut"
