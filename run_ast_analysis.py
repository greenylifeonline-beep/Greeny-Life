# run_ast_analysis.py
# ============================================================================
# تشغيل محرك AST على brain.py واستخراج الأدلة الخام
# ============================================================================

import sys
from pathlib import Path
sys.path.insert(0, '.')

from greenlines_brain.dna.ast_analyzer import ASTAnalyzer

def main():
    brain_path = Path("brain.py")
    if not brain_path.exists():
        print("❌ لم يتم العثور على brain.py")
        return

    analyzer = ASTAnalyzer(brain_path)
    findings = analyzer.analyze()
    report = analyzer.generate_report()

    print("🧠 تقرير التحليل المعجمي (AST)")
    print("=" * 60)
    print(f"📄 الملف المصدر: {report['source_file']}")
    print(f"📏 عدد الأسطر: {report['total_lines']}")
    print(f"📊 عدد النتائج الخام: {report['total_findings']}")
    print("\n📂 التوزيع حسب النوع:")
    for typ, count in report["findings_by_type"].items():
        print(f"   - {typ}: {count}")

    # حفظ التقرير
    output_path = Path("intelligence/ast_raw_findings_report.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    analyzer.save_report(output_path)

    print(f"\n📁 التقرير محفوظ في: {output_path}")
    print("\n💡 هذه هي الأدلة الخام. لم يتم تصنيفها بعد إلى معرفة.")

if __name__ == "__main__":
    main()
