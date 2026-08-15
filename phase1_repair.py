from pathlib import Path
import json
import re
import sys

root = Path.cwd()

contract = root / "greenlines_brain" / "contract.py"
repo = root / "greenlines_brain" / "repository" / "json_repo.py"
kernel = root / "greenlines_brain" / "kernel.py"
test_file = root / "tests" / "test_evidence_gate.py"

for path in (contract, repo, kernel):
    if not path.exists():
        raise SystemExit(f"Missing required file: {path}")

text = contract.read_text(encoding="utf-8-sig")

if "class DecisionStatus(Enum):" not in text:
    text = text.replace(
        "class EvidenceType(Enum):",
        """class DecisionStatus(Enum):
    GO = "GO"
    NEEDS_VERIFICATION = "NEEDS_VERIFICATION"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"
    NO_GO = "NO_GO"

class EvidenceType(Enum):""",
        1,
    )

if "evidence_gaps: List[str]" not in text:
    text = text.replace(
        "    expected_outcome: str",
        """    expected_outcome: str
    status: DecisionStatus = DecisionStatus.NEEDS_VERIFICATION
    evidence_gaps: List[str] = field(default_factory=list)""",
        1,
    )

contract.write_text(text, encoding="utf-8")

text = repo.read_text(encoding="utf-8-sig")

if "def find_evidence(self, *, product: str, destination: str)" not in text:
    text = text.replace(
        "    def search(self, query: str) -> List[Dict]:",
        """    def find_evidence(self, *, product: str, destination: str) -> List[Dict]:
        matches = []
        for evidence in self.load_knowledge().get("evidence", []):
            scope = evidence.get("scope", {})
            if scope.get("product", "").lower() == product.lower() and scope.get("destination", "").lower() == destination.lower():
                matches.append(evidence)
        return matches

    def search(self, query: str) -> List[Dict]:""",
        1,
    )

repo.write_text(text, encoding="utf-8")

text = kernel.read_text(encoding="utf-8-sig")
text = text.replace(
    "    ConfidenceLevel, EvidenceType\n",
    "    ConfidenceLevel, EvidenceType, DecisionStatus\n",
    1,
)

text, count = re.subn(
    r"\n        if not self\.relations:\n.*?\n    def _parse_rule_to_relations",
    "\n    def _parse_rule_to_relations",
    text,
    count=1,
    flags=re.DOTALL,
)
if count != 1:
    raise SystemExit("Safety stop: default relations block was not found.")

text, count = re.subn(
    r"\n        if not relations and .*?\n.*?relations\.append\(SemanticRelation\(words\[0\], \"related_to\", words\[-1\], 0\.3\)\)\n",
    "\n",
    text,
    count=1,
    flags=re.DOTALL,
)
if count != 1:
    raise SystemExit("Safety stop: heuristic relation block was not found.")

if "No current evidence record is explicitly scoped" not in text:
    gate = """        alternatives = []
        finder = getattr(self.repository, "find_evidence", None)
        scenario_evidence = finder(product=product, destination=destination) if objective == "export" and destination and callable(finder) else []

        if objective == "export" and destination and not scenario_evidence:
            return Decision(
                decision_id=decision_id,
                recommendation="Do not execute export. Verification is required before a recommendation.",
                reasoning="No evidence-backed trade decision can be made for this scenario.",
                evidence=[],
                confidence=ConfidenceLevel.UNKNOWN,
                risks=["Unsupported regulatory decision"],
                constraints=["Execution is blocked until required evidence is verified."],
                assumptions=[],
                alternatives=["Collect current official evidence and resubmit the scenario."],
                entity_scope=self.identity.scope.value,
                expected_outcome=f"{objective} for {product} to {destination}",
                status=DecisionStatus.NEEDS_VERIFICATION,
                evidence_gaps=["No current evidence record is explicitly scoped to this product and destination."],
            )
"""
    text = text.replace("        alternatives = []\n", gate, 1)

kernel.write_text(text, encoding="utf-8")

test_file.parent.mkdir(exist_ok=True)
test_file.write_text(
    """import contextlib
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
""",
    encoding="utf-8",
)

print("Phase 1 applied.")
