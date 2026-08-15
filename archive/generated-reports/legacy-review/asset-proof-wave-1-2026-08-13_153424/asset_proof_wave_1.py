import json, os, sys, tempfile, traceback
legacy = os.environ['E3_LEGACY_PROJECT']
sys.path.insert(0, legacy)
outcomes=[]
def record(asset, status, evidence, finding=None):
    outcomes.append({'asset':asset,'status':status,'evidence':evidence,'finding':finding})

try:
    from greenlines_brain.graph import KnowledgeGraph
    g=KnowledgeGraph(); g.add_entity('country','EG',{'name':'Egypt','code':'EG'}); g.add_entity('market','NO',{'name':'Norway','code':'NO'}); g.add_relation('country','EG','exports_to','market','NO')
    lookup=g.find_node_by_name('egypt'); paths=g.find_path('country','EG','market','NO'); restored=KnowledgeGraph.from_dict(g.to_dict())
    assert ('country','EG') in lookup and paths and restored.get_related('country','EG','exports_to')
    if len(lookup) != len(set(lookup)):
        record('KnowledgeGraph','PARTIAL','entity/relation/path/serialization behavior executed successfully in memory','find_node_by_name returns duplicate entity references when `name` is also indexed again during attribute iteration.')
    else:
        record('KnowledgeGraph','PASS','entity/relation/search/path/serialization behavior executed successfully in memory')
except Exception as e:
    record('KnowledgeGraph','FAIL',f'{type(e).__name__}: {e}',traceback.format_exc())

try:
    from greenlines_brain.evidence_layer import create_evidence_from_finding
    finding={'id':'f-1','type':'FunctionDef','stable_fingerprint':'fp-1','line_start':1,'line_end':2,'col_start':0,'col_end':0,'module':'sample','raw':'def f(): pass','normalized_source':'def f(): pass','source_snippet':'def f(): pass'}
    result=create_evidence_from_finding(finding).to_dict(); assert result['stable_fingerprint']=='fp-1'
    record('ImplementationEvidenceLayer','PASS','finding-to-evidence conversion executed in isolated harness')
except Exception as e:
    record('ImplementationEvidenceLayer','FAIL',f'{type(e).__name__}: {e}','Import fails before conversion: dataclass field ordering has a default field before required raw/normalized/source_snippet fields.')

try:
    from pathlib import Path
    from greenlines_brain.repository.json_repo import JSONKnowledgeRepository
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/'knowledge.json';p.write_text(json.dumps({'entities':[{'name':'country','id':'EG'}],'business_rules':[{'condition':'export review'}],'relationships':[{'source_type':'country','source_id':'EG'}],'evidence':[{'source':'EG'}]}),encoding='utf-8')
        r=JSONKnowledgeRepository(p);assert r.get_entity('country','EG');assert r.get_rules('export');assert r.get_relationships('country','EG');assert r.get_evidence('EG')
    record('JSONKnowledgeRepository','PASS','temporary JSON load/entity/rule/relationship/evidence retrieval executed; no legacy data was written')
except Exception as e:
    record('JSONKnowledgeRepository','FAIL',f'{type(e).__name__}: {e}',traceback.format_exc())

try:
    from greenlines_brain.contract import ConfidenceLevel, EvidenceType, Evidence, Decision
    ev=Evidence(source='harness',evidence_type=EvidenceType.VALIDATION,content='ok',confidence=ConfidenceLevel.HIGH)
    decision=Decision(decision_id='d',recommendation='review',reasoning='isolated',evidence=[ev],confidence=ConfidenceLevel.HIGH,risks=[],constraints=[],assumptions=[],alternatives=[],entity_scope='egypt',expected_outcome='review')
    assert decision.evidence[0].source=='harness'
    record('BrainContractDataStructures','PASS','Evidence and Decision contracts instantiate and preserve typed data')
except Exception as e:
    record('BrainContractDataStructures','FAIL',f'{type(e).__name__}: {e}',traceback.format_exc())

print(json.dumps({'outcomes':outcomes},ensure_ascii=False))