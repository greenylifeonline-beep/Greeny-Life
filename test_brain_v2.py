#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
اختبار Greenlines Brain Kernel v0.1
باستخدام المعرفة المستخرجة من brain.py
"""

import sys
from pathlib import Path

# إضافة المجلد الحالي إلى مسار البحث
sys.path.insert(0, str(Path(__file__).parent))

from greenlines_brain.identity import Identity, EntityScope
from greenlines_brain.repository.json_repo import JSONKnowledgeRepository
from greenlines_brain.kernel import GreenlinesBrain

def main():
    print("=" * 60)
    print("🧠 اختبار Greenlines Brain Kernel v0.1")
    print("=" * 60)
    
    # 1. تحديد هوية الكيان المصري
    print("\n📌 1. تهيئة هوية الكيان (Egypt)...")
    egypt_identity = Identity(
        scope=EntityScope.EGYPT,
        legal_name="Greeny Life Egypt",
        country="Egypt",
        currency="EGP",
        regulations=["Egyptian Export Law", "GCC Standards", "EU Food Safety"],
        local_context={
            "allowed_exports": ["gcc", "eu", "norway", "usa"],
            "local_suppliers": ["Nile Valley Honey Co.", "Sinai Spice Mills", "Green Valley Bee Products"],
            "local_products": ["honey", "spices", "herbs", "oils"]
        }
    )
    print(f"   ✅ النطاق: {egypt_identity.scope.value}")
    print(f"   ✅ الوجهات المسموح بها: {egypt_identity.get_allowed_exports()}")
    
    # 2. تحميل المعرفة المستخرجة
    print("\n📌 2. تحميل المعرفة المستخرجة...")
    knowledge_path = Path("greenlines_brain/dna/extracted_knowledge.json")
    if not knowledge_path.exists():
        print("   ❌ لم يتم العثور على extracted_knowledge.json!")
        print(r"   💡 قم بتشغيل: .venv\Scripts\python.exe extract_dna.py")
        return
    
    repository = JSONKnowledgeRepository(knowledge_path)
    print(f"   ✅ تم تحميل المعرفة من: {knowledge_path}")
    
    # 3. إنشاء العقل
    print("\n📌 3. تهيئة العقل...")
    brain = GreenlinesBrain(egypt_identity, repository)
    print("   ✅ تم تهيئة العقل بنجاح!")
    
    # 4. اختبار السؤال
    print("\n" + "=" * 60)
    print("🧠 اختبار 1: السؤال (Ask)")
    print("=" * 60)
    
    question = "ما هي شهادات التصدير؟"
    print(f"\n❓ السؤال: {question}")
    result = brain.ask(question)
    print(f"\n📝 الإجابة:")
    print(f"   {result.answer}")
    print(f"📊 الثقة: {result.confidence.value}")
    print(f"📎 عدد الأدلة: {len(result.evidence)}")
    
    # 5. اختبار القرار
    print("\n" + "=" * 60)
    print("🧠 اختبار 2: القرار (Decide)")
    print("=" * 60)
    
    decision = brain.decide(
        objective="export",
        entity="egypt",
        product="honey",
        destination="norway"
    )
    
    print(f"\n📋 القرار (ID: {decision.decision_id}):")
    print(f"   📌 التوصية: {decision.recommendation}")
    print(f"   📝 الاستدلال:\n{decision.reasoning}")
    print(f"   📊 الثقة: {decision.confidence.value}")
    print(f"   ⚠️ المخاطر: {decision.risks if decision.risks else 'لا توجد مخاطر محددة'}")
    print(f"   🔒 القيود: {decision.constraints if decision.constraints else 'لا توجد قيود محددة'}")
    print(f"   🔄 البدائل: {decision.alternatives if decision.alternatives else 'لا توجد بدائل محددة'}")
    print(f"   🏢 نطاق الكيان: {decision.entity_scope}")
    
    # 6. اختبار الذاكرة
    print("\n" + "=" * 60)
    print("🧠 اختبار 3: الذاكرة (Memory)")
    print("=" * 60)
    
    brain.remember("last_export_decision", decision.decision_id)
    brain.observe("market_update", {
        "country": "norway",
        "status": "new_regulations",
        "details": "Updated food safety requirements"
    })
    
    print("\n✅ تم تسجيل الملاحظات في الذاكرة.")
    # الذاكرة أصبحت InstitutionalMemory وليست قاموسًا عاديًا
    memory_summary = brain.get_memory_summary()
    print(f"📚 ملخص الذاكرة: {memory_summary}")
    # أو عرض المفاتيح من كل مستوى على حدة
    print(f"📚 الذاكرة قصيرة المدى: {list(brain.memory.short_term.keys())}")
    print(f"📚 الذاكرة طويلة المدى: {list(brain.memory.long_term.keys())}")    
    # 7. اختبار الاستدلال
    print("\n" + "=" * 60)
    print("🧠 اختبار 4: الاستدلال (Reason)")
    print("=" * 60)
    
    # يجب تمرير القواعد كقواميس، لأن kernel.reason يتوقع ذلك
    premises = ["export", "egypt"]
    rules = [
        {"condition": "egypt → honey → norway is allowed", "comment": "قاعدة تصدير العسل للنرويج"},
        {"condition": "egypt → spices → eu is allowed", "comment": "قاعدة تصدير التوابل لأوروبا"},
        {"condition": "norway requires organic certification", "comment": "اشتراطات النرويج"}
    ]
    conclusions = brain.reason(premises, rules)
    print(f"\n📝 المقدمات: {premises}")
    print(f"📋 القواعد: {rules}")
    print(f"💡 الاستنتاجات: {conclusions if conclusions else 'لا توجد استنتاجات جديدة'}")
    
    print("\n" + "=" * 60)
    print("🎉 جميع الاختبارات اكتملت بنجاح!")
    print("=" * 60)

if __name__ == "__main__":
    main()
