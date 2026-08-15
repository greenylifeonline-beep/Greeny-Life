# greenlines_brain/evidence_layer/models.py
# ============================================================================
# Implementation Evidence Layer
# ============================================================================
# تمثل هذه الطبقة الجسر بين Raw AST Findings والتصنيف الدلالي.
# تحول كل RawFinding إلى Evidence كامل مع السياق والمصدر والعلاقات.
# ============================================================================

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set
from datetime import datetime
from enum import Enum

# ----------------------------------------------------------------------------
# أنواع الأدلة التنفيذية
# ----------------------------------------------------------------------------
class EvidenceType(Enum):
    FUNCTION = "function"
    CLASS = "class"
    CALL = "call"
    IMPORT = "import"
    CONDITION = "condition"
    LOOP = "loop"
    ASSIGNMENT = "assignment"
    EXTERNAL_EXECUTION = "external_execution"
    HTTP = "http"
    DATA_STRUCTURE = "data_structure"
    DOCUMENTATION = "documentation"
    WORKFLOW_SEQUENCE = "workflow_sequence"
    UNKNOWN = "unknown"

# ----------------------------------------------------------------------------
# الدليل التنفيذي (Implementation Evidence)
# ----------------------------------------------------------------------------
@dataclass
class ImplementationEvidence:
    id: str
    type: EvidenceType
    stable_fingerprint: str
    source_file: str
    line_start: int
    line_end: int
    col_start: int
    col_end: int
    
    # السياق
    module: str
    class_name: Optional[str]
    function_name: Optional[str]
    parent_id: Optional[str] = None
    scope: str = "global"
    
    # المحتوى الخام
    raw: str
    normalized: str
    source_snippet: str
    
    # العلاقات
    children_ids: List[str] = field(default_factory=list)
    parent_ids: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    # البيانات الإضافية
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Provenance
    extracted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    extracted_by: str = "ImplementationEvidenceLayer"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "stable_fingerprint": self.stable_fingerprint,
            "source_file": self.source_file,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "col_start": self.col_start,
            "col_end": self.col_end,
            "module": self.module,
            "class_name": self.class_name,
            "function_name": self.function_name,
            "parent_id": self.parent_id,
            "scope": self.scope,
            "raw": self.raw,
            "normalized": self.normalized,
            "source_snippet": self.source_snippet,
            "children_ids": self.children_ids,
            "parent_ids": self.parent_ids,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
            "extracted_at": self.extracted_at,
            "extracted_by": self.extracted_by
        }

# ----------------------------------------------------------------------------
# دالة مساعدة لإنشاء Evidence من RawFinding
# ----------------------------------------------------------------------------
def create_evidence_from_finding(finding: Dict[str, Any]) -> ImplementationEvidence:
    """يحول RawFinding إلى ImplementationEvidence."""
    node_type = finding.get("type", "").lower()
    
    # تعيين نوع الدليل
    evidence_type = EvidenceType.UNKNOWN
    if node_type == "functiondef":
        evidence_type = EvidenceType.FUNCTION
    elif node_type == "classdef":
        evidence_type = EvidenceType.CLASS
    elif node_type == "call":
        evidence_type = EvidenceType.CALL
    elif node_type in ["import", "importfrom"]:
        evidence_type = EvidenceType.IMPORT
    elif node_type == "if":
        evidence_type = EvidenceType.CONDITION
    elif node_type in ["for", "while"]:
        evidence_type = EvidenceType.LOOP
    elif node_type == "assign":
        evidence_type = EvidenceType.ASSIGNMENT
    elif "subprocess" in node_type:
        evidence_type = EvidenceType.EXTERNAL_EXECUTION
    elif "http" in node_type or "requests" in node_type:
        evidence_type = EvidenceType.HTTP
    elif node_type in ["dict", "list", "tuple", "set"]:
        evidence_type = EvidenceType.DATA_STRUCTURE
    elif "docstring" in node_type or "comment" in node_type:
        evidence_type = EvidenceType.DOCUMENTATION
    elif "workflow" in node_type:
        evidence_type = EvidenceType.WORKFLOW_SEQUENCE
    
    return ImplementationEvidence(
        id=finding.get("id", f"ev_{hash(finding.get('stable_fingerprint', ''))}"),
        type=evidence_type,
        stable_fingerprint=finding.get("stable_fingerprint", ""),
        source_file="brain.py",
        line_start=finding.get("line_start", 0),
        line_end=finding.get("line_end", 0),
        col_start=finding.get("col_start", 0),
        col_end=finding.get("col_end", 0),
        module=finding.get("module", "brain"),
        class_name=finding.get("class_name"),
        function_name=finding.get("function_name"),
        parent_id=None,
        scope="global" if not finding.get("function_name") else "local",
        raw=finding.get("raw", ""),
        normalized=finding.get("normalized_source", ""),
        source_snippet=finding.get("source_snippet", ""),
        children_ids=[],
        parent_ids=[],
        dependencies=[],
        metadata={
            "ast_node_type": finding.get("type"),
            "original_raw": finding.get("raw")
        }
    )
