import json
import os
import sys
import tempfile
import traceback

legacy = os.environ['E3_LEGACY_PROJECT']
sys.path.insert(0, legacy)
results = []

def check(name, action):
    try:
        detail = action()
        results.append({'asset': name, 'status': 'PASS', 'detail': detail})
    except Exception as exc:
        results.append({'asset': name, 'status': 'FAIL', 'detail': f'{type(exc).__name__}: {exc}', 'traceback': traceback.format_exc()})

def graph_check():
    from greenlines_brain.graph import KnowledgeGraph
    graph = KnowledgeGraph()
    graph.add_entity('country', 'EG', {'name': 'Egypt', 'code': 'EG'})
    graph.add_entity('market', 'NO', {'name': 'Norway', 'code': 'NO'})
    graph.add_relation('country', 'EG', 'exports_to', 'market', 'NO')
    assert graph.get_entity('country', 'EG')['code'] == 'EG'
    assert graph.find_node_by_name('egypt') == [('country', 'EG')]
    assert graph.get_related('country', 'EG', 'exports_to') == [('market', 'NO', 'exports_to')]
    assert graph.find_path('country', 'EG', 'market', 'NO')
    restored = KnowledgeGraph.from_dict(graph.to_dict())
    assert restored.get_related('country', 'EG', 'exports_to') == [('market', 'NO', 'exports_to')]
    return 'entity/relation/search/path/serialization round-trip passed; in-memory only'

def evidence_check():
    from greenlines_brain.evidence_layer import create_evidence_from_finding, EvidenceType
    finding = {'id': 'f-1', 'type': 'FunctionDef', 'stable_fingerprint': 'fp-1', 'line_start': 2, 'line_end': 4,
               'col_start': 0, 'col_end': 1, 'module': 'sample', 'function_name': 'verify', 'raw': 'def verify(): pass',
               'normalized_source': 'def verify(): pass', 'source_snippet': 'def verify(): pass'}
    evidence = create_evidence_from_finding(finding)
    assert evidence.type == EvidenceType.FUNCTION
    payload = evidence.to_dict()
    assert payload['stable_fingerprint'] == 'fp-1' and payload['function_name'] == 'verify'
    return 'AST finding -> typed evidence conversion passed; no project input/output file used'

def repository_check():
    from pathlib import Path
    from greenlines_brain.repository.json_repo import JSONKnowledgeRepository
    with tempfile.TemporaryDirectory() as work:
        path = Path(work) / 'knowledge.json'
        path.write_text(json.dumps({'entities': [{'name':'country','id':'EG','title':'Egypt'}],
                                    'business_rules': [{'condition':'honey export requires review'}],
                                    'relationships': [{'source_type':'country','source_id':'EG','target_id':'NO'}],
                                    'evidence': [{'source':'EG','id':'e-1'}]}), encoding='utf-8')
        repo = JSONKnowledgeRepository(path)
        assert repo.get_entity('country', 'EG')['title'] == 'Egypt'
        assert len(repo.get_relationships('country', 'EG')) == 1
        assert len(repo.get_rules('export')) == 1
        assert len(repo.get_evidence('EG')) == 1
        assert repo.search('honey')
    return 'temporary JSON repository read/search passed; temporary data was outside legacy project'

def contract_check():
    from greenlines_brain.contract import ConfidenceLevel, EvidenceType, Evidence, Decision
    evidence = Evidence(source='harness', evidence_type=EvidenceType.VALIDATION, content='checked', confidence=ConfidenceLevel.HIGH)
    decision = Decision(decision_id='d-1', recommendation='review', reasoning='harness', evidence=[evidence],
                        confidence=ConfidenceLevel.HIGH, risks=[], constraints=[], assumptions=[], alternatives=[],
                        entity_scope='egypt', expected_outcome='none')
    assert decision.evidence[0].source == 'harness'
    return 'brain contract data structures instantiate correctly; no decision engine was invoked'

check('KnowledgeGraph', graph_check)
check('ImplementationEvidenceLayer', evidence_check)
check('JSONKnowledgeRepository', repository_check)
check('BrainContractDataStructures', contract_check)

print(json.dumps({'harness': 'E3_LEGACY_PURE_ASSET_HARNESS_V1', 'legacyProject': legacy, 'results': results}, ensure_ascii=False))
if any(item['status'] == 'FAIL' for item in results):
    raise SystemExit(1)