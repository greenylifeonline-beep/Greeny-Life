from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from raios_fi.authority import classify_authority
from raios_fi.classify import classify_path
from raios_fi.confidence import build_confidence, verification_from_confidence
from raios_fi.config import CLASSIFIER_VERSION, PARSER_VERSION, PROVIDER_VERSION
from raios_fi.cortex import synthesize_proposal
from raios_fi.disagreement import resolve_votes
from raios_fi.identity import match_records
from raios_fi.liveness import classify_liveness
from raios_fi.modify import ModificationEngine, REQUIRED_STAGES
from raios_fi.query import compile_query
from raios_fi.store import IndexStore
from raios_fi.types import classify_file


class AddendumTests(unittest.TestCase):
    def test_authority_dimensions_independent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "archive" / "old.zip"
            path.parent.mkdir(parents=True)
            with zipfile.ZipFile(path, "w") as zf:
                zf.writestr("[Content_Types].xml", "<Types/>")
                zf.writestr("word/document.xml", "<w:document/>")
            typed = classify_file(path)
            classified = classify_path(path, typed)
            self.assertEqual(typed.physical_type, "ZIP")
            self.assertEqual(typed.logical_type, "OOXML_DOCUMENT")
            self.assertEqual(classified.authority_class, "HISTORICAL_EVIDENCE")
            self.assertEqual(classified.temporal_scope, "HISTORICAL")
            self.assertEqual(classified.knowledge_state, "SUPERSEDED")
            self.assertNotEqual(classified.authority_class, typed.file_class)
            self.assertNotEqual(classified.temporal_scope, classified.verification_state)
            self.assertNotEqual(classified.knowledge_state, classified.authority_class)

    def test_model_confidence_cannot_verify(self) -> None:
        conf = build_confidence(model=["qwen-says-ok"], supporting=["fluff"], base=0.99)
        self.assertFalse(conf.verification_eligible)
        self.assertEqual(verification_from_confidence(conf), "PARTIALLY_VERIFIED" if conf.band in {"STRONG", "DETERMINISTIC_REQUIRED"} else "UNVERIFIED")
        self.assertNotEqual(verification_from_confidence(conf), "VERIFIED")

    def test_disagreement_not_averaged(self) -> None:
        obj = resolve_votes(
            {
                "path_rules": "json",
                "signatures": "python",
                "parser": "python",
                "magika": "UNAVAILABLE",
            },
            file_id="f1",
            relative_path="not.json",
        )
        self.assertFalse(obj.averaged)
        self.assertGreaterEqual(len(obj.disagreeing_providers), 2)
        self.assertEqual(obj.resolution, "UNRESOLVED_DISAGREEMENT")

    def test_liveness_not_dead_from_one_heuristic(self) -> None:
        live = classify_liveness(Path("/tmp/orphan.py"), referenced=False)
        self.assertEqual(live.active_state, "ORPHAN_CANDIDATE")
        self.assertNotEqual(live.active_state, "DEAD_PROVEN")
        self.assertFalse(live.archive_allowed)
        self.assertFalse(live.delete_allowed)
        vendor = classify_liveness(Path("/tmp/node_modules/x.js"))
        self.assertEqual(vendor.active_state, "DYNAMIC_REFERENCE_POSSIBLE")

    def test_identity_basename_insufficient(self) -> None:
        a = {"relative_path": "a/foo.py", "root_relative": "a/foo.py", "sha256": "aaa"}
        b = {"relative_path": "b/foo.py", "root_relative": "b/foo.py", "sha256": "bbb"}
        match = match_records(a, b)
        self.assertTrue(match.basename_only)
        self.assertEqual(match.relation, "UNKNOWN")
        same = match_records(
            {"relative_path": "old.txt", "root_relative": "old.txt", "sha256": "dead"},
            {"relative_path": "new.txt", "root_relative": "new.txt", "sha256": "dead"},
        )
        self.assertEqual(same.relation, "RENAMED")
        moved = match_records(
            {"relative_path": "dir1/moved.txt", "root_relative": "dir1/moved.txt", "sha256": "m1"},
            {"relative_path": "dir2/moved.txt", "root_relative": "dir2/moved.txt", "sha256": "m1"},
        )
        self.assertEqual(moved.relation, "MOVED")

    def test_economic_planner_skips_unused_stages(self) -> None:
        plan = compile_query("find where an order becomes shipped and compare both versions")
        self.assertIn("STAGE_0_METADATA", plan.selected_stages)
        self.assertNotIn("STAGE_8_QWEN", plan.selected_stages)
        self.assertIn("STAGE_8_QWEN", plan.skipped_stages)
        self.assertFalse(plan.model_synthesis)
        cheap = compile_query("filename readme")
        self.assertLess(len(cheap.selected_stages), len(plan.selected_stages))
        self.assertNotIn("STAGE_4_AST", cheap.selected_stages)

    def test_cache_key_includes_classifier_and_provider_versions(self) -> None:
        self.assertTrue(CLASSIFIER_VERSION)
        self.assertTrue(PROVIDER_VERSION)
        self.assertTrue(PARSER_VERSION)
        with tempfile.TemporaryDirectory() as tmp:
            store = IndexStore(Path(tmp) / "idx")
            store.cache_put("abc", {"kind": "parse", "parser": "python-ast"}, kind="parse")
            hit = store.cache_get("abc", kind="parse")
            self.assertEqual(hit["parser"], "python-ast")
            self.assertGreaterEqual(store.cache_hits, 1)
            store.close()

    def test_cortex_output_is_proposal(self) -> None:
        proposal = synthesize_proposal(query_plan={"q": "x"}, evidence=[{"file_id": "1"}])
        self.assertEqual(proposal.knowledge_state, "PROPOSAL")
        self.assertFalse(proposal.model_used)
        self.assertIn(proposal.status, {"SKIPPED", "UNAVAILABLE"})

    def test_change_txn_abort_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = IndexStore(Path(tmp) / "idx")
            original = Path(tmp) / "src.py"
            original.write_text("x=1\n", encoding="utf-8")
            engine = ModificationEngine(store)
            txn = engine.begin(original)
            self.assertIn("READ", txn.stages_completed)
            self.assertIn("SNAPSHOT", txn.stages_completed)
            txn = engine.propose_and_shadow(txn, b"x=2\n")
            txn = engine.abort(txn, "forced")
            self.assertTrue(txn.aborted)
            self.assertTrue(txn.rolled_back)
            self.assertFalse(txn.applied)
            self.assertEqual(txn.failure_event["type"], "FAILURE_EVENT")
            self.assertEqual(txn.learning_signal["type"], "LEARNING_SIGNAL")
            self.assertEqual(original.read_text(encoding="utf-8"), "x=1\n")
            self.assertIn("EXPERIENCE_CAPTURE", REQUIRED_STAGES)
            store.close()

    def test_canonical_not_assigned_by_this_package(self) -> None:
        rec = classify_authority(Path("/workspace/app/page.tsx"))
        self.assertNotEqual(rec.knowledge_state, "CANONICAL")
        self.assertFalse(rec.model_used)


if __name__ == "__main__":
    unittest.main()
