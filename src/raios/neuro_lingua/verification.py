"""Risk-based semantic verification.

Reuses GL-DOS RiskLevel (LOW/MEDIUM/HIGH/CRITICAL). Back-translation is
never the default; it is available only at CRITICAL when explicitly enabled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from raios.neuro_lingua.packet import CognitiveMeaningPacket
from raios.neuro_lingua.preservation import canonical_number
from raios.neuro_lingua.scandinavian import LeakageReport, ScandinavianIsolator
from raios.risk import RiskLevel


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    missing: list[str] = field(default_factory=list)
    extras: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "detail": self.detail,
            "missing": list(self.missing),
            "extras": list(self.extras),
        }


@dataclass
class VerificationReport:
    risk_level: RiskLevel
    passed: bool
    checks: list[CheckResult]
    leakage: LeakageReport | None = None
    used_back_translation: bool = False
    independent_verifier: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_level": self.risk_level.value,
            "passed": self.passed,
            "checks": [check.to_dict() for check in self.checks],
            "leakage": self.leakage.to_dict() if self.leakage else None,
            "used_back_translation": self.used_back_translation,
            "independent_verifier": self.independent_verifier,
        }


POLICY = {
    RiskLevel.LOW: ("number", "identifier"),
    RiskLevel.MEDIUM: ("number", "identifier", "entity", "terminology", "semantic", "addition", "omission"),
    RiskLevel.HIGH: ("number", "identifier", "entity", "terminology", "semantic", "addition", "omission", "independent"),
    RiskLevel.CRITICAL: (
        "number",
        "identifier",
        "entity",
        "terminology",
        "semantic",
        "addition",
        "omission",
        "independent",
        "back_translation",
    ),
}


def _surfaces(items: Iterable[Any], attr: str = "surface") -> list[str]:
    return [getattr(item, attr) for item in items]


def _contains(haystack: str, needle: str) -> bool:
    return needle in haystack


class SemanticVerifier:
    def __init__(self, isolator: ScandinavianIsolator) -> None:
        self.isolator = isolator

    def verify(
        self,
        meaning: CognitiveMeaningPacket,
        rendered: str,
        target_locale: str,
        *,
        risk_level: RiskLevel | None = None,
        allow_back_translation: bool = False,
        independent_payload: dict[str, Any] | None = None,
    ) -> VerificationReport:
        level = risk_level or meaning.risk_level
        required = POLICY[level]
        checks: list[CheckResult] = []

        if "number" in required:
            checks.append(self._preserve("number", _surfaces(meaning.numbers), rendered, numeric=True))
        if "identifier" in required:
            checks.append(self._preserve("identifier", _surfaces(meaning.identifiers), rendered))
        if "entity" in required:
            checks.append(self._preserve("entity", _surfaces(meaning.entities), rendered))
        if "terminology" in required:
            terms = [span.surface for span in meaning.terminology]
            preserve_ids = [
                c.concept_id for c in meaning.concepts
            ]
            # Terminology that the registry marked preserve_surface is required.
            checks.append(self._preserve("terminology", terms, rendered))
            _ = preserve_ids
        if "semantic" in required:
            checks.append(self._semantic_equivalence(meaning, rendered, target_locale))
        if "addition" in required:
            checks.append(self._unsupported_additions(meaning, rendered))
        if "omission" in required:
            checks.append(self._omissions(meaning, rendered))

        leakage = self.isolator.detect_leakage(rendered, target_locale)
        if target_locale in {"nb-NO", "sv-SE", "da-DK"}:
            checks.append(
                CheckResult(
                    name="target_language_leakage",
                    passed=leakage.passed,
                    detail="scandinavian_isolation",
                    extras=leakage.leaked_tokens,
                )
            )

        independent = False
        used_bt = False
        if "independent" in required:
            independent = independent_payload is not None
            if independent_payload is None:
                checks.append(
                    CheckResult(
                        name="independent_semantic_verification",
                        passed=False,
                        detail="independent verifier not attached; HIGH/CRITICAL cannot be fully certified offline",
                    )
                )
            else:
                ok = bool(independent_payload.get("equivalent", False))
                checks.append(
                    CheckResult(
                        name="independent_semantic_verification",
                        passed=ok,
                        detail=str(independent_payload.get("detail") or "independent"),
                    )
                )
        if "back_translation" in required:
            if not allow_back_translation:
                checks.append(
                    CheckResult(
                        name="back_translation",
                        passed=True,
                        detail="skipped_not_enabled",
                    )
                )
            else:
                used_bt = True
                checks.append(
                    CheckResult(
                        name="back_translation",
                        passed=bool((independent_payload or {}).get("back_translation_ok", False)),
                        detail="back_translation_requested",
                    )
                )

        passed = all(check.passed for check in checks)
        return VerificationReport(
            risk_level=level,
            passed=passed,
            checks=checks,
            leakage=leakage,
            used_back_translation=used_bt,
            independent_verifier=independent,
        )

    def _preserve(
        self,
        name: str,
        required: list[str],
        rendered: str,
        *,
        numeric: bool = False,
    ) -> CheckResult:
        missing: list[str] = []
        for surface in required:
            if not surface:
                continue
            if _contains(rendered, surface):
                continue
            if numeric and canonical_number(surface) in rendered:
                continue
            # Technical segments may appear as stems (builden → build is NOT OK;
            # the required surface must survive).
            missing.append(surface)
        return CheckResult(
            name=f"{name}_preservation",
            passed=not missing,
            detail="surface_must_survive",
            missing=missing,
        )

    def _semantic_equivalence(
        self,
        meaning: CognitiveMeaningPacket,
        rendered: str,
        target_locale: str,
    ) -> CheckResult:
        missing_concepts: list[str] = []
        for concept in meaning.concepts:
            if concept.concept_id.startswith("pragmatics."):
                continue
            # Preserve-surface concepts must appear as themselves.
            if concept.surface and concept.surface in rendered:
                continue
            # Otherwise we require the concept_id to have been used in construction;
            # the realizer records concept_ids in evidence via presence of realization.
            # If realization_complete is unknown here, treat missing surface of
            # preserve terms only.
            if concept.concept_id.startswith("software.") and concept.surface not in rendered:
                missing_concepts.append(concept.concept_id)
        prag = meaning.pragmatics
        if prag.politeness_marker and any(
            cond in rendered for cond in prag.not_logical_condition
        ):
            return CheckResult(
                name="semantic_equivalence",
                passed=False,
                detail="politeness_marker_realized_as_logical_condition",
                extras=list(prag.not_logical_condition),
            )
        return CheckResult(
            name="semantic_equivalence",
            passed=not missing_concepts,
            detail="concept_surfaces",
            missing=missing_concepts,
        )

    def _unsupported_additions(self, meaning: CognitiveMeaningPacket, rendered: str) -> CheckResult:
        # Cheap heuristic: numeric tokens in output that were not in input.
        src_numbers = {canonical_number(span.surface) for span in meaning.numbers}
        out_numbers = {canonical_number(span.surface) for span in _numbers_in(rendered)}
        extras = sorted(out_numbers - src_numbers - {""})
        return CheckResult(
            name="unsupported_addition",
            passed=not extras,
            detail="unexpected_numbers",
            extras=extras,
        )

    def _omissions(self, meaning: CognitiveMeaningPacket, rendered: str) -> CheckResult:
        missing: list[str] = []
        if meaning.pragmatics.action and meaning.pragmatics.action == "resolve":
            # Action must be represented by a bound realization or by a known verb.
            verbs = ("resolve", "løs", "lös", "خلّص", "خلص", "finish", "løse", "lösa")
            if not any(verb in rendered.lower() for verb in verbs) and "resolve" not in rendered:
                # Arabic realization may use registry form.
                if not any(verb in rendered for verb in verbs):
                    missing.append("action.resolve")
        if meaning.pragmatics.deadline == "today":
            markers = ("today", "i dag", "idag", "اليوم")
            if not any(marker in rendered for marker in markers):
                missing.append("deadline.today")
        return CheckResult(
            name="omission",
            passed=not missing,
            detail="required_pragmatic_slots",
            missing=missing,
        )


def _numbers_in(text: str) -> list[Any]:
    from raios.neuro_lingua.preservation import extract_numbers

    return extract_numbers(text)
