# greenlines_brain/graph.py
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, deque

class KnowledgeGraph:
    def __init__(self):
        self.nodes: Dict[str, Dict[str, Dict]] = defaultdict(dict)
        self.edges: List[Tuple[str, str, str, str, str]] = []
        self.edge_index: Dict[str, List[Tuple]] = defaultdict(list)
        self.name_to_nodes: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    
    def add_entity(self, entity_type: str, entity_id: str, data: Dict[str, Any]):
        self.nodes[entity_type][entity_id] = data
        name = data.get("name", entity_id).lower()
        self.name_to_nodes[name].append((entity_type, entity_id))
        # أيضاً نضيف synonyms محتملة من الـ data
        for key, value in data.items():
            if isinstance(value, str) and len(value) > 2:
                self.name_to_nodes[value.lower()].append((entity_type, entity_id))
    
    def add_relation(self, source_type: str, source_id: str, 
                     relation: str, target_type: str, target_id: str,
                     metadata: Dict[str, Any] = None):
        edge = (source_type, source_id, relation, target_type, target_id)
        self.edges.append(edge)
        key = f"{source_type}:{source_id}"
        self.edge_index[key].append((relation, target_type, target_id))
        rev_key = f"{target_type}:{target_id}"
        self.edge_index[rev_key].append((f"{relation}_reverse", source_type, source_id))
    
    def get_entity(self, entity_type: str, entity_id: str) -> Optional[Dict]:
        return self.nodes.get(entity_type, {}).get(entity_id)
    
    def get_related(self, entity_type: str, entity_id: str, 
                    relation: Optional[str] = None) -> List[Tuple[str, str, str]]:
        key = f"{entity_type}:{entity_id}"
        results = []
        for rel, tgt_type, tgt_id in self.edge_index.get(key, []):
            if relation is None or rel == relation or rel == f"{relation}_reverse":
                results.append((tgt_type, tgt_id, rel))
        return results
    
    def get_entities_by_type(self, entity_type: str) -> List[Tuple[str, Dict]]:
        return [(e_id, e_data) for e_id, e_data in self.nodes.get(entity_type, {}).items()]
    
    def get_all_relations(self, source_type: str, source_id: str) -> List[Dict]:
        results = []
        for tgt_type, tgt_id, rel in self.get_related(source_type, source_id):
            tgt_entity = self.get_entity(tgt_type, tgt_id)
            results.append({
                "source_type": source_type,
                "source_id": source_id,
                "relation": rel,
                "target_type": tgt_type,
                "target_id": tgt_id,
                "target_data": tgt_entity
            })
        return results
    
    def find_node_by_name(self, name: str) -> List[Tuple[str, str]]:
        """يبحث عن عقدة باسم معين (غير حساس لحالة الأحرف)."""
        name_lower = name.lower()
        # بحث مباشر
        if name_lower in self.name_to_nodes:
            return self.name_to_nodes[name_lower]
        # بحث جزئي
        results = []
        for key, nodes in self.name_to_nodes.items():
            if name_lower in key or key in name_lower:
                results.extend(nodes)
        return results
    
    def find_path(self, start_type: str, start_id: str, 
                  end_type: str, end_id: str = None,
                  max_depth: int = 4) -> List[List[Tuple]]:
        """
        يبحث عن جميع المسارات بين عقدتين باستخدام BFS.
        يعيد قائمة بالمسارات، كل مسار هو قائمة من (type, id, relation).
        """
        if end_id is None:
            # البحث عن أي عقدة من النوع المطلوب
            targets = list(self.nodes.get(end_type, {}).keys())
            if not targets:
                return []
            # جرب كل هدف
            all_paths = []
            for tid in targets:
                paths = self._bfs(start_type, start_id, end_type, tid, max_depth)
                all_paths.extend(paths)
            return all_paths
        return self._bfs(start_type, start_id, end_type, end_id, max_depth)
    
    def _bfs(self, start_type: str, start_id: str, 
             end_type: str, end_id: str, max_depth: int) -> List[List[Tuple]]:
        """BFS داخلي للبحث عن مسار واحد أو أكثر."""
        visited = set()
        queue = deque([[(start_type, start_id, None)]])
        visited.add(f"{start_type}:{start_id}")
        paths = []
        
        while queue and len(paths) < 5:  # حد أقصى 5 مسارات
            path = queue.popleft()
            last_type, last_id, _ = path[-1]
            
            if last_type == end_type and last_id == end_id:
                paths.append(path)
                continue
            
            if len(path) > max_depth:
                continue
            
            key = f"{last_type}:{last_id}"
            for rel, tgt_type, tgt_id in self.edge_index.get(key, []):
                new_key = f"{tgt_type}:{tgt_id}"
                if new_key not in visited:
                    visited.add(new_key)
                    new_path = path + [(tgt_type, tgt_id, rel)]
                    queue.append(new_path)
        
        return paths
    
    def to_dict(self) -> Dict:
        return {
            "nodes": {
                entity_type: {
                    entity_id: data
                    for entity_id, data in entities.items()
                }
                for entity_type, entities in self.nodes.items()
            },
            "edges": self.edges
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'KnowledgeGraph':
        graph = cls()
        for entity_type, entities in data.get("nodes", {}).items():
            for entity_id, entity_data in entities.items():
                graph.add_entity(entity_type, entity_id, entity_data)
        for edge in data.get("edges", []):
            if len(edge) == 5:
                graph.add_relation(*edge)
        return graph