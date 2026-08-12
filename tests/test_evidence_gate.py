import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from greenlines_brain.contract import ConfidenceLevel, DecisionStatus
from greenlines_brain.identity import EntityScope, Identity
from greenlines_brain.kernel import GreenlinesBrain
from greenlines_brain.repository.json_repo import JSONKnowledgeRepository


class EvidenceGateTests(unittest.TestCase):
    def test_missing_evidence_blocks_export_twice(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "knowledge.json"
            path.write_text(json.dumps({
                "entities": [], "business_rules": [], "master_data": [],
                "capabilities": [], "relationships": [], "workflows": [], "evidence": []
            }), encoding="utf-8")

            identity = Identity(EntityScope.EGYPT, "Greeny Life Egypt", "Egypt", "EGP")
            with contextlib.redirect_stdout(io.StringIO()):
                brain = GreenlinesBrain(identity, JSONKnowledgeRepository(path))

            first = brain.decide("export", "egypt", "honey", "norway")
            second = brain.decide("export", "egypt", "honey", "norway")

            self.assertEqual(first.status, DecisionStatus.NEEDS_VERIFICATION)
            self.assertEqual(second.status, DecisionStatus.NEEDS_VERIFICATION)
            self.assertEqual(first.confidence, ConfidenceLevel.UNKNOWN)
            self.assertEqual(first.recommendation, second.recommendation)
            self.assertNotEqual(first.status, DecisionStatus.GO)


if __name__ == "__main__":
    unittest.main()
