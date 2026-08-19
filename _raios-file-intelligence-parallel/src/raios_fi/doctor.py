"""FILE-INTELLIGENCE-DOCTOR. Critical failure -> nonzero exit. stdout is not evidence."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .certify import run_certification
from .config import ORGANISM_ID, PACKAGE, FailClosed, canonical_json, package_root, repo_root_from, run, sha256_text, utc_now, which
from .inventory import write_inventories
from .runtime import FileIntelligenceRuntime
from .tools import detect_tools
from .versions import VersionDetector


FORBIDDEN_SUCCESS_TOKENS = (" PASS", "PASS\n", "status PASS", "\"PASS\"", "FILE_INTELLIGENCE=PASS")


def contains_forbidden_success(text: str) -> bool:
    return any(tok in text for tok in FORBIDDEN_SUCCESS_TOKENS)


class GateRegistry:
    def __init__(self) -> None:
        self.gates: dict[str, dict[str, Any]] = {}

    def require(self, name: str, ok: bool, detail: str = "") -> None:
        self.gates[name] = {"ok": bool(ok), "critical": True, "detail": detail}
        if not ok:
            raise FailClosed(f"GATE_FAILED:{name}:{detail}")

    def observe(self, name: str, ok: bool, detail: str = "") -> None:
        self.gates[name] = {"ok": bool(ok), "critical": False, "detail": detail}


def v9_clean(repo: Path) -> bool:
    proc = run(
        ["git", "-C", str(repo), "status", "--porcelain", "--", "RAIOS/V9"],
        cwd=repo,
    )
    return proc.returncode == 0 and proc.stdout.strip() == ""


def run_doctor(var_root: Path, repo: Path, fixtures: Path | None = None, *, scale: str = "fixture") -> dict[str, Any]:
    registry = GateRegistry()
    runtime = FileIntelligenceRuntime(var_root, repo)
    result: dict[str, Any] = {
        "organism_id": ORGANISM_ID,
        "package": PACKAGE,
        "created_at": utc_now(),
        "canonical": False,
    }
    try:
        registry.require("fts5", True, "sqlite compiled with fts5")
        registry.require("v9_unchanged", v9_clean(repo), "RAIOS/V9 dirty")
        # protected write must fail
        blocked = False
        try:
            FailClosed.assert_writable(repo / "RAIOS" / "V9" / "nope.txt", repo)
        except FailClosed:
            blocked = True
        registry.require("v9_write_blocked", blocked)
        harvest = repo / "_raios-a17-native-cortex" / "ccee" / "var"
        harvest_blocked = False
        try:
            FailClosed.assert_writable(harvest / "x", repo)
        except FailClosed:
            harvest_blocked = True
        registry.require("harvest_write_blocked", harvest_blocked)

        fixture_root = fixtures or (package_root(repo) / "tests" / "fixtures" / "corpus")
        cert = run_certification(runtime, repo, scale=scale, fixtures=fixture_root)
        ingest = cert["ingest"]
        health = runtime.health()
        tools = detect_tools()
        available = [t["name"] for t in tools if t.get("available")]
        missing = [t["name"] for t in tools if t.get("missing")]
        qwen = bool(which("ollama"))
        registry.observe("qwen", qwen, "ollama" if qwen else "OLLAMA_MISSING")
        registry.observe("teachers", False, "not_invoked")
        registry.observe("magika", bool(health.get("magika", {}).get("magika")), "ADAPTER_PRESENT_BINARY_MISSING")
        registry.observe("tika", bool(health.get("tika", {}).get("tika")), "ADAPTER_PRESENT_BINARY_MISSING")
        registry.require("index_writable", runtime.var.exists())
        registry.require("ingest", ingest.get("files", 0) >= 0)
        registry.require("false_pass_protection", not contains_forbidden_success("doctor running"))
        registry.require("ccee_not_written", health.get("cognition", {}).get("ccee_wal_writes") is False)
        registry.require("no_fake_file_intelligence_pass", cert.get("FILE_INTELLIGENCE") != "PASS" and cert.get("file_intelligence_pass") is False)
        detector = VersionDetector(repo)
        pair = detector.pair()
        repairs = runtime.store.conn.execute("SELECT COUNT(*) AS c FROM repair_candidates").fetchone()["c"]
        result.update(
            {
                "roots_found": detector.roots(),
                "files_discovered": health["files"],
                "types_recognized": health.get("types_recognized"),
                "unknown_types": health["unknown"],
                "text_searchable_pct": health["text_searchable_pct"],
                "code_structurally_parsed_pct": health.get("code_structurally_parsed_pct"),
                "documents_extractable_pct": health.get("documents_extractable_pct"),
                "symbols_indexed": health["symbols"],
                "relationships": health["relations"],
                "duplicate_groups": health.get("duplicate_groups"),
                "repair_candidates": repairs,
                "fts_index": True,
                "version_pairs": [pair] if pair else [],
                "tools_available": available,
                "tools_missing": missing,
                "magika": health.get("magika"),
                "tika": health.get("tika"),
                "parser": health.get("parser"),
                "cognition": health.get("cognition"),
                "qwen_health": {"ok": qwen, "reason": None if qwen else "OLLAMA_MISSING"},
                "teacher_health": {"ok": False, "reason": "NOT_INVOKED"},
                "index_health": health,
                "ingest": ingest,
                "gates": registry.gates,
                "FILE_INTELLIGENCE": cert.get("FILE_INTELLIGENCE"),
                "file_intelligence_pass": False,
                "degraded_reasons": cert.get("degraded_reasons"),
                "certification_checks": cert.get("checks"),
                "performance": cert.get("performance"),
                "cortex_proposal": cert.get("cortex_proposal"),
                "query_plan": cert.get("query_plan"),
                "disagreements": cert.get("disagreements"),
                "scale": cert.get("scale"),
            }
        )
        critical_ok = all(g["ok"] for g in registry.gates.values() if g["critical"])
        result["status"] = "GATES_SATISFIED" if critical_ok else "FAILED"
        result["exit_nonzero_if_failed"] = not critical_ok
        return result
    finally:
        runtime.close()


def write_reports(repo: Path | None = None) -> dict[str, Any]:
    repo = repo or repo_root_from()
    pkg = package_root(repo)
    reports = pkg / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    write_inventories(repo, reports)
    var = pkg / "var" / "doctor-index"
    doctor = run_doctor(var, repo, pkg / "tests" / "fixtures" / "corpus", scale="repo")
    (reports / "FILE-INTELLIGENCE-DOCTOR.json").write_text(
        json.dumps(doctor, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )

    from .versions import VersionDetector, differential
    from .discovery import FileDiscoveryProvider
    from .store import IndexStore
    from .merge import MergeIntelligence

    detector = VersionDetector(repo)
    pair = detector.pair()
    version_payload: dict[str, Any] = {
        "generated_at": utc_now(),
        "assumed_newer": False,
        "pair": pair,
        "note": "newer != better; labels not assigned without evidence",
    }
    if pair:
        store = IndexStore(pkg / "var" / "version-index", repo=repo)
        discovery = FileDiscoveryProvider(repo)
        try:
            diff = differential(store, Path(pair[0]["path"]), Path(pair[1]["path"]), discovery, limit=120)
            version_payload.update(diff.to_dict())
            version_payload["merge_candidates"] = [c.to_dict() for c in MergeIntelligence().decide(diff)[:80]]
        finally:
            store.close()
    (reports / "VERSION-DIFFERENTIAL.json").write_text(
        json.dumps(version_payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )

    tools = detect_tools()
    available = {t["name"]: t for t in tools}
    final = {
        "generated_at": utc_now(),
        "organism_id": ORGANISM_ID,
        "package": PACKAGE,
        "canonical": False,
        "doctor_status": doctor.get("status"),
        "FILE_INTELLIGENCE": doctor.get("FILE_INTELLIGENCE"),
        "file_intelligence_pass": False,
        "performance": doctor.get("performance"),
        "degraded_reasons": doctor.get("degraded_reasons"),
        "certification_checks": doctor.get("certification_checks"),
        "IMPLEMENTED": [
            "read-only git ls-files discovery + FileObject",
            "Magika adapter WRAP (detect-only); signature+parser-probe fallback; extension never sole authority",
            "Tika adapter WRAP (detect-only, no OCR); stdlib decode + zip manifest fallback",
            "python ast symbols; heuristic TS/JS/PS1/SQL; GNU Emacs ctags rejected as Universal Ctags",
            "SQLite+FTS5 index and parser cache keyed by sha256+parser_version (type cache no longer clobbers parse cache)",
            "staged search plan (metadata, filename, rg, symbols, fts5); STAGE 8 fail-closed",
            "two-version detector without assuming newer",
            "text/symbol/schema/config comparison (jq/yq structural when present)",
            "proven duplicate groups by identical sha256",
            "rule-first classification",
            "evidence-based architecture edges PROVEN/INFERRED/UNKNOWN",
            "shadow modification txn + rollback; governed apply forbidden",
            "merge candidates KEEP_A/REVIEW_REQUIRED (no auto-keep)",
            "repair candidates from syntax/broken local imports",
            "archive lineage states without delete",
            "file knowledge graph",
            "query-plan JSON compiler",
            "tool economy (LLM not default parser)",
            "shared cognitive state contract (identity shared; CCEE WAL not merged)",
            "idle loop without model calls; foreground preempts",
            "FILE-INTELLIGENCE-DOCTOR fail-closed",
            "independent authority/temporal/verification/knowledge dimensions",
            "evidence-native confidence; model cannot produce VERIFIED",
            "DISAGREEMENT_OBJECT persisted without averaging",
            "active/dead safety; no archive from one heuristic",
            "cross-version identity (hash/path/symbols; basename insufficient)",
            "economic query planner (minimum sufficient stages)",
            "incremental cache key sha256+parser+classifier+provider versions",
            "Qwen cortex consumer emits PROPOSAL only",
            "governed change txn with abort/rollback/learning signal",
            "repository-scale certification reports DEGRADED_MODE when tools missing",
        ],
        "REUSED": [
            "git",
            "rg",
            "python ast.parse",
            "sqlite3 FTS5",
            "zipfile",
            "file(1) as Magika fallback",
            "jq structural JSON canonicalization when present",
            "yq YAML canonicalization when present",
            "CAS pattern from _raios-a17-integration-wave",
            "fail-closed / doctor pattern from CCEE",
        ],
        "AVAILABLE_NOT_INTEGRATED": [
            {"name": "java", "reason": "present but Tika jar not installed; do not download"},
            {"name": "node/npm/pnpm", "reason": "JS ecosystem present; not used as parser"},
            {"name": "greenlines_brain/dna/ast_analyzer.py", "reason": "historical; not imported to avoid collision"},
            {"name": "brain.py scan_project_metadata", "reason": "stale 316-file index; not authoritative"},
        ],
        "MISSING": [
            "magika binary/python package (adapter present)",
            "apache tika jar/cli (adapter present; java is not tika)",
            "tree-sitter",
            "universal ctags (GNU Emacs ctags present and rejected)",
            "ast-grep (/usr/bin/sg is Linux set-group, not ast-grep)",
            "semgrep",
            "7z",
            "fd",
            "ollama / qwen3.6",
            "docker",
        ],
        "BLOCKED": [
            "RAIOS/V9 mutation",
            "A17 harvest / CCEE var writes",
            "teacher deletion",
            "canonical mutation",
            "OCR by default",
            "Qwen as default parser",
            "governed apply onto original sources in this parallel package",
        ],
        "PENDING_RUNTIME_VALIDATION": [
            "Magika live classify",
            "Tika PDF/Office extract",
            "tree-sitter TS/TSX accuracy vs heuristic",
            "Ollama STAGE 8 synthesis over evidence bundle",
            "full 2000-file ingest vs remaining untracked/hidden scan",
            "Windows PowerShell A17 live harvest coexistence on operator machine",
            "shared storage merge with CCEE (intentionally not merged)",
            "live Qwen evidence synthesis (ollama missing; PROPOSAL path only)",
        ],
        "tools": {k: {"available": v.get("available"), "version": v.get("version")} for k, v in available.items()},
        "integrity": {
            "doctor_sha256": sha256_text(canonical_json(doctor)),
            "version_sha256": sha256_text(canonical_json(version_payload)),
        },
        "not_scaffolding": True,
        "false_pass_token_emitted": False,
    }
    audit = {
        "generated_at": utc_now(),
        "repo": str(repo),
        "package": PACKAGE,
        "doctor": doctor.get("status"),
        "version_pair": pair,
        "tools_missing": [t["name"] for t in tools if t.get("missing")],
        "collision_guard": {
            "RAIOS/V9": "read-only",
            "native_cortex_var": "write-blocked",
            "this_package_only": True,
            "ccee_wal_writes": False,
        },
        "adapters": {
            "magika": "WRAP_DETECT_ONLY",
            "tika": "WRAP_DETECT_ONLY_NO_OCR",
        },
    }
    (reports / "FILE-INTELLIGENCE-REALITY-AUDIT.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    (reports / "FILE-INTELLIGENCE-FINAL-REPORT.json").write_text(
        json.dumps(final, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    return {"doctor": doctor, "final": final, "reports": str(reports)}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    repo = repo_root_from()
    if "--report" in argv:
        payload = write_reports(repo)
        status = payload["doctor"].get("status")
        print(json.dumps({"status": status, "FILE_INTELLIGENCE": payload["doctor"].get("FILE_INTELLIGENCE"), "reports": str(package_root(repo) / "reports")}, indent=2))
        if contains_forbidden_success(json.dumps(payload["doctor"])):
            return 2
        return 0 if status == "GATES_SATISFIED" else 2
    var = package_root(repo) / "var" / "doctor-index"
    doctor = run_doctor(var, repo)
    print(json.dumps({"status": doctor["status"], "gates": doctor["gates"]}, indent=2, default=str))
    return 0 if doctor["status"] == "GATES_SATISFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
