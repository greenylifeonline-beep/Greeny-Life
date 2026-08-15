#!/usr/bin/env python3
# test_brain_v3.py - اختبار شامل للعقل المؤسسي

import sys
import json
from pathlib import Path

# تأكد من أن المجلد الحالي في مسار البحث
sys.path.insert(0, '.')

from greenlines_brain.identity import Identity, EntityScope
from greenlines_brain.repository.json_repo import JSONKnowledgeRepository
from greenlines_brain.kernel import GreenlinesBrain

def print_section(title):
    print("\n" + "="*60)
    print(f"🧠 {title}")
    print("="*60)

def test_brain():
    print("="*60)
    print("🧪 اختبار شامل لـ Greenlines Brain Kernel v1.0")
    print("="*60)
    
    # 1. تهيئة الهوية
    print_section("1. تهيئة الهوية")
    egypt_identity = Identity(
        scope=EntityScope.EGYPT,
        legal_name="Greeny Life Egypt",
        country="Egypt",
        currency="EGP",
        regulations=["Egyptian Export Law", "GCC Standards", "EU Food Safety"],
        local_context={
            "allowed_exports": ["gcc", "eu", "norway", "usa"],
            "local_suppliers": ["Nile Valley Honey Co.", "Sinai Spice Mills"],
            "local_products": ["honey", "spices", "herbs", "oils"]
        }
    )
    print(f"✅ النطاق: {egypt_identity.scope.value}")
    print(f"✅ الوجهات المسموح بها: {egypt_identity.get_allowed_exports()}")
    
    # 2. تحميل المعرفة
    print_section("2. تحميل المعرفة")
    knowledge_path = Path("greenlines_brain/dna/extracted_knowledge.json")
    if not knowledge_path.exists():
        print("❌ extracted_knowledge.json غير موجود!")
        return
    
    repository = JSONKnowledgeRepository(knowledge_path)
    knowledge = repository.load_knowledge()
    print(f"✅ تم تحميل {len(knowledge.get('entities', []))} كيان")
    print(f"✅ تم تحميل {len(knowledge.get('business_rules', []))} قاعدة")
    print(f"✅ تم تحميل {len(knowledge.get('capabilities', []))} قدرة")
    
    # 3. إنشاء العقل
    print_section("3. إنشاء العقل")
    brain = GreenlinesBrain(egypt_identity, repository)
    print("✅ تم إنشاء العقل بنجاح")
    
    # 4. اختبار Ask
    print_section("4. اختبار Ask (السؤال)")
    
    questions = [
        "ما هي شهادات التصدير؟",
        "ما هي شهادات التصدير المطلوبة للعسل إلى النرويج؟",
        "هل يمكن تصدير العسل إلى أوروبا؟",
        "ما هي متطلبات التصدير؟"
    ]
    
    for q in questions:
        print(f"\n❓ السؤال: {q}")
        result = brain.ask(q)
        print(f"📝 الإجابة:\n{result.answer}")
        print(f"📊 الثقة: {result.confidence.value}")
        print(f"📎 الأدلة: {len(result.evidence)}")
        print("-"*40)
    
    # 5. اختبار Decide
    print_section("5. اختبار Decide (القرار)")
    
    scenarios = [
        {"objective": "export", "entity": "egypt", "product": "honey", "destination": "norway"},
        {"objective": "export", "entity": "egypt", "product": "spices", "destination": "eu"},
        {"objective": "export", "entity": "egypt", "product": "herbs", "destination": "usa"},
        {"objective": "export", "entity": "egypt", "product": "oils", "destination": "gcc"},
    ]
    
    for scenario in scenarios:
        print(f"\n📋 السيناريو: {scenario}")
        decision = brain.decide(**scenario)
        print(f"   📌 التوصية: {decision.recommendation}")
        print(f"   📊 الثقة: {decision.confidence.value}")
        print(f"   📝 الاستدلال:\n{decision.reasoning[:200]}..." if len(decision.reasoning) > 200 else f"   📝 الاستدلال:\n{decision.reasoning}")
        if decision.risks:
            print(f"   ⚠️ المخاطر: {decision.risks}")
        if decision.constraints:
            print(f"   🔒 القيود: {decision.constraints}")
        print("-"*40)
    
    # 6. اختبار Reason
    print_section("6. اختبار Reason (الاستدلال)")
    
    premises_sets = [
        ["export", "egypt", "honey", "norway"],
        ["export", "egypt", "spices", "eu"],
        ["export", "egypt", "norway"],
        ["export", "egypt"],
    ]
    
    for premises in premises_sets:
        print(f"\n📝 المقدمات: {premises}")
        results = brain.reason(premises)
        for r in results:
            print(f"   - {r}")
    
    # 7. اختبار الذاكرة
    print_section("7. اختبار الذاكرة")
    brain.remember("test_key", "test_value")
    brain.observe("test_event", {"status": "ok"})
    memory_summary = brain.get_memory_summary()
    print(f"📚 ملخص الذاكرة: {memory_summary}")
    
    # 8. اختبار الرسم البياني
    print_section("8. اختبار الرسم البياني")
    graph_summary = brain.get_graph_summary()
    print(f"📊 ملخص الرسم البياني: {graph_summary}")
    
    # 9. اختبار الاستعلام في الرسم البياني
    print("\n🔍 البحث عن كيانات:")
    test_names = ["honey", "norway", "egypt", "spices"]
    for name in test_names:
        nodes = brain.graph.find_node_by_name(name)
        if nodes:
            print(f"   ✅ '{name}' -> {nodes}")
        else:
            print(f"   ❌ '{name}' غير موجود في الرسم البياني")
    
    # 10. ملخص نهائي
    print_section("10. الملخص النهائي")
    print("✅ جميع الاختبارات اكتملت!")
    print(f"📊 حالة العقل:")
    print(f"   - الذاكرة: {brain.get_memory_summary()}")
    print(f"   - الرسم البياني: {brain.get_graph_summary()}")
    print(f"   - المعرفة: {brain.get_knowledge_summary()}")

if __name__ == "__main__":
    test_brain()