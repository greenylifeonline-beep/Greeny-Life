#!/usr/bin/env python3
"""
Greeny-Life EOS - Product Master & GELS Extractor
يقوم بالبحث عن ملفات وبيانات Product Master وملفات GELS داخل النظام القديم وتجهيزها للاستيراد.
"""

import json
from pathlib import Path

def extract_products():
    print("==================================================")
    print("   GREENY LIFE - PRODUCT MASTER EXTRACTOR")
    print("==================================================\n")

    report_path = Path("legacy_audit_reports/legacy_system_inventory.json")
    if not report_path.exists():
        print("❌ تقرير الجرد غير موجود.")
        return

    with open(report_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # البحث عن الملفات التي تتعلق بالمنتجات أو GELS أو JSON configs
    target_files = []
    for file in data['json_configs'] + data['python_files'] + data['typescript_files']:
        lower = file.lower()
        if any(keyword in lower for keyword in ['product', 'gel', 'master', 'honey', 'catalog']):
            target_files.append(file)

    print(f"🎯 تم العثور على {len(target_files)} ملفاً مرتبطاً بـ Product Master / GELS:")
    for f in target_files[:15]: # عرض أول 15 ملفاً كمثال
        print(f" - {f}")

    if len(target_files) > 15:
        print(f" ... و {len(target_files) - 15} ملفات أخرى.")

    # حفظ قائمة ملفات المنتجات المستهدفة
    output_path = Path("legacy_audit_reports/product_master_targets.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(target_files, f, indent=2, ensure_ascii=False)

    print(f"\n📂 تم حفظ قائمة أهداف Product Master في: {output_path}")
    print("==================================================")

if __name__ == "__main__":
    extract_products()