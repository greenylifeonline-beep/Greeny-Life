param([string]$Repo="")
$ErrorActionPreference='Stop'
if(-not $Repo){$Repo=(Resolve-Path(Join-Path $PSScriptRoot '..\..')).Path}
$Repo=(Resolve-Path $Repo).Path
Set-Location $Repo
$Canonical='ai-evolution-202608051809'
$Current=(git rev-parse --abbrev-ref HEAD).Trim()
if($Current -ne $Canonical){throw "NONCANONICAL_BRANCH:$Current"}
$WorktreeCount=@(git worktree list --porcelain | Where-Object {$_ -like 'worktree *'}).Count
if($WorktreeCount -ne 1){throw "MULTIPLE_WORKTREES:$WorktreeCount"}
$RealHome=$HOME
if($Repo -match '^(?<h>[A-Za-z]:\\Users\\[^\\]+)\\'){$RealHome=$Matches.h}
git config --local raios.home $RealHome
git config --local core.hooksPath .githooks
git config --local push.default nothing
git config --local remote.origin.push "refs/heads/$Canonical:refs/heads/$Canonical"
git config --local branch.autoSetupMerge false
git remote set-head origin $Canonical
$Python=Join-Path $RealHome '.raios\runtime\c5\.venv\Scripts\python.exe'
if(-not(Test-Path $Python)){throw 'CANONICAL_PYTHON_MISSING'}
& $Python scripts\ai-os\raios_change_gate.py status
if($LASTEXITCODE -ne 0){throw 'CHANGE_GATE_STATUS_FAILED'}
Write-Host 'RAIOS_CHANGE_GATE_INSTALLED=true'
Write-Host "CANONICAL_BRANCH=$Canonical"
Write-Host 'ONLY_CANONICAL_PUSH_REF=true'
Write-Host 'NEW_WORKTREE_ALLOWED=false'
Write-Host 'NONCANONICAL_COMMIT_ALLOWED=false'
Write-Host 'C1_APPROVAL_RECEIPT_REQUIRED=true'
