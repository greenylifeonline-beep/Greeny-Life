param(
    [string]$Repo = $(if ($env:RAIOS_CANONICAL_REPO) { $env:RAIOS_CANONICAL_REPO } else { (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path }),
    [switch]$InstallTask,
    [switch]$HelpersOnly
)
$ErrorActionPreference = "Stop"
# T_C5_SERVICE_REPAIR=540s is DERIVED (C8 T_DEPLOY_TOTAL_COLD≈516s + margin). NOT MEASURED.
# MEASURED C2 ValidateOnly successful path = 43.622s; exact dirty-source fail = 24.096s.
# T_C5_COGNITIVE_REPAIR=180s is DERIVED candidate.
$T_C5_SERVICE_REPAIR = 540
$T_C5_COGNITIVE_REPAIR = 180
$T_TASK_LIMIT_ISO = "PT15M"
$RAIOS_CONTINUITY_MUTEX_NAME = "Global\RAIOS-Canonical-Continuity"
function Enter-RaiosContinuityMutex([string]$Name = $RAIOS_CONTINUITY_MUTEX_NAME, [int]$TimeoutMs = 0) {
    $mutex = [Threading.Mutex]::new($false, $Name)
    $owned = $false
    $state = "FAILED"
    try {
        try {
            if ($mutex.WaitOne([Math]::Max(0, $TimeoutMs))) {
                $owned = $true
                $state = "ACQUIRED_NORMAL"
            } else {
                $state = "BUSY"
            }
        } catch [Threading.AbandonedMutexException] {
            # AbandonedMutexException means this caller now owns the mutex.
            # Do NOT ReleaseMutex then WaitOne again.
            $owned = $true
            $state = "ACQUIRED_ABANDONED"
        }
    } catch {
        $state = "FAILED"
        try { $mutex.Dispose() } catch {}
        return [pscustomobject]@{ Mutex = $null; Owned = $false; State = $state }
    }
    return [pscustomobject]@{ Mutex = $mutex; Owned = $owned; State = $state }
}
function Exit-RaiosContinuityMutex($Handle) {
    if ($null -eq $Handle) { return }
    if ($Handle.Owned -and $Handle.Mutex) {
        try { $Handle.Mutex.ReleaseMutex() } catch {}
        $Handle.Owned = $false
    }
    if ($Handle.Mutex) {
        try { $Handle.Mutex.Dispose() } catch {}
    }
}
function Test-RaiosRouterHttpReady([string]$Url = 'http://127.0.0.1:20128/v1/models', [int]$TimeoutMs = 10000) {
    # Production readiness uses the authenticated API, never the dashboard page.
    if ($Url -eq 'http://127.0.0.1:20128/v1/models') {
        $proc=$null
        try {
            $python='C:\Users\Ghanam\.raios\runtime\c5\.venv\Scripts\python.exe'
            if(-not [IO.File]::Exists($python)){return $false}
            $budget=[Math]::Min(10000,[Math]::Max(100,$TimeoutMs))
            $code=@'
import sqlite3,json,urllib.request,sys
from pathlib import Path
db=sqlite3.connect('file:'+Path(r'C:\Users\Ghanam\AppData\Roaming\9router\db\data.sqlite').as_posix()+'?mode=ro',uri=True,timeout=.5)
cols=[x[1] for x in db.execute('pragma table_info(apiKeys)')]
key=None
for row in db.execute('select * from apiKeys'):
    d=dict(zip(cols,row))
    if d.get('isActive',True) and d.get('key'):
        key=d['key'];break
db.close()
if not key:sys.exit(2)
req=urllib.request.Request('http://127.0.0.1:20128/v1/models',headers={'Authorization':'Bearer '+key,'Connection':'close'})
with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=6) as res:
    if res.status!=200:sys.exit(3)
    body=res.read(2000001)
if len(body)>2000000:sys.exit(4)
models=json.loads(body).get('data')
if not isinstance(models,list) or not any(isinstance(x,dict) and isinstance(x.get('id'),str) and x['id'] for x in models):sys.exit(5)
key=None
print('RAIOS_ROUTER_AUTH_READY')
'@
            $encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($code))
            $info=[Diagnostics.ProcessStartInfo]::new()
            $info.FileName=$python
            $info.Arguments='-c "import base64;exec(base64.b64decode('''+$encoded+'''))"'
            $info.UseShellExecute=$false;$info.CreateNoWindow=$true
            $info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true
            $proc=[Diagnostics.Process]::new();$proc.StartInfo=$info
            $clock=[Diagnostics.Stopwatch]::StartNew()
            if(-not $proc.Start()){return $false}
            $out=$proc.StandardOutput.ReadToEndAsync()
            $err=$proc.StandardError.ReadToEndAsync()
            while(-not $proc.HasExited){
                if($clock.ElapsedMilliseconds -ge $budget){try{$proc.Kill()}catch{};return $false}
                Start-Sleep -Milliseconds 50
            }
            if($proc.ExitCode -ne 0){return $false}
            # Process exit does not imply asynchronous stdout EOF has completed.
            # Share the original deadline; never extend the health probe budget.
            $remaining=[Math]::Max(0,$budget-[int]$clock.ElapsedMilliseconds)
            if(-not $out.IsCompleted -and -not $out.Wait($remaining)){return $false}
            if(-not $out.IsCompleted){return $false}
            return ($out.Result.Trim() -eq 'RAIOS_ROUTER_AUTH_READY')
        }catch{return $false}
        finally{if($proc){try{if(-not $proc.HasExited){$proc.Kill()}}catch{};try{$proc.Dispose()}catch{}}}
    }

    $request = $null
    $response = $null
    $pending = $null
    try {
        $uri = [Uri]$Url
        if ($uri.Scheme -ne 'http' -or $uri.Host -ne '127.0.0.1') { return $false }
        $budget = [Math]::Min(10000, [Math]::Max(100, $TimeoutMs))
        $request = [Net.HttpWebRequest]::Create($uri)
        $request.Method = 'GET'
        $request.Proxy = [Net.GlobalProxySelection]::GetEmptyWebProxy()
        $request.KeepAlive = $false
        $request.AllowAutoRedirect = $false
        $request.Timeout = $budget
        $request.ReadWriteTimeout = $budget
        $pending = $request.BeginGetResponse($null, $null)
        if (-not $pending.AsyncWaitHandle.WaitOne($budget)) { return $false }
        $response = $request.EndGetResponse($pending)
        # Application response only. Authenticated model execution has a separate gate.
        $code = [int]$response.StatusCode
        return [bool]($code -ge 200 -and $code -lt 300)
    } catch { return $false }
    finally {
        if ($response) { try { $response.Close() } catch {} }
        if ($request) { try { $request.Abort() } catch {} }
        if ($pending) { try { $pending.AsyncWaitHandle.Close() } catch {} }
    }
}



function Get-RaiosC5AuthorizedOverlay([string]$CanonicalRepo,[string]$CanonicalHead,[string]$AppRoot) {
 try {
  $scope='src/raios/c5_gateway/cognitive_loop.py'
  $sha=[Security.Cryptography.SHA256]::Create()
  try{$key=([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($scope))).Replace('-','').ToLowerInvariant()).Substring(0,24)}finally{$sha.Dispose()}
  $leases=Join-Path $CanonicalRepo '.ai-os\state\command-fabric\leases'
  $cursor=Get-Content -LiteralPath (Join-Path $leases ('_current\'+$key+'.json')) -Raw|ConvertFrom-Json
  if(-not $cursor.lease_id){return $null}
  if([string]$cursor.lease_id -notmatch '^L-[0-9]+-[a-f0-9]+$'){return $null}
  $lease=Get-Content -LiteralPath (Join-Path $leases ($cursor.lease_id+'.json')) -Raw|ConvertFrom-Json
  if($lease.scope -ne $scope -or $lease.owner -ne 'RAIOS_SYSTEM' -or $lease.lease_holder -ne 'C1' -or $lease.state -ne 'ACTIVE' -or $lease.head -ne $CanonicalHead){return $null}
  if([DateTimeOffset]::Parse([string]$lease.expires_at) -le [DateTimeOffset]::UtcNow){return $null}
  $tasksPath=Join-Path $CanonicalRepo '.ai-os\state\TASKS.json'
  if((Get-Item -LiteralPath $tasksPath).Length -gt 4194304){return $null}
  $doc=Get-Content -LiteralPath $tasksPath -Raw|ConvertFrom-Json
  $task=@($doc.tasks|Where-Object{$_.id -eq $lease.task_id -and $_.authorized_by -eq 'C1' -and $_.status -in @('READY','IN_PROGRESS')})
  if($task.Count -ne 1 -or @($task[0].scope) -notcontains $scope){return $null}
  $request=@($task[0].runtime_source_overlays|Where-Object{$_.path -eq $scope -and $_.canonical_head -eq $CanonicalHead})
  if($request.Count -ne 1 -or [string]$request[0].sha256 -notmatch '^[a-f0-9]{64}$'){return $null}
  $source=Join-Path $CanonicalRepo $scope
  if((Get-Item -LiteralPath $source).Length -gt 1048576){return $null}
  $sourceHash=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
  if($sourceHash -ne $request[0].sha256){return $null}
  $deployed=Join-Path $AppRoot 'raios\c5_gateway\cognitive_loop.py'
  $deployedMatches=[bool]((Test-Path -LiteralPath $deployed) -and (Get-FileHash -LiteralPath $deployed -Algorithm SHA256).Hash.ToLowerInvariant() -eq $sourceHash)
  $manifestPath=Join-Path (Split-Path -Parent $AppRoot) 'deployment.json'
  if(Test-Path -LiteralPath $manifestPath){$manifest=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json;if(@($manifest.leased_overlay_files|Where-Object{$_ -ne $scope}).Count -gt 0){return $null}}
  if($deployedMatches -and $manifest -and @($manifest.leased_overlay_files) -contains $scope){return $null}
  return $scope
 }catch{return $null}
}

function Test-RaiosC5RecoveryGatewayReady($Health,[string]$ExpectedHead) {
 # Recovery admission is separate from deployment certification; final gates stay strict.
 return [bool]($Health -and $ExpectedHead -and
  [string]$Health.system_identity -eq 'RAIOS/C5' -and
  [string]$Health.canonical_head -eq $ExpectedHead -and
  [string]$Health.runtime_source -eq 'CANONICAL_DEPLOYMENT' -and
  $Health.gateway -eq $true -and $Health.model_fabric -eq $true)
}

function Get-RaiosRecoveryBudget([int]$RequestedSeconds,[int]$RemainingSeconds,$State,[DateTimeOffset]$Now=[DateTimeOffset]::UtcNow) {
 $seconds=[Math]::Min([Math]::Max(0,$RequestedSeconds),[Math]::Max(0,$RemainingSeconds-60))
 $reason='READY'
 if($seconds -le 0){$reason='CYCLE_BUDGET_EXHAUSTED'}
 if($State -and $State.next_attempt_at){
  try{if([DateTimeOffset]::Parse([string]$State.next_attempt_at) -gt $Now){$seconds=0;$reason='BACKOFF'}}catch{$seconds=0;$reason='INVALID_RECOVERY_STATE'}
 }
 return [pscustomobject]@{seconds=$seconds;allowed=($seconds -gt 0);reason=$reason}
}
function Test-RaiosRecoveryGenerationChanged($State,[string]$SourceHash) {
 if($SourceHash -notmatch '^[a-f0-9]{64}$'){throw 'RECOVERY_SOURCE_HASH_INVALID'}
 return [bool]($State -and [string]$State.command_sha256 -ne $SourceHash)
}

function Get-RaiosRecoveryDelay([int]$Failures) {
 return [int][Math]::Min(900,30*[Math]::Pow(2,[Math]::Min(5,[Math]::Max(0,$Failures-1))))
}
function Set-RaiosNatsRuntimePriority {
 $task=Get-ScheduledTask -TaskName 'RAIOS-NATS-Local' -ErrorAction Stop
 $changed=$false
 if([int]$task.Settings.Priority -gt 6){
  $task.Settings.Priority=6
  Set-ScheduledTask -InputObject $task -ErrorAction Stop | Out-Null
  $changed=$true
 }
 $owned=@(Get-Process -Name 'nats-server' -ErrorAction SilentlyContinue | Where-Object {$_.Path -eq 'C:\ProgramData\RAIOS\transport\nats\nats-server.exe'})
 if($owned.Count -gt 1){throw 'DUPLICATE_OWNED_NATS_PROCESSES'}
 foreach($p in $owned){if([string]$p.PriorityClass -in @('BelowNormal','Idle')){$p.PriorityClass='Normal';$changed=$true}}
 return $changed
}

function Test-RaiosNatsIdentity([int]$Port=4222) {
 $client=$null
 try{
  $client=[Net.Sockets.TcpClient]::new()
  $pending=$client.BeginConnect('127.0.0.1',$Port,$null,$null)
  if(-not $pending.AsyncWaitHandle.WaitOne(800)){return $false}
  $client.EndConnect($pending);$stream=$client.GetStream();$stream.ReadTimeout=800
  $reader=[IO.StreamReader]::new($stream);$line=$reader.ReadLine()
  if(-not $line -or -not $line.StartsWith('INFO ')){return $false}
  $info=$line.Substring(5)|ConvertFrom-Json
  return [bool]($info.server_id -and $info.version -and $info.port)
 }catch{return $false}finally{if($client){$client.Close()}}
}


function Get-RaiosMaintenanceContext([string]$CanonicalRepo) {
 $proc=$null
 try{
  $python=Join-Path $StableUserProfile '.raios\runtime\c5\.venv\Scripts\python.exe'
  $si=[Diagnostics.ProcessStartInfo]::new();$si.FileName=$python
  $si.Arguments='-c "import base64;exec(base64.b64decode(''CmltcG9ydCBwYXRobGliLHN5cyxqc29uLGhhc2hsaWIsY29uY3VycmVudC5mdXR1cmVzLHVybGxpYi5yZXF1ZXN0CnJvb3Q9cGF0aGxpYi5QYXRoKHN5cy5hcmd2WzFdKTtzeXMucGF0aC5pbnNlcnQoMCxzdHIocm9vdC8nc3JjJykpCmZyb20gcmFpb3MuY29tbWFuZF9jZW50ZXIuZW5naW5lX3BsYW5lIGltcG9ydCBzbmFwc2hvdApwbGFuZT1zbmFwc2hvdChyb290KQpyb3dzPVtdCmZvciByb3cgaW4gcGxhbmUuZ2V0KCdlbmdpbmVzJyxbXSk6CiBoZWFsdGhfc291cmNlPXN0cihyb3cuZ2V0KCdoZWFsdGhfc291cmNlJykgb3IgJ05PTkUnKQogYWN0dWFsPWhlYWx0aF9zb3VyY2Ugbm90IGluIFsnTk9ORScsJ1BBVEhfRVhJU1RTJywnSU5WRU5UT1JZJ10gYW5kIHJvdy5nZXQoJ2hlYWx0aHknKSBpcyBUcnVlCiByb3dzLmFwcGVuZCh7azpyb3cuZ2V0KGspIGZvciBrIGluIFsnaWQnLCdyb2xlJywnYWN0aXZhdGlvbl9tb2RlJywnc3RhdGUnLCdoZWFsdGhfc291cmNlJywnY2Fub25pY2FsX3BhdGgnLCdlbnRyeXBvaW50JywnZGVwZW5kZW5jaWVzJywnbGFzdF9zdWNjZXNzJywnZGVncmFkZWRfcmVhc29uJ119KQogcm93c1stMV0udXBkYXRlKHN0YXRlPXJvdy5nZXQoJ1NUQVRFJywnVU5LTk9XTicpLGV4ZWN1dGlvbl9wcm92ZW49RmFsc2UsaGlzdG9yaWNhbF9leGVjdXRpb25fZXZpZGVuY2U9Ym9vbChhY3R1YWwgYW5kIHJvdy5nZXQoJ2xhc3Rfc3VjY2VzcycpKSxmcmVzaG5lc3M9cm93LmdldCgnRlJFU0hORVNTJywnVU5LTk9XTicpLGZpbGVfZXhpc3RlbmNlX25lX2V4ZWN1dGlvbj1UcnVlKQpkZWYgZmV0Y2goaXRlbSk6CiBuYW1lLHBhdGg9aXRlbQogdHJ5OgogIHJlcT11cmxsaWIucmVxdWVzdC5SZXF1ZXN0KCdodHRwOi8vMTI3LjAuMC4xOjg3NzAnK3BhdGgpCiAgd2l0aCB1cmxsaWIucmVxdWVzdC5idWlsZF9vcGVuZXIodXJsbGliLnJlcXVlc3QuUHJveHlIYW5kbGVyKHt9KSkub3BlbihyZXEsdGltZW91dD0yKSBhcyByZXNwb25zZToKICAgZGF0YT1yZXNwb25zZS5yZWFkKDUyNDI4OSkKICBpZiBsZW4oZGF0YSk+NTI0Mjg4OnJhaXNlIFZhbHVlRXJyb3IoJ1JFU1BPTlNFX1RPT19MQVJHRScpCiAgb2JqPWpzb24ubG9hZHMoZGF0YSkKICBpZiBuYW1lPT0ncm91dGluZyc6CiAgIHJldHVybiBuYW1lLHsnc3RhdGUnOidPQlNFUlZFRCcsJ2NhcGFiaWxpdHlfY291bnQnOmxlbihvYmouZ2V0KCdjYXBhYmlsaXRpZXMnLFtdKSksJ3Byb3ZpZGVycyc6b2JqLmdldCgncHJvdmlkZXJzX2RlY2xhcmVkJyxbXSksJ2F1dGhvcml0eV9jaGFpbic6b2JqLmdldCgnY2hhaW4nLFtdKSwncm91dGVyX2lkcyc6W3guZ2V0KCdpZCcpIGZvciB4IGluIG9iai5nZXQoJ3JvdXRlcnMnLFtdKV19CiAga2V5cz17J3Byb3ZpZGVycyc6J3Byb3ZpZGVycycsJ2ZhY3Rvcmllcyc6J2ZhY3RvcmllcycsJ3Jlc291cmNlcyc6J3Jlc291cmNlcyd9CiAgc2VsZWN0ZWQ9b2JqLmdldChrZXlzLmdldChuYW1lLCcnKSx7fSkKICBpZGVudGlmaWVycz1saXN0KHNlbGVjdGVkKSBpZiBpc2luc3RhbmNlKHNlbGVjdGVkLGRpY3QpIGVsc2UgW3guZ2V0KCdpZCcpIG9yIHguZ2V0KCduYW1lJykgZm9yIHggaW4gc2VsZWN0ZWQgaWYgaXNpbnN0YW5jZSh4LGRpY3QpXSBpZiBpc2luc3RhbmNlKHNlbGVjdGVkLGxpc3QpIGVsc2UgW10KICByZXR1cm4gbmFtZSx7J3N0YXRlJzonT0JTRVJWRURfUFJPSkVDVElPTicsJ2lkcyc6aWRlbnRpZmllcnMsJ3Byb2plY3Rpb25fbmVfZXhlY3V0aW9uJzpUcnVlfQogZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOnJldHVybiBuYW1lLHsnc3RhdGUnOidVTktOT1dOJywnZmFpbHVyZV90eXBlJzp0eXBlKGUpLl9fbmFtZV9ffQp3aXRoIGNvbmN1cnJlbnQuZnV0dXJlcy5UaHJlYWRQb29sRXhlY3V0b3IobWF4X3dvcmtlcnM9NCkgYXMgcG9vbDoKIHByb2plY3Rpb25zPWRpY3QocG9vbC5tYXAoZmV0Y2gsWygncm91dGluZycsJy9hcGkvY2FwYWJpbGl0eS1yb3V0aW5nJyksKCdwcm92aWRlcnMnLCcvYXBpL3Byb3ZpZGVycycpLCgnZmFjdG9yaWVzJywnL2FwaS9mYWN0b3JpZXMnKSwoJ3Jlc291cmNlcycsJy9hcGkvcmVzb3VyY2VzJyldKSkKCmlmIHByb2plY3Rpb25zWydyb3V0aW5nJ10uZ2V0KCdzdGF0ZScpPT0nVU5LTk9XTic6CiB0cnk6CiAgZnJvbSByYWlvcy5jb21tYW5kX2NlbnRlci5zeXN0ZW1fc3VyZmFjZSBpbXBvcnQgY2FwYWJpbGl0eV9yb3V0aW5nX3Byb2plY3Rpb24KICBsb2NhbD1jYXBhYmlsaXR5X3JvdXRpbmdfcHJvamVjdGlvbihyb290KQogIHByb2plY3Rpb25zWydyb3V0aW5nJ109eydzdGF0ZSc6J0NBTk9OSUNBTF9TT1VSQ0VfRkFMTEJBQ0tfTk9UX0xJVkUnLCdjYXBhYmlsaXR5X2NvdW50JzpsZW4obG9jYWwuZ2V0KCdjYXBhYmlsaXRpZXMnLFtdKSksJ2F1dGhvcml0eV9jaGFpbic6bG9jYWwuZ2V0KCdjaGFpbicsW10pLCdyb3V0ZXJfaWRzJzpbeC5nZXQoJ2lkJykgZm9yIHggaW4gbG9jYWwuZ2V0KCdyb3V0ZXJzJyxbXSldLCdsaXZlX2ZhaWx1cmVfdHlwZSc6cHJvamVjdGlvbnNbJ3JvdXRpbmcnXS5nZXQoJ2ZhaWx1cmVfdHlwZScpLCdwcm9qZWN0aW9uX25lX2V4ZWN1dGlvbic6VHJ1ZX0KIGV4Y2VwdCBFeGNlcHRpb24gYXMgZXhjOnByb2plY3Rpb25zWydyb3V0aW5nJ11bJ3NvdXJjZV9mYWlsdXJlX3R5cGUnXT10eXBlKGV4YykuX19uYW1lX18Kb3V0PXsnc2NoZW1hJzoncmFpb3MubWFpbnRlbmFuY2UtY29udGV4dC52MScsJ3NvdXJjZSc6J0NBTk9OSUNBTF9FTkdJTkVfUExBTkVfQU5EX0VYSVNUSU5HX0NPTU1BTkRfQ0VOVEVSJywnZW5naW5lcyc6cm93cywnZW5naW5lX2NvdW50JzpsZW4ocm93cyksJ2ludmVudG9yeV9oZWFkJzpwbGFuZS5nZXQoJ2ludmVudG9yeV9oZWFkJyksJ2ludmVudG9yeV9hbGlnbm1lbnQnOnBsYW5lLmdldCgnY2Fub25pY2FsX2hlYWRfYWxpZ25tZW50JyksJ3Byb2plY3Rpb25zJzpwcm9qZWN0aW9ucywncm91dGluZ19hdXRob3JpdHknOidSQUlPU19NT0RFTF9ST1VURVInLCdleGVjdXRpb25fYXV0aG9yaXR5JzonRVhJU1RJTkdfVEFTS19DT01NQU5EX0ZBQlJJQycsJ3Byb3ZpZGVyX25lX2NvcmUnOlRydWUsJ3NlY29uZF9yZWdpc3RyeSc6RmFsc2UsJ3NlY29uZF9zY2hlZHVsZXInOkZhbHNlLCdhdXRvbWF0aWNfaW52ZW50b3J5X2V4ZWN1dGlvbic6RmFsc2V9Cm91dFsnY29udGV4dF9zaGEyNTYnXT1oYXNobGliLnNoYTI1Nihqc29uLmR1bXBzKG91dCxzb3J0X2tleXM9VHJ1ZSxzZXBhcmF0b3JzPSgnLCcsJzonKSkuZW5jb2RlKCkpLmhleGRpZ2VzdCgpCnByaW50KGpzb24uZHVtcHMob3V0LHNlcGFyYXRvcnM9KCcsJywnOicpKSkK''))" "'+$CanonicalRepo+'"'
  $si.UseShellExecute=$false;$si.CreateNoWindow=$true;$si.RedirectStandardOutput=$true;$si.RedirectStandardError=$true
  $proc=[Diagnostics.Process]::new();$proc.StartInfo=$si
  if(-not $proc.Start()){throw 'CONTEXT_START_FAILED'}
  $out=$proc.StandardOutput.ReadToEndAsync();$err=$proc.StandardError.ReadToEndAsync();$clock=[Diagnostics.Stopwatch]::StartNew()
  while(-not $proc.HasExited -and $clock.ElapsedMilliseconds -lt 20000){Start-Sleep -Milliseconds 50}
  if(-not $proc.HasExited){$proc.Kill();throw 'CONTEXT_TIMEOUT'}
  $remaining=[Math]::Max(0,20000-[int]$clock.ElapsedMilliseconds)
  if(-not $out.IsCompleted -and -not $out.Wait($remaining)){throw 'CONTEXT_STDOUT_TIMEOUT'}
  if($proc.ExitCode -ne 0 -or -not $out.IsCompleted -or $out.Result.Length -gt 524288){throw 'CONTEXT_FAILED'}
  $value=$out.Result|ConvertFrom-Json
  if($value.schema -ne 'raios.maintenance-context.v1' -or $value.engine_count -lt 6 -or $value.second_registry -ne $false){throw 'CONTEXT_CONTRACT_FAILED'}
  return $value
 }catch{return [pscustomobject]@{schema='raios.maintenance-context.v1';state='UNKNOWN';failure_type=$_.Exception.GetType().Name;source='CANONICAL_ENGINE_PLANE';execution_proven=$false}}
 finally{if($proc){$proc.Dispose()}}
}

function Write-RaiosBoundedLog([string]$Path,[string]$Line,[int]$MaxBytes=2097152,[int]$Archives=3) {
 if($MaxBytes -lt 1024 -or $Archives -lt 1 -or $Archives -gt 5){throw 'LOG_BOUND_INVALID'}
 $encoding=[Text.UTF8Encoding]::new($false)
 if($encoding.GetByteCount($Line) -gt 4096){$Line=$Line.Substring(0,[Math]::Min(1024,$Line.Length))}
 $limit=[Math]::Min(4096,$MaxBytes)
 while($encoding.GetByteCount($Line+[Environment]::NewLine) -gt $limit -and $Line.Length -gt 0){
  $Line=$Line.Substring(0,[Math]::Max(0,[int]($Line.Length*0.75)))
 }
 $payload=$Line+[Environment]::NewLine
 $sha=[Security.Cryptography.SHA256]::Create()
 try{$key=-join($sha.ComputeHash($encoding.GetBytes([IO.Path]::GetFullPath($Path)))|ForEach-Object{$_.ToString('x2')})}finally{$sha.Dispose()}
 $guard=[Threading.Mutex]::new($false,'Local\RAIOS-Bounded-Log-'+$key.Substring(0,24));$held=$false
 try {
  try{$held=$guard.WaitOne(250)}catch [Threading.AbandonedMutexException]{$held=$true}
  if(-not $held){return}
  if([IO.File]::Exists($Path) -and ((Get-Item -LiteralPath $Path).Length+$encoding.GetByteCount($payload) -gt $MaxBytes)){
   for($i=$Archives;$i -ge 1;$i--){
    $target=$Path+'.'+$i
    $source=$(if($i -eq 1){$Path}else{$Path+'.'+($i-1)})
    if([IO.File]::Exists($source)){
     if([IO.File]::Exists($target)){[IO.File]::Delete($target)}
     [IO.File]::Move($source,$target)
    }
   }
  }
  [IO.File]::AppendAllText($Path,$payload,$encoding)
 }finally{if($held){try{$guard.ReleaseMutex()}catch{}};$guard.Dispose()}
}

function Invoke-RaiosResumeMonitor([string]$CanonicalRepo,[string]$CommandCenterRuntime,[string]$MonitorPath) {
 try {
  $python=Join-Path $HOME '.raios\runtime\c5\.venv\Scripts\python.exe'
  if(-not(Test-Path -LiteralPath $python)){return [pscustomobject]@{ok=$false;code='RESUME_MONITOR_PYTHON_MISSING'}}
  $saved=$env:PYTHONPATH
  try {
   $env:PYTHONPATH=Join-Path $CanonicalRepo 'src'
   $raw=& $python -c "from raios.orchestration.continuity_resume import _cli; raise SystemExit(_cli())" --repo $CanonicalRepo --refresh-live --runtime-root $CommandCenterRuntime --monitor-path $MonitorPath 2>$null
   if($LASTEXITCODE -ne 0){return [pscustomobject]@{ok=$false;code='RESUME_MONITOR_REJECTED'}}
   return (($raw -join '')|ConvertFrom-Json)
  } finally {$env:PYTHONPATH=$saved}
 }catch{return [pscustomobject]@{ok=$false;code='RESUME_MONITOR_EXCEPTION'}}
}
$script:RaiosHelpersOnly = [bool]($HelpersOnly -or ($env:RAIOS_C5_HELPERS_ONLY -eq '1'))
if (-not $script:RaiosHelpersOnly) {
$StableUserProfile = [Environment]::GetFolderPath("UserProfile")
if ([string]::IsNullOrWhiteSpace($StableUserProfile)) { $StableUserProfile = $env:USERPROFILE }
if ([string]::IsNullOrWhiteSpace($StableUserProfile)) { throw "RAIOS_USER_PROFILE_UNAVAILABLE" }
$env:RAIOS_CANONICAL_REPO = $Repo
$LegacyTaskName = "RAIOS-C5-Permanent"
$ControlAuthority = "RAIOS-C5-SCM"
$RecoveryRole = "RECOVERY_CONTROLLER"
$RuntimeRoot = Join-Path $StableUserProfile ".raios\runtime\continuity"
$CommandCenterRuntime = Join-Path $StableUserProfile ".raios\runtime\command-center"
$ResumeMonitorPath = Join-Path $RuntimeRoot "resume-monitor.json"
$StatusPath = Join-Path $RuntimeRoot "status.json"
$NetworkStatePath = Join-Path $RuntimeRoot "network-resume.json"
$TransportContinuityPath = Join-Path $RuntimeRoot "rdc-transport-continuity.json"
$ReconnectCheckpointPath = Join-Path $RuntimeRoot "checkpoints\reconnect\CURRENT.json"
$NetworkResumeCooldownSeconds = 300
$NetworkRequiredSuccesses = 2

# Windows SCM is the only continuity/boot authority.  The legacy
# -InstallTask switch is retained only as a migration-safe compatibility
# surface; it never creates or re-enables a Scheduled Task.
if ($InstallTask) {
    Write-Host "RAIOS_SCHEDULER_AUTHORITY_RETIRED=true"
    Write-Host ("RAIOS_CONTROL_AUTHORITY=" + $ControlAuthority)
    Write-Host ("LEGACY_TASK=" + $LegacyTaskName)
    exit 0
}
[IO.Directory]::CreateDirectory($RuntimeRoot) | Out-Null
$TracePath = Join-Path $RuntimeRoot "phase.log"
$RunId = [guid]::NewGuid().ToString("N")
$TraceEncoding = New-Object Text.UTF8Encoding($false)
function Mark-Phase([string]$Name) {
    try {
        $line = ([DateTimeOffset]::UtcNow.ToString("o")) + "|RUN=" + $RunId + "|PID=" + $PID + "|" + $Name + [Environment]::NewLine
        Write-RaiosBoundedLog -Path $TracePath -Line $line.TrimEnd()
    } catch {}
}
Mark-Phase "RUN_START"

$mutexHandle = Enter-RaiosContinuityMutex -Name $RAIOS_CONTINUITY_MUTEX_NAME -TimeoutMs 0
if ($mutexHandle.State -eq "BUSY") {
    Mark-Phase "MUTEX_BUSY"
    Write-Host "RAIOS_CONTINUITY_ALREADY_RUNNING"
    Exit-RaiosContinuityMutex $mutexHandle
    Mark-Phase "SCRIPT_EXIT"
    exit 0
}
if ($mutexHandle.State -eq "FAILED" -or -not $mutexHandle.Owned) {
    Mark-Phase "MUTEX_FAILED"
    Exit-RaiosContinuityMutex $mutexHandle
    Mark-Phase "SCRIPT_EXIT"
    exit 1
}
if ($mutexHandle.State -eq "ACQUIRED_ABANDONED") { Mark-Phase "MUTEX_ABANDONED_RECOVERED" }
Mark-Phase "MUTEX_ACQUIRED"
$scriptExitEmitted = $false
$resumeMonitorBefore = Invoke-RaiosResumeMonitor -CanonicalRepo $Repo -CommandCenterRuntime $CommandCenterRuntime -MonitorPath $ResumeMonitorPath
if($resumeMonitorBefore.ok){Mark-Phase "RESUME_MONITOR_PRE_PASS"}else{Mark-Phase ("RESUME_MONITOR_PRE_"+[string]$resumeMonitorBefore.code)}
try {
    # Hermes provider pulse is owned by the C5 User Lane. Continuity recovery must never
    # dispatch a duplicate provider tick or block channel recovery on an optional provider.
    Mark-Phase "HERMES_TICK_OWNED_BY_C5_USER_LANE"
    function Get-JsonHealth([string]$Url,[int]$Timeout=4) {
        $req = $null
        $resp = $null
        try {
            $timeoutMs = [Math]::Max(1,$Timeout) * 1000
            $req = [System.Net.HttpWebRequest]::Create($Url)
            $req.Method = "GET"
            $req.Timeout = $timeoutMs
            $req.ReadWriteTimeout = $timeoutMs
            $req.KeepAlive = $false
            $req.Proxy = [System.Net.GlobalProxySelection]::GetEmptyWebProxy()
            $req.ServicePoint.Expect100Continue = $false
            $ar = $req.BeginGetResponse($null, $null)
            if (-not $ar.AsyncWaitHandle.WaitOne($timeoutMs + 1500)) {
                try { $req.Abort() } catch {}
                return $null
            }
            $resp = $req.EndGetResponse($ar)
            $sr = New-Object IO.StreamReader($resp.GetResponseStream())
            try {
                $payload = $sr.ReadToEnd()
                if ([string]::IsNullOrWhiteSpace($payload)) { return $null }
                return ($payload | ConvertFrom-Json)
            } finally { $sr.Close() }
        } catch { return $null }
        finally { if ($resp) { try { $resp.Close() } catch {} } }
    }
    function Test-Tcp([int]$Port) {
        try {
            $client = [Net.Sockets.TcpClient]::new()
            $pending = $client.BeginConnect("127.0.0.1",$Port,$null,$null)
            $ok = $pending.AsyncWaitHandle.WaitOne(800) -and $client.Connected
            $client.Close()
            return $ok
        } catch { return $false }
    }
    function Test-Internet {
        try {
            $client = [Net.Sockets.TcpClient]::new()
            $pending = $client.BeginConnect("1.1.1.1",443,$null,$null)
            $ok = $pending.AsyncWaitHandle.WaitOne(1500) -and $client.Connected
            $client.Close()
            return $ok
        } catch { return $false }
    }
    function Read-NetworkState {
        try { return Get-Content -LiteralPath $NetworkStatePath -Raw | ConvertFrom-Json }
        catch { return [pscustomobject]@{ online = $false; success_streak = 0; last_resume_at = $null; last_remote_resume_proof_hash = $null } }
    }
    function Read-TransportContinuity {
        try { return Get-Content -LiteralPath $TransportContinuityPath -Raw | ConvertFrom-Json }
        catch {
            return [pscustomobject]@{
                transport_online = $false
                transport_execution_allowed = $false
                reconciliation_required = $true
                continuation_allowed = $true
                mutation_allowed = $false
                event = "MISSING_TRANSPORT_CONTINUITY_STATE"
                checkpoint_proof_hash = $null
            }
        }
    }
    function Write-JsonFileAtomic([string]$Path,[hashtable]$Value) {
        $Value["generated_at"] = [DateTimeOffset]::UtcNow.ToString("o")
        $tmp = $Path + ".tmp-" + [guid]::NewGuid().ToString("N")
        $utf8 = [Text.UTF8Encoding]::new($false)
        try {
            $json = $Value | ConvertTo-Json -Depth 12
            $json | Out-File -LiteralPath $tmp -Encoding utf8
            [void](ConvertFrom-Json (Get-Content -LiteralPath $tmp -Raw))
            for ($i=0; $i -lt 5; $i++) {
                try {
                    if (Test-Path -LiteralPath $Path) {
                        $backup = $Path + ".bak-" + [guid]::NewGuid().ToString("N")
                        try {
                            [IO.File]::Replace($tmp,$Path,$backup,$true)
                        } finally {
                            if ([IO.File]::Exists($backup)) { [IO.File]::Delete($backup) }
                        }
                    } else {
                        Move-Item -LiteralPath $tmp -Destination $Path
                    }
                    return
                } catch [IO.IOException] {
                    if ($i -eq 4) { throw }
                    Start-Sleep -Milliseconds (25 * ($i + 1))
                } catch [UnauthorizedAccessException] {
                    if ($i -eq 4) { throw }
                    Start-Sleep -Milliseconds (25 * ($i + 1))
                }
            }
        } finally {
            if (Test-Path -LiteralPath $tmp) { try { Remove-Item -LiteralPath $tmp -Force } catch {} }
        }
    }
    $script:recoveryCycleClock=[Diagnostics.Stopwatch]::StartNew()
    $script:recoveryCycleBudgetSeconds=600
    $script:recoveryAttempts=@{}
    function Invoke-BoundedRecovery([string]$Name,[string]$ScriptPath,[string[]]$Arguments,[int]$TimeoutSeconds=90) {
        $retryPath=Join-Path $RuntimeRoot ($Name.ToLowerInvariant()+'.retry.json')
        $retry=$null
        try{$retry=Get-Content -LiteralPath $retryPath -Raw|ConvertFrom-Json}catch{}
        $commandHash=(Get-FileHash -LiteralPath $ScriptPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if(Test-RaiosRecoveryGenerationChanged $retry $commandHash){
            Mark-Phase ($Name+'_SOURCE_VERSION_CHANGED')
            $retry=$null
        }
        $remaining=$script:recoveryCycleBudgetSeconds-[int]$script:recoveryCycleClock.Elapsed.TotalSeconds
        $budget=Get-RaiosRecoveryBudget $TimeoutSeconds $remaining $retry
        if(-not $budget.allowed){
            Mark-Phase ($Name+'_'+$budget.reason)
            return [pscustomobject]@{ok=$false;timed_out=$false;exit_code=$null;pid=$null;error=$budget.reason}
        }
        $TimeoutSeconds=$budget.seconds
        $failures=1
        if($retry -and $retry.failures){$failures=[Math]::Min(16,[int]$retry.failures+1)}
        # Persist before spawn, including interruption. Reset only after application health.
        Write-JsonFileAtomic $retryPath @{
            failures=$failures;next_attempt_at=[DateTimeOffset]::UtcNow.AddSeconds((Get-RaiosRecoveryDelay $failures)+$TimeoutSeconds).ToString('o')
            authority='RAIOS-C5';state='ATTEMPTING';canonical_head=$Head;command_sha256=$commandHash
        }
        $script:recoveryAttempts[$Name]=$retryPath
        $outPath = Join-Path $RuntimeRoot ($Name.ToLowerInvariant() + ".out.log")
        $errPath = Join-Path $RuntimeRoot ($Name.ToLowerInvariant() + ".err.log")
        $ps = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
        $proc = $null
        $outputRead=$null;$errorRead=$null
        try {
            $argv = @("-NoLogo","-NoProfile","-NonInteractive","-ExecutionPolicy","Bypass","-File",$ScriptPath) + @($Arguments)
            Mark-Phase ($Name + "_CHILD_START")
            foreach($item in $argv){if($item -match '["\r\n]'){throw 'RECOVERY_ARGUMENT_INVALID'}}
            $startInfo=[Diagnostics.ProcessStartInfo]::new();$startInfo.FileName=$ps
            $startInfo.Arguments=(($argv|ForEach-Object{'"'+$_+'"'}) -join ' ')
            $startInfo.UseShellExecute=$false;$startInfo.CreateNoWindow=$true
            $startInfo.RedirectStandardOutput=$true;$startInfo.RedirectStandardError=$true
            $proc=[Diagnostics.Process]::new();$proc.StartInfo=$startInfo
            if(-not $proc.Start()){throw 'RECOVERY_START_FAILED'}
            $outputRead=$proc.StandardOutput.ReadToEndAsync();$errorRead=$proc.StandardError.ReadToEndAsync()
            # Pin the native handle before exit. Start-Process otherwise loses ExitCode
            # when its asynchronously redirected child finishes before handle caching.
            $nativeHandle=$proc.Handle
            # Poll HasExited. WaitForExit(ms) with redirected I/O can ignore the timeout and hold the continuity mutex.
            $deadline = [DateTimeOffset]::UtcNow.AddSeconds([Math]::Max(1,$TimeoutSeconds))
            while (-not $proc.HasExited) {
                if ([DateTimeOffset]::UtcNow -ge $deadline) { break }
                Start-Sleep -Milliseconds 250
            }
            $completed = [bool]$proc.HasExited
            if (-not $completed) {
                Mark-Phase ($Name + "_TIMEOUT")
                try {
                    $tk = Join-Path $env:SystemRoot "System32\taskkill.exe"
                    # Cognitive recovery launches persistent, separately health-gated daemons.
                    # A timed-out transient repair parent must not kill those services.
                    $killArguments=@('/PID',[string]$proc.Id,'/F')
                    if($Name -ne 'C5_COGNITIVE_REPAIR'){$killArguments+=@('/T')}
                    $killer = Start-Process -FilePath $tk -ArgumentList $killArguments -WindowStyle Hidden -PassThru
                    $killDeadline = [DateTimeOffset]::UtcNow.AddSeconds(8)
                    while ($killer -and -not $killer.HasExited) {
                        if ([DateTimeOffset]::UtcNow -ge $killDeadline) {
                            try { Stop-Process -Id $killer.Id -Force -ErrorAction SilentlyContinue } catch {}
                            break
                        }
                        Start-Sleep -Milliseconds 200
                    }
                } catch {}
                return [pscustomobject]@{ ok=$false; timed_out=$true; exit_code=$null; pid=$proc.Id; error="TIMEOUT" }
            }
            $ok = ($proc.ExitCode -eq 0)
            Mark-Phase ($Name + $(if($ok){"_CHILD_OK"}else{"_CHILD_FAILED"}))
            return [pscustomobject]@{ ok=$ok; timed_out=$false; exit_code=$proc.ExitCode; pid=$proc.Id; error=$null }
        } catch {
            $msg = ([string]$_.Exception.Message -replace '[\r\n]+',' ')
            if ($msg.Length -gt 240) { $msg = $msg.Substring(0,240) }
            Mark-Phase ($Name + "_CHILD_EXCEPTION")
            return [pscustomobject]@{ ok=$false; timed_out=$false; exit_code=$null; pid=$(if($proc){$proc.Id}else{$null}); error=$msg }
        }
        finally {
            if($proc){
                foreach($capture in @(@($outputRead,$outPath),@($errorRead,$errPath))){
                    try{
                        $text='STREAM_INCOMPLETE_USE_CANONICAL_CHILD_RECEIPT'
                        if($capture[0] -and $capture[0].Status -eq 'RanToCompletion'){$text=$capture[0].Result;if($text.Length -gt 1048576){$text=$text.Substring(0,1048576)+' OUTPUT_TRUNCATED'}}
                        [IO.File]::WriteAllText($capture[1],$text,[Text.UTF8Encoding]::new($false))
                    }catch{}
                }
                $proc.Dispose()
            }
        }
    }
    function Write-AtomicJson([hashtable]$Value) {
        Write-JsonFileAtomic -Path $StatusPath -Value $Value
    }

    $Head = (git -C $Repo rev-parse HEAD).Trim()
    Mark-Phase "HEAD_OK"

    # Log retention is deliberately outside the continuity critical path.
    # Broad directory scans are forbidden here because maintenance must never
    # hold the singleton mutex while walking an unbounded archive set.
    Mark-Phase 'NATS_LOG_RETENTION_DEFERRED_BOUNDED'

    $C5CanonicalSourcePaths = @("requirements-c5.txt","src/raios/c5_gateway","src/raios/search_cortex","src/raios/neuro_lingua",".ai-os/mcp/C5-MAINTENANCE-LAWS.json","scripts/ai-os/raios_c5_maintenance_guard.py","scripts/runtime/Deploy-RAIOS-C5.ps1")
    function Test-C5DeploymentCurrent([string]$DeployedHead) {
        if (-not $DeployedHead -or $DeployedHead -eq "UNKNOWN") { return $false }
        if ($DeployedHead -eq $Head) { return $true }
        try {
            & git -C $Repo cat-file -e ($DeployedHead + "^{commit}") 2>$null
            if ($LASTEXITCODE -ne 0) { return $false }
            & git -C $Repo diff --quiet $DeployedHead $Head -- $C5CanonicalSourcePaths
            return ($LASTEXITCODE -eq 0)
        } catch { return $false }
    }
    $CommandCenterCanonicalSourcePaths = @("src/raios/command_center","src/raios/goals","src/raios/search_cortex","src/raios/resource_fabric","src/raios/ai_gateway","src/raios/council_ops","src/raios/a2a","scripts/ai-os/raios_mcp","scripts/runtime/Deploy-RAIOS-Command-Center.ps1")
    function Test-CommandCenterDeploymentCurrent([string]$DeployedHead) {
        if (-not $DeployedHead -or $DeployedHead -eq "UNKNOWN") { return $false }
        if ($DeployedHead -eq $Head) { return $true }
        try {
            & git -C $Repo cat-file -e ($DeployedHead + "^{commit}") 2>$null
            if ($LASTEXITCODE -ne 0) { return $false }
            & git -C $Repo diff --quiet $DeployedHead $Head -- $CommandCenterCanonicalSourcePaths
            return ($LASTEXITCODE -eq 0)
        } catch { return $false }
    }
    $actions = [System.Collections.Generic.List[string]]::new()
    $errors = [System.Collections.Generic.List[string]]::new()
    $warnings = [System.Collections.Generic.List[string]]::new()

    # Remote Capability is a provider under C5/SCM. Maintenance observes it only.
    $DcrSupervisorStatePath=Join-Path $StableUserProfile ".raios\runtime\remote-access\rdc-system-direct\rdc-supervisor-state.json"
    $dcrSupervisorAlive=$false
    try{
        $dcrState=Get-Content -LiteralPath $DcrSupervisorStatePath -Raw|ConvertFrom-Json
        $dcrPid=[int]$dcrState.supervisor_pid
        $dcrProc=if($dcrPid -gt 4){Get-Process -Id $dcrPid -ErrorAction SilentlyContinue}else{$null}
        $dcrSupervisorAlive=[bool]($dcrProc -and [string]$dcrState.status -eq 'ONLINE' -and [string]$dcrState.authority -eq 'RAIOS-C5' -and @($dcrState.owned_remote_pids).Count -eq 1 -and @($dcrState.owned_local_mcp_pids).Count -eq 1 -and @($dcrState.legacy_remote_pids).Count -eq 0)
    }catch{$dcrSupervisorAlive=$false}
    if($dcrSupervisorAlive){Mark-Phase 'DCR_PROVIDER_OK'}else{$warnings.Add('DCR_PROVIDER_PENDING_C5_SCM');Mark-Phase 'DCR_PROVIDER_DEGRADED'}

    # Internet affects remote observers only. Two successes debounce reconnect;
    # persisted pending/cooldown state makes each one-minute pulse idempotent.
    $networkPrevious = Read-NetworkState
    $transportContinuity = Read-TransportContinuity
    $internetProbe = [bool](Test-Internet)
    $successStreak = if ($internetProbe) { [int]$networkPrevious.success_streak + 1 } else { 0 }
    $internetOnline = $internetProbe -and $successStreak -ge $NetworkRequiredSuccesses
    $lastResume = $null
    if ($networkPrevious.last_resume_at) {
        try { $lastResume = [DateTimeOffset]::Parse([string]$networkPrevious.last_resume_at) } catch {}
    }
    $cooldownElapsed = -not $lastResume -or (([DateTimeOffset]::UtcNow - $lastResume).TotalSeconds -ge $NetworkResumeCooldownSeconds)
    $reconnected = $internetOnline -and -not [bool]$networkPrevious.online
    $resumePending = $reconnected -or [bool]$networkPrevious.resume_pending
    # Checkpoint/reconciliation is evidence and a mutation safety gate, never a runtime stop.
    # RAIOS continuation, Remote transport execution, and canonical mutation are independent truths.
    $continuationGateOpen = [bool]$(if ($transportContinuity.PSObject.Properties['continuation_allowed']) {
        $transportContinuity.continuation_allowed
    } else { $true })
    $remoteTransportExecutionAllowed = [bool](
        $transportContinuity.transport_online -and
        $(if ($transportContinuity.PSObject.Properties['transport_execution_allowed']) {
            $transportContinuity.transport_execution_allowed
        } else { $transportContinuity.transport_online })
    )
    $mutationAllowed = [bool]$(if ($transportContinuity.PSObject.Properties['mutation_allowed']) {
        $transportContinuity.mutation_allowed
    } else { $false })
    $remoteProof = [string]$transportContinuity.checkpoint_proof_hash
    $previousRemoteProof = [string]$networkPrevious.last_remote_resume_proof_hash
    $remoteResumePending = [bool](
        $remoteTransportExecutionAllowed -and
        ([string]$transportContinuity.event -like "RECONNECT*") -and
        -not [string]::IsNullOrWhiteSpace($remoteProof) -and
        ($remoteProof -ne $previousRemoteProof)
    )
    if ([bool]$transportContinuity.reconciliation_required) {
        $actions.Add("RECONNECT_RECONCILIATION_PENDING_NONBLOCKING")
        Mark-Phase "RECONNECT_RECONCILIATION_PENDING"
    }
    if (-not $remoteTransportExecutionAllowed) {
        $actions.Add("REMOTE_TRANSPORT_EXECUTION_UNAVAILABLE")
        Mark-Phase "REMOTE_TRANSPORT_DEGRADED"
    }
    if (-not $continuationGateOpen) {
        # Reserved for an explicit future system-level stop contract; checkpoint uncertainty alone never closes it.
        $actions.Add("SYSTEM_CONTINUATION_EXPLICITLY_DISABLED")
        Mark-Phase "SYSTEM_CONTINUATION_DISABLED"
    }
    $resumeTriggered = $false
    $resumeAt = if ($lastResume) { $lastResume.ToString("o") } else { $null }
    $resumeEligible = $internetOnline -and ($resumePending -or $remoteResumePending) -and $cooldownElapsed -and $continuationGateOpen
    Mark-Phase "NETWORK_OK"

    # Local Ollama is optional on this cloud-first remote node.
    $ollamaHealth=Get-JsonHealth "http://127.0.0.1:11434/api/tags" 2
    $ollamaHttpReady=[bool]$ollamaHealth
    $ollamaModelReady=$false
    if($ollamaHttpReady){
        try{$ollamaModelReady=[bool](@($ollamaHealth.models).Count -gt 0)}catch{}
        Mark-Phase 'OLLAMA_OPTIONAL_OBSERVED'
    }else{
        $warnings.Add('OLLAMA_OPTIONAL_NOT_READY')
        Mark-Phase 'OLLAMA_OPTIONAL_SKIPPED'
    }

    # Priority-0 recovery: restore the cognitive brain before long
    # infrastructure repairs. This reuses the existing Manager, Evolution,
    # canonical TASKS ledger and canonical cognitive WAL; it creates no second
    # runtime, WAL, task authority, watchdog or scheduler.
    Mark-Phase 'COGNITIVE_PRIORITY0_CHECK'
    $managerHeartbeatPath = Join-Path $StableUserProfile ".raios\runtime\manager\heartbeat.json"
    $managerHeartbeatDir = Split-Path $managerHeartbeatPath
    $evolutionHeartbeatPath = Join-Path $StableUserProfile ".raios\runtime\evolution-brain\heartbeat.json"

    function Get-FreshManagerHeartbeat {
        $best=$null
        $bestTime=[DateTimeOffset]::MinValue
        $candidates=[System.Collections.Generic.List[string]]::new()
        if(Test-Path -LiteralPath $managerHeartbeatPath){$candidates.Add($managerHeartbeatPath)}
        try{
            $seen=0
            foreach($candidate in [IO.Directory]::EnumerateFiles($managerHeartbeatDir,'heartbeat.live-*.json',[IO.SearchOption]::TopDirectoryOnly)){
                if($seen -ge 32){break}
                $candidates.Add($candidate)
                $seen++
            }
        }catch{}
        foreach($candidate in @($candidates)){
            try{
                $obj=Get-Content -LiteralPath $candidate -Raw|ConvertFrom-Json
                $when=[DateTimeOffset]::Parse([string]$obj.generated_at)
                if($when -gt $bestTime){$best=$obj;$bestTime=$when}
            }catch{}
        }
        return $best
    }

    $managerAlive = $false
    $evolutionAlive = $false
    try {
        $mh = Get-FreshManagerHeartbeat
        $mpid = [int]($mh | Select-Object -ExpandProperty manager_pid -ErrorAction Stop)
        $mstate = [string]($mh | Select-Object -ExpandProperty state -ErrorAction Stop)
        $mtime = [DateTimeOffset]::Parse([string]($mh | Select-Object -ExpandProperty generated_at -ErrorAction Stop))
        $managerAlive = [bool](
            $mpid -gt 4 -and
            (Get-Process -Id $mpid -ErrorAction SilentlyContinue) -and
            $mstate -in @('RUNNING','ONLINE','ACTIVE') -and
            (([DateTimeOffset]::UtcNow-$mtime).TotalSeconds -le 60)
        )
    } catch { $managerAlive = $false }
    try {
        $eh = Get-Content -LiteralPath $evolutionHeartbeatPath -Raw | ConvertFrom-Json
        $epid = [int]$eh.PSObject.Properties['pid'].Value
        $estate = [string]$(if($eh.PSObject.Properties['state']){$eh.PSObject.Properties['state'].Value}else{$eh.PSObject.Properties['status'].Value})
        $etime = [DateTimeOffset]::Parse([string]$eh.timestamp)
        $evolutionAlive = [bool](
            $epid -gt 4 -and
            (Get-Process -Id $epid -ErrorAction SilentlyContinue) -and
            $estate -in @('RUNNING','ONLINE','ACTIVE','BACKLOG_IN_PROGRESS') -and
            (([DateTimeOffset]::UtcNow-$etime).TotalSeconds -le 60)
        )
    } catch { $evolutionAlive = $false }

    if (-not ($managerAlive -and $evolutionAlive)) {
        Mark-Phase 'COGNITIVE_PRIORITY0_RECOVERY_START'
        try {
            $cognitiveEnsure = Join-Path $PSScriptRoot "Ensure-RAIOS-Cognitive-Loop.ps1"
            $cognitiveRecovery = Invoke-BoundedRecovery "COGNITIVE_PRIORITY0" $cognitiveEnsure @("-Repo",$Repo) $T_C5_COGNITIVE_REPAIR
            if ($cognitiveRecovery.ok) {
                $actions.Add('COGNITIVE_PRIORITY0_RECOVERY_OK')
                Mark-Phase 'COGNITIVE_PRIORITY0_RECOVERY_OK'
            } else {
                # Ensure-Cognitive can return non-zero while the C5 gateway is
                # still offline even after Manager/Evolution are restored.
                # Preserve that progress and continue gateway repair.
                $warnings.Add('COGNITIVE_PRIORITY0_RECOVERY_PARTIAL')
                Mark-Phase 'COGNITIVE_PRIORITY0_RECOVERY_PARTIAL'
            }
        } catch {
            $warnings.Add('COGNITIVE_PRIORITY0_RECOVERY_EXCEPTION:' + $_.Exception.GetType().Name)
            Mark-Phase 'COGNITIVE_PRIORITY0_RECOVERY_PARTIAL'
        }
    } else {
        Mark-Phase 'COGNITIVE_PRIORITY0_ALREADY_READY'
    }

    try { if(Set-RaiosNatsRuntimePriority){$actions.Add('NORMALIZE_EXISTING_NATS_RUNTIME_PRIORITY')} } catch { $errors.Add('NATS_PRIORITY_REPAIR_FAILED:' + $_.Exception.GetType().Name) }
    if (-not (Test-Tcp 4222)) {
        try {
            $natsTask = Get-ScheduledTask -TaskName "RAIOS-NATS-Local" -ErrorAction Stop
            if ($natsTask.State -ne "Running") {
                Start-ScheduledTask -TaskName "RAIOS-NATS-Local"
                $actions.Add("START_EXISTING_NATS_TASK")
            } else {
                $actions.Add("WAIT_EXISTING_NATS_TASK")
            }
            for ($i=0; $i -lt 20; $i++) {
                if (Test-Tcp 4222) { break }
                Start-Sleep -Seconds 1
            }
            if (-not (Test-Tcp 4222)) { $errors.Add("NATS_NOT_READY_AFTER_WAIT") }
        } catch { $errors.Add("NATS_RESTORE_FAILED:" + $_.Exception.GetType().Name) }
    }
    if(Test-RaiosNatsIdentity){Mark-Phase "NATS_OK"}else{Mark-Phase "NATS_FAILED";$errors.Add("NATS_IDENTITY_NOT_READY")}

    function Test-C5ContinuityHealthReady($health) {
        if (-not $health) { return $false }
        if ($health.status -eq "ONLINE") { return $true }
        $timeoutInventory = [bool](
            $health.status -eq "UNKNOWN" -and
            $health.model_fabric_probe_state -eq "TIMEOUT" -and
            $health.model_fabric_error -eq "OLLAMA_INVENTORY_PROBE_TIMEOUT" -and
            $health.gateway -eq $true -and
            $health.model_fabric -eq $true
        )
        if ($timeoutInventory) { return $true }
        # HTTP 200 DEGRADED with gateway proof is not a deploy trigger. model_fabric_ready=false stays visible.
        return [bool](
            $health.status -eq "DEGRADED" -and
            $health.gateway -eq $true -and
            $health.model_fabric -eq $true
        )
    }
    # HTTP headers must arrive within the bounded probe; a TCP listener is not READY.
    $routerOnline = Test-RaiosRouterHttpReady
    if (-not $routerOnline -and (Test-Tcp 20128)) {
        # Preserve the listener until strict owned-process recovery is available.
        $errors.Add("9ROUTER_HTTP_UNRESPONSIVE")
    } elseif (-not $routerOnline) {
        # Resolve the installed package but never execute its console .cmd shim.
        # Direct Node + cli.js + tray is the package's own canonical windowless path.
        $routerCommand = Get-Command 9router.cmd -ErrorAction SilentlyContinue
        $routerRoot = if ($routerCommand) {
            Split-Path -Parent $routerCommand.Source
        } else {
            Join-Path $env:APPDATA "npm"
        }
        $routerCli = Join-Path $routerRoot "node_modules\9router\cli.js"
        $node = Get-Command node.exe -ErrorAction SilentlyContinue
        if ($node -and (Test-Path -LiteralPath $routerCli)) {
            Start-Process -FilePath $node.Source -ArgumentList @($routerCli,"--tray","--host","127.0.0.1","--port","20128","--no-browser","--skip-update") -WindowStyle Hidden -RedirectStandardOutput (Join-Path $RuntimeRoot "9router.out.log") -RedirectStandardError (Join-Path $RuntimeRoot "9router.err.log") | Out-Null
            $actions.Add("START_EXISTING_9ROUTER_WINDOWLESS")
            Start-Sleep -Seconds 5
        } else { $errors.Add("9ROUTER_WINDOWLESS_ENTRY_MISSING") }
    }
    $routerOnline = Test-RaiosRouterHttpReady
    if ($routerOnline) { Mark-Phase "ROUTER_OK" } else { Mark-Phase "ROUTER_FAILED"; $errors.Add("9ROUTER_NOT_HTTP_READY") }

    $c5AuthorizedOverlay=Get-RaiosC5AuthorizedOverlay -CanonicalRepo $Repo -CanonicalHead $Head -AppRoot (Join-Path $StableUserProfile '.raios\runtime\c5\app')
    Mark-Phase "C5_HEALTH_CHECK_1"
    $c5 = Get-JsonHealth "http://127.0.0.1:8766/health" 6
    $c5ServiceReady = Test-RaiosC5RecoveryGatewayReady $c5 $Head
    $loop = if ($c5 -and $c5.cognitive_loop) { $c5.cognitive_loop } elseif ($c5ServiceReady) { Get-JsonHealth "http://127.0.0.1:8766/v1/cognitive/status" 4 } else { $null }
    $cognitiveReady = [bool]($loop -and $loop.manager.alive -eq $true -and $loop.evolution.alive -eq $true)
    if($c5AuthorizedOverlay -and $c5ServiceReady -and -not $cognitiveReady){
        $c5AuthorizedOverlay=$null
        Mark-Phase 'C5_SOURCE_REFRESH_DEFERRED_FOR_COGNITIVE_RECOVERY'
    }
    if (-not $c5ServiceReady -or $c5AuthorizedOverlay) {
        Mark-Phase "C5_SERVICE_REPAIR_ATTEMPT"
        try {
            $deployArguments=@('-Repo',$Repo,'-RuntimeRoot',(Join-Path $StableUserProfile '.raios\runtime\c5'),'-HeadOnlyRecovery')
            if($c5AuthorizedOverlay){$deployArguments+=@('-LeasedOverlayFiles',$c5AuthorizedOverlay);Mark-Phase 'C5_AUTHORIZED_SOURCE_REFRESH'}
            $r = Invoke-BoundedRecovery "C5_SERVICE_REPAIR" (Join-Path $PSScriptRoot "Deploy-RAIOS-C5.ps1") $deployArguments $T_C5_SERVICE_REPAIR
            if ($r.timed_out) { Mark-Phase "C5_SERVICE_REPAIR_TIMEOUT" }
            elseif ($r.ok) { Mark-Phase "C5_SERVICE_REPAIR_OK" }
            else { Mark-Phase "C5_SERVICE_REPAIR_FAILED" }
            if (-not $r.ok) { throw ("C5_SERVICE_BOUNDED_RECOVERY_FAILED timeout=" + $r.timed_out + " exit=" + $r.exit_code + " error=" + $r.error) }
            $actions.Add("DEPLOY_C5_HEAD_ONLY_RECOVERY")
        } catch {
            $msg = ([string]$_.Exception.Message -replace '[\r\n]+',' ')
            if ($msg.Length -gt 240) { $msg = $msg.Substring(0,240) }
            $errors.Add("C5_SERVICE_RESTORE_FAILED:" + $_.Exception.GetType().Name + ":" + $msg)
        }
    }
    # A deployment may start the gateway yet fail certification because cognition is absent.
    # Re-probe that gateway and repair cognition in this cycle without trusting its manifest.
    $c5 = Get-JsonHealth "http://127.0.0.1:8766/health" 6
    $c5ServiceReady = Test-RaiosC5RecoveryGatewayReady $c5 $Head
    $loop = if($c5 -and $c5.cognitive_loop){$c5.cognitive_loop}else{$null}

    # Gateway cognition can lag the live processes. Re-probe direct liveness
    # before launching a duplicate cognitive recovery.
    try {
        $mh = Get-FreshManagerHeartbeat
        $mpid = [int]($mh | Select-Object -ExpandProperty manager_pid -ErrorAction Stop)
        $mstate = [string]($mh | Select-Object -ExpandProperty state -ErrorAction Stop)
        $mtime = [DateTimeOffset]::Parse([string]($mh | Select-Object -ExpandProperty generated_at -ErrorAction Stop))
        $managerAlive = [bool]($mpid -gt 4 -and (Get-Process -Id $mpid -ErrorAction SilentlyContinue) -and $mstate -in @('RUNNING','ONLINE','ACTIVE') -and (([DateTimeOffset]::UtcNow-$mtime).TotalSeconds -le 120))
    } catch { $managerAlive = $false }
    try {
        $eh = Get-Content -LiteralPath $evolutionHeartbeatPath -Raw | ConvertFrom-Json
        $epid = [int]$eh.PSObject.Properties['pid'].Value
        $estate = [string]$(if($eh.PSObject.Properties['state']){$eh.PSObject.Properties['state'].Value}else{$eh.PSObject.Properties['status'].Value})
        $etime = [DateTimeOffset]::Parse([string]$eh.timestamp)
        $evolutionAlive = [bool]($epid -gt 4 -and (Get-Process -Id $epid -ErrorAction SilentlyContinue) -and $estate -in @('RUNNING','ONLINE','ACTIVE','BACKLOG_IN_PROGRESS') -and (([DateTimeOffset]::UtcNow-$etime).TotalSeconds -le 120))
    } catch { $evolutionAlive = $false }

    $directCognitiveReady = [bool]($managerAlive -and $evolutionAlive)
    $cognitiveReady = [bool](($loop -and $loop.manager.alive -eq $true -and $loop.evolution.alive -eq $true) -or $directCognitiveReady)
    if ($c5ServiceReady -and -not $cognitiveReady) {
        Mark-Phase "C5_COGNITIVE_REPAIR_ATTEMPT"
        try {
            Mark-Phase "C5_COGNITIVE_REPAIR_START"
            $r = Invoke-BoundedRecovery "C5_COGNITIVE_REPAIR" (Join-Path $PSScriptRoot "Ensure-RAIOS-Cognitive-Loop.ps1") @("-Repo",$Repo) $T_C5_COGNITIVE_REPAIR
            if (-not $r.ok) { throw ("C5_COGNITIVE_BOUNDED_RECOVERY_FAILED timeout=" + $r.timed_out + " exit=" + $r.exit_code + " error=" + $r.error) }
            $actions.Add("ENSURE_EXISTING_COGNITIVE_LOOP")
        } catch {
            $msg = ([string]$_.Exception.Message -replace '[\r\n]+',' ')
            if ($msg.Length -gt 240) { $msg = $msg.Substring(0,240) }
            $errors.Add("COGNITIVE_LOOP_RESTORE_FAILED:" + $_.Exception.GetType().Name + ":" + $msg)
        }
    }
    Mark-Phase "C5_HEALTH_CHECK_2"
    $c5 = Get-JsonHealth "http://127.0.0.1:8766/health" 12
    $loop = if ($c5 -and $c5.cognitive_loop) { $c5.cognitive_loop } else { Get-JsonHealth "http://127.0.0.1:8766/v1/cognitive/status" 6 }
    $c5Ready = [bool](
        $c5 -and
        (Test-C5ContinuityHealthReady $c5) -and
        (Test-C5DeploymentCurrent ([string]$c5.canonical_head)) -and
        (
            ($loop -and $loop.manager.alive -eq $true -and $loop.evolution.alive -eq $true) -or
            $directCognitiveReady
        )
    )
    if ($c5Ready) { Mark-Phase "C5_LOOP_OK" } else { Mark-Phase "C5_REPAIR_FAILED" }

    $center = Get-JsonHealth "http://127.0.0.1:8770/health" 12
    $centerReady = [bool]($center -and $center.status -eq "ONLINE" -and (Test-CommandCenterDeploymentCurrent ([string]$center.canonical_head)))
    if (-not $centerReady) {
        # Recovery is deliberately idempotent. A one-minute continuity loop must not
        # materialize a new HEAD-RECOVERY transaction every time an unhealthy
        # Command Center survives on the old listener.
        $ccRecoveryStatePath = Join-Path $RuntimeRoot "command-center-recovery.json"
        $ccRecoveryCooldownSeconds = 900
        $canonicalHead = (git -C $Repo rev-parse HEAD).Trim()
        $ccRecoveryState = $null
        try { $ccRecoveryState = Get-Content -LiteralPath $ccRecoveryStatePath -Raw | ConvertFrom-Json } catch {}
        $lastAttempt = [DateTimeOffset]::MinValue
        if ($ccRecoveryState -and [string]$ccRecoveryState.canonical_head -eq $canonicalHead -and $ccRecoveryState.last_attempt_at) {
            try { $lastAttempt = [DateTimeOffset]::Parse([string]$ccRecoveryState.last_attempt_at) } catch {}
        }
        $ccDeploymentLeaseActive = $false
        try {
            $lockLedger = Get-Content -LiteralPath (Join-Path $Repo '.ai-os\state\LOCKS.json') -Raw | ConvertFrom-Json
            $now = [DateTimeOffset]::UtcNow
            $ccDeploymentLeaseActive = [bool](@($lockLedger.locks | Where-Object {
                $_.status -eq 'ACTIVE' -and $_.owner -eq 'RAIOS_SYSTEM' -and $_.scope -eq 'scripts/runtime/Deploy-RAIOS-Command-Center.ps1' -and
                $_.lease_holder -eq 'C1' -and $_.expires_at -and ([DateTimeOffset]::Parse([string]$_.expires_at) -gt $now)
            }).Count -gt 0)
        } catch {}
        # Command-Fabric current lease is the live deployment-intent authority.
        # This closes the race before the deployment mutex is acquired.
        try {
            $scope = 'scripts/runtime/Deploy-RAIOS-Command-Center.ps1'
            $sha = [Security.Cryptography.SHA256]::Create()
            try {
                $hash = $sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($scope))
            } finally {
                $sha.Dispose()
            }
            $key = (-join ($hash | ForEach-Object { $_.ToString('x2') })).Substring(0,24)
            $projectionPath = Join-Path $Repo ('.ai-os\state\command-fabric\leases\_current\'+$key+'.json')
            if (Test-Path -LiteralPath $projectionPath -PathType Leaf) {
                $projection = Get-Content -LiteralPath $projectionPath -Raw | ConvertFrom-Json
                $leaseId = [string]$projection.lease_id
                if ($leaseId) {
                    $leasePath = Join-Path $Repo ('.ai-os\state\command-fabric\leases\'+$leaseId+'.json')
                    if (Test-Path -LiteralPath $leasePath -PathType Leaf) {
                        $cfLease = Get-Content -LiteralPath $leasePath -Raw | ConvertFrom-Json
                        if (
                            [string]$cfLease.owner -eq 'RAIOS_SYSTEM' -and
                            [string]$cfLease.scope -eq $scope -and
                            [string]$cfLease.state -eq 'ACTIVE' -and
                            $cfLease.expires_at -and
                            ([DateTimeOffset]::Parse([string]$cfLease.expires_at) -gt [DateTimeOffset]::UtcNow)
                        ) {
                            $ccDeploymentLeaseActive = $true
                        }
                    }
                }
            }
        } catch {}
        $ccTransactionalGuardActive = $false
        try {
            $guardPath = Join-Path $StableUserProfile '.raios\runtime\command-center\transactional-deployment-active.json'
            if (Test-Path -LiteralPath $guardPath -PathType Leaf) {
                $guard = Get-Content -LiteralPath $guardPath -Raw | ConvertFrom-Json
                $guardPid = 0
                try { $guardPid = [int]$guard.pid } catch { $guardPid = 0 }
                $guardPidAlive = [bool]($guardPid -gt 4 -and (Get-Process -Id $guardPid -ErrorAction SilentlyContinue))
                $ccTransactionalGuardActive = [bool](
                    [string]$guard.schema -eq 'raios.command-center-transaction-guard.v1' -and
                    [string]$guard.canonical_head -eq $canonicalHead -and
                    $guard.expires_at -and ([DateTimeOffset]::Parse([string]$guard.expires_at) -gt [DateTimeOffset]::UtcNow) -and
                    $guardPidAlive
                )
                if (-not $ccTransactionalGuardActive -and -not $guardPidAlive) {
                    Remove-Item -LiteralPath $guardPath -Force -ErrorAction SilentlyContinue
                }
            }
        } catch {}
        $ccDeploymentMutexActive = $false
        try {
            $mutexPath = Join-Path $StableUserProfile '.raios\runtime\command-center\deployment-exclusive.lock'
            if (Test-Path -LiteralPath $mutexPath -PathType Leaf) {
                $probe = $null
                try {
                    $probe = [IO.File]::Open($mutexPath,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
                } catch [IO.IOException] {
                    $ccDeploymentMutexActive = $true
                } finally {
                    if ($probe) { $probe.Dispose() }
                }
            }
        } catch {}
        $recoveryDue = (-not $ccRecoveryState) -or
            ([string]$ccRecoveryState.canonical_head -ne $canonicalHead) -or
            (([DateTimeOffset]::UtcNow - $lastAttempt).TotalSeconds -ge $ccRecoveryCooldownSeconds)
        if ($recoveryDue -and -not $ccDeploymentLeaseActive -and -not $ccTransactionalGuardActive -and -not $ccDeploymentMutexActive) {
            Mark-Phase "CC_REPAIR_ATTEMPT"
            Write-JsonFileAtomic $ccRecoveryStatePath @{
                schema = "raios.command-center-recovery-state.v1"
                canonical_head = $canonicalHead
                last_attempt_at = [DateTimeOffset]::UtcNow.ToString("o")
                outcome = "ATTEMPTING"
            }
            try {
                $r = Invoke-BoundedRecovery "CC_REPAIR" (Join-Path $PSScriptRoot "Deploy-RAIOS-Command-Center.ps1") @("-HeadOnlyRecovery") 120; if (-not $r.ok) { throw ("CC_BOUNDED_RECOVERY_FAILED timeout=" + $r.timed_out + " exit=" + $r.exit_code) }
                $actions.Add("DEPLOY_COMMAND_CENTER_HEAD_ONLY_RECOVERY")
                Write-JsonFileAtomic $ccRecoveryStatePath @{
                    schema = "raios.command-center-recovery-state.v1"
                    canonical_head = $canonicalHead
                    last_attempt_at = [DateTimeOffset]::UtcNow.ToString("o")
                    outcome = "DEPLOY_RETURNED"
                }
            } catch {
                $msg = ([string]$_.Exception.Message -replace '[\r\n]+',' ')
                if ($msg.Length -gt 240) { $msg = $msg.Substring(0,240) }
                $errors.Add("COMMAND_CENTER_RESTORE_FAILED:" + $_.Exception.GetType().Name + ":" + $msg)
                Write-JsonFileAtomic $ccRecoveryStatePath @{
                    schema = "raios.command-center-recovery-state.v1"
                    canonical_head = $canonicalHead
                    last_attempt_at = [DateTimeOffset]::UtcNow.ToString("o")
                    outcome = "FAILED"
                    error = $msg
                }
            }
        } else {
            Mark-Phase "CC_REPAIR_COOLDOWN"
            $actions.Add("COMMAND_CENTER_RECOVERY_COOLDOWN")
        }
        $center = Get-JsonHealth "http://127.0.0.1:8770/health" 12
        $centerReady = [bool]($center -and $center.status -eq "ONLINE" -and (Test-CommandCenterDeploymentCurrent ([string]$center.canonical_head)))
    }
    if ($centerReady) { Mark-Phase "CC_OK" } else { Mark-Phase "CC_REPAIR_FAILED" }

    # Universal MCP is part of the same canonical continuity fabric; never create a second watchdog.
    $mcp = Get-JsonHealth "http://127.0.0.1:8788/health" 4
    $mcpReady = [bool]($mcp -and $mcp.ok -eq $true -and $mcp.tool_count -eq 8 -and $mcp.second_gateway -eq $false -and [string]$mcp.head -eq $Head -and [string]$mcp.head_source -eq "git-file")
    if (-not $mcpReady) {
        $mcpRecoveryStatePath = Join-Path $RuntimeRoot "mcp-recovery.json"
        $mcpRecoveryCooldownSeconds = 900
        $canonicalHead = (git -C $Repo rev-parse HEAD).Trim()
        $mcpRecoveryState = $null
        try { $mcpRecoveryState = Get-Content -LiteralPath $mcpRecoveryStatePath -Raw | ConvertFrom-Json } catch {}
        $lastMcpAttempt = [DateTimeOffset]::MinValue
        if ($mcpRecoveryState -and [string]$mcpRecoveryState.canonical_head -eq $canonicalHead -and $mcpRecoveryState.last_attempt_at) {
            try { $lastMcpAttempt = [DateTimeOffset]::Parse([string]$mcpRecoveryState.last_attempt_at) } catch {}
        }
        $mcpHardDown = (-not $mcp) -or (-not (Test-Tcp 8788))
        $mcpRecoveryDue = $mcpHardDown -or
            (-not $mcpRecoveryState) -or
            ([string]$mcpRecoveryState.canonical_head -ne $canonicalHead) -or
            (([DateTimeOffset]::UtcNow - $lastMcpAttempt).TotalSeconds -ge $mcpRecoveryCooldownSeconds)
        if ($mcpRecoveryDue) {
            Mark-Phase "MCP_REPAIR_ATTEMPT"
            Write-JsonFileAtomic $mcpRecoveryStatePath @{
                schema = "raios.mcp-recovery-state.v1"
                canonical_head = $canonicalHead
                last_attempt_at = [DateTimeOffset]::UtcNow.ToString("o")
                outcome = "ATTEMPTING"
            }
            try {
                $mcpEnsure = Join-Path $Repo "scripts\ai-os\raios_mcp_local_ensure.ps1"
                $r = Invoke-BoundedRecovery "MCP_REPAIR" $mcpEnsure @("-Port","8788") 120; if (-not $r.ok) { throw ("MCP_BOUNDED_RECOVERY_FAILED timeout=" + $r.timed_out + " exit=" + $r.exit_code) }
                $actions.Add("ENSURE_EXISTING_UNIVERSAL_MCP")
                $mcp = Get-JsonHealth "http://127.0.0.1:8788/health" 4
                $mcpReady = [bool]($mcp -and $mcp.ok -eq $true -and $mcp.tool_count -eq 8 -and $mcp.second_gateway -eq $false -and [string]$mcp.head -eq $Head -and [string]$mcp.head_source -eq "git-file")
                $mcpOutcome = if ($mcpReady) { "HEALTHY" } else { "DEPLOY_RETURNED_UNHEALTHY" }
                Write-JsonFileAtomic $mcpRecoveryStatePath @{
                    schema = "raios.mcp-recovery-state.v1"
                    canonical_head = $canonicalHead
                    last_attempt_at = [DateTimeOffset]::UtcNow.ToString("o")
                    outcome = $mcpOutcome
                }
                if (-not $mcpReady) { $errors.Add("UNIVERSAL_MCP_NOT_READY_AFTER_DEPLOY") }
            } catch {
                $msg = ([string]$_.Exception.Message -replace '[\r\n]+',' ')
                if ($msg.Length -gt 240) { $msg = $msg.Substring(0,240) }
                $errors.Add("UNIVERSAL_MCP_RESTORE_FAILED:" + $_.Exception.GetType().Name + ":" + $msg)
                Write-JsonFileAtomic $mcpRecoveryStatePath @{
                    schema = "raios.mcp-recovery-state.v1"
                    canonical_head = $canonicalHead
                    last_attempt_at = [DateTimeOffset]::UtcNow.ToString("o")
                    outcome = "FAILED"
                    error = $msg
                }
            }
        } else {
            Mark-Phase "MCP_REPAIR_COOLDOWN"
            $actions.Add("UNIVERSAL_MCP_RECOVERY_COOLDOWN")
        }
    }
    if ($mcpReady) { Mark-Phase "MCP_OK" } else { Mark-Phase "MCP_FAILED" }

    function Test-NativeMcpTunnelReady {
        $mcpHealth = Get-JsonHealth "http://127.0.0.1:8788/health" 3
        if (-not ($mcpHealth -and $mcpHealth.ok -eq $true -and $mcpHealth.tool_count -eq 8 -and $mcpHealth.second_gateway -eq $false)) { return $false }

        $healthFile = Join-Path $StableUserProfile ".local\state\tunnel-client\health\raios-native.url"
        if (-not (Test-Path -LiteralPath $healthFile)) { return $false }
        try {
            $base = (Get-Content -LiteralPath $healthFile -Raw).Trim()
            if ($base -notmatch '^http://127\.0\.0\.1:\d+$') { return $false }
        } catch { return $false }

        try {
            $resp = Invoke-WebRequest -UseBasicParsing -Uri ($base + "/readyz") -TimeoutSec 3
            if ($resp.StatusCode -eq 200 -and $resp.Content.Trim().StartsWith("ready",[StringComparison]::OrdinalIgnoreCase)) { return $true }
        } catch {}

        # OAuth discovery is optional for the RAIOS native transport.  The
        # runtime admin plane plus the canonical MCP health contract proves
        # operational liveness without creating a restart loop.
        try {
            $resp = Invoke-WebRequest -UseBasicParsing -Uri ($base + "/metrics") -TimeoutSec 3
            return ($resp.StatusCode -eq 200)
        } catch { return $false }
    }
    $nativeTunnelReady = Test-NativeMcpTunnelReady
    if (-not $nativeTunnelReady) {
        # Native RAIOS tunnel ownership belongs only to the RAIOS-C5 Windows
        # service. Maintenance observes and waits; it never starts a second
        # user-session/Console tunnel-client.
        try {
            $svc = Get-Service -Name 'RAIOS-C5' -ErrorAction Stop
            if ($svc.Status -ne 'Running') { throw "RAIOS_C5_SCM_NOT_RUNNING" }
            $actions.Add("NATIVE_MCP_TUNNEL_DEFER_TO_C5_SCM")
            for($i=0;$i-lt 6 -and -not $nativeTunnelReady;$i++){
                Start-Sleep -Seconds 2
                $nativeTunnelReady = Test-NativeMcpTunnelReady
            }
            if (-not $nativeTunnelReady) {
                $warnings.Add("NATIVE_MCP_TUNNEL_PENDING_C5_SCM")
            }
        } catch {
            $msg = ([string]$_.Exception.Message -replace '[\r\n]+',' ')
            if ($msg.Length -gt 240) { $msg = $msg.Substring(0,240) }
            $errors.Add("NATIVE_MCP_TUNNEL_SCM_AUTHORITY_UNAVAILABLE:" + $msg)
        }
    }
    if ($nativeTunnelReady) { Mark-Phase "NATIVE_MCP_TUNNEL_OK" } else { Mark-Phase "NATIVE_MCP_TUNNEL_FAILED" }

    $r=$null
    try {
        $r = Invoke-BoundedRecovery "SEAT_REPAIR" (Join-Path $PSScriptRoot "Ensure-RAIOS-Seat-Sessions.ps1") @("-Repo",$Repo) 45; if (-not $r.ok) { throw ("SEAT_BOUNDED_RECOVERY_FAILED timeout=" + $r.timed_out + " exit=" + $r.exit_code) }
        $actions.Add("ENSURE_RAIOS_SEAT_SESSIONS")
    } catch { $warnings.Add("SEAT_SESSION_RESTORE_FAILED:" + $_.Exception.GetType().Name) }
    if($r -and $r.ok){
        Mark-Phase "SEAT_REPAIR_CALL_OK"
        Write-JsonFileAtomic (Join-Path $RuntimeRoot 'seat_repair.retry.json') @{failures=0;next_attempt_at=$null;state='CALL_COMPLETED_NOT_SEAT_HEALTH';authority='RAIOS-C5';canonical_head=$Head}
    }else{Mark-Phase "SEAT_REPAIR_FAILED"}

    Mark-Phase "C5_HEALTH_CHECK_3"
    $c5 = Get-JsonHealth "http://127.0.0.1:8766/health" 12
    $loop = if ($c5 -and $c5.cognitive_loop) { $c5.cognitive_loop } else { Get-JsonHealth "http://127.0.0.1:8766/v1/cognitive/status" 6 }
    $center = Get-JsonHealth "http://127.0.0.1:8770/health" 12
    $routerOnline = Test-RaiosRouterHttpReady
    # Refresh direct cognitive liveness after all bounded repairs. Gateway
    # health is useful but is not the sole truth for Manager/Evolution.
    try {
        $mh = Get-FreshManagerHeartbeat
        $mpid = [int]($mh | Select-Object -ExpandProperty manager_pid -ErrorAction Stop)
        $mstate = [string]($mh | Select-Object -ExpandProperty state -ErrorAction Stop)
        $mtime = [DateTimeOffset]::Parse([string]($mh | Select-Object -ExpandProperty generated_at -ErrorAction Stop))
        $managerAlive = [bool]($mpid -gt 4 -and (Get-Process -Id $mpid -ErrorAction SilentlyContinue) -and $mstate -in @('RUNNING','ONLINE','ACTIVE') -and (([DateTimeOffset]::UtcNow-$mtime).TotalSeconds -le 60))
    } catch { $managerAlive = $false }
    try {
        $eh = Get-Content -LiteralPath $evolutionHeartbeatPath -Raw | ConvertFrom-Json
        $epid = [int]$eh.PSObject.Properties['pid'].Value
        $estate = [string]$(if($eh.PSObject.Properties['state']){$eh.PSObject.Properties['state'].Value}else{$eh.PSObject.Properties['status'].Value})
        $etime = [DateTimeOffset]::Parse([string]$eh.timestamp)
        $evolutionAlive = [bool]($epid -gt 4 -and (Get-Process -Id $epid -ErrorAction SilentlyContinue) -and $estate -in @('RUNNING','ONLINE','ACTIVE','BACKLOG_IN_PROGRESS') -and (([DateTimeOffset]::UtcNow-$etime).TotalSeconds -le 60))
    } catch { $evolutionAlive = $false }

    $services = [ordered]@{
        C5 = [bool](Test-C5ContinuityHealthReady $c5)
        MANAGER = [bool](($loop -and $loop.manager.alive -eq $true) -or $managerAlive)
        EVOLUTION = [bool](($loop -and $loop.evolution.alive -eq $true) -or $evolutionAlive)
        COMMAND_CENTER = [bool]($center -and $center.status -eq "ONLINE")
        UNIVERSAL_MCP = [bool]$mcpReady
        NATIVE_MCP_TUNNEL = [bool]$nativeTunnelReady
        ROUTER_9 = $routerOnline
        NATS = [bool](Test-RaiosNatsIdentity)
        OLLAMA = [bool](Get-JsonHealth "http://127.0.0.1:11434/api/tags" 3)
    }
    $verifiedRecovery=@{
        C5_SERVICE_REPAIR=$services.C5;C5_COGNITIVE_REPAIR=($services.MANAGER -and $services.EVOLUTION)
        CC_REPAIR=$services.COMMAND_CENTER;MCP_REPAIR=$services.UNIVERSAL_MCP;NATIVE_MCP_TUNNEL_REPAIR=$services.NATIVE_MCP_TUNNEL
    }
    foreach($name in @($verifiedRecovery.Keys)){
        if($verifiedRecovery[$name]){
            $path=Join-Path $RuntimeRoot ($name.ToLowerInvariant()+'.retry.json')
            if(Test-Path -LiteralPath $path){Write-JsonFileAtomic $path @{failures=0;next_attempt_at=$null;state='VERIFIED_HEALTHY';authority='RAIOS-C5';canonical_head=$Head}}
        }
    }
    $coreServiceKeys=@('C5','MANAGER','EVOLUTION','COMMAND_CENTER','UNIVERSAL_MCP','NATIVE_MCP_TUNNEL','ROUTER_9','NATS')
    $localReady = -not [bool](@($coreServiceKeys|Where-Object{-not [bool]$services[$_]}).Count)

    # Recovery attempts are provisional evidence. Once the corresponding live
    # service is independently verified healthy in this same cycle, retire only
    # that service's transient recovery error; never let a failed attempt
    # override stronger final health truth.
    if($services.MANAGER -and $services.EVOLUTION){
        for($i=$errors.Count-1;$i-ge 0;$i--){
            if([string]$errors[$i] -like 'COGNITIVE_LOOP_RESTORE_FAILED:*'){
                $errors.RemoveAt($i)
                $actions.Add('CLEAR_TRANSIENT_COGNITIVE_RECOVERY_ERROR_AFTER_VERIFIED_HEALTH')
            }
        }
        for($i=$warnings.Count-1;$i-ge 0;$i--){
            if([string]$warnings[$i] -eq 'COGNITIVE_PRIORITY0_RECOVERY_PARTIAL'){
                $warnings.RemoveAt($i)
                $actions.Add('CLEAR_TRANSIENT_COGNITIVE_RECOVERY_WARNING_AFTER_VERIFIED_HEALTH')
            }
        }
    }
    if($services.C5){
        for($i=$errors.Count-1;$i-ge 0;$i--){
            if([string]$errors[$i] -like 'C5_SERVICE_RESTORE_FAILED:*'){
                $errors.RemoveAt($i)
                $actions.Add('CLEAR_TRANSIENT_C5_RECOVERY_ERROR_AFTER_VERIFIED_HEALTH')
            }
        }
    }

    if($localReady){Mark-Phase "SERVICES_OK"}else{Mark-Phase "SERVICES_DEGRADED"}
    if ($resumeEligible -and $localReady -and $errors.Count -eq 0) {
        $PythonWindowless = Join-Path $StableUserProfile ".raios\runtime\c5\.venv\Scripts\pythonw.exe"
        if (Test-Path -LiteralPath $PythonWindowless) {
            $env:PYTHONPATH = Join-Path $Repo "src"
            Start-Process -FilePath $PythonWindowless -ArgumentList @("-m","raios.manager.live_manager","--refresh-resources") -WorkingDirectory $Repo -WindowStyle Hidden | Out-Null
            $actions.Add("NETWORK_RESUME_RESOURCES")
            $resumeTriggered = $true
            $resumeAt = [DateTimeOffset]::UtcNow.ToString("o")
        } else { $errors.Add("NETWORK_RESUME_PYTHONW_MISSING") }
    }
    Mark-Phase "BEFORE_NETWORK_STATE_WRITE"
    Write-JsonFileAtomic -Path $NetworkStatePath -Value @{
        schema = "raios.network-resume.v1"
        online = $internetOnline
        probe_ok = $internetProbe
        success_streak = $successStreak
        reconnect_detected = $reconnected
        resume_pending = [bool]($resumePending -and -not $resumeTriggered)
        remote_resume_pending = [bool]($remoteResumePending -and -not $resumeTriggered)
        resume_triggered = $resumeTriggered
        last_resume_at = $resumeAt
        last_remote_resume_proof_hash = $(if ($resumeTriggered -and $remoteResumePending) { $remoteProof } else { $previousRemoteProof })
        continuation_gate_open = $continuationGateOpen
        remote_transport_execution_allowed = $remoteTransportExecutionAllowed
        mutation_allowed = $mutationAllowed
        reconciliation_required = [bool]$transportContinuity.reconciliation_required
        checkpoint_nonblocking = $true
        transport_event = [string]$transportContinuity.event
        reconnect_checkpoint_path = $ReconnectCheckpointPath
        transport_continuity_path = $TransportContinuityPath
        cooldown_seconds = $NetworkResumeCooldownSeconds
        safe_jobs = @("RESOURCES")
        local_services_required = $true
        paid_resource_created = $false
        gpu_session_started = $false
        model_download_executed = $false
        canonical_mutation = $false
    }
    Mark-Phase "NETWORK_STATE_WRITTEN"
    $online = $localReady -and $errors.Count -eq 0
    # Read the single existing capability graph; do not spawn its ON_DEMAND or gated engines.
    $maintenanceContext=Get-RaiosMaintenanceContext -CanonicalRepo $Repo
    if($maintenanceContext.state -eq 'UNKNOWN'){Mark-Phase 'ENGINE_CONTEXT_UNKNOWN'}else{Mark-Phase 'ENGINE_CONTEXT_OBSERVED'}
    $resumeMonitorAfter = Invoke-RaiosResumeMonitor -CanonicalRepo $Repo -CommandCenterRuntime $CommandCenterRuntime -MonitorPath $ResumeMonitorPath
    if($resumeMonitorAfter.ok){Mark-Phase "RESUME_MONITOR_POST_PASS"}else{Mark-Phase ("RESUME_MONITOR_POST_"+[string]$resumeMonitorAfter.code)}
    Mark-Phase "BEFORE_STATUS_WRITE"
    Write-AtomicJson @{
        schema = "raios.continuity.status.v3"
        status = $(if ($online) { "ONLINE" } else { "DEGRADED" })
        control_authority = $ControlAuthority
        recovery_role = $RecoveryRole
        scheduler_authority = $false
        native_tunnel_launcher_authority = $false
        dcr_launcher_authority = $false
        canonical_head = $Head
        services = $services
        actions = @($actions)
        errors = @($errors)
        nonblocking_capability_warnings = @($warnings)
        core_health_ne_optional_seat_auth = $true
        task_name = $null
        task_reused = $false
        interval_seconds = $null
        invocation_model = "SCM_CHILD_BOUNDED"
        self_healing = $true
        recovery_cycle_budget_seconds = $script:recoveryCycleBudgetSeconds
        recovery_elapsed_seconds = [int]$script:recoveryCycleClock.Elapsed.TotalSeconds
        recovery_backoff_max_seconds = 900
        health_ne_child_exit_code = $true
        internet_online = $internetOnline
        remote_transport_online = [bool]$transportContinuity.transport_online
        remote_transport_execution_allowed = $remoteTransportExecutionAllowed
        reconciliation_required = [bool]$transportContinuity.reconciliation_required
        mutation_allowed = $mutationAllowed
        checkpoint_nonblocking = $true
        automatic_continuation = $(if ($continuationGateOpen) { "ALLOWED" } else { "BLOCKED" })
        reconnect_checkpoint_proof_hash = [string]$transportContinuity.checkpoint_proof_hash
        network_resume_triggered = $resumeTriggered
        network_state_path = $NetworkStatePath
        transport_continuity_path = $TransportContinuityPath
        reconnect_checkpoint_path = $ReconnectCheckpointPath
        maintenance_context = $maintenanceContext
        engine_context_ne_execution = $true
        resume_monitor_path = $ResumeMonitorPath
        resume_monitor_ok = [bool]$resumeMonitorAfter.ok
        resume_monitor_code = [string]$resumeMonitorAfter.code
        resume_monitor_authority = $false
        resume_dont_rediscover = $true
        auto_canonical_mutation = $false
    }
    Mark-Phase "STATUS_WRITTEN"
    Write-Host ("RAIOS_CONTINUITY=" + $(if ($online) { "ONLINE" } else { "DEGRADED" }))
    Write-Host ("ACTIONS=" + (@($actions) -join ","))
    if (-not $online) { exit 2 }
} finally {
    Mark-Phase "FINALLY_ENTER"
    Exit-RaiosContinuityMutex $mutexHandle
    Mark-Phase "MUTEX_RELEASED"
    if (-not $scriptExitEmitted) {
        Mark-Phase "SCRIPT_EXIT"
        $scriptExitEmitted = $true
    }
}
if (-not $scriptExitEmitted) { Mark-Phase "SCRIPT_EXIT" }
exit 0
}