# fix_brain.py - إصلاح المسافة البادئة في brain.py
import re

# قراءة الملف
with open('brain.py', 'r', encoding='utf-8') as f:
    content = f.read()

# إصلاح المسافة البادئة للفواصل التي تسبق execute_full_pipeline
# نبحث عن النمط: سطر فاصل بدون مسافة بادئة، ثم سطر AGENT 22 بدون مسافة بادئة
pattern = r'^# -------------------------------------------------------------------------$\n^# AGENT 22: FULL PIPELINE ORCHESTRATOR$'

# نستبدله بنفس الفواصل ولكن مع 4 مسافات بادئة
replacement = r'    # -------------------------------------------------------------------------\n    # AGENT 22: FULL PIPELINE ORCHESTRATOR'

# تطبيق الاستبدال (مع علامة MULTILINE)
new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

# حفظ الملف المعدل
with open('brain_fixed.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ تم إنشاء brain_fixed.py مع المسافات البادئة المصححة.")
print("🚀 قم بتشغيل: python brain_fixed.py --repo . --full-audit")