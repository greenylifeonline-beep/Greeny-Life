#!/usr/bin/env python3
"""
Greeny-Life EOS - Master Products Inspector
يقوم بقراءة وعرض محتوى أحدث ملف منتجات رئيسي من النسخ الاحتياطية.
"""

import json
from pathlib import Path

def inspect_products():
    print("==================================================")
    print("   GREENY LIFE - MASTER PRODUCTS INSPECTOR")
    print("==================================================\n")

    # البحث عن أحدث ملف 05_master_products.json داخل مجلدات backup
    backup_dir = Path("backup")
    if not backup_dir.exists():
        print("❌ مجلد backup غير موجود.")
        return

    master_files = list(backup_dir.glob("**/05_master_products.json"))
    if not master_files:
        print("❌ لم يتم العثور على أي ملف 05_master_products.json.")
        return

    # ترتيب الملفات حسب تاريخ التعديل (الأحدث أولاً)
    latest_file = max(master_files, key=lambda p: p.stat().st_mtime)
    print(f"📂 قراءة أحدث ملف منتجات: {latest_file}\n")

    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        print(json.dumps(content, indent=2, ensure_ascii=False)[:2000]) # طباعة أول 2000 حرف للعرض
        print("\n[تم اقتطاع العرض مطولاً، الملف يحتوي على كامل البيانات المؤسسية]")

        # حفظ نسخة موحدة في مسار عملي للاستيراد
        target_path = Path("legacy_audit_reports/active_master_products.json")
        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        print(f"\n✨ تم نسخ الملف النشط إلى: {target_path}")

    except Exception as e:
        print(f"❌ خطأ أثناء قراءة الملف: {e}")

    print("==================================================")

if __name__ == "__main__":
    inspect_products()