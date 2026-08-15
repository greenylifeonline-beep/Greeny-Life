# greenlines_brain/contract.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

class ConfidenceLevel(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"

class DecisionStatus(Enum):
    GO = "GO"
    NEEDS_VERIFICATION = "NEEDS_VERIFICATION"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"
    NO_GO = "NO_GO"

class EvidenceType(Enum):
    LEGACY_CODE = "LEGACY_CODE"
    BUSINESS_RULE = "BUSINESS_RULE"
    MASTER_DATA = "MASTER_DATA"
    VALIDATION = "VALIDATION"
    EXTERNAL_API = "EXTERNAL_API"
    USER_INPUT = "USER_INPUT"

@dataclass
class Evidence:
    """تسجل مصدر كل معلومة أو قرار."""
    source: str  # اسم الملف أو المرجع
    evidence_type: EvidenceType
    content: str
    confidence: ConfidenceLevel
    legacy_origin: Optional[str] = None  # مثلاً: "brain.py:line 1234"
    timestamp: str = ""

@dataclass
class Decision:
    """كائن القرار المنظم."""
    decision_id: str
    recommendation: str
    reasoning: str
    evidence: List[Evidence]
    confidence: ConfidenceLevel
    risks: List[str]
    constraints: List[str]
    assumptions: List[str]
    alternatives: List[str]
    entity_scope: str  # "egypt", "norway", "gulf"
    expected_outcome: str
    status: DecisionStatus = DecisionStatus.NEEDS_VERIFICATION
    evidence_gaps: List[str] = field(default_factory=list)

@dataclass
class AskResult:
    """نتيجة سؤال موجه للعقل."""
    answer: str
    evidence: List[Evidence]
    confidence: ConfidenceLevel
    related_entities: List[str]

class BrainContract:
    """
    العقد الذي يحدد واجهة العقل.
    جميع التطبيقات والوكلاء تتفاعل مع العقل من خلال هذه الدوال فقط.
    """
    def ask(self, question: str, context: Dict[str, Any] = None) -> AskResult:
        raise NotImplementedError
    
    def decide(self, objective: str, entity: str, product: str, destination: str = None) -> Decision:
        raise NotImplementedError
    
    def observe(self, event: str, details: Dict[str, Any]) -> None:
        """يسجل حدثاً ملاحظاً في العالم الخارجي."""
        raise NotImplementedError
    
    def remember(self, key: str, value: Any) -> None:
        """يخزن معلومة في الذاكرة المؤسسية."""
        raise NotImplementedError
    
    def reason(self, premises: List[str], rules: List[str]) -> List[str]:
        """يطبق الاستدلال المنطقي على مقدمات وقواعد."""
        raise NotImplementedError
    
    def evaluate(self, decision_id: str, outcome: Dict[str, Any]) -> None:
        """يقيم نتيجة قرار سابق ويسجل التعلم."""
        raise NotImplementedError