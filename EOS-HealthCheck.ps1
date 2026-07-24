param(
    [string]$ProjectPath = (Get-Location).Path,
    [string]$OutputReport = ".\eos-health-report.json"
)

$ErrorActionPreference = "Stop"
$Report = @{
    Timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    ProjectPath = $ProjectPath
    Structure = @{}
    Tools = @{}
    MissingItems = @()
    Recommendations = @()
    Status = "SUCCESS"
}

function Test-CommandExists {
    param([string]$Command)
    return (Get-Command $Command -ErrorAction SilentlyContinue) -ne $null
}

Write-Host "Checking Greeny-Life EOS project structure..." -ForegroundColor Cyan

$ExpectedModules = @(
    "src/master_data", "src/gl_dos", "src/operations",
    "src/crm", "src/logistics", "src/compliance",
    "src/finance", "src/analytics", "src/administration",
    "tests", "docs", "scripts"
)

foreach ($module in $ExpectedModules) {
    $modulePath = Join-Path $ProjectPath $module
    $exists = Test-Path $modulePath
    $Report.Structure[$module] = $exists
    if (-not $exists) {
        $Report.MissingItems += "Missing module: $module"
    }
}

Write-Host "Checking tools and agents..." -ForegroundColor Cyan

$Tools = @{
    "git" = Test-CommandExists "git"
    "python" = Test-CommandExists "python"
    "pip" = Test-CommandExists "pip"
    "npm" = Test-CommandExists "npm"
    "bandit" = Test-CommandExists "bandit"
    "k6" = Test-CommandExists "k6"
    "claude" = Test-CommandExists "claude"
}

$Report.Tools = $Tools

$Report | ConvertTo-Json -Depth 4 | Out-File $OutputReport -Encoding utf8
Write-Host "Health check report generated successfully: $OutputReport" -ForegroundColor Green