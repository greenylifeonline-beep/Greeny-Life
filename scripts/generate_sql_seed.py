#!/usr/bin/env python3
"""
Greeny-Life EOS - SQL Seed Generator
يولد ملف SQL مباشر لإدخال بيانات Product Master في قاعدة البيانات دون الحاجة لـ Prisma Client.
"""

import json
from pathlib import Path

def generate_sql():
    print("==================================================")
    print("   GREENY LIFE - SQL SEED GENERATOR")
    print("==================================================\n")

    filePath = Path("legacy_audit_reports/active_master_products.json")
    if not filePath.exists():
        print("❌ ملف active_master_products.json غير موجود.")
        return

    with open(filePath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    products = data.get("products", [])
    print(f"📦 تم العثور على {len(products)} منتجاً. جاري توليد أوامر SQL...")

    sql_statements = [
        "-- Greeny Life EOS - Master Products Direct Seed",
        "BEGIN;\n"
    ]

    for p in products:
        p_id = p.get("id")
        p_code = p.get("product_code")
        ref_id = p.get("ref_id")
        collection = p.get("collection")
        name_en = p.get("name", {}).get("en", "")
        name_ar = p.get("name", {}).get("ar", "")
        accent_color = p.get("accent_color", "#000000")
        published = 'TRUE' if p.get("status", {}).get("published") else 'FALSE'
        active = 'TRUE' if p.get("status", {}).get("active") else 'FALSE'
        featured = 'TRUE' if p.get("status", {}).get("featured") else 'FALSE'

        # جملة الـ SQL للاستدخال مع تحديث البيانات في حال وجود مكرر
        stmt = f"""
INSERT INTO "Product" (id, "productCode", "refId", collection, "nameEn", "nameAr", "accentColor", published, active, featured, "createdAt", "updatedAt")
VALUES ('{p_id}', '{p_code}', '{ref_id}', '{collection}', '{name_en}', '{name_ar}', '{accent_color}', {published}, {active}, {featured}, NOW(), NOW())
ON CONFLICT ("productCode") DO UPDATE SET
    "refId" = EXCLUDED."refId",
    collection = EXCLUDED.collection,
    "nameEn" = EXCLUDED."nameEn",
    "nameAr" = EXCLUDED."nameAr",
    "accentColor" = EXCLUDED."accentColor",
    published = EXCLUDED.published,
    active = EXCLUDED.active,
    featured = EXCLUDED.featured,
    "updatedAt" = NOW();
"""
        sql_statements.append(stmt)

    sql_statements.append("COMMIT;")

    output_path = Path("legacy_audit_reports/seed_products.sql")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(sql_statements))

    print(f"\n✨ تم توليد ملف SQL بنجاح في: {output_path}")
    print("==================================================")

if __name__ == "__main__":
    generate_sql()