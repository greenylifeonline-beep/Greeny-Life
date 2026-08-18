from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from raios_fi.adapters import MagikaAdapter, TikaAdapter, is_ast_grep, is_universal_ctags
from raios_fi.cognition import SharedCognitiveState, idle_continue
from raios_fi.compare import ComparisonEngine
from raios_fi.config import ORGANISM_ID, FailClosed
from raios_fi.duplicates import duplicate_groups
from raios_fi.extract import TextExtractionProvider
from raios_fi.store import IndexStore
from raios_fi.tools import detect_tools
from raios_fi.types import FileTypeProvider, classify_file


class AdapterCognitionTests(unittest.TestCase):
    def test_magika_adapter_reports_unavailable_without_install(self) -> None:
        health = MagikaAdapter.health()
        self.assertFalse(health["ok"])
        self.assertIn(health["status"], ("MISSING", "UNAVAILABLE"))
        self.assertEqual(health["adapter"], "WRAP")
        self.assertFalse(health["install"])
        self.assertIn("ADAPTER_PRESENT_BINARY_MISSING", health["evidence"])
        self.assertNotIn("PASS", json.dumps(health))

    def test_tika_adapter_reports_unavailable_without_install(self) -> None:
        health = TikaAdapter.health()
        self.assertFalse(health["ok"])
        self.assertIn(health["status"], ("MISSING", "UNAVAILABLE"))
        self.assertFalse(health["ocr"])
        self.assertFalse(health["install"])

    def test_gnu_ctags_is_not_universal(self) -> None:
        self.assertFalse(is_universal_ctags())

    def test_linux_sg_is_not_ast_grep(self) -> None:
        self.assertFalse(is_ast_grep())

    def test_type_classification_does_not_claim_magika_when_missing(self) -> None:
        health = FileTypeProvider().health()
        self.assertEqual(health["status"], "FALLBACK")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "probe.py"
            path.write_text("x=1\n", encoding="utf-8")
            result = classify_file(path)
            self.assertNotEqual(result.detector, "magika")
            self.assertIn(result.detector, ("signature+probe", "probe+ext-hint", "parser-probe-python", "signature"))

    def test_extraction_records_tika_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "note.pdf"
            path.write_bytes(b"%PDF-1.4 fake")
            result = TextExtractionProvider().analyze(
                {"absolute_path": str(path), "language": "pdf", "mime": "application/pdf", "sha256": "x"}
            )
            self.assertEqual(result["status"], "UNAVAILABLE")
            self.assertIn("TIKA_MISSING", result.get("errors") or [])
            self.assertIsNone(result.get("text"))
            self.assertNotIn('"PASS"', json.dumps(result))

    def test_utf16_extract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "utf16.md"
            path.write_bytes("hello café".encode("utf-16"))
            result = TextExtractionProvider().analyze(
                {"absolute_path": str(path), "is_text": True, "encoding": "utf-16", "sha256": "u"}
            )
            self.assertEqual(result["status"], "EXTRACTED")
            self.assertIn("hello", result["text"])

    def test_duplicate_groups_from_identical_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = IndexStore(Path(tmp) / "idx")
            rec = {
                "file_id": "a",
                "root_id": "r",
                "relative_path": "one.txt",
                "absolute_path": str(Path(tmp) / "one.txt"),
                "sha256": "deadbeef",
                "size": 4,
                "class": "DOCUMENT",
                "language": "txt",
                "mime": "text/plain",
                "is_text": True,
                "is_binary": False,
                "confidence": 1.0,
            }
            store.upsert_file(rec)
            rec2 = dict(rec)
            rec2["file_id"] = "b"
            rec2["relative_path"] = "two.txt"
            rec2["absolute_path"] = str(Path(tmp) / "two.txt")
            store.upsert_file(rec2)
            groups = duplicate_groups(store)
            self.assertEqual(len(groups), 1)
            self.assertEqual(groups[0]["count"], 2)
            self.assertEqual(groups[0]["confidence"], 1.0)
            self.assertEqual(groups[0]["state"], "PROVEN")
            store.close()

    def test_shared_cognitive_state_does_not_write_ccee(self) -> None:
        state = SharedCognitiveState.snapshot()
        self.assertEqual(state.organism, ORGANISM_ID)
        self.assertFalse(state.ccee_wal_writes)
        self.assertFalse(state.canonical_writes)
        idle = idle_continue(foreground_busy=True)
        self.assertTrue(idle["preempted"])
        self.assertEqual(idle["model_calls"], 0)
        self.assertNotIn("PASS", json.dumps(state.payload))

    def test_v9_write_still_blocked(self) -> None:
        with self.assertRaises(FailClosed):
            FailClosed.assert_writable(Path("/workspace/RAIOS/V9/README.md"))

    def test_tools_do_not_install_missing_binaries(self) -> None:
        catalog = {row["name"]: row for row in detect_tools()}
        self.assertFalse(catalog["magika"]["available"])
        self.assertFalse(catalog["tika"]["available"])
        self.assertFalse(catalog["tree-sitter"]["available"])
        self.assertIn("detect", catalog["magika"]["recommended_action"].lower())
        self.assertFalse(catalog["magika"]["install"])

    def test_json_config_diff_equivalent_and_modified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.json"
            b = Path(tmp) / "b.json"
            c = Path(tmp) / "c.json"
            a.write_text('{"z": 1, "a": 2}\n', encoding="utf-8")
            b.write_text('{"a": 2, "z": 1}\n', encoding="utf-8")
            c.write_text('{"a": 3, "z": 1}\n', encoding="utf-8")
            engine = ComparisonEngine()
            same = engine.config_diff(a, b)
            changed = engine.config_diff(a, c)
            self.assertEqual(same.what_changed, "config_equivalent")
            self.assertEqual(changed.what_changed, "config_modified")
            self.assertIn(same.why_likely_changed.split("_")[0], ("jq", "python-json"))


if __name__ == "__main__":
    unittest.main()
