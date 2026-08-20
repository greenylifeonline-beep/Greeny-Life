from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .risk import verification_plan
from .schema import CognitiveMeaningPacket, RiskLevel


@dataclass
class VerificationResult:
    status: str
    risk: RiskLevel
    checks: dict[str, bool]
    omissions: list[str] = field(default_factory=list)
    unsupported_additions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    provider: str = "deterministic-verifier"
    back_translation_used: bool = False


_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _numbers(text: str) -> set[str]:
    return set(_NUMBER_RE.findall(text))


def verify_realization(
    meaning: CognitiveMeaningPacket,
    realized: str,
    target_locale: str,
) -> dict[str, Any]:
    risk = meaning.risk_level or meaning.risk
    plan = verification_plan(risk)
    source = meaning.source_text
    checks: dict[str, bool] = {}
    omissions: list[str] = []
    additions: list[str] = []
    warnings: list[str] = []

    if plan.number_lock:
        src_n = _numbers(source)
        out_n = _numbers(realized)
        missing = sorted(src_n - out_n)
        extra = sorted(out_n - src_n)
        checks["number_preservation"] = not missing
        if missing:
            omissions.extend(f"number:{n}" for n in missing)
        if extra:
            additions.extend(f"number:{n}" for n in extra)

    if plan.entity_lock or plan.terminology_lock:
        for token in meaning.preserved_tokens:
            if token.text in source and token.text not in realized:
                checks["identifier_preservation"] = False
                omissions.append(f"identifier:{token.text}")
            else:
                checks.setdefault("identifier_preservation", True)

    intent_ok = True
    if meaning.semantics.action == "resolve" and target_locale.startswith("ar") and "شوف" not in realized and "خلّص" not in realized and "خلص" not in realized:
        if "resolve" not in realized.lower() and "løse" not in realized.lower() and "lösa" not in realized.lower():
            # Arabic realizers use خلّص / شوف; Latin locales use løse/lösa/resolve
            if not any(word in realized.lower() for word in ("løse", "lösa", "resolve", "خل", "شوف")):
                intent_ok = False
    checks["intent_preservation"] = intent_ok

    if "avoid_regression" in meaning.constraints:
        constraint_ok = any(
            marker in realized.lower()
            for marker in ("regression", "produksjon", "produktion", "produktionen", "تبوّظ", "تبوظ", "يتأثر")
        )
        checks["constraint_preservation"] = constraint_ok
        if not constraint_ok:
            omissions.append("constraint:avoid_regression")

    if plan.independent_verification:
        warnings.append("INDEPENDENT_VERIFIER_UNAVAILABLE_DETERMINISTIC_ONLY")
    back_translation = False
    if plan.back_translation:
        warnings.append("BACKTRANSLATION_OPTIONAL_NOT_RUN")

    status = "OK" if not omissions and checks.get("intent_preservation", True) else "FAILED"
    return {
        "status": status,
        "confidence": 0.8 if status == "OK" else 0.35,
        "evidence": [f"risk:{risk.value}", f"checks:{checks}"],
        "result": VerificationResult(
            status=status,
            risk=risk,
            checks=checks,
            omissions=omissions,
            unsupported_additions=additions,
            warnings=warnings,
            back_translation_used=back_translation,
        ),
        "warnings": warnings,
        "fallback_used": bool(plan.independent_verification),
        "provider": "deterministic-verifier",
    }
