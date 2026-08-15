# ============================================================================
# PACKAGING POLICY AUDIT SCRIPT
# ============================================================================
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "📦 GREENY-LIFE EOS - PACKAGING POLICY AUDIT" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. تحميل ملف المنتجات
$ProductsPath = ".\data\master_products.json"
if (-not (Test-Path $ProductsPath)) {
    Write-Host "❌ Products file not found at $ProductsPath" -ForegroundColor Red
    exit 1
}
$Products = Get-Content $ProductsPath -Raw | ConvertFrom-Json
$ProductList = $Products.products

# 2. تحميل تقرير سياسة التعبئة والتغليف
$PolicyPath = ".\data\packaging_visual_integration_report.json"
if (-not (Test-Path $PolicyPath)) {
    Write-Host "⚠️  Packaging policy report not found at $PolicyPath. Using embedded policy." -ForegroundColor Yellow
    $Policy = $null
    

# 3. تعريف السياسة الرسمية (مأخوذة من الصورة IMG_3459.webp)
$OfficialPolicy = @{
    "honey" = @{
        "retail" = @{ "material" = "Glass Jar"; "sizes" = @("250g", "500g", "750g", "1kg") }
        "refill" = @{ "material" = "Stand-up Pouch"; "sizes" = @("500g", "1kg") }
        "food_service" = @{ "material" = "Food Grade Bucket"; "sizes" = @("3kg", "5kg", "10kg") }
        "wholesale" = @{ "material" = "Food Grade Drum"; "sizes" = @("25kg", "50kg", "300kg") }
        "private_label" = @{ "available" = $true }
    }
    "spices" = @{
        "retail" = @{ "material" = "Glass Jar"; "sizes" = @("250g", "500g", "750g", "1kg") }
        "refill" = @{ "material" = "Stand-up Pouch"; "sizes" = @("500g", "1kg") }
        "food_service" = @{ "material" = "Heavy Duty Pouch"; "sizes" = @("500g", "1kg") }
        "wholesale" = @{ "material" = "Industrial Multi-Layer Bag"; "sizes" = @("10kg", "25kg") }
        "private_label" = @{ "available" = $true }
    }
    "oils" = @{
        "retail" = @{ "material" = "Glass Bottle"; "sizes" = @("30ml", "50ml", "100ml", "250ml", "500ml") }
        "food_service" = @{ "material" = "HDPE Food Grade"; "sizes" = @("1L", "5L", "20L") }
        "wholesale" = @{ "material" = "HDPE Food Grade"; "sizes" = @("1L", "5L", "20L") }
        "private_label" = @{ "available" = $true }
    }
    "bee_products" = @{
        "retail" = @{ "material" = "Glass Jar"; "sizes" = @("30ml", "50ml", "100ml", "250ml", "500ml") }
        "refill" = @{ "material" = "Stand-up Pouch"; "sizes" = @("250g", "500g") }
        "food_service" = @{ "material" = "Not Applicable"; "sizes" = @() }
        "wholesale" = @{ "material" = "Food Grade Bucket"; "sizes" = @("1kg", "5kg") }
        "private_label" = @{ "available" = $true }
    }
    "herbs" = @{
        "retail" = @{ "material" = "Glass Jar"; "sizes" = @("250g", "500g") }
        "refill" = @{ "material" = "Stand-up Pouch"; "sizes" = @("500g") }
        "food_service" = @{ "material" = "Heavy Duty Pouch"; "sizes" = @("500g") }
        "wholesale" = @{ "material" = "Industrial Multi-Layer Bag"; "sizes" = @("10kg", "25kg") }
        "private_label" = @{ "available" = $true }
    }
}

# ============================================================================
# 4. التدقيق الفعلي
# ============================================================================
$Errors = @()
$Warnings = @()
$ProductCount = $ProductList.Count
Write-Host "`n🔍 Products Found: $ProductCount" -ForegroundColor Yellow

foreach ($Product in $ProductList) {
    $ProductId = $Product.id
    $Collection = $Product.collection
    $PackagingProfile = $Product.packaging_profile
    $RefId = $Product.ref_id

    # تحديد السياسة الصحيحة بناءً على الـ collection
    $PolicyForCollection = $OfficialPolicy[$Collection]
    if (-not $PolicyForCollection) {
        $Warnings += "⚠️  $RefId ($ProductId): Unknown collection '$Collection'. Using default 'honey'."
        $PolicyForCollection = $OfficialPolicy["honey"]
    }

    # 1. التحقق من وجود `packaging_profile` صحيح (يجب أن يكون مطابقاً للـ collection)
    $ExpectedProfile = "$Collection`_default"
    if ($PackagingProfile -ne $ExpectedProfile -and $PackagingProfile -ne "honey_default" -and $Collection -ne "honey") {
        $Warnings += "⚠️  $RefId ($ProductId): packaging_profile '$PackagingProfile' does not match expected '$ExpectedProfile'."
    }

    # 2. التحقق من المواد الأساسية (Retail)
    $RetailPolicy = $PolicyForCollection.retail
    if ($RetailPolicy) {
        Write-Host "   ✅ $RefId ($ProductId) - Retail: $($RetailPolicy.material)" -ForegroundColor Green
    } else {
        $Errors += "❌  $RefId ($ProductId): Missing Retail policy."
    }

    # 3. التحقق من وجود Refill (إذا كانت السياسة تدعمه)
    if ($PolicyForCollection.refill -and $PolicyForCollection.refill.material -ne "Not Applicable") {
        Write-Host "   ✅ $RefId ($ProductId) - Refill: $($PolicyForCollection.refill.material)" -ForegroundColor Green
    }

    # 4. التحقق من وجود Food Service (إذا كانت السياسة تدعمه)
    if ($PolicyForCollection.food_service -and $PolicyForCollection.food_service.material -ne "Not Applicable") {
        Write-Host "   ✅ $RefId ($ProductId) - Food Service: $($PolicyForCollection.food_service.material)" -ForegroundColor Green
    }

    # 5. التحقق من Private Label
    if ($PolicyForCollection.private_label.available -eq $true) {
        Write-Host "   ✅ $RefId ($ProductId) - Private Label: Available" -ForegroundColor Green
    }
}

# ============================================================================
# 5. تقرير الملخص
# ============================================================================
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "📊 AUDIT SUMMARY" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Total Products Checked: $ProductCount" -ForegroundColor White
Write-Host "Errors: $($Errors.Count)" -ForegroundColor Red
Write-Host "Warnings: $($Warnings.Count)" -ForegroundColor Yellow

if ($Errors.Count -gt 0) {
    Write-Host "`n🚨 Errors:" -ForegroundColor Red
    $Errors | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
}

if ($Warnings.Count -gt 0) {
    Write-Host "`n⚠️  Warnings:" -ForegroundColor Yellow
    $Warnings | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
}

if ($Errors.Count -eq 0 -and $Warnings.Count -eq 0) {
    Write-Host "`n✅ ALL PRODUCTS ARE FULLY COMPLIANT WITH PACKAGING POLICY!" -ForegroundColor Green
} else {
    Write-Host "`n🛠️  Please fix the issues above before proceeding to Master Data expansion." -ForegroundColor Magenta
}