[CmdletBinding()]
param(
    [string]$Repo = "",
    [string]$Store = (Join-Path $HOME ".raios\runtime\cognitive-store\v9"),
    [string]$ArchiveBase = (Join-Path $HOME ".raios\archive\cognitive-store-migration"),
    [string]$RunId = "",
    [int]$BatchSize = 250,
    [int]$MaxSeconds = 120,
    [switch]$Resume,
    [switch]$ExecuteCleanup
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if (-not $Repo) { $Repo = Join-Path $PSScriptRoot "..\.." }
$Repo = (Resolve-Path $Repo).Path
$V9 = Join-Path $Repo "RAIOS\V9"
$Store = [IO.Path]::GetFullPath($Store)
$ArchiveBase = [IO.Path]::GetFullPath($ArchiveBase)
if ($BatchSize -lt 1) { throw "INVALID_BATCH_SIZE" }
if ($MaxSeconds -lt 1) { throw "INVALID_MAX_SECONDS" }
$Roots = @("wal","runtime/event-state","experience/automatic-a4","performance/a4","evidence/events","failures/a4","skills/candidates-a4","evolution/a5")
$GeneratedRoots = @("RAIOS/V9/experience/automatic-a4/","RAIOS/V9/performance/a4/","RAIOS/V9/evidence/events/","RAIOS/V9/failures/a4/","RAIOS/V9/skills/candidates-a4/","RAIOS/V9/evolution/a5/experience-patterns/","RAIOS/V9/evolution/a5/failure-families/")
if (-not $RunId) { $RunId = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ") + "-" + ([guid]::NewGuid().ToString("N").Substring(0,8)) }
$RunRoot = Join-Path $ArchiveBase $RunId
$StageRoot = Join-Path $RunRoot "snapshot-stage"
$SnapshotPath = Join-Path $RunRoot "snapshot.json"
$LedgerPath = Join-Path $RunRoot "ledger.jsonl"
$ProgressPath = Join-Path $RunRoot "progress.json"
$PriorCachePath = Join-Path $RunRoot "prior-evidence.json"
$ReportPath = Join-Path $RunRoot "MIGRATION-REPORT.json"
$Archive = Join-Path $RunRoot "repo-cognitive-store-before-migration.zip"
New-Item -ItemType Directory -Force -Path $RunRoot,$StageRoot,$Store | Out-Null
function Write-JsonAtomic([string]$Path,$Value) {
    $tmp = "$Path.tmp-$PID"
    $Value | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $tmp -Encoding utf8
    Move-Item -LiteralPath $tmp -Destination $Path -Force
}
function Get-Sha256Hex([string]$Path) {
    $sha=[Security.Cryptography.SHA256]::Create()
    try {
        $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
        try { return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace("-","").ToLowerInvariant() } finally { $stream.Dispose() }
    } finally { $sha.Dispose() }
}
function Relative-To([string]$Base,[string]$Full) {
    $prefix=$Base.TrimEnd("\")+"\"
    return $Full.Substring($prefix.Length).Replace("\","/")
}
function Get-PriorEvidence {
    if([IO.File]::Exists($PriorCachePath)){
        try{
            $cache=Get-Content $PriorCachePath -Raw|ConvertFrom-Json
            if([IO.File]::Exists([string]$cache.archive) -and [IO.File]::Exists([string]$cache.manifest_path)){
                $fi=[IO.FileInfo]::new([string]$cache.archive);$fi.Refresh()
                if($fi.Length -eq [int64]$cache.archive_bytes -and $fi.LastWriteTimeUtc.ToString("o") -eq [string]$cache.archive_last_write_utc){
                    $rows=@(Get-Content ([string]$cache.manifest_path) -Raw|ConvertFrom-Json);$map=@{}
                    foreach($row in $rows){if($row.relative_path -and $row.sha256){$map[[string]$row.relative_path]=$row}}
                    if($map.Count){return [pscustomobject]@{manifest=$map;archive=[string]$cache.archive;archive_sha256=[string]$cache.archive_sha256;report=[string]$cache.report;manifest_path=[string]$cache.manifest_path;cache_hit=$true}}
                }
            }
        }catch{}
    }
    foreach($dir in (Get-ChildItem -LiteralPath $ArchiveBase -Directory -ErrorAction SilentlyContinue | Where-Object {$_.Name -ne $RunId} | Sort-Object LastWriteTimeUtc -Descending)){
        $reportPath=Join-Path $dir.FullName "MIGRATION-REPORT.json";$manifestPath=Join-Path $dir.FullName "source-manifest.json"
        if(-not([IO.File]::Exists($reportPath) -and [IO.File]::Exists($manifestPath))){continue}
        try{$report=Get-Content $reportPath -Raw|ConvertFrom-Json}catch{continue}
        if([string]$report.status -ne "PASS" -or [string]$report.schema -notin @("raios.cognitive-store-migration.v1","raios.cognitive-store-migration.v2") -or -not $report.archive_sha256 -or -not $report.archive){continue}
        $sourceRootProp=$report.PSObject.Properties["source_root"]
        if($sourceRootProp -and $sourceRootProp.Value -and ([IO.Path]::GetFullPath([string]$sourceRootProp.Value) -ne [IO.Path]::GetFullPath($V9))){continue}
        if(-not [IO.File]::Exists([string]$report.archive)){continue}
        $actualArchiveHash=Get-Sha256Hex ([string]$report.archive)
        if($actualArchiveHash -ne ([string]$report.archive_sha256).ToLowerInvariant()){continue}
        try{$rows=@(Get-Content $manifestPath -Raw|ConvertFrom-Json)}catch{continue}
        $map=@{};foreach($row in $rows){if($row.relative_path -and $row.sha256){$map[[string]$row.relative_path]=$row}}
        if($map.Count){
            $afi=[IO.FileInfo]::new([string]$report.archive);$afi.Refresh()
            Write-JsonAtomic $PriorCachePath ([ordered]@{archive=[string]$report.archive;archive_sha256=$actualArchiveHash;archive_bytes=$afi.Length;archive_last_write_utc=$afi.LastWriteTimeUtc.ToString("o");report=$reportPath;manifest_path=$manifestPath;verified_at=(Get-Date).ToUniversalTime().ToString("o")})
            return [pscustomobject]@{manifest=$map;archive=[string]$report.archive;archive_sha256=$actualArchiveHash;report=$reportPath;manifest_path=$manifestPath;cache_hit=$false}
        }
    }
    return $null
}
$PriorEvidence=Get-PriorEvidence
$Prior=@{}
if($PriorEvidence){$Prior=$PriorEvidence.manifest}
function New-Snapshot {
    $rows = [System.Collections.Generic.List[object]]::new()
    foreach($root in $Roots){
        $absolute=Join-Path $V9 ($root -replace "/","\")
        if(-not(Test-Path -LiteralPath $absolute)){continue}
        foreach($f in [IO.Directory]::EnumerateFiles($absolute,"*",[IO.SearchOption]::AllDirectories)){
            $i=[IO.FileInfo]::new($f)
            $rows.Add([pscustomobject]@{relative_path=(Relative-To $V9 $i.FullName);bytes=$i.Length;last_write_utc=$i.LastWriteTimeUtc.ToString("o")})
        }
    }
    $ordered=@($rows|Sort-Object relative_path)
    if($ordered.Count -eq 0){throw "COGNITIVE_SOURCE_EMPTY"}
    Write-JsonAtomic $SnapshotPath ([ordered]@{schema="raios.cognitive-snapshot.v2";created_at=(Get-Date).ToUniversalTime().ToString("o");source_root=$V9;files=$ordered})
    return $ordered
}
if($Resume){
    if(-not(Test-Path $SnapshotPath)){throw "RESUME_SNAPSHOT_MISSING:$RunId"}
    $Snapshot=@((Get-Content $SnapshotPath -Raw|ConvertFrom-Json).files)
}else{
    if(Test-Path $SnapshotPath){throw "RUN_ID_ALREADY_EXISTS:$RunId"}
    $Snapshot=New-Snapshot
}
$Ledger=@{}
if(Test-Path $LedgerPath){
    foreach($line in Get-Content $LedgerPath){if(-not $line.Trim()){continue};$r=$line|ConvertFrom-Json;$Ledger[[string]$r.relative_path]=$r}
}
$sw=[Diagnostics.Stopwatch]::StartNew();$processedThisRun=0;$drift=@();$failures=@()
$LedgerBuffer=[Collections.Generic.List[string]]::new()
function Flush-LedgerBuffer {
    if($LedgerBuffer.Count -eq 0){return}
    [IO.File]::AppendAllLines($LedgerPath,$LedgerBuffer,[Text.UTF8Encoding]::new($false))
    $LedgerBuffer.Clear()
}
foreach($row in $Snapshot){
    $rel=[string]$row.relative_path
    if($Ledger.ContainsKey($rel) -and $Ledger[$rel].status -in @("VERIFIED","VERIFIED_PRIOR_ARCHIVE")){continue}
    if($processedThisRun -ge $BatchSize -or $sw.Elapsed.TotalSeconds -ge $MaxSeconds){break}
    $src=Join-Path $V9 ($rel -replace "/","\");$dst=Join-Path $StageRoot ($rel -replace "/","\")
    $status="VERIFIED";$reason=$null;$sha=$null
    if(-not [IO.File]::Exists($src)){$status="SOURCE_DRIFT";$reason="MISSING_AFTER_SNAPSHOT"}
    else{
        $before=[IO.FileInfo]::new($src);$before.Refresh()
        if($before.Length -ne [int64]$row.bytes -or $before.LastWriteTimeUtc.ToString("o") -ne [string]$row.last_write_utc){$status="SOURCE_DRIFT";$reason="METADATA_CHANGED_AFTER_SNAPSHOT"}
        else{
            $sha=Get-Sha256Hex $src
            $afterHash=[IO.FileInfo]::new($src);$afterHash.Refresh()
            if($afterHash.Length -ne $before.Length -or $afterHash.LastWriteTimeUtc -ne $before.LastWriteTimeUtc){$status="SOURCE_DRIFT";$reason="CHANGED_DURING_HASH"}
            elseif($Prior.ContainsKey($rel) -and [int64]$Prior[$rel].bytes -eq $before.Length -and ([string]$Prior[$rel].sha256).ToLowerInvariant() -eq $sha){
                $status="VERIFIED_PRIOR_ARCHIVE";$reason=[string]$PriorEvidence.archive
            }else{
                [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($dst))|Out-Null
                [IO.File]::Copy($src,$dst,$true)
                $targetHash=Get-Sha256Hex $dst
                $after=[IO.FileInfo]::new($src);$after.Refresh()
                if($after.Length -ne $before.Length -or $after.LastWriteTimeUtc -ne $before.LastWriteTimeUtc){$status="SOURCE_DRIFT";$reason="CHANGED_DURING_COPY";Remove-Item -LiteralPath $dst -Force -ErrorAction SilentlyContinue}
                elseif($targetHash -ne $sha){$status="VERIFY_FAILED";$reason="HASH_MISMATCH"}
            }
        }
    }
    $entry=[ordered]@{relative_path=$rel;status=$status;sha256=$sha;reason=$reason;processed_at=(Get-Date).ToUniversalTime().ToString("o")}
    $LedgerBuffer.Add(($entry|ConvertTo-Json -Compress));if($LedgerBuffer.Count -ge 25){Flush-LedgerBuffer}
    $Ledger[$rel]=[pscustomobject]$entry;$processedThisRun++
    if($status -eq "SOURCE_DRIFT"){$drift+=$rel};if($status -eq "VERIFY_FAILED"){$failures+=$rel}
}
Flush-LedgerBuffer
$deltaVerified=@($Ledger.Values|Where-Object {$_.status -eq "VERIFIED"}).Count
$priorVerified=@($Ledger.Values|Where-Object {$_.status -eq "VERIFIED_PRIOR_ARCHIVE"}).Count
$verified=$deltaVerified+$priorVerified
$remaining=$Snapshot.Count-$verified
$progress=[ordered]@{schema="raios.cognitive-migration-progress.v2";run_id=$RunId;snapshot_files=$Snapshot.Count;verified=$verified;remaining=$remaining;processed_this_run=$processedThisRun;elapsed_seconds=[math]::Round($sw.Elapsed.TotalSeconds,3);source_drift=@($drift).Count;verify_failures=@($failures).Count;delta_verified=$deltaVerified;prior_archive_reused=$priorVerified;prior_archive=if($PriorEvidence){$PriorEvidence.archive}else{$null};prior_evidence_cache_hit=if($PriorEvidence){[bool]$PriorEvidence.cache_hit}else{$false};updated_at=(Get-Date).ToUniversalTime().ToString("o")}
Write-JsonAtomic $ProgressPath $progress
if($drift.Count -or $failures.Count){
    $report=[ordered]@{schema="raios.cognitive-store-migration.v2";status="SOURCE_DRIFT_OR_VERIFY_FAILURE";run_id=$RunId;progress=$progress;cleanup_executed=$false;promotion_executed=$false;archive_created=$false}
    Write-JsonAtomic $ReportPath $report;$report|ConvertTo-Json -Depth 6;throw "COGNITIVE_MIGRATION_FAIL_CLOSED"
}
if($remaining -gt 0){
    $report=[ordered]@{schema="raios.cognitive-store-migration.v2";status="IN_PROGRESS";run_id=$RunId;progress=$progress;cleanup_executed=$false;promotion_executed=$false;archive_created=$false;resume_command="-RunId $RunId -Resume"}
    Write-JsonAtomic $ReportPath $report;$report|ConvertTo-Json -Depth 6;exit 0
}
if($deltaVerified -gt 0){
    Push-Location $StageRoot
    try{& tar.exe -a -c -f $Archive .;if($LASTEXITCODE -ne 0){throw "ARCHIVE_CREATE_FAILED:$LASTEXITCODE"}}finally{Pop-Location}
    $ArchiveHash=Get-Sha256Hex $Archive
    Set-Content -LiteralPath "$Archive.sha256" -Value "$ArchiveHash  $([IO.Path]::GetFileName($Archive))" -Encoding ascii
}else{$ArchiveHash=$null}
$promotionMismatch=@()
foreach($row in $Snapshot){
    $rel=[string]$row.relative_path;$entry=$Ledger[$rel]
    if($entry.status -eq "VERIFIED"){
        $src=Join-Path $StageRoot ($rel-replace "/","\");$target=Join-Path $Store ($rel-replace "/","\")
        [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target))|Out-Null;[IO.File]::Copy($src,$target,$true)
        $expected=[string]$entry.sha256;$actual=Get-Sha256Hex $target
        if($actual -ne $expected){$promotionMismatch+=$rel}
    }
}
if($promotionMismatch.Count){Write-JsonAtomic (Join-Path $RunRoot "promotion-mismatches.json") $promotionMismatch;throw "COGNITIVE_PROMOTION_VERIFICATION_FAILED:$($promotionMismatch.Count)"}
$Removed=@()
if($ExecuteCleanup){
    $pathSpecs=$GeneratedRoots|ForEach-Object{"$_*"};$untracked=@(& git -C $Repo ls-files --others --exclude-standard -- @pathSpecs);if($LASTEXITCODE-ne 0){throw "GIT_UNTRACKED_DISCOVERY_FAILED"}
    foreach($relative in $untracked){$normalized=$relative.Replace("\","/");$allowed=$false;foreach($root in $GeneratedRoots){if($normalized.StartsWith($root,[StringComparison]::OrdinalIgnoreCase)){$allowed=$true;break}};if(-not $allowed){throw "CLEANUP_SCOPE_VIOLATION:$normalized"};Remove-Item -LiteralPath (Join-Path $Repo ($normalized-replace "/","\")) -Force;$Removed+=$normalized}
    $Removed|Set-Content -LiteralPath (Join-Path $RunRoot "removed-untracked-files.txt") -Encoding utf8
}
$report=[ordered]@{schema="raios.cognitive-store-migration.v2";status="PASS";run_id=$RunId;completed_at=(Get-Date).ToUniversalTime().ToString("o");source_root=$V9;target_root=$Store;snapshot_files=$Snapshot.Count;source_files_verified=$verified;archive=$Archive;archive_sha256=$ArchiveHash;archive_bytes=if($ArchiveHash){(Get-Item $Archive).Length}else{0};delta_files=$deltaVerified;prior_archive_reused=$priorVerified;prior_archive=if($PriorEvidence){$PriorEvidence.archive}else{$null};prior_archive_sha256=if($PriorEvidence){$PriorEvidence.archive_sha256}else{$null};promotion_verified=$true;removed_untracked_files=$Removed.Count;cleanup_executed=[bool]$ExecuteCleanup;bounded_snapshot=$true;resumable=$true}
Write-JsonAtomic $ReportPath $report;$report|ConvertTo-Json -Depth 6

