param(
 [string]$Repo = $(if($env:RAIOS_CANONICAL_REPO){$env:RAIOS_CANONICAL_REPO}else{(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path}),
 [string]$RaiosUserProfile = $(if($env:RAIOS_USER_PROFILE){$env:RAIOS_USER_PROFILE}else{Split-Path (Split-Path (Split-Path $Repo))})
)
$ErrorActionPreference='Stop'
if(-not(Test-Path -LiteralPath $RaiosUserProfile)){throw "RAIOS_USER_PROFILE_MISSING:$RaiosUserProfile"}
$Runtime=Join-Path $RaiosUserProfile '.raios\runtime\continuity'
$Source=Join-Path $Repo 'scripts\runtime\continuity'
$C5Source=Join-Path $Repo 'scripts\runtime\c5-service\Invoke-RAIOS-C5-UserLane.ps1'
$C5Target=Join-Path $Runtime 'c5-service\Invoke-RAIOS-C5-UserLane.ps1'
$Receipt=Join-Path $Runtime 'c5-service\continuity-install-receipt.json'

function Copy-IfChanged([string]$SourcePath,[string]$TargetPath){
 if(-not(Test-Path -LiteralPath $SourcePath)){throw "SOURCE_MISSING:$SourcePath"}
 $same=$false
 if(Test-Path -LiteralPath $TargetPath){
  try{$same=((Get-FileHash -Algorithm SHA256 -LiteralPath $SourcePath).Hash -eq (Get-FileHash -Algorithm SHA256 -LiteralPath $TargetPath).Hash)}catch{$same=$false}
 }
 if($same){return [pscustomobject]@{path=$TargetPath;changed=$false;sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $TargetPath).Hash}}
 $dir=Split-Path $TargetPath
 New-Item -ItemType Directory -Path $dir -Force|Out-Null
 $tmp=$TargetPath+'.tmp-'+[guid]::NewGuid().ToString('N')
 Copy-Item -LiteralPath $SourcePath -Destination $tmp -Force
 Move-Item -LiteralPath $tmp -Destination $TargetPath -Force
 return [pscustomobject]@{path=$TargetPath;changed=$true;sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $TargetPath).Hash}
}

$results=@()
$results+=Copy-IfChanged (Join-Path $Source 'raios_reconnect_checkpoint.py') (Join-Path $Runtime 'raios_reconnect_checkpoint.py')
$results+=Copy-IfChanged (Join-Path $Source 'reap_stale_rdc_sessions.py') (Join-Path $Runtime 'reap_stale_rdc_sessions.py')
$results+=Copy-IfChanged $C5Source $C5Target
$record=[ordered]@{
 schema='raios.c5.continuity.install.v1'
 observed_at=[DateTimeOffset]::UtcNow.ToString('o')
 authority='RAIOS-C5'
 canonical_repo=$Repo
 source='scripts/runtime'
 second_runtime=$false
 results=$results
}
$tmpReceipt=$Receipt+'.tmp-'+[guid]::NewGuid().ToString('N')
$record|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $tmpReceipt -Encoding UTF8
Move-Item -LiteralPath $tmpReceipt -Destination $Receipt -Force
$record|ConvertTo-Json -Depth 6
