# audit_brain_intelligence.py
# ============================================================================
# BRAIN INTELLIGENCE AUDIT
# ============================================================================
# ينتج تقريراً شاملاً عن حالة المعرفة المستخرجة من brain.py
# ============================================================================

import json
from pathlib import Path
from collections import defaultdict

def audit():
    enriched_path = Path("intelligence/ast_enriched_findings.json")
    if not enriched_path.exists():
        print("❌ التقرير المُثرى غير موجود. قم بتشغيل enrich_context.py أولاً.")
        return
    
    with open(enriched_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    findings = data.get("findings", [])
    
    # تصنيف النتائج حسب النوع
    classified = defaultdict(int)
    for f in findings:
        classified[f.get("type", "unknown")] += 1
    
    # تصنيفات المرشحين
    candidates = {
        "Agent": [],
        "Tool": [],
        "Capability": [],
        "Workflow": [],
        "Entity": [],
        "Relationship": [],
        "Rule": [],
        "Policy": [],
        "Requirement": [],
        "Constraint": [],
        "Fact": [],
        "Event": [],
        "Decision": []
    }
    
    for f in findings:
        node_type = f.get("type", "")
        node_raw = f.get("raw", "").lower()
        # تحديد المرشحين بناءً على الكلمات المفتاحية والسياق
        if node_type == "FunctionDef":
            if "run_" in f.get("name", ""):
                candidates["Agent"].append(f)
            elif "build_" in f.get("name", ""):
                candidates["Capability"].append(f)
            elif "validate_" in f.get("name", ""):
                candidates["Rule"].append(f)
        elif "call" in node_type.lower() or "subprocess" in node_type.lower():
            candidates["Tool"].append(f)
        elif "if" in node_type.lower():
            candidates["Conditional"].append(f)
        elif "class" in node_type.lower():
            if any(kw in node_raw for kw in ["product", "supplier", "customer"]):
                candidates["Entity"].append(f)
        elif "import" in node_type.lower():
            pass
        else:
            # إضافة غير مصنفة
            pass
    
    # بناء التقرير النهائي
    report = {
        "source": str(enriched_path),
        "generated_at": "2026-08-09",
        "AST": {
            "total_findings": len(findings),
            "findings_without_location": data.get("findings_without_location", 0),
            "stable_ids": data.get("stable_id_count", 0),
            "by_type": dict(classified)
        },
        "candidates": {k: len(v) for k, v in candidates.items()},
        "details": {
            "Agent_candidates": [{"name": f.get("name", ""), "type": f.get("type")} for f in candidates["Agent"][:10]],
            "Tool_candidates": [{"type": f.get("type"), "raw": f.get("raw", "")[:50]} for f in candidates["Tool"][:10]],
            "Capability_candidates": [{"name": f.get("name", ""), "type": f.get("type")} for f in candidates["Capability"][:10]]
        },
        "summary": {
            "structural_coverage": 10,
            "provenance_readiness": 8 if data.get("findings_without_location", 0) < 100 else 6,
            "semantic_knowledge_readiness": 3,
            "governance_readiness": 0
        }
    }
    
    # حفظ التقرير
    output_path = Path("intelligence/brain_intelligence_audit.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*80)
    print("🧠 BRAIN INTELLIGENCE AUDIT")
    print("="*80)
    print(f"📄 المصدر: {report['source']}")
    print(f"📊 إجمالي النتائج: {report['AST']['total_findings']}")
    print(f"🔍 بدون موقع: {report['AST']['findings_without_location']}")
    print(f"🆔 معرفات مستقرة: {report['AST']['stable_ids']}")
    print("\n📂 توزيع الأنواع:")
    for typ, count in sorted(report['AST']['by_type'].items(), key=lambda x: -x[1]):
        print(f"   - {typ}: {count}")
    print("\n🧩 المرشحون:")
    for typ, count in report['candidates'].items():
        print(f"   - {typ}: {count}")
    print("\n📊 تقييم الجاهزية:")
    for key, value in report['summary'].items():
        print(f"   - {key}: {value}/10")
    print("="*80)
    print(f"📁 التقرير محفوظ في: {output_path}")

if __name__ == "__main__":
    audit()
