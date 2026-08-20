"""Shared NeuroLingua types. Meaning is canonical; locale is a view."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any

from raios.risk import RiskLevel


INITIAL_LOCALES = ("ar-EG", "ar-GULF", "en", "nb-NO", "sv-SE", "da-DK")

GULF_PARENT = "ar-GULF"
GULF_CHILDREN = {
    "ar-SA": "saudi",
    "ar-AE": "emirati",
    "ar-KW": "kuwaiti",
    "ar-QA": "qatari",
    "ar-BH": "bahraini",
    "ar-OM": "omani",
}

SCANDINAVIAN_LOCALES = ("nb-NO", "sv-SE", "da-DK")


class Register(str, Enum):
    UNKNOWN = "unknown"
    INFORMAL = "informal"
    NEUTRAL = "neutral"
    FORMAL = "formal"
    TECHNICAL = "technical"


class SegmentKind(str, Enum):
    LANGUAGE = "language"
    TECHNICAL = "technical"
    MIXED = "mixed"
    PRESERVED = "preserved"


@dataclass
class Confidence:
    """Measured confidence. Never a placeholder.

    ``value`` is computed from observed evidence. If no evidence exists the
    value is 0.0 and ``method`` explains why, rather than inventing 0.5.
    """

    value: float
    method: str
    evidence: list[str] = field(default_factory=list)
    sample_size: int = 0
    unavailable_tiers: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"Confidence must be in [0, 1], got {self.value}")
        self.value = round(float(self.value), 4)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InterpretationContext:
    domain: str | None = None
    organization_id: str | None = None
    project_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    risk_level: RiskLevel = RiskLevel.LOW
    offline: bool = True
    allow_llm: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: InterpretationContext | dict[str, Any] | None) -> "InterpretationContext":
        if raw is None:
            return cls()
        if isinstance(raw, cls):
            return raw
        data = dict(raw)
        if "risk_level" in data:
            data["risk_level"] = RiskLevel.from_value(data["risk_level"])
        known = {k: data[k] for k in cls.__dataclass_fields__ if k in data and k != "extra"}
        extra = {k: v for k, v in data.items() if k not in cls.__dataclass_fields__}
        extra.update(data.get("extra") or {})
        return cls(**known, extra=extra)

    @property
    def scope_chain(self) -> list[tuple[str, str]]:
        chain: list[tuple[str, str]] = []
        if self.domain:
            chain.append(("domain", self.domain))
        if self.organization_id:
            chain.append(("organization", self.organization_id))
        if self.project_id:
            chain.append(("project", self.project_id))
        if self.user_id:
            chain.append(("user", self.user_id))
        if self.session_id:
            chain.append(("session", self.session_id))
        return chain


@dataclass
class CodeSwitchSegment:
    index: int
    text: str
    locale: str
    kind: SegmentKind
    confidence: Confidence
    technical: bool = False
    preserve: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "text": self.text,
            "locale": self.locale,
            "kind": self.kind.value,
            "confidence": self.confidence.to_dict(),
            "technical": self.technical,
            "preserve": self.preserve,
            "notes": list(self.notes),
        }


@dataclass
class BoundConcept:
    concept_id: str
    canonical_meaning: str
    surface: str
    locale: str
    scope: str = "global"
    confidence: Confidence = field(
        default_factory=lambda: Confidence(value=1.0, method="exact_alias", sample_size=1)
    )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["confidence"] = self.confidence.to_dict()
        return payload


@dataclass
class PreservedSpan:
    kind: str
    surface: str
    start: int
    end: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PragmaticFrame:
    action: str | None = None
    deadline: str | None = None
    politeness_marker: bool = False
    not_logical_condition: list[str] = field(default_factory=list)
    register: Register = Register.UNKNOWN
    flags: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["register"] = self.register.value
        return payload


@dataclass
class DetectionResult:
    locale: str | None
    language: str | None
    dialect: str | None
    script: str | None
    code_switched: bool
    language_confidence: Confidence
    dialect_confidence: Confidence
    tiers_used: list[str] = field(default_factory=list)
    competing: list[tuple[str, float]] = field(default_factory=list)
    gulf_child: str | None = None
    gulf_child_implemented: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "locale": self.locale,
            "language": self.language,
            "dialect": self.dialect,
            "script": self.script,
            "code_switched": self.code_switched,
            "language_confidence": self.language_confidence.to_dict(),
            "dialect_confidence": self.dialect_confidence.to_dict(),
            "tiers_used": list(self.tiers_used),
            "competing": [list(item) for item in self.competing],
            "gulf_child": self.gulf_child,
            "gulf_child_implemented": self.gulf_child_implemented,
        }


@dataclass
class ExecutionMetrics:
    latency_ms: float = 0.0
    provider_calls: int = 0
    llm_calls: int = 0
    local_steps: int = 0
    tiers_used: list[str] = field(default_factory=list)

    @property
    def local_execution_ratio(self) -> float:
        total = self.local_steps + self.llm_calls
        if total == 0:
            return 1.0
        return round(self.local_steps / total, 4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "latency_ms": self.latency_ms,
            "provider_calls": self.provider_calls,
            "llm_calls": self.llm_calls,
            "local_steps": self.local_steps,
            "local_execution_ratio": self.local_execution_ratio,
            "tiers_used": list(self.tiers_used),
        }
