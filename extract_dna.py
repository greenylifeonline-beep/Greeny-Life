#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
مستخرج الحمض النووي من brain.py
يستخرج الكيانات، القواعد، البيانات الرئيسية، والقدرات.
"""

import sys
import json
from pathlib import Path

# إضافة المجلد الحالي إلى مسار البحث حتى نتمكن من استيراد greenlines_brain
sys.path.insert(0, str(Path(__file__).parent))

from greenlines_brain.dna.extractor import DNAExtractor

def main():
    # تحديد مسار brain.py
    brain_path = Path("brain.py")
    if not brain_path.exists():
        print("❌ لم يتم العثور على brain.py في المسار الحالي.")
        return
    
    print("🧬 بدء استخراج الحمض النووي من brain.py...")
    
    # استخراج المعرفة
    extractor = DNAExtractor(brain_path)
    knowledge = extractor.extract_knowledge()
    
    # إنشاء مجلد dna إذا لم يكن موجوداً
    dna_dir = Path("greenlines_brain/dna")
    dna_dir.mkdir(parents=True, exist_ok=True)
    
    # حفظ المعرفة
    output_path = dna_dir / "extracted_knowledge.json"
    extractor.save_knowledge(output_path)
    
    # إحصائيات
    print(f"\n📊 إحصائيات الاستخراج:")
    print(f"   - الكيانات: {len(knowledge.get('entities', []))}")
    print(f"   - القواعد التجارية: {len(knowledge.get('business_rules', []))}")
    print(f"   - البيانات الرئيسية: {len(knowledge.get('master_data', []))}")
    print(f"   - القدرات: {len(knowledge.get('capabilities', []))}")
    print(f"\n📁 الملف المحفوظ: {output_path}")

if __name__ == "__main__":
    main()
