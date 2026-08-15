# audit_ast_extraction.py
# ============================================================================
# تدقيق اكتمال استخراج AST
# ============================================================================
# يتحقق من أن ast_analyzer.py يستخرج كل أنواع AST المهمة
# ويقدم تقريراً عن النتائج المفقودة أو غير المغطاة.
# ============================================================================

import json
import ast
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set

# أنواع AST التي يجب أن يتم استخراجها
REQUIRED_AST_TYPES = {
    "Module": "الملف بأكمله",
    "FunctionDef": "تعريف دالة",
    "AsyncFunctionDef": "دالة غير متزامنة",
    "ClassDef": "تعريف كلاس",
    "Return": "عبارة return",
    "Delete": "حذف",
    "Assign": "تعيين قيمة",
    "AugAssign": "تعيين مع عملية",
    "AnnAssign": "تعيين مع نوع",
    "For": "حلقة for",
    "AsyncFor": "حلقة for غير متزامنة",
    "While": "حلقة while",
    "If": "شرط if",
    "With": "مدير سياق with",
    "AsyncWith": "مدير سياق غير متزامن",
    "Match": "مطابقة النمط (Python 3.10+)",
    "Raise": "رفع استثناء",
    "Try": "محاولة try",
    "Assert": "تأكيد assert",
    "Import": "استيراد import",
    "ImportFrom": "استيراد from ... import",
    "Global": "تعريف متغير عام",
    "Nonlocal": "تعريف متغير nonlocal",
    "Expr": "تعبير",
    "Pass": "pass",
    "Break": "break",
    "Continue": "continue",
    "Call": "استدعاء دالة",
    "Attribute": "وصول إلى سمة",
    "Subscript": "فهرسة",
    "Starred": "توسيع قائمة",
    "Name": "اسم متغير",
    "List": "قائمة",
    "Tuple": "صف",
    "Dict": "قاموس",
    "Set": "مجموعة",
    "Constant": "ثابت",
    "JoinedStr": "سلسلة منسقة (f-string)",
    "FormattedValue": "قيمة منسقة",
    "ListComp": "فهم قائمة",
    "SetComp": "فهم مجموعة",
    "DictComp": "فهم قاموس",
    "GeneratorExp": "تعبير مولد",
    "Await": "انتظار await",
    "Yield": "yield",
    "YieldFrom": "yield from",
    "Lambda": "دالة لامدا",
    "BoolOp": "عملية منطقية",
    "BinOp": "عملية ثنائية",
    "UnaryOp": "عملية أحادية",
    "Compare": "مقارنة",
    "IfExp": "تعبير شرطي",
}

class ASTExtractionAudit:
    def __init__(self, report_path: Path, source_path: Path):
        self.report_path = report_path
        self.source_path = source_path
        self.report = None
        self.source_tree = None
        self.findings_by_type = {}
        
    def load_report(self):
        with open(self.report_path, 'r', encoding='utf-8') as f:
            self.report = json.load(f)
        # تحويل findings_by_type إلى قاموس عددي
        raw_by_type = self.report.get("findings_by_type", {})
        self.findings_by_type = {k: v for k, v in raw_by_type.items()}
        
    def parse_source(self):
        """يحلل الكود المصدري الأصلي باستخدام AST لإحصاء جميع العقد."""
        source_code = self.source_path.read_text(encoding='utf-8')
        self.source_tree = ast.parse(source_code)
        
    def count_ast_nodes(self) -> Dict[str, int]:
        """يعد جميع العقد في الشجرة حسب النوع."""
        counters = defaultdict(int)
        for node in ast.walk(self.source_tree):
            node_type = node.__class__.__name__
            counters[node_type] += 1
        return dict(counters)
    
    def audit(self) -> Dict:
        self.load_report()
        self.parse_source()
        
        source_counts = self.count_ast_nodes()
        extracted_counts = self.findings_by_type
        
        result = {
            "required_types": {},
            "missing_types": [],
            "coverage_percentage": 0.0,
            "recommendations": []
        }
        
        # 1. التحقق من كل نوع مطلوب
        for ast_type, description in REQUIRED_AST_TYPES.items():
            in_source = source_counts.get(ast_type, 0)
            extracted = extracted_counts.get(ast_type, 0)
            result["required_types"][ast_type] = {
                "description": description,
                "in_source": in_source,
                "extracted": extracted,
                "status": "✅" if extracted >= in_source else "⚠️" if extracted > 0 else "❌"
            }
            if extracted == 0 and in_source > 0:
                result["missing_types"].append(ast_type)
        
        # 2. الأنواع الموجودة في التقرير ولكن غير مطلوبة (مفيدة)
        extra_types = set(extracted_counts.keys()) - set(REQUIRED_AST_TYPES.keys())
        if extra_types:
            result["recommendations"].append(f"تم استخراج أنواع إضافية: {', '.join(sorted(extra_types))}")
        
        # 3. حساب نسبة التغطية
        total_required = len(REQUIRED_AST_TYPES)
        covered = total_required - len(result["missing_types"])
        result["coverage_percentage"] = (covered / total_required) * 100 if total_required > 0 else 0
        
        # 4. تحليل شامل للـ findings
        findings = self.report.get("findings", [])
        result["total_findings"] = len(findings)
        
        # 5. التحقق من source location
        missing_location = 0
        for f in findings:
            if not f.get("line"):
                missing_location += 1
        result["findings_without_location"] = missing_location
        
        # 6. توصيات عامة
        if result["missing_types"]:
            result["recommendations"].append(f"❌ الأنواع المفقودة: {', '.join(result['missing_types'])} - أضفها إلى ast_analyzer.py")
        if missing_location > 0:
            result["recommendations"].append(f"⚠️ {missing_location} نتيجة بدون موقع (line). حسّن استخراج الموقع.")
        if result["coverage_percentage"] < 80:
            result["recommendations"].append("⚠️ التغطية أقل من 80%. راجع الأنواع المفقودة.")
        else:
            result["recommendations"].append("✅ التغطية جيدة. يمكن البدء في بناء المصنفات.")
        
        return result

def main():
    report_path = Path("intelligence/ast_raw_findings_report.json")
    source_path = Path("brain.py")
    
    if not report_path.exists():
        print("❌ التقرير غير موجود. قم بتشغيل run_ast_analysis.py أولاً.")
        return
    
    print("🧠 بدء تدقيق اكتمال استخراج AST...")
    print("=" * 60)
    
    auditor = ASTExtractionAudit(report_path, source_path)
    result = auditor.audit()
    
    print(f"📄 الملف المصدر: {source_path}")
    print(f"📊 إجمالي النتائج الخام: {result['total_findings']}")
    print(f"📈 نسبة تغطية الأنواع المطلوبة: {result['coverage_percentage']:.1f}%")
    print(f"🔍 النتائج بدون موقع: {result['findings_without_location']}")
    
    print("\n📂 تغطية الأنواع:")
    for ast_type, info in sorted(result["required_types"].items()):
        status = info["status"]
        desc = info["description"]
        in_src = info["in_source"]
        ext = info["extracted"]
        print(f"   {status} {ast_type:15s} ({desc})  المصدر: {in_src:3d}  المستخرج: {ext:3d}")
    
    if result["missing_types"]:
        print(f"\n❌ الأنواع المفقودة تماماً: {', '.join(result['missing_types'])}")
    
    print("\n📋 التوصيات:")
    for rec in result["recommendations"]:
        print(f"   {rec}")
    
    print("\n" + "="*60)
    print("✅ اكتمل التدقيق.")
    
    # حفظ التقرير الكامل
    output_path = Path("intelligence/ast_extraction_audit_report.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    print(f"📁 التقرير محفوظ في: {output_path}")

if __name__ == "__main__":
    main()
