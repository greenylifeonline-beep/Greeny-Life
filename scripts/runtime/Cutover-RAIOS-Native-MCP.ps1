param([switch]$Rollback)

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$Repo='C:\Users\Ghanam\Documents\Codex\Greeny-Life'
$Branch='ai-evolution-202608051809'
$C5Root='C:\Users\Ghanam\.raios\runtime\continuity\c5-service'
$UserLane=Join-Path $C5Root 'Invoke-RAIOS-C5-UserLane.ps1'
$UserLaneV2=Join-Path $C5Root 'Invoke-RAIOS-C5-UserLane.v2.ps1'
$UserState=Join-Path $C5Root 'user-lane-state.json'
$DcrState='C:\Users\Ghanam\.raios\runtime\remote-access\rdc-system-direct\rdc-supervisor-state.json'
$DcrSupervisor='C:\Users\Ghanam\.raios\runtime\continuity\reap_stale_rdc_sessions.py'
$Marker=Join-Path $C5Root 'DCR-NATIVE-PROVIDER.enabled'
$Ensure=Join-Path $Repo 'scripts\ai-os\raios_mcp_local_ensure.ps1'
$Patcher=Join-Path $Repo 'scripts\runtime\patch_c5_native_provider.py'
$Python=Join-Path $Repo '.venv\Scripts\python.exe'
$TokenPath=Join-Path $Repo '.ai-os\mcp\tokens.local.json'
$Stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$Evidence="C:\Users\Ghanam\.raios\runtime\evidence\C1-NATIVE-MCP-CUTOVER-$Stamp"
New-Item -ItemType Directory -Force -Path $Evidence|Out-Null

function J([string]$p){if(Test-Path $p){try{return Get-Content $p -Raw|ConvertFrom-Json}catch{return $null}};return $null}
function W([scriptblock]$q,[int]$s,[string]$n){$sw=[Diagnostics.Stopwatch]::StartNew();while($sw.Elapsed.TotalSeconds-lt$s){try{$v=&$q;if($null-ne$v-and$v-ne$false){return $v}}catch{};Start-Sleep -Milliseconds 500};throw "TIMEOUT=$n"}
function L(){ $x=@(Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 8788 -State Listen -ErrorAction SilentlyContinue);if($x.Count-eq1){return $x[0]};return $null}
function ReloadMcp(){& $Ensure -Port 8788 -Reload;if($LASTEXITCODE-ne0){throw "MCP_RELOAD_FAILED=$LASTEXITCODE"}}
function RestartLane(){
 $o=J $UserState;$op=if($o-and$o.pid){[int]$o.pid}else{0}
 if($op-gt4){Stop-Process -Id $op -Force -ErrorAction SilentlyContinue}
 return W {$u=J $UserState;if($u-and$u.schema-eq'raios.c5.user-lane.state.v2'-and[int]$u.pid-gt4-and[int]$u.pid-ne$op){$u}else{$null}} 60 'USER_LANE'
}
function Rpc([string]$token,[int]$id,[string]$method,$params){
 $h=@{Accept='application/json';'Content-Type'='application/json'}
 if($token){$h['X-RAIOS-TOKEN']=$token}
 $b=[ordered]@{jsonrpc='2.0';id=$id;method=$method;params=$params}|ConvertTo-Json -Depth 30 -Compress
 return Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8788/mcp' -Headers $h -Body $b -TimeoutSec 45
}
function RollbackNative(){
 try{ReloadMcp}catch{}
 Remove-Item $Marker -Force -ErrorAction SilentlyContinue
 try{[void](RestartLane)}catch{}
 Write-Host 'RAIOS_NATIVE_MCP_ROLLBACK=COMPLETE' -ForegroundColor Yellow
}
if($Rollback){RollbackNative;exit 0}

$activated=$false
try{
 Write-Host 'PHASE=CANONICAL_GATE' -ForegroundColor Cyan
 if((git -C $Repo branch --show-current).Trim()-ne$Branch){throw 'WRONG_BRANCH'}
 if(@(git -C $Repo worktree list --porcelain|Select-String '^worktree ').Count-ne1){throw 'WORKTREE_COUNT_NE_1'}

 Write-Host 'PHASE=SYNC_CANONICAL' -ForegroundColor Cyan
 git -C $Repo fetch origin $Branch
 if($LASTEXITCODE-ne0){throw 'FETCH_FAILED'}
 $lh=(git -C $Repo rev-parse HEAD).Trim()
 $rh=(git -C $Repo rev-parse "origin/$Branch").Trim()
 git -C $Repo merge-base --is-ancestor $lh $rh
 if($LASTEXITCODE-ne0){throw ("NON_FAST_FORWARD={0}->{1}" -f $lh,$rh)}
 $targets=@('scripts/ai-os/raios_mcp/gateway.py','scripts/ai-os/raios_mcp/server.py','scripts/ai-os/raios_mcp/desktop_commander_provider.py','scripts/ai-os/raios_mcp_local_ensure.ps1','.ai-os/mcp/POLICY.json','tests/mcp/test_mcp_health.py','scripts/runtime/patch_c5_native_provider.py')
 $dirty=@(git -C $Repo status --porcelain -- $targets)
 if($dirty.Count){throw ('TARGET_DIRTY:'+($dirty-join';'))}
 git -C $Repo merge --ff-only "origin/$Branch"
 if($LASTEXITCODE-ne0){throw 'FF_ONLY_FAILED'}
 $head=(git -C $Repo rev-parse HEAD).Trim()
 if($head-ne$rh){throw 'HEAD_MISMATCH'}

 Write-Host 'PHASE=SOURCE_VALIDATE' -ForegroundColor Cyan
 if(-not(Test-Path $Python)){throw 'VENV_PYTHON_MISSING'}
 $files=@((Join-Path $Repo 'scripts\ai-os\raios_mcp\desktop_commander_provider.py'),(Join-Path $Repo 'scripts\ai-os\raios_mcp\gateway.py'),(Join-Path $Repo 'scripts\ai-os\raios_mcp\server.py'),$Patcher)
 & $Python -m py_compile @files
 if($LASTEXITCODE-ne0){throw 'PY_COMPILE_FAILED'}
 $pol=Get-Content (Join-Path $Repo '.ai-os\mcp\POLICY.json') -Raw|ConvertFrom-Json
 if(@($pol.execution_tools)-notcontains'execute_scoped_task'){throw 'EXECUTION_TOOL_MISSING'}
 if($pol.providers.desktop_commander.hosted_remote_required-ne$false){throw 'HOSTED_REMOTE_REQUIRED'}

 Write-Host 'PHASE=C1_SCOPE' -ForegroundColor Cyan
 if(-not(Test-Path $TokenPath)){throw 'TOKENS_LOCAL_MISSING'}
 Copy-Item $TokenPath (Join-Path $Evidence 'tokens.local.before.json') -Force
 $tok=Get-Content $TokenPath -Raw|ConvertFrom-Json
 $c1=@($tok.actors|Where-Object{$_.actor_id-eq'C1'})|Select-Object -First 1
 if(-not$c1-or-not[string]$c1.token){throw 'C1_TOKEN_MISSING'}
 $sc=@($c1.scopes)
 if($sc-notcontains'execute_scoped_task'){$sc+='execute_scoped_task'}
 if($c1.PSObject.Properties['scopes']){$c1.scopes=@($sc|Select-Object -Unique)}else{$c1|Add-Member -NotePropertyName scopes -NotePropertyValue @($sc|Select-Object -Unique)}
 $tmp=$TokenPath+'.tmp';$tok|ConvertTo-Json -Depth 20|Set-Content $tmp -Encoding UTF8;Move-Item $tmp $TokenPath -Force
 $token=[string]$c1.token

 Write-Host 'PHASE=C5_NATIVE_PROVIDER_MODE' -ForegroundColor Cyan
 if(-not(Test-Path $UserLane)){throw 'USER_LANE_MISSING'}
 Copy-Item $UserLane (Join-Path $Evidence 'UserLane.before.ps1') -Force
 & $Python $Patcher --lane $UserLane --lane-v2 $UserLaneV2 --marker $Marker
 if($LASTEXITCODE-ne0){throw 'C5_PATCH_FAILED'}
 [void][scriptblock]::Create((Get-Content $UserLane -Raw))
 $activated=$true
 $u=RestartLane;$userPid=[int]$u.pid
 W {$s=J $DcrState;if(-not$s-or-not$s.supervisor_pid){return $true};$p=[int]$s.supervisor_pid;if($p-le4-or-not(Get-Process -Id $p -ErrorAction SilentlyContinue)){return $true};return $null} 60 'HOSTED_DCR_RETIRE'|Out-Null

 Write-Host 'PHASE=UNIVERSAL_MCP_RELOAD' -ForegroundColor Cyan
 ReloadMcp
 $health=W {try{$h=Invoke-RestMethod 'http://127.0.0.1:8788/health' -TimeoutSec 5;if($h.ok-and[int]$h.tool_count-eq9-and@($h.tools)-contains'execute_scoped_task'){$h}else{$null}}catch{$null}} 60 'MCP_9_TOOLS'

 Write-Host 'PHASE=LOCAL_PROVIDER_HANDSHAKE' -ForegroundColor Cyan
 $i=Rpc '' 1 'initialize' @{protocolVersion='2025-06-18';capabilities=@{};clientInfo=@{name='raios-cutover';version='1'}}
 if($i.error){throw 'INITIALIZE_FAILED'}
 $ls=Rpc '' 2 'tools/list' @{}
 $names=@($ls.result.tools|ForEach-Object{$_.name})
 if($names.Count-ne9-or$names-notcontains'execute_scoped_task'){throw 'TOOLS_LIST_FAILED'}
 $args=@{provider='desktop_commander';capability='remote';operation='__list_tools__';arguments=@{};mode='READ_ONLY';execution_intent='SCOPED';authority_scope='REMOTE_CAPABILITY_READ'}
 $p=Rpc $token 3 'tools/call' @{name='execute_scoped_task';arguments=$args}
 if($p.error-or$p.result.isError){throw ('PROVIDER_HANDSHAKE_FAILED:'+($p|ConvertTo-Json -Depth 10 -Compress))}
 $pr=([string]$p.result.content[0].text)|ConvertFrom-Json
 $disc=@($pr.result.discovered_tools)
 if(-not$disc.Count){throw 'NO_DCR_TOOLS'}

 Write-Host 'PHASE=REAL_TOOL' -ForegroundColor Cyan
 if($disc-contains'list_directory'){$op='list_directory';$oa=@{path=$Repo;depth=1}}
 elseif($disc-contains'get_file_info'){$op='get_file_info';$oa=@{path=$Repo}}
 elseif($disc-contains'read_file'){$op='read_file';$oa=@{path=(Join-Path $Repo 'README.md');offset=0;length=10}}
 elseif($disc-contains'list_processes'){$op='list_processes';$oa=@{}}
 else{throw ('NO_ALLOWED_TOOL:'+($disc-join','))}
 $args.operation=$op;$args.arguments=$oa
 $real=Rpc $token 4 'tools/call' @{name='execute_scoped_task';arguments=$args}
 if($real.error-or$real.result.isError){throw ('REAL_TOOL_FAILED:'+($real|ConvertTo-Json -Depth 10 -Compress))}

 Write-Host 'PHASE=EXACT_ONE_PROVIDER' -ForegroundColor Cyan
 $listener=L;if(-not$listener){throw 'MCP_LISTENER_COUNT'}
 $mcpPid=[int]$listener.OwningProcess;$entry=[string]$pol.providers.desktop_commander.entry
 $nodes=@(Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue|Where-Object{[string]$_.CommandLine-like('*'+$entry+'*')})
 if($nodes.Count-ne1){throw "LOCAL_DCR_COUNT=$($nodes.Count)"}
 $dcrPid=[int]$nodes[0].ProcessId
 if([int]$nodes[0].ParentProcessId-ne$mcpPid){throw 'LOCAL_DCR_PARENT_MISMATCH'}
 $hosted=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction SilentlyContinue|Where-Object{[string]$_.CommandLine-like('*'+$DcrSupervisor+'*')-and[string]$_.CommandLine-match'--supervise'})
 if($hosted.Count-ne0){throw "HOSTED_SUPERVISOR_COUNT=$($hosted.Count)"}

 $rec=[ordered]@{schema='raios.native-mcp-cutover.v1';observed_at=[DateTimeOffset]::UtcNow.ToString('o');result='PASS';canonical_head=$head;universal_mcp=@{endpoint='http://127.0.0.1:8788/mcp';pid=$mcpPid;tool_count=9;second_gateway=$false};remote_capability=@{provider='desktop_commander';transport='local_stdio';hosted_remote_required=$false;hosted_supervisor_count=0;local_provider_pid=$dcrPid;parent_mcp_pid=$mcpPid;discovered_tool_count=$disc.Count;proof_operation=$op;mutation_enabled=$false};c5=@{user_lane_pid=$userPid;authority='RAIOS-C5';marker=$Marker}}
 $rp=Join-Path $Evidence 'RAIOS-NATIVE-MCP-CUTOVER.json';$rec|ConvertTo-Json -Depth 20|Set-Content $rp -Encoding UTF8;$hash=(Get-FileHash $rp -Algorithm SHA256).Hash
 Write-Host 'RAIOS_NATIVE_MCP_CUTOVER=PASS' -ForegroundColor Green
 Write-Host "HEAD=$head";Write-Host "UNIVERSAL_MCP_PID=$mcpPid";Write-Host "LOCAL_DCR_PID=$dcrPid";Write-Host 'HOSTED_DCR_SUPERVISOR_COUNT=0';Write-Host "REAL_TOOL=$op";Write-Host "RECEIPT=$rp";Write-Host "SHA256=$hash"
}catch{
 $e=$_.Exception.GetType().Name+':'+$_.Exception.Message
 Write-Host "RAIOS_NATIVE_MCP_CUTOVER=FAIL|$e" -ForegroundColor Red
 if($activated){RollbackNative}
 $fp=Join-Path $Evidence 'FAIL.json';[ordered]@{result='FAIL';observed_at=[DateTimeOffset]::UtcNow.ToString('o');error=$e}|ConvertTo-Json|Set-Content $fp -Encoding UTF8;Write-Host "FAIL_RECEIPT=$fp"
 exit 1
}
