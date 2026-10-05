$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
Add-Type -AssemblyName System.Security

$Root='C:\Users\Ghanam\.raios\runtime\mcp-tunnel'
$Repo='C:\Users\Ghanam\Documents\Codex\Greeny-Life'
$Client=Join-Path $Root 'bin\tunnel-client.exe'
$ProfileDir=Join-Path $Root 'profiles'
$MachineSecret=Join-Path $Root 'secrets\control-plane-api-key.machine.dpapi'
$TokenStore=Join-Path $Repo '.ai-os\mcp\tokens.local.json'
$HealthFile='C:\Users\Ghanam\.local\state\tunnel-client\health\raios-native.url'
$OwnerFile=Join-Path $Root 'health\raios-native.owner.json'
$MutexName='Global\RAIOS_NATIVE_MCP_TUNNEL_OWNER_V1'

function Test-LocalMcpReady {
 try {
  . (Join-Path $Repo 'scripts\ai-os\raios_mcp\Readiness.ps1')
  $health=Invoke-RestMethod -Uri 'http://127.0.0.1:8788/health' -TimeoutSec 3
  return (Test-RaiosMcpHealth -Health $health -PolicyPath (Join-Path $Repo '.ai-os\mcp\POLICY.json'))
 } catch {return $false}
}

function Test-TransportAlive {
 if(-not(Test-Path -LiteralPath $HealthFile)){return $false}
 try{
  $u=(Get-Content -LiteralPath $HealthFile -Raw).Trim()
  if($u -notmatch '^http://127\.0\.0\.1:\d+$'){return $false}
 }catch{return $false}
 foreach($suffix in @('/metrics','/readyz')){
  try{
   $r=Invoke-WebRequest -UseBasicParsing -Uri ($u+$suffix) -TimeoutSec 2
   if($r.StatusCode -eq 200){return $true}
  }catch{}
 }
 return $false
}

function Write-OwnerState([int]$ChildPid,[bool]$TransportAlive,[bool]$BackendReady){
 try{$servicePid=[int]$env:RAIOS_NATIVE_TUNNEL_OWNER_PID}catch{$servicePid=0}
 $o=[ordered]@{
  schema='raios.native-tunnel-owner.v1'
  observed_at=[DateTimeOffset]::UtcNow.ToString('o')
  authority='RAIOS-C5-SCM'
  service_pid=$servicePid
  launcher_pid=$PID
  child_pid=$ChildPid
  transport_alive=$TransportAlive
  backend_ready=$BackendReady
 }
 [IO.Directory]::CreateDirectory((Split-Path $OwnerFile))|Out-Null
 $o|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $OwnerFile -Encoding UTF8
}

function Test-Ready {
 if(-not(Test-LocalMcpReady)){return $false}
 if(-not(Test-Path -LiteralPath $HealthFile)){return $false}
 try{
  $u=(Get-Content -LiteralPath $HealthFile -Raw).Trim()
  if($u -notmatch '^http://127\.0\.0\.1:\d+$'){return $false}
 }catch{return $false}

 # Prefer the tunnel client's full readiness gate, but do not kill a valid
 # RAIOS transport merely because optional OAuth discovery is degraded.
 try{
  $r=Invoke-WebRequest -UseBasicParsing -Uri ($u+'/readyz') -TimeoutSec 2
  if($r.StatusCode -eq 200 -and $r.Content.Trim().StartsWith('ready',[StringComparison]::OrdinalIgnoreCase)){return $true}
 }catch{}

 # /metrics proves the tunnel runtime/admin plane is alive. Combined with the
 # canonical MCP health contract above, this is sufficient for Native RAIOS.
 try{
  $r=Invoke-WebRequest -UseBasicParsing -Uri ($u+'/metrics') -TimeoutSec 2
  return ($r.StatusCode -eq 200)
 }catch{return $false}
}

if(-not(Test-Path -LiteralPath $Client)){throw 'TUNNEL_CLIENT_MISSING'}
if(-not(Test-Path -LiteralPath $MachineSecret)){throw 'MACHINE_DPAPI_SECRET_MISSING'}
if(-not(Test-Path -LiteralPath $TokenStore)){throw 'RAIOS_TOKEN_STORE_MISSING'}

$mutex=[Threading.Mutex]::new($false,$MutexName)
$owns=$false
$cipher=$null
$plainBytes=$null
$apiKey=$null
$p=$null
try{
 try{$owns=$mutex.WaitOne(0,$false)}catch [Threading.AbandonedMutexException]{$owns=$true}
 if(-not $owns){
  Write-Host 'NATIVE_TUNNEL_SINGLETON_OWNER_EXISTS=true'
  exit 23
 }

 $tokens=Get-Content -LiteralPath $TokenStore -Raw|ConvertFrom-Json
 $c1=@($tokens.actors|Where-Object{[string]$_.actor_id -eq 'C1'})|Select-Object -First 1
 if(-not $c1 -or [string]::IsNullOrWhiteSpace([string]$c1.token)){throw 'C1_TOKEN_GRANT_MISSING'}

 $cipher=[IO.File]::ReadAllBytes($MachineSecret)
 $plainBytes=[Security.Cryptography.ProtectedData]::Unprotect($cipher,$null,[Security.Cryptography.DataProtectionScope]::LocalMachine)
 $apiKey=[Text.Encoding]::UTF8.GetString($plainBytes)
 if([string]::IsNullOrWhiteSpace($apiKey)){throw 'MACHINE_DPAPI_DECRYPT_EMPTY'}

 $env:CONTROL_PLANE_API_KEY=$apiKey
 $env:RAIOS_MCP_C1_TOKEN=[string]$c1.token
 $env:RAIOS_NATIVE_TUNNEL_AUTHORITY='RAIOS-C5-SCM'
 New-Item -ItemType Directory -Path (Split-Path $OwnerFile) -Force|Out-Null
 # Owner/health files are projections. Never delete them during bootstrap:
 # publish fresh truth over them when the new generation is ready. This avoids
 # destructive gaps and Windows file-lock races during generation handoff.
 $p=Start-Process -FilePath $Client -ArgumentList @('run','--profile-dir',$ProfileDir,'--profile','raios-native') -WorkingDirectory $Root -WindowStyle Hidden -PassThru
 Write-Host ('NATIVE_TUNNEL_CHILD_PID='+$p.Id)
 Write-OwnerState -ChildPid $p.Id -TransportAlive $false -BackendReady $false

 $transportAlive=$false
 for($i=0;$i-lt 45;$i++){
  try{$p.Refresh()}catch{}
  if($p.HasExited){throw ('NATIVE_TUNNEL_CHILD_EARLY_EXIT:'+ $p.ExitCode)}
  if(Test-TransportAlive){$transportAlive=$true;break}
  Start-Sleep -Seconds 1
 }
 if(-not $transportAlive){
  try{Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue}catch{}
  throw 'NATIVE_TUNNEL_TRANSPORT_TIMEOUT'
 }

 $backendReady=Test-Ready
 Write-OwnerState -ChildPid $p.Id -TransportAlive $true -BackendReady $backendReady
 Write-Host 'NATIVE_TUNNEL_TRANSPORT_ALIVE=true'
 Write-Host ('NATIVE_TUNNEL_BACKEND_READY='+$backendReady)
 Write-Host 'NATIVE_TUNNEL_AUTHORITY=RAIOS-C5-SCM'
 while($true){
  Start-Sleep -Seconds 2
  try{$p.Refresh()}catch{}
  if($p.HasExited){throw ('NATIVE_TUNNEL_CHILD_EXIT:'+ $p.ExitCode)}
  $backendReady=Test-Ready
  Write-OwnerState -ChildPid $p.Id -TransportAlive $true -BackendReady $backendReady
 }
}
finally{
 Remove-Item Env:CONTROL_PLANE_API_KEY -ErrorAction SilentlyContinue
 Remove-Item Env:RAIOS_MCP_C1_TOKEN -ErrorAction SilentlyContinue
 Remove-Item Env:RAIOS_NATIVE_TUNNEL_AUTHORITY -ErrorAction SilentlyContinue
 Remove-Item Env:RAIOS_NATIVE_TUNNEL_OWNER_PID -ErrorAction SilentlyContinue
 try{
  if(Test-Path -LiteralPath $OwnerFile){
   $current=Get-Content -LiteralPath $OwnerFile -Raw|ConvertFrom-Json
   $childAlive=$false
   try{
    $childPid=[int]$current.child_pid
    $childAlive=[bool](Get-Process -Id $childPid -ErrorAction SilentlyContinue)
   }catch{$childAlive=$false}
   if([int]$current.launcher_pid -eq $PID -and -not $childAlive){
    Remove-Item -LiteralPath $OwnerFile -Force -ErrorAction SilentlyContinue
   }
  }
 }catch{}
 if($plainBytes){[Array]::Clear($plainBytes,0,$plainBytes.Length)}
 if($cipher){[Array]::Clear($cipher,0,$cipher.Length)}
 $apiKey=$null
 if($owns){try{$mutex.ReleaseMutex()}catch{}}
 $mutex.Dispose()
}
