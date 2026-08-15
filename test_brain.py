from pathlib import Path
from greenlines_brain.identity import Identity, EntityScope
from greenlines_brain.repository.json_repo import JSONKnowledgeRepository
from greenlines_brain.kernel import GreenlinesBrain

# 1. هوية الكيان المصري
egypt_identity = Identity(
    scope=EntityScope.EGYPT,
    legal_name="Greeny Life Egypt",
    country="Egypt",
    currency="EGP",
    regulations=["Egyptian Export Law", "GCC Standards"],
    local_context={
        "allowed_exports": ["gcc", "eu", "norway"],
        "local_suppliers": ["Nile Valley Honey Co.", "Sinai Spice Mills"],
        "local_products": ["honey", "spices", "herbs"]
    }
)

# 2. تحميل المعرفة المستخرجة
knowledge_path = Path("greenlines_brain/dna/extracted_knowledge.json")
if not knowledge_path.exists():
    print("❌ لم يتم العثور على extracted_knowledge.json. قم بتشغيل extract_dna.py أولاً.")
    exit(1)

repository = JSONKnowledgeRepository(knowledge_path)

# 3. إنشاء العقل
brain = GreenlinesBrain(egypt_identity, repository)

# 4. اختبار السؤال
print("\n🧠 اختبار السؤال:")
result = brain.ask("ما هي شهادات التصدير؟")
print(f"الإجابة: {result.answer}")
print(f"الثقة: {result.confidence.value}")

# 5. اختبار القرار
print("\n🧠 اختبار القرار:")
decision = brain.decide(
    objective="export",
    entity="egypt",
    product="honey",
    destination="norway"
)
print(f"التوصية: {decision.recommendation}")
print(f"الاستدلال:\n{decision.reasoning}")
print(f"الثقة: {decision.confidence.value}")
print(f"المخاطر: {decision.risks}")
print(f"القيود: {decision.constraints}")