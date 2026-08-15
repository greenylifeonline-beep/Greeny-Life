# ========================================================================
# run_brain.ps1 - الإصدار النهائي (يعمل مع brain.py)
# ========================================================================

param(
    [string]$Command = "--full-audit"
)

# تحميل .env إن وجد
if (Test-Path ".env") {
    Write-Host "📄 تحميل المتغيرات من .env..." -ForegroundColor Cyan
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value)
        }
    }
    Write-Host "✅ تم تحميل المتغيرات." -ForegroundColor Green
}

# التأكد من وجود brain.py
if (-not (Test-Path "brain.py")) {
    Write-Host "❌ ملف brain.py غير موجود في المسار الحالي!" -ForegroundColor Red
    exit 1
}

# تشغيل الأمر (مع تمرير اسم الملف و المعاملات)
Write-Host "`n🚀 تشغيل: python brain.py --repo . $Command" -ForegroundColor Cyan
python brain.py --repo . $Command

# النتيجة
if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ تم التنفيذ بنجاح." -ForegroundColor Green
} else {
    Write-Host "`n❌ فشل التنفيذ (رمز: $LASTEXITCODE)." -ForegroundColor Red
    Write-Host "📋 تحقق من السجلات في logs/." -ForegroundColor Yellow
}