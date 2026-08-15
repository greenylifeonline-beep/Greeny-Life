import json, os, sys, tempfile, traceback
from pathlib import Path
legacy=os.environ['E3_LEGACY_PROJECT'];sys.path.insert(0,legacy)
result={'asset':'GreenlinesBrainKernel','status':'UNKNOWN','tests':[],'finding':None,'recommendation':None}
try:
 from greenlines_brain.identity import Identity, EntityScope
 from greenlines_brain.repository.json_repo import JSONKnowledgeRepository
 from greenlines_brain.kernel import GreenlinesBrain
 with tempfile.TemporaryDirectory() as d:
  knowledge=Path(d)/'knowledge.json';knowledge.write_text(json.dumps({'entities':[],'business_rules':[],'master_data':[],'capabilities':[],'relationships':[],'workflows':[],'evidence':[]}),encoding='utf-8')
  identity=Identity(scope=EntityScope.EGYPT,legal_name='Harness Entity',country='Egypt',currency='EGP')
  brain=GreenlinesBrain(identity,JSONKnowledgeRepository(knowledge))
  defaults=[(r.subject,r.predicate,r.object,r.confidence) for r in brain.semantic_engine.relations]
  result['tests'].append({'name':'empty_knowledge_initialization','status':'PASS','detail':f'Kernel instantiated with empty temporary knowledge; relations={len(defaults)}'})
  fabricated=[r for r in defaults if r[0] in ('egypt','honey','spices','norway')]
  if fabricated:
   result['tests'].append({'name':'absence_of_evidence_behavior','status':'FAIL','detail':f'Kernel created default semantic relations: {fabricated}'})
   decision=brain.decide('export','egypt','honey','norway')
   result['tests'].append({'name':'decision_on_empty_knowledge','status':'PARTIAL','detail':f'confidence={decision.confidence.value}; recommendation={decision.recommendation}; evidence_count={len(decision.evidence)}'})
   result['status']='FAIL'
   result['finding']='P1: semantic engine fabricates trade/export relations when repository rules are empty. This violates fail-closed evidence governance.'
   result['recommendation']='DO_NOT_REUSE_AS_DECISION_ENGINE. Extract memory, repository and explicit-rule parsing only after a promoted copy removes defaults and enforces NEEDS_VERIFICATION.'
  else:
   result['tests'].append({'name':'absence_of_evidence_behavior','status':'PASS','detail':'No default trade relation was created.'})
   result['status']='PARTIAL';result['recommendation']='Further evidence and decision-path tests required.'
except Exception as e:
 result['status']='FAIL';result['finding']=f'{type(e).__name__}: {e}';result['recommendation']='DO_NOT_REUSE until import/runtime fault is understood.';result['traceback']=traceback.format_exc()
print(json.dumps(result,ensure_ascii=False))