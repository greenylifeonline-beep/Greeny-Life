from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))

from raios_fi.archive import ArchiveEngine  # noqa: E402
from raios_fi.compare import ComparisonEngine  # noqa: E402
from raios_fi.config import FailClosed, MAX_INDEX_BYTES, sha256_bytes  # noqa: E402
from raios_fi.discovery import FileDiscoveryProvider  # noqa: E402
from raios_fi.doctor import contains_forbidden_success, run_doctor  # noqa: E402
from raios_fi.economy import ToolEconomy  # noqa: E402
from raios_fi.extract import TextExtractionProvider  # noqa: E402
from raios_fi.graph import FileKnowledgeGraph  # noqa: E402
from raios_fi.idle import IdleLoop  # noqa: E402
from raios_fi.merge import MergeIntelligence  # noqa: E402
from raios_fi.modify import ModificationEngine  # noqa: E402
from raios_fi.parse import parse_file  # noqa: E402
from raios_fi.providers import default_registry  # noqa: E402
from raios_fi.query import compile_query  # noqa: E402
from raios_fi.repair import mine_repairs  # noqa: E402
from raios_fi.runtime import FileIntelligenceRuntime  # noqa: E402
from raios_fi.search import SearchProvider  # noqa: E402
from raios_fi.store import IndexStore  # noqa: E402
from raios_fi.types import classify_file  # noqa: E402
from raios_fi.versions import differential  # noqa: E402


def _write(path: Path, data: bytes | str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_bytes(data)
    return path


class FileIntelligenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = IndexStore(self.root / "index", repo=REPO)

    def tearDown(self) -> None:
        self.store.close()
        self.tmp.cleanup()

    def test_unknown_binary(self) -> None:
        path = _write(self.root / "blob.unknown", b"\x00\x01\x02\xff\x00RANDOM")
        typed = classify_file(path)
        self.assertEqual(typed.file_class, "BINARY")
        self.assertFalse(typed.extension_trusted)

    def test_misleading_extension_python_as_json(self) -> None:
        path = _write(self.root / "not.json", "def hello():\n    return 1\n")
        typed = classify_file(path)
        self.assertEqual(typed.file_class, "CODE")
        self.assertEqual(typed.language, "python")
        self.assertNotEqual(typed.detector, "extension")

    def test_misleading_zip_as_txt(self) -> None:
        path = self.root / "secret.txt"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("inner.txt", "hello")
        typed = classify_file(path)
        self.assertEqual(typed.file_class, "ARCHIVE")

    def test_utf8(self) -> None:
        path = _write(self.root / "utf8.md", "café résumé\n")
        typed = classify_file(path)
        self.assertTrue(typed.is_text)
        self.assertEqual(typed.encoding, "utf-8")
        extracted = TextExtractionProvider().analyze(
            {"absolute_path": str(path), "sha256": sha256_bytes(path.read_bytes()), "is_text": True, "encoding": "utf-8"}
        )
        self.assertIn("café", extracted["text"])

    def test_utf16(self) -> None:
        path = self.root / "utf16.md"
        path.write_bytes("hello world".encode("utf-16"))
        typed = classify_file(path)
        self.assertTrue(typed.is_text)
        self.assertEqual(typed.encoding, "utf-16")

    def test_large_text_skips_full_index_hash(self) -> None:
        path = _write(self.root / "huge.txt", "x" * (MAX_INDEX_BYTES + 10))
        disc = FileDiscoveryProvider(self.root)
        rec = disc.file_object(path, self.root, "root-test")
        self.assertEqual(rec["size"], MAX_INDEX_BYTES + 10)
        self.assertFalse(rec["evidence"]["hash"])

    def test_json_yaml_md(self) -> None:
        js = _write(self.root / "a.json", '{"ok": true}')
        yml = _write(self.root / "a.yaml", "ok: true\n")
        md = _write(self.root / "a.md", "# title\n")
        self.assertEqual(classify_file(js).file_class, "DATA")
        self.assertEqual(classify_file(yml).file_class, "CONFIG")
        self.assertEqual(classify_file(md).file_class, "DOCUMENT")

    def test_python_symbols(self) -> None:
        path = _write(
            self.root / "mod.py",
            "import os\nclass Box:\n    def hold(self):\n        return 1\n\ndef run():\n    return Box()\n",
        )
        parsed = parse_file(path)
        names = {s.qualified_name for s in parsed.symbols}
        self.assertIn("Box", names)
        self.assertIn("Box.hold", names)
        self.assertIn("run", names)
        self.assertFalse(parsed.qwen_used)
        self.assertEqual(parsed.parser, "python-ast")

    def test_ts_tsx_ps1_sql(self) -> None:
        ts = _write(self.root / "a.ts", "export function shipOrder() { return true }\n")
        tsx = _write(self.root / "a.tsx", "export function Page() { return null }\n")
        ps = _write(self.root / "a.ps1", "function Get-Order { param($Id) }\n")
        sql = _write(self.root / "a.sql", "CREATE TABLE orders (id INT);\n")
        self.assertTrue(any(s.name == "shipOrder" for s in parse_file(ts).symbols))
        self.assertTrue(any(s.name == "Page" for s in parse_file(tsx).symbols))
        self.assertTrue(any(s.name == "Get-Order" for s in parse_file(ps).symbols))
        self.assertTrue(any(s.name == "orders" for s in parse_file(sql).symbols))

    def test_pdf_unavailable_without_tika(self) -> None:
        path = _write(self.root / "doc.pdf", b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\ntrailer\n")
        typed = classify_file(path)
        self.assertEqual(typed.file_class, "DOCUMENT")
        extracted = TextExtractionProvider().analyze(
            {"absolute_path": str(path), "sha256": "x", "language": "pdf", "mime": "application/pdf"}
        )
        self.assertEqual(extracted["status"], "UNAVAILABLE")
        self.assertEqual(extracted["reason"], "TIKA_MISSING")
        self.assertIsNone(extracted["text"])

    def test_zip_manifest(self) -> None:
        path = self.root / "pack.zip"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("a/b.txt", "n")
        extracted = TextExtractionProvider().analyze(
            {"absolute_path": str(path), "sha256": "z", "class": "ARCHIVE"}
        )
        self.assertEqual(extracted["status"], "MANIFEST")
        self.assertIn("a/b.txt", extracted["embedded_resources"])

    def test_duplicate_and_same_content_different_name(self) -> None:
        a = _write(self.root / "one.txt", "same-bytes")
        b = _write(self.root / "two.txt", "same-bytes")
        self.assertEqual(sha256_bytes(a.read_bytes()), sha256_bytes(b.read_bytes()))

    def test_renamed_and_moved_cross_version(self) -> None:
        va = self.root / "ver_a"
        vb = self.root / "ver_b"
        _write(va / "only_a.txt", "A")
        _write(vb / "only_b.txt", "B")
        _write(va / "shared.txt", "same")
        _write(vb / "shared.txt", "same")
        _write(va / "old_name.txt", "renamed-body")
        _write(vb / "new_name.txt", "renamed-body")
        _write(va / "dir1" / "moved.txt", "moved-body")
        _write(vb / "dir2" / "moved.txt", "moved-body")
        _write(va / "changed.py", "def alpha():\n    return 1\n")
        _write(vb / "changed.py", "def alpha():\n    return 2\n")
        disc = FileDiscoveryProvider(self.root)
        diff = differential(self.store, va, vb, disc, limit=50)
        self.assertFalse(diff.assumed_newer)
        self.assertTrue(any("only_a.txt" in n for n in diff.only_in_a))
        self.assertTrue(any("only_b.txt" in n for n in diff.only_in_b))
        self.assertTrue(any("shared.txt" in n for n in diff.same_hash))
        self.assertTrue(any("changed.py" in n for n in diff.modified))
        self.assertTrue(diff.renamed_or_moved)
        self.assertTrue(diff.moved_candidate)
        decisions = MergeIntelligence().decide(diff)
        self.assertTrue(all(d.assumed_newer_is_better is False for d in decisions))

    def test_modified_symbol(self) -> None:
        a = _write(self.root / "s_a.py", "def ship():\n    return 'pending'\n")
        b = _write(self.root / "s_b.py", "def ship():\n    return 'shipped'\n\ndef extra():\n    return 1\n")
        cmp = ComparisonEngine().symbol_diff(a, b)
        self.assertEqual(cmp.what_changed, "symbol_modified")
        self.assertIn("extra", str(cmp.evidence))

    def test_broken_import_repair_candidate(self) -> None:
        path = _write(self.root / "broken.py", "import missing_local_mod\n")
        cands = mine_repairs(path)
        self.assertTrue(any(c.kind == "broken_import" for c in cands))
        self.assertFalse(any(c.to_dict().get("applied") for c in cands))

    def test_parser_failure_fallback(self) -> None:
        path = _write(self.root / "bad.py", "def oops(\n")
        parsed = parse_file(path)
        self.assertEqual(parsed.parser, "python-ast-failed")
        cands = mine_repairs(path)
        self.assertTrue(any(c.kind == "syntax_error" for c in cands))

    def test_hash_cache_incremental_unchanged(self) -> None:
        path = _write(self.root / "cacheme.py", "def n():\n    return 1\n")
        first = parse_file(path, store=self.store)
        second = parse_file(path, store=self.store)
        self.assertEqual(first.symbols[0].name, second.symbols[0].name)
        self.assertEqual(second.evidence, "parser_cache")

    def test_model_unavailable_fallback(self) -> None:
        search = SearchProvider(self.store, self.root)
        with self.assertRaises(FailClosed):
            search.execute("order", allow_model=True)
        out = search.execute("order", allow_model=False)
        self.assertFalse(out["model_used"])

    def test_read_only_analysis(self) -> None:
        path = _write(self.root / "immutable.py", "x = 1\n")
        before = sha256_bytes(path.read_bytes())
        runtime = FileIntelligenceRuntime(self.root / "rt", repo=REPO)
        try:
            runtime.ingest(self.root, "tmp", limit=20)
        finally:
            runtime.close()
        self.assertEqual(sha256_bytes(path.read_bytes()), before)

    def test_shadow_patch_and_rollback(self) -> None:
        original = _write(self.root / "edit_me.py", "x = 1\n")
        before = sha256_bytes(original.read_bytes())
        engine = ModificationEngine(self.store)
        txn = engine.begin(original)
        txn = engine.propose_and_shadow(txn, b"x = 2\n")
        self.assertEqual(sha256_bytes(original.read_bytes()), before)
        self.assertTrue(Path(txn.shadow_path).exists())
        txn = engine.rollback(txn)
        self.assertTrue(txn.rolled_back)
        self.assertFalse(Path(txn.shadow_path).exists())
        txn = engine.governed_apply_forbidden_by_default(txn)
        self.assertFalse(txn.applied)
        self.assertEqual(sha256_bytes(original.read_bytes()), before)

    def test_archive_lineage(self) -> None:
        path = _write(self.root / "old.txt", "body")
        engine = ArchiveEngine(self.store)
        rec = engine.record(path, "SUPERSEDED", "replaced_by_new", version="a", replacement="new.txt", evidence="hash")
        self.assertEqual(rec.state, "SUPERSEDED")
        self.assertEqual(rec.original_path, str(path))
        rows = list(self.store.conn.execute("SELECT payload_json FROM archive_records"))
        self.assertEqual(len(rows), 1)

    def test_query_plan_before_expensive(self) -> None:
        plan = compile_query("find where an order becomes shipped and compare both versions")
        self.assertTrue(plan.version_comparison)
        self.assertFalse(plan.model_synthesis)
        self.assertIn("shipped", plan.lexical_queries)
        self.assertNotIn("STAGE_8", plan.expensive_stages_allowed)

    def test_tool_economy_rejects_llm_as_parser(self) -> None:
        registry = default_registry(self.store)

        class FakeLlm:
            name = "qwen-parser"
            capability = "parse"
            startup_cost = 0
            per_file_cost = 0.0001
            accuracy = 1
            supported_types = ()
            risk = "HIGH"

            def cost(self):
                return {
                    "capability": "parse",
                    "startup_cost": 0,
                    "per_file_cost": 0.0001,
                    "accuracy": 1,
                    "supported_types": [],
                    "risk": "HIGH",
                }

        registry.register(FakeLlm())  # type: ignore[arg-type]
        choice = ToolEconomy(registry).choose("parse", "parse")
        self.assertNotIn("qwen", choice.selected.lower())
        self.assertFalse(choice.llm_used)

    def test_idle_preempts_model(self) -> None:
        loop = IdleLoop()
        self.assertEqual(loop.tick("scan"), "ok")
        self.assertEqual(loop.tick("user", foreground=True), "preempted")
        self.assertEqual(loop.tick("synth", model=True), "skipped_model_due_to_foreground")
        self.assertEqual(loop.model_calls, 0)

    def test_graph_unknown_not_hallucinated(self) -> None:
        graph = FileKnowledgeGraph(self.store)
        graph.add_edge("FILE", "a.py", "MODULE", "os", "IMPORTS", "PROVEN", 0.9, "ast")
        with self.assertRaises(ValueError):
            graph.add_edge("FILE", "a.py", "MODULE", "os", "IMPORTS", "GUESSED", 0.9, "nope")

    def test_false_pass_impossible(self) -> None:
        self.assertTrue(contains_forbidden_success("status PASS"))
        self.assertFalse(contains_forbidden_success("GATES_SATISFIED"))
        self.assertFalse(contains_forbidden_success("FAILED"))

    def test_protected_paths_blocked(self) -> None:
        with self.assertRaises(FailClosed):
            FailClosed.assert_writable(REPO / "RAIOS" / "V9" / "x", REPO)
        with self.assertRaises(FailClosed):
            FailClosed.assert_writable(REPO / "_raios-a17-native-cortex" / "ccee" / "var" / "x", REPO)

    def test_doctor_gates(self) -> None:
        corpus = ROOT / "tests" / "fixtures" / "corpus"
        report = run_doctor(self.root / "doctor", REPO, corpus)
        self.assertEqual(report["status"], "GATES_SATISFIED")
        self.assertNotEqual(report["status"], "PASS")
        self.assertNotEqual(report.get("FILE_INTELLIGENCE"), "PASS")
        self.assertFalse(report.get("file_intelligence_pass"))
        self.assertEqual(report.get("FILE_INTELLIGENCE"), "DEGRADED_MODE")
        self.assertLessEqual(float(report.get("documents_extractable_pct") or 0), 100.0)
        self.assertLessEqual(float(report.get("code_structurally_parsed_pct") or 0), 100.0)
        self.assertFalse(report["cognition"]["ccee_wal_writes"])
        self.assertIn("total_files", report.get("performance") or {})


if __name__ == "__main__":
    unittest.main()
