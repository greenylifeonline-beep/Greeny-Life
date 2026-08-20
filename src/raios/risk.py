"""Risk taxonomy mirrored from the existing GL-DOS runtime.

The TypeScript controlled runtime already uses the string union
``LOW | MEDIUM | HIGH | CRITICAL``
(``unified-intelligence/runtime/controlled-runtime-orchestrator.ts`` and
``unified-intelligence/adapters/gl-dos-governance-gate.ts``).

NeuroLingua reuses that taxonomy instead of inventing a second scale.
"""

from __future__ import annotations

from enum import Enum


class RiskLevel(str, Enum):
    """Operational risk level. Names match the existing GL-DOS contract."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_value(cls, value: str | RiskLevel | None) -> "RiskLevel":
        if value is None:
            return cls.LOW
        if isinstance(value, cls):
            return value
        normalized = str(value).strip().upper()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValueError(f"Unknown risk level {value!r}; expected {list(cls)}") from exc

    @property
    def rank(self) -> int:
        return {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3,
        }[self]
