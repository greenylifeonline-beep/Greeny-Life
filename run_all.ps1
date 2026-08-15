# run_all.ps1 - تشغيل جميع الأوامر الفردية
$commands = @(
    "--classify",
    "--build-suppliers",
    "--build-certificates",
    "--build-els",
    "--build-customers",
    "--build-analytics",
    "--build-logistics",
    "--build-finance",
    "--build-inventory",
    "--build-crm",
    "--build-packaging-visual",
    "--generate-labels-visual",
    "--deep-packaging-audit",
    "--integrate-business-assets",
    "--master-data-audit",
    "--deep-clean",
    "--validate-global-specs"
)

foreach ($cmd in $commands) {
    Write-Host "`n🚀 تشغيل: python brain_fixed.py --repo . $cmd" -ForegroundColor Cyan
    python brain_fixed.py --repo . $cmd
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ نجاح: $cmd" -ForegroundColor Green
    } else {
        Write-Host "❌ فشل: $cmd (رمز: $LASTEXITCODE)" -ForegroundColor Red
    }
}
