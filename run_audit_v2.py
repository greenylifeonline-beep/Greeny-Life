import json
from pathlib import Path
import sys
sys.path.insert(0, '.')

from audit_brain_intelligence_v2 import BrainIntelligenceAudit

# تشغيل التدقيق
audit = BrainIntelligenceAudit(Path('brain.py'), Path('intelligence/ast_enriched_findings_v2.json'))
report = audit.analyze()

# حفظ التقرير
output_path = Path('intelligence/brain_intelligence_audit_v2_final.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

# عرض النتائج
print("\n" + "="*80)
print("🧠 GREENLINES BRAIN — EXTRACTION AUDIT v2")
print("="*80)
print(f"📄 المصدر: {report['source']['file']}")
print("\n📊 RAW FINDINGS")
print(f"   Total:                         {report['raw_findings']['total']}")
print(f"   Retained:                      {report['raw_findings']['retained']}")
print(f"   Lost:                          {report['raw_findings']['lost']}")

print("\n📍 LOCATION")
loc = report['location']
print(f"   Direct location:               {loc['direct_location']}")
print(f"   Inherited location:            {loc['inherited_location']}")
print(f"   Inherently unlocated:          {loc['inherently_unlocated']}")
print(f"   Actually missing:              {loc['actually_missing']}")

print("\n🆔 IDENTITY")
print(f"   Stable ID:                     {report['identity']['stable_id']}")
print(f"   Non-semantic:                  {report['identity']['non_semantic']}")
print(f"   Identity missing:              {report['identity']['identity_missing']}")

print("\n📂 CONTEXT")
print(f"   With function context:         {report['context']['with_function_context']}")
print(f"   With class context:            {report['context']['with_class_context']}")
print(f"   Coverage:                      {report['context']['coverage_percentage']:.1f}%")

print("\n📎 PROVENANCE")
print(f"   With source:                   {report['provenance']['with_source']}")
print(f"   Coverage:                      {report['provenance']['coverage_percentage']:.1f}%")

print("\n🧩 SEMANTIC ELIGIBILITY")
print(f"   Eligible findings:             {report['semantic_eligibility']['eligible']}")
print(f"   Non-semantic findings:         {report['semantic_eligibility']['non_semantic']}")
print(f"   Eligible percentage:           {report['semantic_eligibility']['eligible_percentage']:.1f}%")

print("\n📊 READINESS SCORES")
for key, value in report['readiness'].items():
    print(f"   {key}: {value:.1f}/10")

print(f"\n📌 OVERALL STATUS: {report['overall_status']}")

print("\n📋 RECOMMENDATIONS:")
for rec in report['recommendations']:
    print(f"   {rec}")
print("="*80)
print(f"📁 التقرير محفوظ في: {output_path}")
