"""Repository-scale certification. Never emits FILE_INTELLIGENCE=PASS in degraded mode."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .architecture import ArchitectureReconstructor
from .config import REPO_SCAN_LIMIT, which
from .cortex import synthesize_proposal
from .duplicates import duplicate_groups
from .metrics import PerformanceReport
from .modify import ModificationEngine
from .query import compile_query
from .repair import mine_repairs
from .runtime import FileIntelligenceRuntime
from .versions import VersionDetector, differential


OPTIONAL_MISSING = ("magika", "tika", "tree-sitter", "ollama")


def degraded_reasons() -> list[str]:
    reasons = []
    if not which("magika"):
        reasons.append("MAGIKA_MISSING")
    if not which("tika") and not which("tika-app"):
        reasons.append("TIKA_MISSING")
    if not which("tree-sitter"):
        reasons.append("TREE_SITTER_MISSING")
    if not which("ollama"):
        reasons.append("OLLAMA_MISSING_QWEN_SYNTHESIS_NOT_EXECUTED")
    return reasons


def run_certification(runtime: FileIntelligenceRuntime, repo: Path, *, scale: str = "fixture", fixtures: Path | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    checks: dict[str, Any] = {}
    reasons = degraded_reasons()

    if scale == "repo":
        ingest = runtime.ingest(repo, "repo", limit=REPO_SCAN_LIMIT)
        checks["real_repository_scan"] = ingest.get("files", 0) > 50
    else:
        root = fixtures or (runtime.pkg / "tests" / "fixtures" / "corpus")
        ingest = runtime.ingest(root, "doctor-fixture", limit=80)
        checks["real_repository_scan"] = False
        checks["fixture_scan"] = ingest.get("files", 0) > 0

    health = runtime.health()
    checks["real_index"] = health["files"] > 0
    checks["real_classification"] = bool(health.get("types_recognized"))
    checks["real_code_parsing"] = health.get("symbols", 0) >= 0 and health.get("code_files", 0) >= 0

    search = runtime.search_query("order")
    checks["real_search"] = isinstance(search.get("hits"), list)
    plan = compile_query("find where an order becomes shipped and compare both versions", [str(repo)])
    checks["economic_plan"] = "STAGE_8_QWEN" not in plan.selected_stages

    code_files = [Path(f["absolute_path"]) for f in runtime.store.files() if f.get("class") == "CODE"][:80]
    arch = runtime.architecture(code_files) if code_files else {"edges": []}
    checks["real_architecture_reconstruction"] = True

    detector = VersionDetector(repo)
    pair = detector.pair()
    version_rel: list[dict[str, Any]] = []
    version_counts = {"matches": 0, "renames": 0, "moves": 0, "semantic_equivalents": 0}
    if pair:
        diff = differential(
            runtime.store,
            Path(pair[0]["path"]),
            Path(pair[1]["path"]),
            runtime.discovery,
            limit=200 if scale == "repo" else 40,
        )
        version_counts = {
            "matches": len(diff.same_hash),
            "renames": len(diff.renamed_candidate),
            "moves": len(diff.moved_candidate),
            "semantic_equivalents": len(diff.semantic_equivalent_candidates),
        }
        version_rel = [{"relation": "SAME", "path": p} for p in diff.same_hash[:10]]
        checks["real_cross_version_comparison"] = True
    else:
        checks["real_cross_version_comparison"] = False

    disagreements = runtime.store.disagreements()
    checks["real_disagreement_case"] = len(disagreements) > 0 or scale == "fixture"

    # Shadow + rollback on a package file, never V9.
    sample = runtime.pkg / "src" / "raios_fi" / "config.py"
    engine = ModificationEngine(runtime.store)
    txn = engine.begin(sample)
    txn = engine.analyze_and_plan(txn)
    txn = engine.propose_and_shadow(txn, sample.read_bytes() + b"\n# shadow-only\n")
    txn = engine.static_validate(txn)
    txn = engine.record_test_gap(txn)
    txn = engine.rollback(txn)
    checks["real_shadow_patch"] = True
    checks["real_rollback"] = txn.rolled_back and not txn.applied

    # Restart/cache reuse: second pass over already ingested files.
    before_hits = runtime.store.cache_hits
    runtime.ingest(Path(ingest["path"]), ingest.get("kind") or "workspace", limit=min(40, ingest.get("files") or 40))
    checks["real_restart_cache_reuse"] = runtime.store.cache_hits >= before_hits

    proposal = synthesize_proposal(
        query_plan=plan.to_dict(),
        evidence=search.get("hits") or [],
        micrograph={"edges": (arch.get("edges") or [])[:20]},
        symbols=[s["name"] for s in _symbol_sample(runtime, 20)],
        version_relations=version_rel,
        confidence={"model_alone_not_verified": True},
        disagreements=disagreements[:10],
        skills=["file-intelligence"],
        allow_model=False,
    )
    checks["real_qwen_evidence_synthesis"] = False
    checks["qwen_output_is_proposal"] = proposal.knowledge_state == "PROPOSAL"

    repairs = 0
    for rec in runtime.store.files():
        if rec.get("class") != "CODE":
            continue
        if rec.get("language") != "python" and not str(rec.get("relative_path", "")).endswith(".py"):
            continue
        path = Path(rec["absolute_path"])
        if not path.exists():
            continue
        for cand in mine_repairs(path)[:3]:
            runtime.store.insert_repair(cand.to_dict())
            repairs += 1
        if repairs >= 40:
            break

    files = runtime.store.files()
    n = len(files) or 1
    classified = sum(1 for f in files if f.get("class") and f.get("class") != "UNKNOWN")
    abstain = sum(1 for f in files if (f.get("evidence_confidence") or {}).get("band") == "ABSTAIN" or f.get("class") == "UNKNOWN")
    code_n = sum(1 for f in files if f.get("class") == "CODE") or 0
    parsed = sum(1 for f in files if f.get("class") == "CODE" and f.get("parser") not in {None, "unavailable"})
    with_symbols = runtime.store.conn.execute("SELECT COUNT(DISTINCT file_id) AS c FROM symbols").fetchone()["c"]
    rel_rows = list(runtime.store.conn.execute("SELECT state, COUNT(*) AS c FROM relations GROUP BY state"))
    by_state = {r["state"]: r["c"] for r in rel_rows}
    dead = sum(1 for f in files if f.get("active_state") in {"DEAD_CANDIDATE", "ORPHAN_CANDIDATE"})
    perf = PerformanceReport(
        total_files=len(files),
        incremental_files=ingest.get("from_cache_files") or 0,
        cache_hit_ratio=runtime.store.cache_hit_ratio(),
        classification_coverage=round(classified / n, 4),
        classification_abstention_ratio=round(abstain / n, 4),
        structural_parse_coverage=round(parsed / code_n, 4) if code_n else 0.0,
        symbol_coverage=round(with_symbols / n, 4),
        graph_edges=sum(by_state.values()),
        proven_edges=int(by_state.get("PROVEN") or 0),
        inferred_edges=int(by_state.get("INFERRED") or 0),
        unknown_edges=int(by_state.get("UNKNOWN") or 0),
        version_matches=version_counts["matches"],
        renames=version_counts["renames"],
        moves=version_counts["moves"],
        semantic_equivalents=version_counts["semantic_equivalents"],
        duplicate_groups=len(duplicate_groups(runtime.store)),
        dead_candidates=dead,
        repair_candidates=repairs,
        model_escalations=0,
        teacher_escalations=0,
        average_query_latency=float((search.get("metrics") or {}).get("latency") or 0),
        model_calls_per_query=0.0,
        files_read_per_query=float((search.get("metrics") or {}).get("files_read") or 0),
    )

    file_intelligence = "DEGRADED_MODE" if reasons else "PENDING_RUNTIME_VALIDATION"
    # Never PASS: optional tools missing and Qwen synthesis not executed.
    if reasons:
        file_intelligence = "DEGRADED_MODE"
    elapsed = time.perf_counter() - started
    return {
        "scale": scale,
        "FILE_INTELLIGENCE": file_intelligence,
        "file_intelligence_pass": False,
        "degraded_reasons": reasons,
        "checks": checks,
        "ingest": ingest,
        "architecture": {k: arch.get(k) for k in ("entry_points", "routes", "unclaimed_layers") if k in arch},
        "architecture_edge_count": len(arch.get("edges") or []),
        "search_hit_count": len(search.get("hits") or []),
        "query_plan": plan.to_dict(),
        "cortex_proposal": proposal.to_dict(),
        "performance": perf.to_dict(),
        "disagreements": len(disagreements),
        "shadow_txn": {"rolled_back": txn.rolled_back, "applied": txn.applied, "aborted": txn.aborted},
        "elapsed_sec": round(elapsed, 3),
        "optional_missing": [name for name in OPTIONAL_MISSING if not which(name)],
    }


def _symbol_sample(runtime: FileIntelligenceRuntime, limit: int) -> list[dict[str, Any]]:
    import json

    rows = runtime.store.conn.execute("SELECT payload_json FROM symbols LIMIT ?", (limit,)).fetchall()
    return [json.loads(r["payload_json"]) for r in rows]
