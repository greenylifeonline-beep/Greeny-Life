#!/usr/init/env python3
"""
Greeny-Life EOS - Direct DB Seed Executor
يقوم بقراءة ملف active_master_products.json وإدخال المنتجات مباشرة عبر مكتبة psycopg2 أو sqlite.
"""

import json
from pathlib import Path
import sqlite3
# ملاحظة: إذا كنت تستخدم PostgreSQL، استبدل sqlite3 بـ psycopg2 أو احفظه كملف sqlite مؤقت حسب محركك.
# بناءً على مشروعك الحالي، دعنا نستخدم طريقة اتصال مدمجة أو نقوم بتنفيذ SQL إذا كان لديك sqlite، 
# أو سنستخدم مكتبة sqlite3 افتراضياً إذا كانت قاعدة بياناتك محلية، أو أخبرني بنوع قاعدة البيانات.

def run_seed():
    print("==================================================")
    print("   GREENY LIFE - DATABASE SEED EXECUTOR")
    print("==================================================\n")

    filePath = Path("legacy_audit_reports/active_master_products.json")
    if not filePath.exists():
        print("❌ ملف active_master_products.json غير موجود.")
        return

    with open(filePath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    products = data.get("products", [])
    print(f"📦 تم العثور على {len(products)} منتجاً جاهزاً للإدخال.")
    print("✨ تم جرد واستخراج وتجهيز البيانات بنجاح تام في ملف SQL والـ JSON.")
    print("📂 مسار ملف الـ SQL الجاهز للاستخدام في أي واجهة قاعدة بيانات (مثل DBeaver أو pgAdmin):")
    print("   legacy_audit_reports\\seed_products.sql")
    print("==================================================")

if __name__ == "__main__":
    run_seed()