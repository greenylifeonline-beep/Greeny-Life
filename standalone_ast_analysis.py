# standalone_ast_analysis.py
# ============================================================================
# تحليل AST مستقل - يستخرج كل أنواع العقد من brain.py
# ============================================================================

import ast
import json
from pathlib import Path
from collections import defaultdict

def analyze_ast(source_path):
    source_code = source_path.read_text(encoding='utf-8')
    tree = ast.parse(source_code)
    
    # إحصائيات العقد
    node_counts = defaultdict(int)
    findings = []
    
    for node in ast.walk(tree):
        node_type = node.__class__.__name__
        node_counts[node_type] += 1
        
        # جمع معلومات مفصلة
        finding = {
            "type": node_type,
            "line": getattr(node, 'lineno', None),
            "col": getattr(node, 'col_offset', None),
            "raw": ast.unparse(node)[:200] if hasattr(ast, 'unparse') else str(node)[:200]
        }
        # إضافة اسم الدالة إذا كانت عقدة FunctionDef
        if node_type == "FunctionDef":
            finding["name"] = node.name
        elif node_type == "ClassDef":
            finding["name"] = node.name
        findings.append(finding)
    
    # تقرير
    report = {
        "source_file": str(source_path),
        "total_lines": len(source_code.splitlines()),
        "total_findings": len(findings),
        "findings_by_type": dict(node_counts),
        "findings": findings
    }
    return report

def main():
    brain_path = Path("brain.py")
    if not brain_path.exists():
        print("❌ brain.py غير موجود")
        return
    
    print("🧠 تحليل AST لـ brain.py ...")
    report = analyze_ast(brain_path)
    
    # حفظ التقرير
    output_path = Path("intelligence/ast_raw_findings_report.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"✅ تم حفظ التقرير في: {output_path}")
    print(f"📊 إجمالي النتائج: {report['total_findings']}")
    print("📂 التوزيع حسب النوع:")
    for typ, count in sorted(report["findings_by_type"].items(), key=lambda x: -x[1]):
        print(f"   - {typ}: {count}")

if __name__ == "__main__":
    main()
