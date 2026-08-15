import re

# اقرأ الملف الأصلي
with open('brain.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# ابحث عن السطر الذي يحتوي على "AGENT 22: FULL PIPELINE ORCHESTRATOR"
# وأضف 4 مسافات بادئة للسطر الذي يسبقه (الفاصل) وللسطر نفسه
fixed = False
new_lines = []
for i, line in enumerate(lines):
    # إذا وجدنا السطر الذي يحتوي على AGENT 22 مع مسافة بادئة خاطئة (أقل من 4)
    if '# AGENT 22: FULL PIPELINE ORCHESTRATOR' in line and not line.startswith('    '):
        # أضف 4 مسافات بادئة لهذا السطر
        new_lines.append('    ' + line.lstrip())
        # أيضاً أصلح السطر السابق إذا كان فاصلاً
        if i > 0 and '# -----' in lines[i-1] and not lines[i-1].startswith('    '):
            new_lines[-2] = '    ' + lines[i-1].lstrip()
        fixed = True
    else:
        new_lines.append(line)

if fixed:
    # احفظ الملف المعدل
    with open('brain_fixed.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("✅ تم إنشاء brain_fixed.py مع المسافات البادئة المصححة.")
    print("🚀 قم بتشغيل: python brain_fixed.py --repo . --full-audit")
else:
    print("⚠️ لم يتم العثور على السطر المطلوب. قد تكون المشكلة في مكان آخر.")