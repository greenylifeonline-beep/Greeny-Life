import json, os, sys, tempfile, traceback
try:
 sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
except AttributeError: pass
legacy=os.environ['E3_LEGACY_PROJECT'];sys.path.insert(0,legacy)
results=[]
def check(name, action):
 try: results.append({'test':name,'status':'PASS','detail':action()})
 except Exception as e: results.append({'test':name,'status':'FAIL','detail':f'{type(e).__name__}: {e}','traceback':traceback.format_exc()})

def memory_lifecycle():
 from greenlines_brain.kernel import InstitutionalMemory, MemoryLevel
 from greenlines_brain.contract import ConfidenceLevel
 m=InstitutionalMemory();m.store('policy-1',{'version':1},MemoryLevel.INSTITUTIONAL,source='official-source',confidence=ConfidenceLevel.HIGH)
 first=m.retrieve('policy-1');assert first and first.source=='official-source' and first.timestamp and first.confidence==ConfidenceLevel.HIGH
 m.store('policy-1',{'version':2},MemoryLevel.INSTITUTIONAL,source='official-source-v2',confidence=ConfidenceLevel.MEDIUM)
 second=m.retrieve('policy-1');assert second.value['version']==2 and second.source=='official-source-v2'
 assert m.search('policy') and m.search('version')
 return 'create/store/retrieve/overwrite/search preserves current source/timestamp/confidence in memory only'

def memory_limitations():
 from greenlines_brain.kernel import InstitutionalMemory, MemoryLevel
 from greenlines_brain.contract import ConfidenceLevel
 m=InstitutionalMemory();m.store('fact',{'x':1},MemoryLevel.LONG_TERM,source='s',confidence=ConfidenceLevel.HIGH)
 entry=m.retrieve('fact')
 missing=[name for name in ('version','expiry','invalidated','evidence_type','audit_id') if not hasattr(entry,name)]
 if missing: return 'PARTIAL: no lifecycle/provenance fields for '+', '.join(missing)
 return 'PASS: lifecycle fields present'

def explicit_rule_parser():
 from greenlines_brain.graph import KnowledgeGraph
 from greenlines_brain.kernel import SemanticReasoningEngine
 class Repo:
  def __init__(self,rules): self.rules=rules
  def get_rules(self,domain=None): return self.rules
 empty=SemanticReasoningEngine(Repo([]),KnowledgeGraph())
 defaults=[(r.subject,r.predicate,r.object) for r in empty.relations]
 assert defaults, 'legacy parser did not expose the known fallback behavior'
 explicit=SemanticReasoningEngine(Repo([{'condition':'honey requires organic certification','legacy_origin':'official'}]),KnowledgeGraph())
 relations=[(r.subject,r.predicate,r.object,r.confidence) for r in explicit.relations]
 assert relations == [('honey','requires','organic',0.8)]
 conclusions=explicit.apply_rules(['honey'],explicit.repository.get_rules())
 assert conclusions
 return {'emptyKnowledgeFallback':defaults,'explicitRuleRelations':relations,'explicitRuleConclusions':conclusions}

def parser_conflict_and_staleness():
 from greenlines_brain.graph import KnowledgeGraph
 from greenlines_brain.kernel import SemanticReasoningEngine
 class Repo:
  def get_rules(self,domain=None): return [
    {'condition':'honey requires organic certification','legacy_origin':'source-a','status':'valid'},
    {'condition':'honey requires halal certification','legacy_origin':'source-b','status':'conflicting'},
    {'condition':'honey requires obsolete certification','legacy_origin':'source-c','status':'stale'}]
 engine=SemanticReasoningEngine(Repo(),KnowledgeGraph());rels=[(r.subject,r.predicate,r.object) for r in engine.relations]
 assert len(rels)==3
 return 'PARTIAL: parser includes conflicting/stale rules without status, time or authority filtering: '+str(rels)

check('InstitutionalMemoryLifecycle',memory_lifecycle)
check('InstitutionalMemoryGovernance',memory_limitations)
check('SemanticRuleParserExplicitRule',explicit_rule_parser)
check('SemanticRuleParserConflictStaleness',parser_conflict_and_staleness)
print(json.dumps({'results':results},ensure_ascii=False))