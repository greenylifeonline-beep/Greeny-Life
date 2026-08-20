#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Content-addressed barn compression. Deletes hash-duplicates of keepers and listed obsolete trees.
# Unique non-keeper source is listed, not deleted.

$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Repo

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Get-Rel([string]$Path) {
    return ($Path.Substring($Repo.Length).TrimStart("\", "/")).Replace("\", "/")
}

$ReceiptDir = Join-Path $Repo ".ai-os\reports\estate-gc"
New-Item -ItemType Directory -Force -Path $ReceiptDir | Out-Null

$Tag = "safety/pre-consolidation-$(git rev-parse --short HEAD)"
$existing = git tag --list $Tag
if (-not $existing) {
    git tag $Tag
}

$KeeperRoots = @(
    "canonical", "lib", "app", "src", "tests", "prisma", "scripts",
    "RAIOS\V9", ".ai-os", "greenlines_brain", "configs"
)

$SkipDir = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
@(
    ".git", "node_modules", ".next", ".venv", "venv", "site-packages",
    "__pycache__", ".venv-multimodal"
) | ForEach-Object { [void]$SkipDir.Add($_) }

$KeeperHashes = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($root in $KeeperRoots) {
    $full = Join-Path $Repo $root
    if (-not (Test-Path $full)) { continue }
    Get-ChildItem -LiteralPath $full -Recurse -File -Force -ErrorAction SilentlyContinue |
        Where-Object {
            $parts = $_.FullName.Substring($Repo.Length).Split([char[]]@("\", "/"), [System.StringSplitOptions]::RemoveEmptyEntries)
            -not ($parts | Where-Object { $SkipDir.Contains($_) })
        } |
        ForEach-Object { [void]$KeeperHashes.Add((Get-Sha256 $_.FullName)) }
}

$BarnRoots = @(
    "_raios-kaggle-census",
    "RAIOS-GREENY-DEEP-EVIDENCE",
    "RAIOS-CONTINUITY-EVIDENCE",
    "RAIOS-CAPABILITY-BRIDGE",
    "RAIOS-MISSION-PACKAGE",
    "archive\retired-worktree-preservation",
    "_raios-engine-deep-audit",
    "_raios-innovation-recon",
    "_raios-wave2-semantic-capability-classifier",
    "_raios-wave2-post-retirement",
    "_raios-legacy-global-forensics",
    "_raios-worktree-salvage",
    "_raios-cursor-recovery-audit",
    "_raios-old-business-salvage\shadow",
    "_raios-communication-fabric\.venv-multimodal"
)

$WholeDelete = @(
    "RAIOS-GREENY-DEEP-EVIDENCE.zip",
    "RAIOS-GREENY-CONTINUITY-EVIDENCE.zip",
    "RAIOS-GREENY-CAPABILITY-BRIDGE.zip",
    "RAIOS-GREENY-MISSION-PACKAGE.zip",
    "RAIOS-MISSION-PACKAGE.zip",
    "E3-SOURCE-TRACE-PACKAGE.zip",
    "GreenyLifeEOS_Review.zip"
)

$ObsoleteFiles = @(
    "canonical\intelligence\intelligence\intelligence-test.ts",
    "canonical\intelligence\intelligence\gl-dos.ts",
    "archive\duplicates\route.ts",
    "archive\historical\__tests__\workflowEngine.test.ts",
    "archive\historical\intelligence\intelligence\core\engine-registry.ts"
)

$deleted = New-Object System.Collections.Generic.List[object]
$uniqueKept = New-Object System.Collections.Generic.List[object]
$deletedBytes = [int64]0

function Remove-TrackedOrNot([string]$Rel) {
    $full = Join-Path $Repo $Rel
    if (-not (Test-Path -LiteralPath $full)) { return }
    $size = (Get-Item -LiteralPath $full).Length
    $sha = if ((Get-Item -LiteralPath $full).PSIsContainer) { $null } else { Get-Sha256 $full }
    Remove-Item -LiteralPath $full -Force -Recurse
    $script:deletedBytes += $size
    $deleted.Add([pscustomobject]@{ path = $Rel.Replace("\", "/"); sha256 = $sha; bytes = $size })
}

foreach ($rel in $ObsoleteFiles) { Remove-TrackedOrNot $rel }
foreach ($rel in $WholeDelete) { Remove-TrackedOrNot $rel }

foreach ($root in $BarnRoots) {
    $full = Join-Path $Repo $root
    if (-not (Test-Path $full)) { continue }
    Get-ChildItem -LiteralPath $full -Recurse -File -Force -ErrorAction SilentlyContinue | ForEach-Object {
        $rel = Get-Rel $_.FullName
        $sha = Get-Sha256 $_.FullName
        $ext = $_.Extension.ToLowerInvariant()
        $isSource = $ext -in ".ts", ".tsx", ".py", ".js"
        if ($KeeperHashes.Contains($sha)) {
            $deletedBytes += $_.Length
            Remove-Item -LiteralPath $_.FullName -Force
            $deleted.Add([pscustomobject]@{ path = $rel; sha256 = $sha; bytes = $_.Length; reason = "BYTE_IDENTICAL_KEEPER" })
        }
        elseif ($isSource -and $_.Length -ge 2048) {
            $uniqueKept.Add([pscustomobject]@{ path = $rel; sha256 = $sha; bytes = $_.Length; reason = "UNIQUE_SOURCE_NOT_DELETED" })
        }
        else {
            $deletedBytes += $_.Length
            Remove-Item -LiteralPath $_.FullName -Force
            $deleted.Add([pscustomobject]@{ path = $rel; sha256 = $sha; bytes = $_.Length; reason = "GENERATED_OR_NONSOURCE_BARN" })
        }
    }
    Get-ChildItem -LiteralPath $full -Recurse -Directory -Force -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending |
        ForEach-Object {
            if (-not (Get-ChildItem -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue)) {
                Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
            }
        }
}

$KeepProtect = "canonical/|lib/|app/|src/raios/|RAIOS/V9/|tests/|prisma/|\.ai-os/"
$Needles = @(
    "intelligence-test",
    "duplicate-engine-v2",
    "archive/duplicates/route",
    "_raios-kaggle-census",
    "RAIOS-GREENY-DEEP-EVIDENCE",
    ".venv-multimodal"
)
$dangling = @()
foreach ($needle in $Needles) {
    $hits = rg -l --hidden -g "!node_modules" -g "!.git" -g "!.next" $needle $Repo 2>$null
    if ($hits) {
        $dangling += $hits | ForEach-Object { $_.Replace($Repo + "\", "").Replace("\", "/") } |
            Where-Object { $_ -notmatch $KeepProtect -or $needle -eq "duplicate-engine-v2" }
    }
}

$tc = $null
$canon = $null
$orch = $null
try { npm run type-check --silent; $tc = $LASTEXITCODE } catch { $tc = 1 }
try { npx --yes tsx tests/canonical_intelligence_check.ts; $canon = $LASTEXITCODE } catch { $canon = 1 }
try { npx --yes tsx tests/task_orchestration_check.ts; $orch = $LASTEXITCODE } catch { $orch = 1 }

$receipt = [ordered]@{
    schema = "raios.estate-hash-gc.v1"
    repo = $Repo
    tag = $Tag
    head = (git rev-parse HEAD)
    deleted_files = $deleted.Count
    deleted_bytes = $deletedBytes
    unique_kept = $uniqueKept.Count
    dangling_count = @($dangling | Select-Object -Unique).Count
    typecheck_exit = $tc
    test_canonical_exit = $canon
    test_orch_exit = $orch
    deleted = $deleted
    unique_source_not_deleted = $uniqueKept
    dangling = @($dangling | Select-Object -Unique)
}
$receiptPath = Join-Path $ReceiptDir "ESTATE-HASH-GC.json"
$receipt | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
$receiptSha = Get-Sha256 $receiptPath

Write-Output "GC_EXIT=0"
Write-Output "TAG=$Tag"
Write-Output "DELETED_FILES=$($deleted.Count)"
Write-Output "DELETED_BYTES=$deletedBytes"
Write-Output "UNIQUE_KEPT=$($uniqueKept.Count)"
Write-Output "DANGLING_COUNT=$(@($dangling | Select-Object -Unique).Count)"
Write-Output "TYPECHECK_EXIT=$tc"
Write-Output "TEST_CANONICAL_EXIT=$canon"
Write-Output "TEST_ORCH_EXIT=$orch"
Write-Output "RECEIPT_PATH=$receiptPath"
Write-Output "RECEIPT_SHA256=$receiptSha"
exit 0
