import contextlib
import io
import unittest
from pathlib import Path

from greenlines_brain.contract import ConfidenceLevel, DecisionStatus
from greenlines_brain.identity import EntityScope, Identity
from greenlines_brain.kernel import GreenlinesBrain
from greenlines_brain.repository.json_repo import JSONKnowledgeRepository


class LegacyBrainRuntimeTests(unittest.TestCase):
    def setUp(self):
        identity = Identity(EntityScope.EGYPT, "Greeny Life Egypt", "Egypt", "EGP")
        with contextlib.redirect_stdout(io.StringIO()):
            self.brain = GreenlinesBrain(identity, JSONKnowledgeRepository(Path("greenlines_brain/dna/extracted_knowledge.json")))

    def test_extracted_knowledge_does_not_authorize_honey_to_norway(self):
        decision = self.brain.decide("export", "egypt", "honey", "norway")
        self.assertEqual(decision.status, DecisionStatus.NEEDS_VERIFICATION)
        self.assertEqual(decision.confidence, ConfidenceLevel.UNKNOWN)
        self.assertNotEqual(decision.status, DecisionStatus.GO)
        self.assertEqual(len(decision.evidence), 0)

    def test_extracted_knowledge_does_not_authorize_spices_to_eu(self):
        decision = self.brain.decide("export", "egypt", "spices", "eu")
        self.assertEqual(decision.status, DecisionStatus.NEEDS_VERIFICATION)
        self.assertEqual(decision.confidence, ConfidenceLevel.UNKNOWN)
        self.assertNotEqual(decision.status, DecisionStatus.GO)


if __name__ == "__main__":
    unittest.main()
