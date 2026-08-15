# greenlines_brain/evidence/models.py
# ============================================================================
# عقد الأدلة - Evidence Contract
# ============================================================================
# يمثل هذا الملف الطبقة السفلية للنظام: كل معلومة خام تدخل النظام
# يجب أن تكون موثقة بالمصدر والزمان والثقة.
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
import hashlib

# ----------------------------------------------------------------------------
# 1. مستويات السلطة (Authority)
# ----------------------------------------------------------------------------
class AuthorityLevel(Enum):
    OFFICIAL_REGULATION = 100   # وثيقة رسمية (قانون، لائحة)
    OFFICIAL_API = 90           # واجهة حكومية رسمية
    VERIFIED_DOCUMENT = 80      # وثيقة تم التحقق منها
    APPROVED_INTERNAL = 70      # قاعدة داخلية معتمدة
    MASTER_DATA = 60            # بيانات رئيسية
    OBSERVED_EVENT = 40         # حدث تم رصده
    HISTORICAL_DECISION = 30    # قرار سابق
    AI_INFERRED = 10            # استنتاج آلي (أقل ثقة)

# ----------------------------------------------------------------------------
# 2. حالة الصلاحية الزمنية (Temporal Validity)
# ----------------------------------------------------------------------------
@dataclass
class TemporalValidity:
    valid_from: Optional[str] = None        # تاريخ بدء الصلاحية
    valid_until: Optional[str] = None       # تاريخ انتهاء الصلاحية
    observed_at: Optional[str] = None       # وقت الرصد
    effective_at: Optional[str] = None      # وقت التفعيل
    superseded_at: Optional[str] = None     # وقت الاستبدال

# ----------------------------------------------------------------------------
# 3. المصدر (Source)
# ----------------------------------------------------------------------------
@dataclass
class Source:
    source_type: str            # "brain.py", "pdf_regulation", "api", "event"
    uri: str                    # مسار الملف أو رابط المصدر
    version: Optional[str] = None
    retrieved_at: str = field(default_factory=lambda: datetime.now().isoformat())
    hash: Optional[str] = None  # تجزئة للمصدر للتحقق من integrity

    def __post_init__(self):
        if self.hash is None:
            content = f"{self.source_type}:{self.uri}:{self.version or ''}"
            self.hash = hashlib.sha256(content.encode()).hexdigest()[:16]

# ----------------------------------------------------------------------------
# 4. الأثر (Provenance)
# ----------------------------------------------------------------------------
@dataclass
class Provenance:
    source: Source
    extracted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    extracted_by: str = "ASTAnalyzer"  # اسم المستخرج
    confidence: float = 0.5            # 0.0 - 1.0

# ----------------------------------------------------------------------------
# 5. الدليل الخام (Evidence)
# ----------------------------------------------------------------------------
@dataclass
class Evidence:
    id: str
    provenance: Provenance
    raw_content: str                    # النص المستخرج
    context: Dict[str, Any] = field(default_factory=dict)  # سياق إضافي
    evidence_type: str = "UNKNOWN"      # "conditional", "call", "assignment", etc.
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    ast_node_type: Optional[str] = None

# ----------------------------------------------------------------------------
# 6. الادعاء (Claim)
# ----------------------------------------------------------------------------
@dataclass
class Claim:
    id: str
    statement: str                     # النص الصريح للادعاء
    supporting_evidence_ids: List[str] = field(default_factory=list)
    confidence: float = 0.5
    authority: AuthorityLevel = AuthorityLevel.AI_INFERRED
    classification: str = "UNCLASSIFIED"  # "RULE", "FACT", "REQUIREMENT", etc.

# ----------------------------------------------------------------------------
# 7. النتيجة الخام (RawFinding)
# ----------------------------------------------------------------------------
@dataclass
class RawFinding:
    id: str
    evidence: Evidence                 # الدليل الذي أدى لهذه النتيجة
    claim: Optional[Claim] = None      # الادعاء المستخلص (إن وجد)
    status: str = "UNCLASSIFIED"       # "UNCLASSIFIED", "CANDIDATE", "CONFIRMED"
    notes: Optional[str] = None
