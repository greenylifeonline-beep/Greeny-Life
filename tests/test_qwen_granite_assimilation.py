"""Qwen/Granite compiled-capability seam. No historical runtime import, no weights."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
os.environ.setdefault("NO_LLM_CALLS", "true")

from assimilated_brain import (  # noqa: E402
    c5_capability_surface,
    consult_assimilated,
    d059_acceptance_records,
    invoke_capability,
    list_capability_ids,
    load_assimilated_knowledge,
)
from assimilation_acceptance.d059_evidence_gate import (  # noqa: E402
    validate_evidence_file,
    validate_pair,
)


class QwenGraniteAssimilationSeam(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = ROOT
        cls.knowledge = load_assimilated_knowledge(cls.repo)

    def test_compiled_kb_is_present(self):
        self.assertEqual(self.knowledge["status"], "COMPILED_PROVEN")
        self.assertTrue(self.knowledge["SOURCE_INDEPENDENT"])
        self.assertFalse(self.knowledge["OLLAMA_REQUIRED"])
        self.assertFalse(self.knowledge["HISTORICAL_RUNTIME_IMPORTED"])
        self.assertFalse(self.knowledge["LIVE_INFERRED"])

    def test_qwen_capability_ids_are_explicit(self):
        ids = list_capability_ids(self.knowledge, "qwen")
        self.assertIn("brain.assimilated.qwen.CODE_REPAIR", ids)
        self.assertTrue(all(i.startswith("brain.assimilated.qwen.") for i in ids))
        self.assertGreaterEqual(len(ids), 8)

    def test_granite_capability_ids_are_explicit_and_distinct(self):
        qwen_ids = list_capability_ids(self.knowledge, "qwen")
        granite_ids = list_capability_ids(self.knowledge, "granite")
        self.assertIn("brain.assimilated.granite.KNOWLEDGE_ASSIMILATION", ids := granite_ids)
        self.assertNotIn("brain.assimilated.granite.KNOWLEDGE_ASSIMILATION", qwen_ids)
        self.assertNotIn("brain.assimilated.qwen.CODE_REPAIR", granite_ids)
        self.assertTrue(all(i.startswith("brain.assimilated.granite.") for i in granite_ids))
        self.assertFalse(set(qwen_ids) & set(granite_ids))

    def test_source_hashes_are_family_independent(self):
        qwen = {u["source_sha256"] for u in self.knowledge["families"]["qwen"]["units"]}
        granite = {u["source_sha256"] for u in self.knowledge["families"]["granite"]["units"]}
        self.assertTrue(qwen)
        self.assertTrue(granite)
        self.assertFalse(qwen & granite)

    def test_runtime_does_not_import_historical_tree(self):
        rec = consult_assimilated("debug failing pytest and repair repository code", self.knowledge)
        self.assertEqual(rec["selected_family"], "qwen")
        self.assertFalse(rec["HISTORICAL_RUNTIME_IMPORTED"])
        self.assertFalse(rec["OLLAMA_REQUIRED"])
        for name in sys.modules:
            self.assertFalse(name.startswith("_raios"), name)
            self.assertNotIn("live_assimilation_runtime", name)
            self.assertNotIn("LiveAssimilationBridge", name)

    def test_granite_not_inferred_from_qwen(self):
        rec = consult_assimilated(
            "ingest claims with provenance and resolve contradictions for critique",
            self.knowledge,
        )
        self.assertEqual(rec["selected_family"], "granite")
        inv = invoke_capability("brain.assimilated.granite.KNOWLEDGE_ASSIMILATION", self.repo, cortex_available=False)
        self.assertEqual(inv["status"], "COMPILED_PROVEN")
        self.assertEqual(inv["family"], "granite")
        self.assertTrue(inv["cortex_absence_does_not_falsify_compiled"])

    def test_qwen_invoke_fail_closed_on_unknown(self):
        inv = invoke_capability("brain.assimilated.qwen.NOT_A_CAPABILITY", self.repo)
        self.assertEqual(inv["status"], "FAIL_CLOSED")
        self.assertEqual(inv["reason"], "CAPABILITY_NOT_MATERIALIZED")
        self.assertFalse(inv["LIVE_INFERRED"])

    def test_missing_kb_is_fail_closed_not_live_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            packed = load_assimilated_knowledge(tmp)
            rec = consult_assimilated("anything", packed, tmp)
        self.assertEqual(packed["status"], "FAIL_CLOSED")
        self.assertEqual(rec["status"], "FAIL_CLOSED")
        self.assertFalse(rec["LIVE_INFERRED"])

    def test_stale_historical_live_artifact_rejected(self):
        rec = consult_assimilated("replay LiveAssimilationBridge LIVE-ASSIMILATION-STATE.json", self.knowledge)
        self.assertEqual(rec["status"], "FAIL_CLOSED")
        self.assertEqual(rec["reason"], "STALE_HISTORICAL_LIVE_ARTIFACT")

    def test_c5_enterprise_brain_surface(self):
        surface = c5_capability_surface(self.repo)
        self.assertEqual(surface["status"], "COMPILED_PROVEN")
        self.assertTrue(surface["QWEN_BRAIN_WIRING_PROVEN"])
        self.assertTrue(surface["GRANITE_BRAIN_WIRING_PROVEN"])
        self.assertTrue(surface["QWEN_RUNTIME_PROVEN"])
        self.assertTrue(surface["GRANITE_RUNTIME_PROVEN"])
        self.assertFalse(surface["HISTORICAL_LINEAGE_147D_MERGED"])
        self.assertFalse(surface["OLLAMA_REQUIRED"])

    def test_qwen13_is_not_a_capability(self):
        ids = list_capability_ids(self.knowledge, "qwen") + list_capability_ids(self.knowledge, "granite")
        blob = " ".join(ids).lower()
        self.assertNotIn("13b", blob)
        self.assertNotIn("qwen-13", blob)
        self.assertNotIn("35b", blob)

    def test_no_archive_path_required_at_runtime(self):
        for fam in ("qwen", "granite"):
            rec = self.knowledge["families"][fam]
            self.assertFalse(rec.get("runtime_requires_archive_path"))
            self.assertFalse(rec.get("runtime_requires_ollama"))
            for unit in rec["units"]:
                self.assertNotIn("source_rel", unit)
                self.assertTrue(unit.get("source_sha256"))

    def test_d059_acceptance_records_pass_c1_gate(self):
        records = d059_acceptance_records(self.repo)
        self.assertEqual(validate_pair(records), [])
        by_family = {r["family"]: r for r in records}
        self.assertIn("brain.assimilated.qwen.CODE_REPAIR", by_family["qwen"]["capability_ids"])
        self.assertIn(
            "brain.assimilated.granite.KNOWLEDGE_ASSIMILATION",
            by_family["granite"]["capability_ids"],
        )
        self.assertNotEqual(by_family["qwen"]["source_provenance"], by_family["granite"]["source_provenance"])

    def test_d059_acceptance_evidence_file_passes_gate(self):
        path = ROOT / "intelligence" / "knowledge_base" / "assimilated" / "D059-ACCEPTANCE.json"
        self.assertTrue(path.is_file(), path)
        result = validate_evidence_file(path)
        self.assertTrue(result["accepted"], result["errors"])


if __name__ == "__main__":
    unittest.main()
