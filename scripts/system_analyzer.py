#!/usr/bin/env python3
"""
Greeny-Life EOS - System Domain & Architecture Analyzer
يقوم بتحليل تقرير الجرد الشامل وفهم بنية النظام القديم بالكامل.
"""

import json
from pathlib import Path

def analyze_system():
    report_path = Path("legacy_audit_reports/legacy_system_inventory.json")
    if not report_path.exists():
        print("❌ تقرير الجرد غير موجود. يرجى تشغيل legacy_audit.py أولاً.")
        return

    with open(report_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("==================================================")
    print("   GREENY LIFE - SYSTEM ARCHITECTURE ANALYSIS")
    print("==================================================\n")

    print(f"📦 إجمالي الملفات في النظام: {data['total_files']}")
    print(f"🐍 ملفات بايثون (Python): {len(data['python_files'])}")
    print(f"⚛️ ملفات التايبسكريبت/الويب (TS/JS): {len(data['typescript_files'])}")
    print(f"⚙️ ملفات الإعدادات (JSON): {len(data['json_configs'])}")
    print(f"⚠️ ملاحظات الديون التقنية / الأكواد القديمة (TODOs): {len(data['todos_found'])}")

    # تصنيف الملفات حسب النطاقات (Domains) بناءً على مساراتها
    domains = {
        "Product Master / GELS": 0,
        "Database / Migrations": 0,
        "API / Routes": 0,
        "Frontend / UI": 0,
        "Scripts / Automation": 0
    }

    all_files = data['python_files'] + data['typescript_files'] + data['json_configs']
    for file in all_files:
        lower_file = file.lower()
        if 'product' in lower_file or 'gel' in lower_file or 'master' in lower_file:
            domains["Product Master / GELS"] += 1
        elif 'prisma' in lower_file or 'migration' in lower_file or 'db' in lower_file:
            domains["Database / Migrations"] += 1
        elif 'api' in lower_file or 'route' in lower_file:
            domains["API / Routes"] += 1
        elif 'src' in lower_file or 'component' in lower_file or 'app' in lower_file:
            domains["Frontend / UI"] += 1
        elif 'script' in lower_file:
            domains["Scripts / Automation"] += 1

    print("\n📊 توزيع الملفات حسب النطاقات التشغيلية:")
    for domain, count in domains.items():
        print(f" - {domain}: {count} ملفاً")

    print("\n==================================================")
    print("✨ تم تحليل بنية النظام وجاهزون لاستخدام النطاقات الفعالة.")
    print("==================================================")

if __name__ == "__main__":
    analyze_system()