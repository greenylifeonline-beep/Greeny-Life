import asyncio
import sys
from prisma import Prisma

# قائمة الكيانات الـ 17 المعتمدة في المخطط Enterprise Blueprint v1.0
EXPECTED_ENTITIES = [
    "user",
    "auditlog",
    "notification",
    "category",
    "collection",
    "supplier",
    "packagingprofile",
    "market",
    "product",
    "media",
    "warehouse",
    "inventory",
    "customer",
    "salesorder",
    "salesorderitem",
    "shipment",
    "document"
]

async def run_entity_tests():
    print("🚀 Starting Prisma Entity & Connection Integration Tests...\n")
    db = Prisma()
    
    try:
        await db.connect()
        print("✅ Connection to PostgreSQL established successfully!\n")
    except Exception as e:
        print(f"❌ Failed to connect to PostgreSQL: {e}")
        sys.exit(1)

    passed_count = 0
    failed_count = 0

    print("🔍 Testing availability of 17 Core Entities...")
    print("=" * 55)

    for entity_name in EXPECTED_ENTITIES:
        try:
            # الوصول المباشر للـ Dynamic model accessor في Prisma
            model = getattr(db, entity_name)
            # إجراء استعلام عد سريع للاختبار (Count Query)
            count = await model.count()
            print(f"  ✓ [{entity_name.upper():<18}] Access OK | Current Records: {count}")
            passed_count += 1
        except AttributeError:
            print(f"  ✗ [{entity_name.upper():<18}] FAILED: Model not registered on Prisma client")
            failed_count += 1
        except Exception as ex:
            print(f"  ✗ [{entity_name.upper():<18}] FAILED: {ex}")
            failed_count += 1

    print("=" * 55)
    print(f"\n📊 Test Summary:")
    print(f"   - Total Expected Entities: {len(EXPECTED_ENTITIES)}")
    print(f"   - Passed: {passed_count}")
    print(f"   - Failed: {failed_count}")

    await db.disconnect()

    if failed_count == 0:
        print("\n🎉 ALL 17 ENTITIES ARE HEALTHY AND FULLY ACCESSIBLE!")
    else:
        print(f"\n⚠️ {failed_count} entities failed verification. Please review prisma/schema.prisma")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_entity_tests())
