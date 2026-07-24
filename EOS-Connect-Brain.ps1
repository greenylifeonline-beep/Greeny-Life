param(
    [string]$ProjectPath = (Get-Location).Path,
    [switch]$Schedule = $false
)

Push-Location $ProjectPath

# 1. Environment file setup
if (-not (Test-Path ".env")) {
    @"
# Greeny-Life EOS Environment Variables
SONARQUBE_URL=http://localhost:9000
SONAR_TOKEN=your_sonar_token_here
GITHUB_TOKEN=your_github_token_here
LLM_PROVIDER=claude
LLM_MODEL=claude-3-opus-20240229
"@ | Set-Content ".env" -Encoding utf8
    Write-Host "✅ Created .env file." -ForegroundColor Green
}

# 2. Check brain script
$brainScript = "brain.py"
if (-not (Test-Path $brainScript)) {
    Write-Error "❌ Brain file not found: $brainScript"
    Pop-Location
    exit 1
}

# 3. Logs directory & execution
$logDir = "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logFile = Join-Path $logDir "brain-run-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

Write-Host "🧠 Executing Greeny-Life Brain... (Logging to $logFile)" -ForegroundColor Cyan

# Clean execution to prevent NativeCommandError red block in PowerShell
$env:PYTHONUNBUFFERED = "1"
python $brainScript --repo . --output "full_report.json" | Tee-Object -FilePath $logFile

# 4. Commit to Git
if (Get-Command "git" -ErrorAction SilentlyContinue) {
    Write-Host "`n📤 Committing auto-generated docs and reports to Git..." -ForegroundColor Yellow
    git add full_report.json docs/ logs/ 2>$null
    $commitMsg = "🤖 AI Brain auto-run: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    git commit -m $commitMsg 2>$null
}

# 5. Task Scheduler (Optional)
if ($Schedule) {
    $taskName = "GreenyLifeEOS-Brain"
    $scriptPath = Join-Path $ProjectPath "EOS-Connect-Brain.ps1"
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
    $trigger = New-ScheduledTaskTrigger -Daily -At "02:00AM"
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "AI Brain Execution for Greeny-Life EOS" -Force | Out-Null
    Write-Host "✅ Scheduled Task created: Brain will run daily at 02:00 AM." -ForegroundColor Green
}

Write-Host "`n🎉 Greeny-Life EOS Brain pipeline fully connected and complete!" -ForegroundColor Green
Pop-Location
