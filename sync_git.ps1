# ============================================================
# 🐙 Greeny-Life EOS - Automatic Git Sync Script
# ============================================================
$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting Auto Git Sync Process..." -ForegroundColor Cyan

if (-not (Test-Path ".git")) {
    Write-Error "❌ Not a git repository."
    exit 1
}

git add .

$status = git status --porcelain
if (-not $status) {
    Write-Host "✨ Working tree clean. Nothing to commit!" -ForegroundColor Green
    exit 0
}

$branch = (git branch --show-current).Trim()
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$commitMsg = "feat(eos): automatic sync [$timestamp]"

Write-Host "📝 Committing on '$branch'..." -ForegroundColor Yellow
git commit -m "$commitMsg"

Write-Host "⬆️ Pushing to origin/$branch..." -ForegroundColor Yellow
git push origin $branch

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n🎉 Successfully synced!" -ForegroundColor Green
}
