# ========================================================================
# تشغيل جميع وكلاء Greeny-Life EOS (بديل --full-audit)
# ========================================================================

Write-Host "🚀 بدء التشغيل البديل للـ Full Audit..." -ForegroundColor Cyan
Write-Host "📋 سيتم تشغيل جميع الأوامر الفردية التي تعمل بشكل مؤكد." -ForegroundColor Yellow
Write-Host ""

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

$successCount = 0
$failCount = 0
$failedCommands = @()

foreach ($cmd in $commands) {
    Write-Host "`n🔹 تشغيل: python brain.py --repo . $cmd" -ForegroundColor Cyan
    python brain.py --repo . $cmd
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ نجاح: $cmd" -ForegroundColor Green
        $successCount++
    } else {
        Write-Host "❌ فشل: $cmd (رمز: $LASTEXITCODE)" -ForegroundColor Red
        $failCount++
        $failedCommands += $cmd
    }
}

Write-Host "`n" + "="*80 -ForegroundColor Cyan
Write-Host "📊 التقرير النهائي:" -ForegroundColor Yellow
Write-Host "   ✅ نجاح: $successCount أمراً" -ForegroundColor Green
Write-Host "   ❌ فشل: $failCount أمراً" -ForegroundColor Red

if ($failCount -gt 0) {
    Write-Host "   الأوامر الفاشلة:" -ForegroundColor Yellow
    foreach ($f in $failedCommands) {
        Write-Host "      - $f" -ForegroundColor Red
    }
}

Write-Host "="*80 -ForegroundColor Cyan