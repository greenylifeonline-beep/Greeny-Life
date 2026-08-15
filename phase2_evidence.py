from pathlib import Path

root = Path.cwd()
module = root / "greenlines_brain" / "evidence_gate.py"
test = root / "tests" / "test_evidence_registry.py"

module.write_text(r'''
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any, Dict, List


class EvidenceState(Enum):
    NEEDS_VERIFICATION = "NEEDS_VERIFICATION"
    SUPPORTED_BY_OFFICIAL_SOURCE = "SUPPORTED_BY_OFFICIAL_SOURCE"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"
    NO_GO = "NO_GO"


REQUIRED_GATES = {
    "country_eligibility",
    "establishment_listing",
    "official_certificate",
    "border_process",
    "importer_registration",
}


@dataclass(frozen=True)
class EvidenceAssessment:
    state: EvidenceState
    evidence_ids: List[str]
    missing_gates: List[str]
    reasons: List[str]


def assess_export_evidence(
    evidence: List[Dict[str, Any]],
    product: str,
    destination: str,
    today: date | None = None,
) -> EvidenceAssessment:
    today = today or date.today()

    scoped = [
        item for item in evidence
        if item.get("scope", {}).get("product", "").lower() == product.lower()
        and item.get("scope", {}).get("destination", "").lower() == destination.lower()
    ]

    if not scoped:
        return EvidenceAssessment(
            EvidenceState.NEEDS_VERIFICATION,
            [],
            sorted(REQUIRED_GATES),
            ["No evidence is explicitly scoped to this product and destination."],
        )

    evidence_ids = [item.get("id", "unknown") for item in scoped]
    reasons = []
    covered = set()

    for item in scoped:
        if item.get("authority") != "official":
            reasons.append(f'{item.get("id", "unknown")} is not an official source.')
            continue

        if item.get("verification_status") != "verified_current":
            reasons.append(f'{item.get("id", "unknown")} is not verified current.')
            continue

        valid_to = item.get("valid_to")
        if valid_to and date.fromisoformat(valid_to) < today:
            reasons.append(f'{item.get("id", "unknown")} is expired.')
            continue

        if item.get("claim_status") == "prohibited":
            return EvidenceAssessment(
                EvidenceState.NO_GO,
                evidence_ids,
                [],
                [f'{item.get("id", "unknown")} explicitly prohibits this scenario.'],
            )

        covered.update(item.get("gates", []))

    missing = sorted(REQUIRED_GATES - covered)

    if reasons:
        return EvidenceAssessment(
            EvidenceState.REQUIRES_HUMAN_REVIEW,
            evidence_ids,
            missing,
            reasons,
        )

    if missing:
        return EvidenceAssessment(
            EvidenceState.NEEDS_VERIFICATION,
            evidence_ids,
            missing,
            ["Official evidence exists, but required decision gates are incomplete."],
        )

    return EvidenceAssessment(
        EvidenceState.SUPPORTED_BY_OFFICIAL_SOURCE,
        evidence_ids,
        [],
        ["All required gates have current official evidence."],
    )
'''.lstrip(), encoding="utf-8")

test.write_text(r'''
import unittest
from datetime import date

from greenlines_brain.evidence_gate import EvidenceState, assess_export_evidence


def evidence(**overrides):
    item = {
        "id": "EVIDENCE-001",
        "authority": "official",
        "verification_status": "verified_current",
        "claim_status": "supported",
        "valid_to": "2030-01-01",
        "scope": {"product": "honey", "destination": "norway"},
        "gates": [],
    }
    item.update(overrides)
    return item


class EvidenceRegistryTests(unittest.TestCase):
    def test_no_evidence_needs_verification(self):
        result = assess_export_evidence([], "honey", "norway", date(2026, 8, 12))
        self.assertEqual(result.state, EvidenceState.NEEDS_VERIFICATION)
        self.assertEqual(len(result.missing_gates), 5)

    def test_stale_or_unverified_evidence_requires_review(self):
        result = assess_export_evidence(
            [evidence(verification_status="stale")],
            "honey", "norway", date(2026, 8, 12),
        )
        self.assertEqual(result.state, EvidenceState.REQUIRES_HUMAN_REVIEW)

    def test_prohibition_is_no_go(self):
        result = assess_export_evidence(
            [evidence(claim_status="prohibited")],
            "honey", "norway", date(2026, 8, 12),
        )
        self.assertEqual(result.state, EvidenceState.NO_GO)

    def test_complete_official_evidence_is_supported(self):
        result = assess_export_evidence(
            [evidence(gates=[
                "country_eligibility",
                "establishment_listing",
                "official_certificate",
                "border_process",
                "importer_registration",
            ])],
            "honey", "norway", date(2026, 8, 12),
        )
        self.assertEqual(result.state, EvidenceState.SUPPORTED_BY_OFFICIAL_SOURCE)


if __name__ == "__main__":
    unittest.main()
'''.lstrip(), encoding="utf-8")

print("Phase 2 evidence module and tests created.")