param(
 [Parameter(Mandatory=$true)][string]$TaskId,
 [Parameter(Mandatory=$true)][ValidateSet('C1_APPROVED')][string]$ExplicitC1Approval,
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
$Python=Join-Path $RealHome '.raios\runtime\c5\.venv\Scripts\python.exe'
if(-not(Test-Path $Python)){throw 'CANONICAL_PYTHON_MISSING'}
$Gate=Join-Path $Repo 'scripts\ai-os\raios_change_gate.py'
$DiffSha=(& $Python $Gate hash).Trim()
if(-not $DiffSha){throw 'STAGED_DIFF_HASH_FAILED'}
$Root=Join-Path $RealHome '.raios\runtime\change-authority'
New-Item -ItemType Directory -Force $Root|Out-Null
$LeasePath=Join-Path $Root 'active-change.json'
if(-not(Test-Path $LeasePath)){throw 'CANONICAL_CHANGE_LEASE_REQUIRED'}
$Lease=Get-Content $LeasePath -Raw|ConvertFrom-Json
if($Lease.authority -ne 'C1' -or $Lease.task_id -ne $TaskId -or $Lease.base_head -ne $Head){throw 'CANONICAL_CHANGE_LEASE_MISMATCH'}
try{$LeaseExpiry=[DateTimeOffset]::Parse([string]$Lease.expires_at)}catch{throw 'CANONICAL_CHANGE_LEASE_EXPIRY_INVALID'}
if($LeaseExpiry -le [DateTimeOffset]::UtcNow){throw 'CANONICAL_CHANGE_LEASE_EXPIRED'}
$Expires=[DateTimeOffset]::UtcNow.AddMinutes($ValidityMinutes).ToString('o')
$Receipt=[ordered]@{
 schema='raios.canonical-change-approval.v1'
 authority='C1'
 decision='APPROVED'
 canonical_branch=$Branch
 base_head=$Head
 staged_diff_sha256=$DiffSha
 task_id=$TaskId
 approved_at=[DateTimeOffset]::UtcNow.ToString('o')
 expires_at=$Expires
 scope='EXACT_STAGED_DIFF_ONLY'
 reusable=$false
 explicit_c1_approval=$true
}
$ApprovalId=[guid]::NewGuid().ToString('N')
$Receipt.approval_id=$ApprovalId
$Path=Join-Path $Root 'current-approval.json'
$Receipt|ConvertTo-Json -Depth 5|Set-Content $Path -Encoding UTF8
$Lease.staged_diff_sha256=$DiffSha;$Lease.approval_id=$ApprovalId
$Lease|ConvertTo-Json -Depth 5|Set-Content $LeasePath -Encoding UTF8
Write-Host 'C1_CHANGE_APPROVAL_CREATED=true'
Write-Host "TASK_ID=$TaskId"
Write-Host "BASE_HEAD=$Head"
Write-Host "STAGED_DIFF_SHA256=$DiffSha"
Write-Host "EXPIRES_AT=$Expires"
Write-Host "APPROVAL_PATH=$Path"
