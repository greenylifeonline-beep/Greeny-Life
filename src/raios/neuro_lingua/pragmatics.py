from __future__ import annotations

import re
from typing import Any

from .schema import ModalityProfile, PragmaticsProfile, TemporalProfile


POLITENESS_NOT_CONDITION = (
    "إذا ما عليك أمر",
    "اذا ما عليك امر",
    "لو سمحت",
    "من فضلك",
    "لو تكرمت",
    "إذا ما عليك أمر",
)

TODAY_DEADLINE = ("اليوم", "النهارده", "النهاردة", "today", "i dag", "idag")
WARNING_MARKERS = ("هتبوظ", "تتكسر", "يبوظ", "regression", "uten å påvirke", "utan att påverka", "uden at påvirke")
REQUEST_MARKERS = ("شوف لنا", "خلصلي", "خلصه", "kan du", "please", "kontrollera", "tjek")
SOFT_IMPERATIVE = ("شوف لنا", "لو سمحت", "إذا ما عليك أمر")


def analyze_pragmatics(text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    notes: list[str] = []
    evidence: list[str] = []
    politeness = any(marker in text for marker in POLITENESS_NOT_CONDITION) or "لو سمحت" in text
    if politeness:
        evidence.append("politeness_phrase")
        notes.append("politeness_is_not_logical_condition")

    deadline = None
    if any(marker in text.lower() for marker in TODAY_DEADLINE) or "اليوم" in text or "النهارده" in text:
        deadline = "today"
        evidence.append("deadline:today")

    warning = any(marker in text for marker in WARNING_MARKERS) or "متبوظش" in text
    if warning:
        evidence.append("warning_or_non_regression")

    request = any(marker in text.lower() for marker in REQUEST_MARKERS) or "خلصلي" in text or "خلصه" in text
    softened = any(marker in text for marker in SOFT_IMPERATIVE)
    uncertainty = bool(re.search(r"\b(maybe|perhaps|قد|ممكن)\b", text, re.I))

    literal_condition = bool(re.search(r"\b(if|only if|hvis|om)\b", text, re.I))
    condition = literal_condition and not politeness
    if politeness and "إذا" in text:
        notes.append("arabic_in_condition_surface_is_politeness")
        evidence.append("politeness_overrides_condition")

    pragmatics = PragmaticsProfile(
        politeness_marker=politeness,
        urgency="today" if deadline == "today" else None,
        warning=warning,
        softened_command=softened,
        request=request,
        uncertainty=uncertainty,
        condition=condition,
        social_marker="politeness" if politeness else None,
        deadline=deadline,
        notes=notes,
    )
    temporal = TemporalProfile(deadline=deadline, relative=deadline, evidence=evidence if deadline else [])
    modality = ModalityProfile(
        imperative=softened or ("خلصه" in text) or ("remove" in text.lower()),
        request=request or politeness,
        prohibition="متبوظش" in text or "ikke" in text.lower() or "inte" in text.lower() or "uden" in text.lower() or "only if" in text.lower(),
        possibility=uncertainty,
    )

    action = None
    if request or softened or "خلصلي" in text or "خلصه" in text or "شوف لنا" in text:
        action = "resolve"
        evidence.append("action:resolve")
    elif "remove" in text.lower():
        action = "remove"
    elif "kontrollera" in text.lower() or "tjek" in text.lower() or "check" in text.lower():
        action = "inspect"

    domain_warning = None
    if warning and context.get("domain") in {"project", "system", None}:
        if "هتبوظ" in text or "يبوظ" in text:
            domain_warning = "risk_of_regression"
            evidence.append("context_regression_idiom")
            notes.append("idiom_resolved_with_project_context")

    confidence = 0.82 if (politeness or deadline or request) else 0.55
    return {
        "status": "OK",
        "confidence": confidence,
        "evidence": evidence,
        "pragmatics": pragmatics,
        "temporal": temporal,
        "modality": modality,
        "action": action,
        "domain_warning": domain_warning,
        "warnings": [],
    }


def analyze_register(text: str, locale: str) -> dict[str, Any]:
    spoken = 0.7 if locale.startswith("ar-") and any(m in text for m in ("ده", "مش", "وايد", "زين")) else 0.2
    formal = 0.3 if spoken > 0.5 else 0.6
    professional = 0.7 if any(w in text.lower() for w in ("production", "migration", "executor", "deploy")) else 0.5
    return {
        "status": "OK",
        "confidence": 0.6,
        "evidence": [f"spoken={spoken:.2f}"],
        "register": {"formality": formal, "professional": professional, "spoken": spoken},
        "warnings": [],
    }
