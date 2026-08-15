# run_full_audit.ps1 - تشغيل جميع وكلاء Greeny-Life EOS بتسلسل (بديل --full-audit)

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

$success = 0
$failed = 0

foreach ($cmd in $commands) {
    Write-Host "`n🚀 تشغيل: .venv\Scripts\python.exe run_brain_cli.py --repo . $cmd" -ForegroundColor Cyan
    .venv\Scripts\python.exe run_brain_cli.py --repo . $cmd
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ نجاح: $cmd" -ForegroundColor Green
        $success++
    } else {
        Write-Host "❌ فشل: $cmd (رمز: $LASTEXITCODE)" -ForegroundColor Red
        $failed++
    }
}

Write-Host "`n" + "="*80 -ForegroundColor Cyan
Write-Host "📊 التقرير النهائي:" -ForegroundColor Yellow
Write-Host "   ✅ نجاح: $success أمراً" -ForegroundColor Green
Write-Host "   ❌ فشل: $failed أمراً" -ForegroundColor Red
Write-Host "="*80 -ForegroundColor Cyan
