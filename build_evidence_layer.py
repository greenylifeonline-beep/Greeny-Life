# build_evidence_layer.py
# ============================================================================
# بناء Implementation Evidence Layer من AST Findings
# ============================================================================

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List

from greenlines_brain.evidence_layer import create_evidence_from_finding, ImplementationEvidence

def build_evidence_layer():
    # قراءة الملف المُثرى
    enriched_path = Path("intelligence/ast_enriched_findings_v2.json")
    if not enriched_path.exists():
        print("❌ الملف المُثرى غير موجود")
        return
    
    with open(enriched_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    findings = data.get("findings", [])
    
    # تحويل كل Finding إلى Evidence
    evidences = []
    evidence_by_fingerprint = {}
    
    for finding in findings:
        if finding.get("stable_fingerprint"):
            ev = create_evidence_from_finding(finding)
            evidences.append(ev.to_dict())
            evidence_by_fingerprint[ev.stable_fingerprint] = ev.to_dict()
    
    # حفظ الأدلة
    output_path = Path("intelligence/implementation_evidence.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(evidences, f, indent=2, ensure_ascii=False)
    
    print(f"✅ تم إنشاء {len(evidences)} دليل تنفيذي")
    print(f"📁 محفوظ في: {output_path}")
    
    # إحصائيات
    types = defaultdict(int)
    for ev in evidences:
        types[ev['type']] += 1
    
    print("\n📊 توزيع أنواع الأدلة:")
    for ev_type, count in sorted(types.items(), key=lambda x: -x[1]):
        print(f"   - {ev_type}: {count}")

if __name__ == "__main__":
    build_evidence_layer()
