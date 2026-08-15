# extract_dna.py
from pathlib import Path
from greenlines_brain.dna.extractor import DNAExtractor
import json

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
    
    # حفظ في مجلد dna/
    dna_dir = Path("greenlines_brain/dna")
    dna_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = dna_dir / "extracted_knowledge.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(knowledge, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ تم استخراج المعرفة بنجاح.")
    print(f"📊 إحصائيات:")
    print(f"   - الكيانات: {len(knowledge.get('entities', []))}")
    print(f"   - القواعد التجارية: {len(knowledge.get('business_rules', []))}")
    print(f"   - البيانات الرئيسية: {len(knowledge.get('master_data', []))}")
    print(f"   - القدرات: {len(knowledge.get('capabilities', []))}")
    print(f"\n📁 الملف المحفوظ: {output_path}")

if __name__ == "__main__":
    main()
    