# greenlines_brain/repository/json_repo.py
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from .interface import KnowledgeRepository

class JSONKnowledgeRepository(KnowledgeRepository):
    def __init__(self, knowledge_path: Path):
        self.knowledge_path = knowledge_path
        self._knowledge = None
    
    def load_knowledge(self) -> Dict[str, Any]:
        if self._knowledge is None:
            if not self.knowledge_path.exists():
                print(f"Warning: Knowledge file not found: {self.knowledge_path}")
                return {"entities": [], "business_rules": [], "master_data": [], "capabilities": [], "relationships": [], "workflows": [], "evidence": []}
            with open(self.knowledge_path, 'r', encoding='utf-8') as f:
                self._knowledge = json.load(f)
        return self._knowledge
    
    def _load(self) -> Dict:
        return self.load_knowledge()
    
    def get_entity(self, entity_type: str, entity_id: str) -> Optional[Dict]:
        knowledge = self.load_knowledge()
        for entity in knowledge.get("entities", []):
            if entity.get("name") == entity_type and entity.get("id") == entity_id:
                return entity
        return None
    
    def find_entities(self, entity_type: str, filters: Dict = None) -> List[Dict]:
        knowledge = self.load_knowledge()
        result = []
        for entity in knowledge.get("entities", []):
            if entity.get("name") == entity_type:
                if filters:
                    match = True
                    for key, value in filters.items():
                        if entity.get(key) != value:
                            match = False
                            break
                    if match:
                        result.append(entity)
                else:
                    result.append(entity)
        return result
    
    def get_relationships(self, source_type: str, source_id: str) -> List[Dict]:
        knowledge = self.load_knowledge()
        return [r for r in knowledge.get("relationships", []) if r.get("source_type") == source_type and r.get("source_id") == source_id]
    
    def get_rules(self, domain: Optional[str] = None) -> List[Dict]:
        knowledge = self.load_knowledge()
        rules = knowledge.get("business_rules", [])
        if domain:
            return [r for r in rules if domain.lower() in r.get("condition", "").lower()]
        return rules
    
    def get_evidence(self, entity_id: str) -> List[Dict]:
        knowledge = self.load_knowledge()
        return [e for e in knowledge.get("evidence", []) if e.get("source") == entity_id]
    
    def find_evidence(self, *, product: str, destination: str) -> List[Dict]:
        matches = []
        for evidence in self.load_knowledge().get("evidence", []):
            scope = evidence.get("scope", {})
            if scope.get("product", "").lower() == product.lower() and scope.get("destination", "").lower() == destination.lower():
                matches.append(evidence)
        return matches

    def search(self, query: str) -> List[Dict]:
        knowledge = self.load_knowledge()
        results = []
        query_lower = query.lower()
        for entity in knowledge.get("entities", []):
            if query_lower in entity.get("name", "").lower():
                results.append(entity)
        for rule in knowledge.get("business_rules", []):
            if query_lower in rule.get("condition", "").lower():
                results.append(rule)
        return results
