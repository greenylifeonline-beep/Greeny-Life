"""Map A2A tasks onto existing RAIOS risk/policy. WRAP NeuroLingua RiskLevel; do not fork a second engine."""

from __future__ import annotations

from typing import Any

from raios.neuro_lingua.risk import verification_plan
from raios.neuro_lingua.schema import RiskLevel

from .failclosed import AUTHORITY_REQUIRED, RISK_POLICY_DENIED, TARGET_NOT_ALLOWED, FailClosed

DESTRUCTIVE = frozenset(
    {"DELETE", "FORCE_PUSH", "CANONICAL_REPLACEMENT", "IRREVERSIBLE_MIGRATION", "SECRET_ROTATION"}
)

NL_RISK_PATH = "src/raios/neuro_lingua/risk.py"


def map_risk(raw: str | None, capability_risk: str) -> RiskLevel:
    name = (raw or capability_risk or "LOW").upper()
    try:
        return RiskLevel[name]
    except KeyError:
        return RiskLevel.MEDIUM


def evaluate(
    *,
    capability: dict[str, Any],
    action: str,
    risk: RiskLevel,
    effective_authority: bool,
    target_allowed: bool = True,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not target_allowed:
        raise FailClosed(TARGET_NOT_ALLOWED)
    action_u = action.upper()
    needs = action_u in DESTRUCTIVE or (
        risk in (RiskLevel.HIGH, RiskLevel.CRITICAL) and capability.get("SIDE_EFFECTS")
    ) or risk is RiskLevel.CRITICAL
    if needs and not effective_authority:
        if action_u in DESTRUCTIVE or (risk in (RiskLevel.HIGH, RiskLevel.CRITICAL) and capability.get("SIDE_EFFECTS")):
            raise FailClosed(AUTHORITY_REQUIRED, action_u if action_u in DESTRUCTIVE else risk.value)
        raise FailClosed(RISK_POLICY_DENIED, "CRITICAL")
    result = {
        "POLICY_RESULT": "ALLOW",
        "RISK_CLASS": risk.value,
        "AUTHORITY_GATE": bool(effective_authority) if needs else "NOT_REQUIRED",
        "VERIFICATION_PLAN": verification_plan(risk).__dict__,
    }
    if evidence:
        result.update(evidence)
    return result
