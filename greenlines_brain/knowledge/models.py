# greenlines_brain/knowledge/models.py
# ============================================================================
# عقد المعرفة - Knowledge Contract
# ============================================================================
# يمثل هذا الملف الطبقة العليا للنظام: المعرفة المصنفة والموثقة
# بأنواعها المختلفة: كيانات، قواعد، سياسات، وكلاء، أدوات، قدرات، إلخ.
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Set
from enum import Enum

# استيرادات من طبقة الأدلة
from ..evidence.models import AuthorityLevel, TemporalValidity, Provenance

# ----------------------------------------------------------------------------
# 1. أنواع المعرفة
# ----------------------------------------------------------------------------
class KnowledgeType(Enum):
    ENTITY = "entity"
    RULE = "rule"
    POLICY = "policy"
    REQUIREMENT = "requirement"
    CONSTRAINT = "constraint"
    FACT = "fact"
    EVENT = "event"
    DECISION = "decision"
    AGENT = "agent"
    TOOL = "tool"
    CAPABILITY = "capability"
    WORKFLOW = "workflow"
    RELATIONSHIP = "relationship"

# ----------------------------------------------------------------------------
# 2. دورة الحياة (Lifecycle)
# ----------------------------------------------------------------------------
class LifecycleStatus(Enum):
    CANDIDATE = "candidate"        # مرشح غير معتمد
    REVIEW = "review"              # قيد المراجعة البشرية
    APPROVED = "approved"          # معتمد
    ACTIVE = "active"              # نشط وقيد الاستخدام
    DEPRECATED = "deprecated"      # مهمل (لا يستخدم للمستقبل)
    SUPERSEDED = "superseded"      # مستبدل بقاعدة أحدث
    REJECTED = "rejected"          # مرفوض

# ----------------------------------------------------------------------------
# 3. الحالة التشغيلية (للأدوات والوكلاء)
# ----------------------------------------------------------------------------
class OperationalStatus(Enum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    DISABLED = "disabled"
    FAILED = "failed"

# ----------------------------------------------------------------------------
# 4. كائن المعرفة الأساسي (KnowledgeObject)
# ----------------------------------------------------------------------------
@dataclass
class KnowledgeObject:
    id: str
    type: KnowledgeType
    name: str
    description: str
    provenance: Provenance
    authority: AuthorityLevel
    lifecycle: LifecycleStatus
    temporal: TemporalValidity
    operational_status: Optional[OperationalStatus] = None
    
    # الروابط
    supersedes: Optional[str] = None        # معرف الكائن الذي يستبدله
    superseded_by: Optional[str] = None     # معرف الكائن الذي استبدله
    related_objects: List[str] = field(default_factory=list)  # معرفات الكائنات المرتبطة
    evidence_ids: List[str] = field(default_factory=list)      # معرفات الأدلة الداعمة
    
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: Optional[str] = None

    def is_active(self) -> bool:
        return self.lifecycle == LifecycleStatus.ACTIVE

# ----------------------------------------------------------------------------
# 5. الكيانات (Entity)
# ----------------------------------------------------------------------------
@dataclass
class Entity(KnowledgeObject):
    entity_type: str = ""          # "product", "supplier", "customer", etc.
    attributes: Dict[str, Any] = field(default_factory=dict)

# ----------------------------------------------------------------------------
# 6. القواعد (Rule)
# ----------------------------------------------------------------------------
@dataclass
class Rule(KnowledgeObject):
    condition: str
    action: str
    priority: int = 0
    is_active: bool = True

# ----------------------------------------------------------------------------
# 7. السياسات (Policy)
# ----------------------------------------------------------------------------
@dataclass
class Policy(KnowledgeObject):
    scope: str                     # "internal", "regulatory", "operational"
    applicability: List[str] = field(default_factory=list)

# ----------------------------------------------------------------------------
# 8. المتطلبات (Requirement)
# ----------------------------------------------------------------------------
@dataclass
class Requirement(KnowledgeObject):
    target_entity: str             # "product", "supplier", "destination"
    requirement_type: str          # "certification", "documentation", "compliance"
    is_mandatory: bool = True

# ----------------------------------------------------------------------------
# 9. القيود (Constraint)
# ----------------------------------------------------------------------------
@dataclass
class Constraint(KnowledgeObject):
    target: str                    # الحقل أو الكيان المقيد
    constraint_type: str           # "range", "pattern", "dependency"
    expression: str                # تعبير القيد (مثل "weight <= 1kg")

# ----------------------------------------------------------------------------
# 10. الحقائق (Fact)
# ----------------------------------------------------------------------------
@dataclass
class Fact(KnowledgeObject):
    subject: str
    predicate: str
    object: str
    confidence: float = 0.9

# ----------------------------------------------------------------------------
# 11. الأحداث (Event)
# ----------------------------------------------------------------------------
@dataclass
class Event(KnowledgeObject):
    event_type: str                # "shipment", "order", "alert"
    occurred_at: str = field(default_factory=lambda: datetime.now().isoformat())
    payload: Dict[str, Any] = field(default_factory=dict)

# ----------------------------------------------------------------------------
# 12. القرارات (Decision)
# ----------------------------------------------------------------------------
@dataclass
class Decision(KnowledgeObject):
    decision_type: str             # "export_approval", "risk_assessment"
    outcome: str
    reasoning: str
    influenced_by: List[str] = field(default_factory=list)  # معرفات القواعد المؤثرة

# ----------------------------------------------------------------------------
# 13. الوكلاء (Agent)
# ----------------------------------------------------------------------------
@dataclass
class Agent(KnowledgeObject):
    role: str
    capabilities: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    workflows: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)

# ----------------------------------------------------------------------------
# 14. الأدوات (Tool)
# ----------------------------------------------------------------------------
@dataclass
class Tool(KnowledgeObject):
    tool_type: str                 # "cli", "api", "library"
    command: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    risk_level: str = "low"

# ----------------------------------------------------------------------------
# 15. القدرات (Capability)
# ----------------------------------------------------------------------------
@dataclass
class Capability(KnowledgeObject):
    capability_type: str           # "analysis", "validation", "extraction"
    implements: List[str] = field(default_factory=list)  # معرفات الوظائف المنفذة

# ----------------------------------------------------------------------------
# 16. سير العمل (Workflow)
# ----------------------------------------------------------------------------
@dataclass
class Workflow(KnowledgeObject):
    steps: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)

# ----------------------------------------------------------------------------
# 17. العلاقات (Relationship)
# ----------------------------------------------------------------------------
@dataclass
class Relationship(KnowledgeObject):
    source_type: str
    source_id: str
    relation_type: str            # "uses", "depends_on", "implements", "governs"
    target_type: str
    target_id: str

# ----------------------------------------------------------------------------
# 18. التحقق (Validation) - تمثيل لعملية التحقق
# ----------------------------------------------------------------------------
@dataclass
class Validation:
    id: str
    knowledge_id: str
    status: str                    # "PASSED", "FAILED", "PENDING"
    validated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    validated_by: str = ""
    notes: str = ""

# ----------------------------------------------------------------------------
# 19. المرجع التنفيذي (ImplementationReference)
# ----------------------------------------------------------------------------
@dataclass
class ImplementationReference:
    knowledge_id: str
    implementation_type: str       # "function", "class", "module"
    implementation_name: str
    source_file: str
    line_start: int
    line_end: Optional[int] = None
