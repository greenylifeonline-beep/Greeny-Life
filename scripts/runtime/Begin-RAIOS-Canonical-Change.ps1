param(
 [Parameter(Mandatory=$true)][string]$TaskId,
 [Parameter(Mandatory=$true)][ValidateSet('C1_CONTROL')][string]$ExplicitC1Control,
 [int]$ValidityMinutes=30,
 [string]$Repo=""
)
$ErrorActionPreference='Stop'
if(-not $Repo){$Repo=(Resolve-Path(Join-Path $PSScriptRoot '..\..')).Path}
$Repo=(Resolve-Path $Repo).Path
Set-Location $Repo
$Branch=(git rev-parse --abbrev-ref HEAD).Trim()
if($Branch -ne 'ai-evolution-202608051809'){throw 'NONCANONICAL_BRANCH'}
$Head=(git rev-parse HEAD).Trim()
$RealHome=(git config --get raios.home).Trim()
if(-not $RealHome){$RealHome=$HOME}
$Root=Join-Path $RealHome '.raios\runtime\change-authority'
New-Item -ItemType Directory -Force $Root|Out-Null
$LeasePath=Join-Path $Root 'active-change.json'
$Now=[DateTimeOffset]::UtcNow
if(Test-Path $LeasePath){
 try{$Existing=Get-Content $LeasePath -Raw|ConvertFrom-Json}catch{$Existing=$null}
 if($Existing -and $Existing.expires_at){
  try{$Expiry=[DateTimeOffset]::Parse([string]$Existing.expires_at)}catch{$Expiry=$Now.AddSeconds(-1)}
  if($Expiry -gt $Now){
   if($Existing.task_id -eq $TaskId -and $Existing.base_head -eq $Head){
    Write-Host 'CANONICAL_CHANGE_LEASE=ALREADY_HELD';Write-Host "LEASE_PATH=$LeasePath";exit 0
   }
   throw "CANONICAL_CHANGE_LEASE_HELD::$($Existing.task_id)::$($Existing.base_head)"
  }
 }
 Remove-Item $LeasePath -Force -ErrorAction SilentlyContinue
}
$Lease=[ordered]@{
 schema='raios.canonical-change-lease.v1';authority='C1';task_id=$TaskId
 canonical_branch=$Branch;base_head=$Head;device=[Environment]::MachineName
 acquired_at=$Now.ToString('o');expires_at=$Now.AddMinutes($ValidityMinutes).ToString('o')
 staged_diff_sha256=$null;approval_id=$null
}
$Json=$Lease|ConvertTo-Json -Depth 5
try{
 $Stream=[IO.File]::Open($LeasePath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$Bytes=[Text.UTF8Encoding]::new($false).GetBytes($Json);$Stream.Write($Bytes,0,$Bytes.Length)}finally{$Stream.Dispose()}
}catch [IO.IOException]{throw 'CANONICAL_CHANGE_LEASE_RACE_LOST'}
Write-Host 'CANONICAL_CHANGE_LEASE=ACQUIRED'
Write-Host "TASK_ID=$TaskId"
Write-Host "BASE_HEAD=$Head"
Write-Host "LEASE_PATH=$LeasePath"