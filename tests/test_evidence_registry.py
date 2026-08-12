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
