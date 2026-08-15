# greenlines_brain/kernel.py
# =============================================================================
# Greenlines Brain Kernel v1.0 - العقل المؤسسي القابل للتشغيل
# =============================================================================

import uuid
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .contract import (
    BrainContract, Decision, AskResult, Evidence, 
    ConfidenceLevel, EvidenceType, DecisionStatus
)
from .identity import Identity, EntityScope
from .repository.interface import KnowledgeRepository
from .graph import KnowledgeGraph


# =============================================================================
# 1. الذاكرة المؤسسية (Institutional Memory)
# =============================================================================

class MemoryLevel(Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    INSTITUTIONAL = "institutional"


@dataclass
class MemoryEntry:
    key: str
    value: Any
    level: MemoryLevel
    timestamp: str
    source: Optional[str] = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class InstitutionalMemory:
    def __init__(self):
        self.short_term: Dict[str, MemoryEntry] = {}
        self.long_term: Dict[str, MemoryEntry] = {}
        self.institutional: Dict[str, MemoryEntry] = {}
    
    def store(self, key: str, value: Any, level: MemoryLevel, 
              source: Optional[str] = None, 
              confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM) -> None:
        entry = MemoryEntry(
            key=key, value=value, level=level,
            timestamp=datetime.now().isoformat(),
            source=source, confidence=confidence
        )
        if level == MemoryLevel.SHORT_TERM:
            self.short_term[key] = entry
        elif level == MemoryLevel.LONG_TERM:
            self.long_term[key] = entry
        else:
            self.institutional[key] = entry
    
    def retrieve(self, key: str) -> Optional[MemoryEntry]:
        if key in self.short_term:
            return self.short_term[key]
        if key in self.long_term:
            return self.long_term[key]
        if key in self.institutional:
            return self.institutional[key]
        return None
    
    def search(self, query: str, level: Optional[MemoryLevel] = None) -> List[MemoryEntry]:
        results = []
        levels = [level] if level else [MemoryLevel.SHORT_TERM, MemoryLevel.LONG_TERM, MemoryLevel.INSTITUTIONAL]
        for lvl in levels:
            pool = self._get_pool(lvl)
            for entry in pool.values():
                if query.lower() in str(entry.value).lower() or query.lower() in entry.key.lower():
                    results.append(entry)
        return results
    
    def clear_short_term(self) -> None:
        self.short_term.clear()
    
    def get_summary(self) -> Dict[str, int]:
        return {
            "short_term": len(self.short_term),
            "long_term": len(self.long_term),
            "institutional": len(self.institutional)
        }
    
    def _get_pool(self, level: MemoryLevel) -> Dict[str, MemoryEntry]:
        if level == MemoryLevel.SHORT_TERM:
            return self.short_term
        elif level == MemoryLevel.LONG_TERM:
            return self.long_term
        else:
            return self.institutional


# =============================================================================
# 2. محرك الاستدلال الدلالي (Semantic Reasoning Engine)
# =============================================================================

class SemanticRelation:
    def __init__(self, subject: str, predicate: str, object: str, confidence: float = 1.0):
        self.subject = subject.lower()
        self.predicate = predicate.lower()
        self.object = object.lower()
        self.confidence = confidence
    
    def matches(self, subject: str = None, predicate: str = None, object: str = None) -> bool:
        if subject and subject.lower() != self.subject:
            return False
        if predicate and predicate.lower() != self.predicate:
            return False
        if object and object.lower() != self.object:
            return False
        return True
    
    def to_string(self) -> str:
        return f"{self.subject} → {self.predicate} → {self.object}"


class SemanticReasoningEngine:
    def __init__(self, repository: KnowledgeRepository, graph: KnowledgeGraph):
        self.repository = repository
        self.graph = graph
        self.relations: List[SemanticRelation] = []
        self._load_relations_from_rules()
    
    def _load_relations_from_rules(self) -> None:
        rules = self.repository.get_rules()
        for rule in rules:
            condition = rule.get("condition", "")
            relations = self._parse_rule_to_relations(condition)
            for rel in relations:
                rel.confidence = 0.8
                self.relations.append(rel)
        # إضافة علاقات افتراضية من الرسم البياني
        # هذا يضمن أن لدينا على الأقل بعض العلاقات الأساسية
    def _parse_rule_to_relations(self, rule_text: str) -> List[SemanticRelation]:
        relations = []
        rule_lower = rule_text.lower()
        
        if "requires" in rule_lower:
            parts = rule_lower.split("requires")
            if len(parts) == 2:
                subject = parts[0].strip()
                object_part = parts[1].strip()
                req_match = re.search(r'([a-z_]+)\s*(?:certification|standard|approval)', object_part)
                if req_match:
                    req_entity = req_match.group(1)
                    relations.append(SemanticRelation(subject, "requires", req_entity))
                else:
                    relations.append(SemanticRelation(subject, "requires", object_part))
            return relations
        
        if "→" in rule_lower:
            parts = [p.strip() for p in rule_lower.split("→")]
            if len(parts) >= 3:
                subject = parts[0]
                product = None
                destination = None
                result = None
                for part in parts[1:]:
                    if "is allowed" in part:
                        result = "allowed"
                    elif "is not allowed" in part or "is prohibited" in part:
                        result = "not_allowed"
                    elif part in ["norway", "eu", "gcc", "usa", "uk", "uae"]:
                        destination = part
                    else:
                        product = part
                if product:
                    relations.append(SemanticRelation(subject, "exports", product))
                if product and destination:
                    relations.append(SemanticRelation(product, "export_to", destination))
                if destination and result:
                    relations.append(SemanticRelation(destination, "result", result))
            return relations
        
        if "certification" in rule_lower or "certificate" in rule_lower:
            cert_match = re.search(r'([a-z_]+)\s+certification', rule_lower)
            if cert_match:
                entity = cert_match.group(1)
                relations.append(SemanticRelation(entity, "requires", "certification"))
        
        # محاولة استخراج علاقات من أي قاعدة
        
        return relations
    
    def add_relation(self, subject: str, predicate: str, object: str, confidence: float = 1.0) -> None:
        self.relations.append(SemanticRelation(subject, predicate, object, confidence))
    
    def query(self, subject: str = None, predicate: str = None, object: str = None) -> List[SemanticRelation]:
        results = []
        for rel in self.relations:
            if rel.matches(subject, predicate, object):
                results.append(rel)
        return results
    
    def reason_chain(self, start_subject: str, target_predicate: str = None, max_depth: int = 3) -> List[List[SemanticRelation]]:
        chains = []
        self._bfs_chains(start_subject.lower(), target_predicate.lower() if target_predicate else None, max_depth, [], chains)
        return chains
    
    def _bfs_chains(self, current: str, target_predicate: Optional[str], depth: int, 
                    current_chain: List[SemanticRelation], all_chains: List[List[SemanticRelation]]) -> None:
        if depth == 0:
            return
        for rel in self.relations:
            if rel.subject == current:
                if any(r.subject == rel.object for r in current_chain):
                    continue
                new_chain = current_chain + [rel]
                if target_predicate and rel.predicate == target_predicate:
                    all_chains.append(new_chain)
                    continue
                if depth == 1:
                    all_chains.append(new_chain)
                    continue
                self._bfs_chains(rel.object, target_predicate, depth - 1, new_chain, all_chains)
    
    # =========================================================================
    # هذه هي الدالة المفقودة التي كانت تسبب الخطأ
    # =========================================================================
    def apply_rules(self, premises: List[str], rules: Optional[List[Dict]] = None) -> List[str]:
        """
        يطبق القواعد على المقدمات ويعيد الاستنتاجات النصية.
        هذه الدالة مطلوبة من kernel.py
        """
        if rules is None:
            rules = self.repository.get_rules()
        
        conclusions = []
        structured_rules = []
        
        for rule in rules:
            rule_condition = rule.get("condition", "")
            structured = self._parse_rule_to_relations(rule_condition)
            if structured:
                for rel in structured:
                    structured_rules.append({
                        "subject": rel.subject,
                        "predicate": rel.predicate,
                        "object": rel.object,
                        "confidence": rel.confidence,
                        "comment": rule.get("comment", ""),
                        "legacy_origin": rule.get("legacy_origin", "unknown")
                    })
            else:
                # محاولة استخراج من النص مباشرة
                condition_lower = rule_condition.lower()
                for premise in premises:
                    if premise.lower() in condition_lower:
                        conclusions.append(f"⚖️ قاعدة ذات صلة: {rule_condition} - {rule.get('comment', '')} (المقدمة: {premise})")
        
        # إذا وجدنا علاقات منظمة، قم بتطبيقها على المقدمات
        if structured_rules:
            for premise in premises:
                premise_lower = premise.lower()
                for rule in structured_rules:
                    if premise_lower in rule["subject"] or premise_lower in rule["object"]:
                        conclusions.append(f"⚖️ علاقة: {rule['subject']} → {rule['predicate']} → {rule['object']} (المقدمة: {premise})")
                        if rule.get("comment"):
                            conclusions.append(f"   📝 {rule['comment']}")
        
        if not conclusions:
            conclusions.append("لم يتم العثور على قاعدة تنطبق على المقدمات المقدمة.")
        
        return conclusions
    
    def evaluate_export_scenario(self, subject: str, product: str, destination: str) -> Dict[str, Any]:
        result = {
            "allowed": False,
            "reasoning_chain": [],
            "evidence": [],
            "requirements": [],
            "missing_requirements": [],
            "confidence": ConfidenceLevel.LOW,
            "next_actions": []
        }
        
        chains = self.reason_chain(subject.lower(), "export_to", max_depth=4)
        found_path = False
        for chain in chains:
            path_parts = []
            path_products = []
            path_destinations = []
            for rel in chain:
                path_parts.append(f"{rel.subject} → {rel.predicate} → {rel.object}")
                if product.lower() in rel.subject or product.lower() in rel.object:
                    path_products.append(rel)
                if destination.lower() in rel.subject or destination.lower() in rel.object:
                    path_destinations.append(rel)
            if path_products and path_destinations:
                found_path = True
                result["reasoning_chain"] = path_parts
                result["evidence"].append({
                    "source": "semantic_reasoning",
                    "chain": path_parts,
                    "type": "export_path"
                })
                result["confidence"] = ConfidenceLevel.MEDIUM
                break
        
        if found_path:
            req_relations = self.query(subject=destination.lower(), predicate="requires")
            for rel in req_relations:
                result["requirements"].append(rel.object)
                result["evidence"].append({
                    "source": "semantic_reasoning",
                    "requirement": rel.object,
                    "relation": rel.to_string()
                })
            product_req = self.query(subject=product.lower(), predicate="requires")
            for rel in product_req:
                if rel.object not in result["requirements"]:
                    result["requirements"].append(rel.object)
                    result["evidence"].append({
                        "source": "semantic_reasoning",
                        "requirement": rel.object,
                        "relation": rel.to_string()
                    })
        
        for rel in self.relations:
            if rel.subject == destination.lower() and rel.predicate == "result":
                if rel.object == "allowed":
                    result["allowed"] = True
                    result["confidence"] = ConfidenceLevel.HIGH
                elif rel.object == "not_allowed":
                    result["allowed"] = False
                    result["confidence"] = ConfidenceLevel.HIGH
        
        if result["requirements"]:
            product_entity = self.graph.find_node_by_name(product)
            if product_entity:
                p_type, p_id = product_entity[0]
                entity_data = self.graph.get_entity(p_type, p_id)
                if entity_data:
                    certs = entity_data.get("certifications", [])
                    for req in result["requirements"]:
                        if req not in " ".join(certs).lower():
                            result["missing_requirements"].append(req)
            if result["missing_requirements"]:
                result["next_actions"].append(f"تحقق من المتطلبات الناقصة: {', '.join(result['missing_requirements'])}")
        
        if not found_path:
            result["reasoning_chain"] = ["لم يتم العثور على مسار استدلالي مباشر"]
            result["next_actions"].append(f"راجع لوائح التصدير الخاصة بـ {destination}")
            result["confidence"] = ConfidenceLevel.LOW
        
        return result


# =============================================================================
# 3. نواة العقل الأساسية (GreenlinesBrain)
# =============================================================================

class GreenlinesBrain(BrainContract):
    def __init__(self, identity: Identity, repository: KnowledgeRepository):
        self.identity = identity
        self.repository = repository
        self.memory = InstitutionalMemory()
        self.decisions_log: List[Dict[str, Any]] = []
        
        self.knowledge = repository.load_knowledge()
        print(f"📚 تم تحميل المعرفة: {len(self.knowledge.get('entities', []))} كيان، "
              f"{len(self.knowledge.get('business_rules', []))} قاعدة، "
              f"{len(self.knowledge.get('capabilities', []))} قدرة")
        
        self.graph = self._build_graph_from_knowledge(self.knowledge)
        print(f"📊 تم بناء الرسم البياني: {len(self.graph.nodes)} عقدة، {len(self.graph.edges)} علاقة")
        
        self._load_institutional_memory()
        
        self.semantic_engine = SemanticReasoningEngine(repository, self.graph)
        print(f"🧩 تم تحميل {len(self.semantic_engine.relations)} علاقة دلالية")
        
        self.memory.store(
            key="session_start",
            value=datetime.now().isoformat(),
            level=MemoryLevel.SHORT_TERM,
            source="kernel",
            confidence=ConfidenceLevel.HIGH
        )
        
        print(f"🧠 تم تهيئة العقل لنطاق: {identity.scope.value}")
        print(f"   الكيان القانوني: {identity.legal_name}")
        print(f"   الوجهات المسموح بها: {identity.get_allowed_exports()}")
    
    # -------------------------------------------------------------------------
    # بناء الرسم البياني
    # -------------------------------------------------------------------------
    
    def _build_graph_from_knowledge(self, knowledge: Dict[str, Any]) -> KnowledgeGraph:
        graph = KnowledgeGraph()
        for entity in knowledge.get("entities", []):
            entity_type = entity.get("name", "Unknown")
            entity_id = entity.get("id", entity_type)
            graph.add_entity(entity_type, entity_id, entity)
        for rel in knowledge.get("relationships", []):
            graph.add_relation(
                source_type=rel.get("source_type", "Unknown"),
                source_id=rel.get("source_id", "unknown"),
                relation=rel.get("relation", "related_to"),
                target_type=rel.get("target_type", "Unknown"),
                target_id=rel.get("target_id", "unknown"),
                metadata={
                    "source_line": rel.get("source_line"),
                    "confidence": rel.get("confidence", "MEDIUM"),
                    "legacy_origin": rel.get("legacy_origin")
                }
            )
        for master_item in knowledge.get("master_data", []):
            item_name = master_item.get("name", "Unknown")
            graph.add_entity("MasterData", item_name, master_item)
        return graph
    
    def _load_institutional_memory(self) -> None:
        for rule in self.knowledge.get("business_rules", []):
            self.memory.store(
                key=f"rule_{rule.get('source_line', 'unknown')}",
                value=rule,
                level=MemoryLevel.INSTITUTIONAL,
                source=rule.get("legacy_origin", "unknown"),
                confidence=ConfidenceLevel.MEDIUM
            )
        for master in self.knowledge.get("master_data", []):
            self.memory.store(
                key=f"master_{master.get('name', 'unknown')}",
                value=master,
                level=MemoryLevel.INSTITUTIONAL,
                source=master.get("legacy_origin", "unknown"),
                confidence=ConfidenceLevel.HIGH
            )
        for cap in self.knowledge.get("capabilities", []):
            self.memory.store(
                key=f"capability_{cap.get('name', 'unknown')}",
                value=cap,
                level=MemoryLevel.INSTITUTIONAL,
                source=cap.get("legacy_origin", "unknown"),
                confidence=ConfidenceLevel.MEDIUM
            )
    
    # -------------------------------------------------------------------------
    # استخراج المفاهيم والدلالات
    # -------------------------------------------------------------------------
    
    def _extract_concepts(self, question: str) -> Dict[str, Any]:
        concepts = {
            "entities": [],
            "relations": [],
            "actions": [],
            "keywords": [],
            "mapped_concepts": []
        }
        question_lower = question.lower()
        
        concept_mapping = {
            "شهادات": "Certificate", "شهادة": "Certificate",
            "تصدير": "Export", "استيراد": "Import",
            "منتج": "Product", "مورد": "Supplier",
            "عميل": "Customer", "طلب": "Order",
            "شحن": "Shipment", "عسل": "honey",
            "نرويج": "norway", "اوروبا": "eu", "خليج": "gcc"
        }
        
        for arabic, english in concept_mapping.items():
            if arabic in question_lower:
                concepts["mapped_concepts"].append(english)
                concepts["keywords"].append(arabic)
        
        relation_keywords = ["export", "import", "supply", "certify", "require", "ship", "deliver", "شحن", "توصيل", "طلب"]
        for kw in relation_keywords:
            if kw in question_lower:
                concepts["relations"].append(kw)
        
        action_keywords = ["certify", "validate", "check", "verify", "approve", "review", "تأكيد", "تحقق", "مراجعة"]
        for kw in action_keywords:
            if kw in question_lower:
                concepts["actions"].append(kw)
        
        words = question_lower.split()
        for word in words:
            if len(word) > 2:
                nodes = self.graph.find_node_by_name(word)
                if nodes:
                    for n_type, n_id in nodes:
                        entity = self.graph.get_entity(n_type, n_id)
                        if entity:
                            concepts["entities"].append({
                                "name": entity.get("name", word),
                                "type": n_type,
                                "id": n_id,
                                "data": entity
                            })
        
        memory_matches = self.memory.search(question, level=MemoryLevel.INSTITUTIONAL)
        for match in memory_matches[:5]:
            if isinstance(match.value, dict):
                concepts["entities"].append({
                    "name": match.key,
                    "type": "InstitutionalMemory",
                    "id": match.key,
                    "data": match.value,
                    "source": "institutional_memory"
                })
        
        return concepts
    
    def _build_structured_answer(self, question: str, concepts: Dict) -> Dict[str, Any]:
        result = {
            "topic": "",
            "product": None,
            "destination": None,
            "findings": [],
            "missing_requirements": [],
            "conclusion": "",
            "evidence": [],
            "confidence": ConfidenceLevel.LOW,
            "next_action": None,
            "answer_type": "unknown"
        }
        
        for entity in concepts.get("entities", []):
            entity_name = entity.get("name", "").lower()
            entity_type = entity.get("type", "").lower()
            if "product" in entity_type or entity_name in ["honey", "spices", "herbs", "oils"]:
                result["product"] = entity["data"]
                result["topic"] = entity["data"].get("name", entity_name)
            elif "destination" in entity_type or entity_name in ["norway", "eu", "gcc", "usa"]:
                result["destination"] = entity["data"]
            elif "certificate" in entity_type or "certification" in entity_type:
                result["findings"].append(f"شهادة: {entity.get('name', 'غير محددة')}")
                result["evidence"].append({"source": "concept_extraction", "entity": entity})
        
        rules = self.repository.get_rules()
        product_name = result["product"].get("name", "").lower() if result["product"] else ""
        dest_name = result["destination"].get("name", "").lower() if result["destination"] else ""
        
        for rule in rules:
            condition = rule.get("condition", "").lower()
            comment = rule.get("comment", "")
            if product_name and product_name in condition:
                result["findings"].append(f"قاعدة: {rule.get('condition')} - {comment}")
                result["evidence"].append({"source": rule.get("legacy_origin", "unknown"), "condition": rule.get("condition"), "comment": comment})
                result["confidence"] = ConfidenceLevel.MEDIUM
            if dest_name and dest_name in condition:
                result["findings"].append(f"قاعدة للوجهة {dest_name}: {rule.get('condition')} - {comment}")
                result["evidence"].append({"source": rule.get("legacy_origin", "unknown"), "condition": rule.get("condition"), "comment": comment})
                result["confidence"] = ConfidenceLevel.MEDIUM
        
        if result["product"] and result["destination"]:
            product_name_val = result["product"].get("name", "")
            dest_name_val = result["destination"].get("name", "")
            product_nodes = self.graph.find_node_by_name(product_name_val)
            dest_nodes = self.graph.find_node_by_name(dest_name_val)
            if product_nodes and dest_nodes:
                p_type, p_id = product_nodes[0]
                d_type, d_id = dest_nodes[0]
                paths = self.graph.find_path(p_type, p_id, d_type, d_id, max_depth=4)
                if paths:
                    for path in paths:
                        path_str = " → ".join([f"{t}({r})" if r else f"{t}" for t, _, r in path])
                        result["findings"].append(f"المسار: {path_str}")
                        result["evidence"].append({"source": "knowledge_graph", "path": path_str})
                        result["confidence"] = ConfidenceLevel.MEDIUM
                        for node_type, node_id, rel in path:
                            if "certificate" in node_type.lower() or "certification" in node_type.lower():
                                cert = self.graph.get_entity(node_type, node_id)
                                if cert:
                                    result["findings"].append(f"الشهادة المطلوبة: {cert.get('name', node_id)}")
                                    result["evidence"].append({"source": "knowledge_graph", "path": path_str, "certificate": cert.get("name", node_id)})
                                    result["confidence"] = ConfidenceLevel.HIGH
        else:
            question_words = question.lower().split()
            for rule in self.repository.get_rules():
                condition = rule.get("condition", "").lower()
                if any(kw in condition for kw in question_words):
                    result["findings"].append(f"قاعدة ذات صلة: {rule.get('condition')} - {rule.get('comment', '')}")
                    result["evidence"].append({"source": rule.get("legacy_origin", "unknown"), "condition": rule.get("condition")})
                    result["confidence"] = ConfidenceLevel.MEDIUM
        
        memory_matches = self.memory.search(question, level=MemoryLevel.INSTITUTIONAL)
        if memory_matches:
            result["findings"].append(f"تم العثور على {len(memory_matches)} إدخال في الذاكرة المؤسسية")
            for match in memory_matches[:3]:
                if isinstance(match.value, dict):
                    result["evidence"].append({"source": "institutional_memory", "key": match.key, "content": match.value.get("condition", str(match.value))})
        
        if result["findings"]:
            result["answer_type"] = "found"
            result["conclusion"] = f"تم العثور على {len(result['findings'])} معلومة تتعلق بالسؤال."
            if result["product"] and result["destination"]:
                result["conclusion"] += f" المنتج {result['product'].get('name')} والوجهة {result['destination'].get('name')}."
            has_certificates = any("شهادة" in f or "certificate" in f.lower() for f in result["findings"])
            if not has_certificates and result["product"] and result["destination"]:
                result["missing_requirements"].append("لم يتم العثور على شهادات محددة في المعرفة الحالية")
                result["next_action"] = "تحقق من المتطلبات التنظيمية للوجهة"
                result["confidence"] = ConfidenceLevel.MEDIUM
            elif has_certificates:
                result["confidence"] = ConfidenceLevel.HIGH
        else:
            result["answer_type"] = "not_found"
            result["conclusion"] = "لم أجد إجابة محددة بناءً على المعرفة الحالية."
            result["missing_requirements"].append("المعرفة الحالية لا تغطي هذا السؤال بشكل مباشر")
            result["next_action"] = "ابحث في مصادر إضافية أو قم بتحديث مستودع المعرفة"
            result["confidence"] = ConfidenceLevel.LOW
        
        return result
    
    # ------------------------------------------------------------------------
    # واجهة BrainContract
    # ------------------------------------------------------------------------
    
    def ask(self, question: str, context: Dict[str, Any] = None) -> AskResult:
        concepts = self._extract_concepts(question)
        structured = self._build_structured_answer(question, concepts)
        
        evidence_list = []
        for ev in structured.get("evidence", []):
            evidence_list.append(Evidence(
                source=ev.get("source", "unknown"),
                evidence_type=EvidenceType.BUSINESS_RULE if "condition" in ev else EvidenceType.ENTITY,
                content=str(ev),
                confidence=structured["confidence"],
                legacy_origin=ev.get("source")
            ))
        
        answer_lines = []
        answer_lines.append(f"📌 الموضوع: {structured.get('topic', 'غير محدد')}")
        if structured.get("product"):
            answer_lines.append(f"📦 المنتج: {structured['product'].get('name')}")
        if structured.get("destination"):
            answer_lines.append(f"📍 الوجهة: {structured['destination'].get('name')}")
        answer_lines.append("\n📝 المعرفة الموجودة:")
        if structured.get("findings"):
            for f in structured["findings"]:
                answer_lines.append(f"  - {f}")
        else:
            answer_lines.append("  - لا توجد معرفة محددة")
        if structured.get("missing_requirements"):
            answer_lines.append("\n⚠️ المتطلبات الناقصة:")
            for req in structured["missing_requirements"]:
                answer_lines.append(f"  - {req}")
        answer_lines.append(f"\n📊 الثقة: {structured['confidence'].value}")
        answer_lines.append(f"📌 الاستنتاج: {structured['conclusion']}")
        if structured.get("next_action"):
            answer_lines.append(f"🎯 الإجراء التالي: {structured['next_action']}")
        
        self.memory.store(
            key=f"question_{datetime.now().timestamp()}",
            value={"question": question, "concepts": concepts, "answer_type": structured.get("answer_type")},
            level=MemoryLevel.SHORT_TERM,
            source="ask_method",
            confidence=structured["confidence"]
        )
        
        return AskResult(
            answer="\n".join(answer_lines),
            evidence=evidence_list,
            confidence=structured["confidence"],
            related_entities=[e.get("name", "") for e in concepts.get("entities", [])]
        )
    
    def decide(self, objective: str, entity: str, product: str, 
               destination: str = None, options: Dict[str, Any] = None) -> Decision:
        decision_id = f"DEC-{uuid.uuid4().hex[:8].upper()}"
        reasoning_lines = []
        evidence_list = []
        recommendations = []
        risks = []
        constraints = []
        assumptions = []
        alternatives = []
        finder = getattr(self.repository, "find_evidence", None)
        scenario_evidence = finder(product=product, destination=destination) if objective == "export" and destination and callable(finder) else []

        if objective == "export" and destination and not scenario_evidence:
            return Decision(
                decision_id=decision_id,
                recommendation="Do not execute export. Verification is required before a recommendation.",
                reasoning="No evidence-backed trade decision can be made for this scenario.",
                evidence=[],
                confidence=ConfidenceLevel.UNKNOWN,
                risks=["Unsupported regulatory decision"],
                constraints=["Execution is blocked until required evidence is verified."],
                assumptions=[],
                alternatives=["Collect current official evidence and resubmit the scenario."],
                entity_scope=self.identity.scope.value,
                expected_outcome=f"{objective} for {product} to {destination}",
                status=DecisionStatus.NEEDS_VERIFICATION,
                evidence_gaps=["No current evidence record is explicitly scoped to this product and destination."],
            )
        
        reasoning_lines.append(f"📌 نطاق الكيان: {self.identity.scope.value} ({self.identity.legal_name})")
        reasoning_lines.append(f"🎯 الهدف: {objective}")
        reasoning_lines.append(f"📦 المنتج: {product}")
        if destination:
            reasoning_lines.append(f"📍 الوجهة: {destination}")
        reasoning_lines.append("")
        
        if objective == "export" and destination:
            semantic_result = self.semantic_engine.evaluate_export_scenario(
                entity, product, destination
            )
            
            reasoning_lines.append("📊 الاستدلال الدلالي:")
            if semantic_result.get("reasoning_chain"):
                for chain_line in semantic_result["reasoning_chain"]:
                    reasoning_lines.append(f"   {chain_line}")
            else:
                reasoning_lines.append("   لم يتم العثور على سلسلة استدلالية مباشرة")
            
            for ev in semantic_result.get("evidence", []):
                evidence_list.append(Evidence(
                    source=ev.get("source", "semantic_reasoning"),
                    evidence_type=EvidenceType.BUSINESS_RULE,
                    content=ev.get("relation", ev.get("chain", str(ev))),
                    confidence=ConfidenceLevel.MEDIUM,
                    legacy_origin=ev.get("source")
                ))
            
            requirements = semantic_result.get("requirements", [])
            if requirements:
                reasoning_lines.append(f"📋 المتطلبات: {', '.join(requirements)}")
            
            missing = semantic_result.get("missing_requirements", [])
            if missing:
                reasoning_lines.append(f"⚠️ المتطلبات الناقصة: {', '.join(missing)}")
            
            if semantic_result.get("allowed", False):
                recommendations.append(f"✅ نوصي بتصدير {product} إلى {destination}")
                constraints.append("تأكد من توفر جميع الشهادات المطلوبة")
            else:
                recommendations.append(f"⚠️ لا نوصي بتصدير {product} إلى {destination} حالياً")
                if missing:
                    constraints.append(f"يجب استيفاء: {', '.join(missing)}")
                else:
                    constraints.append("يجب دراسة المتطلبات التنظيمية أولاً")
                alternatives.append("النظر في أسواق بديلة مثل GCC أو أوروبا")
            
            risks = semantic_result.get("risks", [])
            if not risks:
                risks = ["تقلبات أسعار الشحن", "تغيرات العملة", "تأخيرات جمركية محتملة"]
            
            confidence = semantic_result.get("confidence", ConfidenceLevel.LOW)
            
            next_actions = semantic_result.get("next_actions", [])
            if next_actions:
                reasoning_lines.append(f"🎯 الإجراءات التالية: {', '.join(next_actions)}")
            
            assumptions = [
                f"افتراض أن المنتج {product} مطابق للمواصفات المطلوبة",
                "افتراض استقرار الأسعار خلال فترة الشحن",
                "افتراض توفر القدرات اللوجستية اللازمة"
            ]
        
        else:
            recommendations = [f"دراسة إمكانية {objective} لـ {product}"]
            risks = ["مخاطر غير معروفة"]
            constraints = ["تحتاج إلى مزيد من المعلومات"]
            assumptions = ["افتراض أن المعلومة الأساسية متوفرة"]
            alternatives = ["البحث عن خيارات أخرى"]
            confidence = ConfidenceLevel.LOW
            reasoning_lines.append("⚠️ لم يتم تحديد هدف معروف (مثل export).")
        
        reasoning = "\n".join(reasoning_lines)
        
        self.memory.store(
            key=f"decision_{decision_id}",
            value={
                "objective": objective, "product": product, "destination": destination,
                "recommendation": recommendations[0] if recommendations else "لا توجد توصية",
                "confidence": confidence.value
            },
            level=MemoryLevel.LONG_TERM,
            source="decide_method",
            confidence=confidence
        )
        
        self.decisions_log.append({
            "decision_id": decision_id,
            "objective": objective, "product": product, "destination": destination,
            "recommendation": recommendations, "confidence": confidence.value,
            "timestamp": datetime.now().isoformat()
        })
        
        return Decision(
            decision_id=decision_id,
            recommendation=", ".join(recommendations) if recommendations else "لا توجد توصية محددة.",
            reasoning=reasoning,
            evidence=evidence_list,
            confidence=confidence,
            risks=risks,
            constraints=constraints,
            assumptions=assumptions,
            alternatives=alternatives,
            entity_scope=self.identity.scope.value,
            expected_outcome=f"{objective} لـ {product}" + (f" إلى {destination}" if destination else "")
        )
    
    def observe(self, event: str, details: Dict[str, Any]) -> None:
        self.memory.store(
            key=f"observation_{event}_{datetime.now().timestamp()}",
            value={"event": event, "details": details},
            level=MemoryLevel.SHORT_TERM,
            source="observe_method",
            confidence=ConfidenceLevel.HIGH
        )
        print(f"👁️ تم تسجيل ملاحظة: {event}")
    
    def remember(self, key: str, value: Any) -> None:
        self.memory.store(
            key=key, value=value, level=MemoryLevel.LONG_TERM,
            source="remember_method", confidence=ConfidenceLevel.HIGH
        )
        print(f"🧠 تم تذكر: {key}")
    
    def reason(self, premises: List[str], rules: Optional[List[Dict]] = None) -> List[str]:
        if rules is None:
            repo_rules = self.repository.get_rules()
            rules = repo_rules
        
        # استخدام محرك الاستدلال الدلالي
        return self.semantic_engine.apply_rules(premises, rules)
    
    def evaluate(self, decision_id: str, outcome: Dict[str, Any]) -> None:
        self.memory.store(
            key=f"evaluation_{decision_id}_{datetime.now().timestamp()}",
            value={"decision_id": decision_id, "outcome": outcome},
            level=MemoryLevel.LONG_TERM,
            source="evaluate_method",
            confidence=ConfidenceLevel.MEDIUM
        )
        for decision in self.decisions_log:
            if decision.get("decision_id") == decision_id:
                decision["outcome"] = outcome
                decision["evaluated_at"] = datetime.now().isoformat()
                break
        print(f"📊 تم تقييم القرار: {decision_id}")
        print(f"   النتيجة: {outcome}")
    
    def get_memory_summary(self) -> Dict[str, int]:
        return self.memory.get_summary()
    
    def get_graph_summary(self) -> Dict[str, int]:
        return {"nodes": len(self.graph.nodes), "edges": len(self.graph.edges)}
    
    def get_knowledge_summary(self) -> Dict[str, int]:
        return {
            "entities": len(self.knowledge.get("entities", [])),
            "rules": len(self.knowledge.get("business_rules", [])),
            "master_data": len(self.knowledge.get("master_data", [])),
            "capabilities": len(self.knowledge.get("capabilities", []))
        }
    
    def clear_session_memory(self) -> None:
        self.memory.clear_short_term()
        print("🧹 تم مسح الذاكرة قصيرة المدى")
    
    def get_decision_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.decisions_log[-limit:]

# =============================================================================
# نهاية الملف
# =============================================================================