from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class KnowledgeState(str, Enum):
    DISCOVERED = "DISCOVERED"
    VALIDATED = "VALIDATED"
    CANONICAL = "CANONICAL"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TokenRole(str, Enum):
    NATURAL_LANGUAGE = "natural_language"
    TECHNICAL = "technical"
    IDENTIFIER = "identifier"
    COMMAND = "command"
    PATH = "path"
    URL = "url"
    NUMBER = "number"
    UNKNOWN = "unknown"


class ConfidenceAtom(BaseModel):
    """Provenance-bearing confidence. None means UNKNOWN, never fabricated."""

    value: float | None = Field(default=None, ge=0.0, le=1.0)
    source: str

    @property
    def known(self) -> bool:
        return self.value is not None


class ConfidenceProvenance(BaseModel):
    language: ConfidenceAtom = Field(
        default_factory=lambda: ConfidenceAtom(value=None, source="UNKNOWN")
    )
    dialect: ConfidenceAtom = Field(
        default_factory=lambda: ConfidenceAtom(value=None, source="UNKNOWN")
    )
    semantic: ConfidenceAtom = Field(
        default_factory=lambda: ConfidenceAtom(value=None, source="UNKNOWN")
    )
    pragmatics: ConfidenceAtom = Field(
        default_factory=lambda: ConfidenceAtom(value=None, source="UNKNOWN")
    )


class LanguageProfile(BaseModel):
    language: str
    locale: str | None = None
    dialect: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    parent: str | None = None
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class DialectResult(BaseModel):
    parent: str
    profile: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    country_claimed: bool = False


class RegisterProfile(BaseModel):
    formality: float = Field(default=0.5, ge=0.0, le=1.0)
    professional: float = Field(default=0.5, ge=0.0, le=1.0)
    spoken: float = Field(default=0.0, ge=0.0, le=1.0)


class Intent(BaseModel):
    primary: str
    subtype: str | None = None


class SemanticPayload(BaseModel):
    action: str | None = None
    target: str | None = None
    goal: str | None = None
    propositions: list[dict[str, Any]] = Field(default_factory=list)


class PreservationPolicy(BaseModel):
    numbers: bool = True
    proper_names: bool = True
    technical_terms: bool = True
    identifiers: bool = True


class CodeSwitchSegment(BaseModel):
    text: str
    locale: str
    role: TokenRole = TokenRole.NATURAL_LANGUAGE
    evidence: list[str] = Field(default_factory=list)


class ProtectedToken(BaseModel):
    text: str
    kind: str
    span: tuple[int, int] | None = None
    translate: bool = False


class PragmaticsProfile(BaseModel):
    politeness_marker: bool = False
    urgency: str | None = None
    warning: bool = False
    softened_command: bool = False
    request: bool = False
    uncertainty: bool = False
    condition: bool = False
    social_marker: str | None = None
    deadline: str | None = None
    notes: list[str] = Field(default_factory=list)


class TemporalProfile(BaseModel):
    deadline: str | None = None
    relative: str | None = None
    evidence: list[str] = Field(default_factory=list)


class ModalityProfile(BaseModel):
    imperative: bool = False
    request: bool = False
    permission: bool = False
    prohibition: bool = False
    possibility: bool = False


class StageTrace(BaseModel):
    stage: str
    status: str
    confidence: float | None = None
    evidence: list[str] = Field(default_factory=list)
    provider: str
    latency_ms: float = 0.0
    fallback_used: bool = False
    warnings: list[str] = Field(default_factory=list)


class CognitiveMeaningPacket(BaseModel):
    schema_version: str = "1.1"
    meaning_id: str = Field(default_factory=lambda: str(uuid4()))
    source_text: str
    source_locale: str | None = None
    detected_languages: list[LanguageProfile] = Field(default_factory=list)
    code_switch_segments: list[CodeSwitchSegment] = Field(default_factory=list)

    language: LanguageProfile | None = None
    speech_register: RegisterProfile = Field(default_factory=RegisterProfile)

    intent: Intent
    semantics: SemanticPayload = Field(default_factory=SemanticPayload)
    propositions: list[dict[str, Any]] = Field(default_factory=list)
    entities: list[dict[str, Any]] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    temporal: TemporalProfile = Field(default_factory=TemporalProfile)
    modality: ModalityProfile = Field(default_factory=ModalityProfile)
    pragmatics: PragmaticsProfile = Field(default_factory=PragmaticsProfile)
    terminology: list[dict[str, Any]] = Field(default_factory=list)
    preserved_tokens: list[ProtectedToken] = Field(default_factory=list)
    context_refs: list[str] = Field(default_factory=list)

    preserve: PreservationPolicy = Field(default_factory=PreservationPolicy)
    uncertainty: list[str] = Field(default_factory=list)

    risk: RiskLevel = RiskLevel.LOW
    risk_level: RiskLevel | None = None
    confidence: ConfidenceProvenance = Field(default_factory=ConfidenceProvenance)
    evidence: list[str] = Field(default_factory=list)
    provider_trace: list[StageTrace] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    knowledge_state: KnowledgeState = KnowledgeState.DISCOVERED
    metadata: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if self.risk_level is None:
            self.risk_level = self.risk
        else:
            self.risk = self.risk_level
        if self.language is None and self.detected_languages:
            self.language = self.detected_languages[0]
        if self.source_locale is None and self.language is not None:
            self.source_locale = self.language.locale or self.language.language
        if not self.propositions and self.semantics.propositions:
            self.propositions = list(self.semantics.propositions)
        if not self.actions and self.semantics.action:
            self.actions = [{"action": self.semantics.action, "target": self.semantics.target}]
