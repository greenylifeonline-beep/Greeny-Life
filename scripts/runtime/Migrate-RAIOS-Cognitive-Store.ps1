[CmdletBinding()]
param(
    [string]$Repo = "",
    [string]$Store = (Join-Path $HOME ".raios\runtime\cognitive-store\v9"),
    [switch]$ExecuteCleanup
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if (-not $Repo) { $Repo = Join-Path $PSScriptRoot "..\.." }
$Repo = (Resolve-Path $Repo).Path
$V9 = Join-Path $Repo "RAIOS\V9"
$Store = [IO.Path]::GetFullPath($Store)
$Roots = @(
    "wal",
    "runtime/event-state",
    "experience/automatic-a4",
    "performance/a4",
    "evidence/events",
    "failures/a4",
    "skills/candidates-a4",
    "evolution/a5"
)
$GeneratedRoots = @(
    "RAIOS/V9/experience/automatic-a4/",
    "RAIOS/V9/performance/a4/",
    "RAIOS/V9/evidence/events/",
    "RAIOS/V9/failures/a4/",
    "RAIOS/V9/skills/candidates-a4/",
    "RAIOS/V9/evolution/a5/experience-patterns/",
    "RAIOS/V9/evolution/a5/failure-families/"
)
$Stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$ArchiveRoot = Join-Path $HOME ".raios\archive\cognitive-store-migration\$Stamp"
$Archive = Join-Path $ArchiveRoot "repo-cognitive-store-before-migration.zip"
New-Item -ItemType Directory -Force -Path $ArchiveRoot, $Store | Out-Null

function Get-SourceManifest {
    param([string]$Base, [string[]]$RelativeRoots)
    $rows = foreach ($root in $RelativeRoots) {
        $absolute = Join-Path $Base ($root -replace "/", "\")
        if (-not (Test-Path -LiteralPath $absolute)) { continue }
        $basePrefix = $Base.TrimEnd("\") + "\"
        Get-ChildItem -LiteralPath $absolute -File -Recurse | ForEach-Object {
            $relative = $_.FullName.Substring($basePrefix.Length).Replace("\", "/")
            [pscustomobject]@{
                relative_path = $relative
                bytes = $_.Length
                sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            }
        }
    }
    return @($rows | Sort-Object relative_path)
}

$SourceManifest = Get-SourceManifest -Base $V9 -RelativeRoots $Roots
if ($SourceManifest.Count -eq 0) { throw "COGNITIVE_SOURCE_EMPTY" }
$SourceManifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $ArchiveRoot "source-manifest.json") -Encoding utf8
Push-Location $V9
try {
    & tar.exe -a -c -f $Archive @Roots
    if ($LASTEXITCODE -ne 0) { throw "ARCHIVE_CREATE_FAILED:$LASTEXITCODE" }
} finally {
    Pop-Location
}
$ArchiveHash = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath "$Archive.sha256" -Value "$ArchiveHash  $([IO.Path]::GetFileName($Archive))" -Encoding ascii

foreach ($row in $SourceManifest) {
    $source = Join-Path $V9 ($row.relative_path -replace "/", "\")
    $target = Join-Path $Store ($row.relative_path -replace "/", "\")
    New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
    Copy-Item -LiteralPath $source -Destination $target -Force
}

$Mismatches = foreach ($row in $SourceManifest) {
    $target = Join-Path $Store ($row.relative_path -replace "/", "\")
    if (-not (Test-Path -LiteralPath $target)) {
        [pscustomobject]@{ path = $row.relative_path; reason = "MISSING" }
        continue
    }
    $hash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($hash -ne $row.sha256) {
        [pscustomobject]@{ path = $row.relative_path; reason = "HASH_MISMATCH" }
    }
}
$Mismatches = @($Mismatches)
if ($Mismatches.Count) {
    $Mismatches | ConvertTo-Json | Set-Content (Join-Path $ArchiveRoot "mismatches.json")
    throw "COGNITIVE_COPY_VERIFICATION_FAILED:$($Mismatches.Count)"
}
$Removed = @()
if ($ExecuteCleanup) {
    $pathSpecs = $GeneratedRoots | ForEach-Object { "$_*" }
    $untracked = @(& git -C $Repo ls-files --others --exclude-standard -- @pathSpecs)
    if ($LASTEXITCODE -ne 0) { throw "GIT_UNTRACKED_DISCOVERY_FAILED" }
    foreach ($relative in $untracked) {
        $normalized = $relative.Replace("\", "/")
        $allowed = $false
        foreach ($root in $GeneratedRoots) {
            if ($normalized.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {
                $allowed = $true
                break
            }
        }
        if (-not $allowed) { throw "CLEANUP_SCOPE_VIOLATION:$normalized" }
        $absolute = Join-Path $Repo ($normalized -replace "/", "\")
        Remove-Item -LiteralPath $absolute -Force
        $Removed += $normalized
    }
    $Removed | Set-Content -LiteralPath (Join-Path $ArchiveRoot "removed-untracked-files.txt") -Encoding utf8
}

$Report = [ordered]@{
    schema = "raios.cognitive-store-migration.v1"
    completed_at = (Get-Date).ToUniversalTime().ToString("o")
    source_root = $V9
    target_root = $Store
    source_files_verified = $SourceManifest.Count
    archive = $Archive
    archive_sha256 = $ArchiveHash
    archive_bytes = (Get-Item -LiteralPath $Archive).Length
    removed_untracked_files = $Removed.Count
    cleanup_executed = [bool]$ExecuteCleanup
    status = "PASS"
}
$ReportPath = Join-Path $ArchiveRoot "MIGRATION-REPORT.json"
$Report | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $ReportPath -Encoding utf8
$Report | ConvertTo-Json -Depth 4
