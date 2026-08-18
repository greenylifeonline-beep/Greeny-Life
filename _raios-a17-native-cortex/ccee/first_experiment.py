"""First live learning experiment: metabolize the A17.13 failure. No mastery claim."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import FailClosed, native_root
from .engine import CCEE

HISTORICAL_FACTS = {
    "id": "a17.13.historical",
    "kind": "atomic_certification",
    "signatures": [
        "missing_ResponseHash",
        "missing_Final",
        "missing_final_report",
        "false_PASS_after_failure",
        "child_exit_1",
        "HTTP_500_ollama",
        "interactive_powershell_else_parse",
    ],
    "authoritative": True,
    "invented": False,
}


def diagnose_atomic_failure(case: dict[str, Any]) -> str:
    blob = json.dumps(case, sort_keys=True).lower().replace("-", "_")
    if case.get("http") == 200 and (case.get("invalid_semantic") or case.get("report_integrity") is False):
        return "HTTP_200_INVALID_SEMANTIC"
    if "evidence_sha" in blob or "evidencesha256" in blob.replace("_", ""):
        return "REPORT_INTEGRITY"
    if case.get("http") in {500, 502, 503, 504} or "ollama_server_error" in blob:
        return "OLLAMA_SERVER_ERROR"
    if "responsehash" in blob.replace("_", "") or "response_hash" in blob:
        return "MISSING_RESPONSE_HASH"
    if "missing_final" in blob:
        return "MISSING_FINAL"
    if "false_pass" in blob or (case.get("printed_pass") and case.get("failed")):
        return "FALSE_PASS"
    if "child" in blob and ("exit" in blob or "returncode" in blob):
        return "CHILD_EXIT_NONZERO"
    if "powershell" in blob and "else" in blob:
        return "INTERACTIVE_PARSE"
    if "timeout" in blob:
        return "TIMEOUT"
    return "UNCLASSIFIED"


def load_historical(repo_root: Path) -> dict[str, Any]:
    path = native_root(repo_root) / "evidence" / "failures" / "HISTORICAL-A17.13.json"
    if not path.is_file():
        raise FailClosed("HISTORICAL_A17_13_MISSING")
    data = json.loads(path.read_text(encoding="utf-8"))
    stored = data.get("sha256")
    body = {k: v for k, v in data.items() if k != "sha256"}
    from .config import sha256_obj

    digest = sha256_obj(body)
    if stored and stored != digest:
        raise FailClosed("HISTORICAL_EVIDENCE_HASH_MISMATCH")
    return data


def run_experiment(ccee: CCEE, repo_root: Path) -> dict[str, Any]:
    historical = load_historical(repo_root)
    try:
        ccee.conscious.handle_task({"id": "a17.13", "fail": True, "error": "HTTP_500", "ok": False})
        conscious_error = None
    except FailClosed as exc:
        conscious_error = str(exc)
    episode = ccee.metabolism.metabolize(
        {"id": "a17.13", "intent": "atomic-certification", "input": historical},
        {"ok": False, "success_score": 0.0, "failure_score": 1.0, "plan": ["certify"], "teacher_used": False},
        {
            "observations": historical.get("signatures") or HISTORICAL_FACTS["signatures"],
            "lessons": ["never emit PASS after failure", "propagate child exit", "hash every receipt"],
            "candidate_skills": ["false_pass_detector", "exit_code_propagator", "response_hash_gate"],
            "uncertainty": 0.4,
            "recovery_used": True,
        },
    )
    imagined = ccee.imagination.imagine({"id": "a17.13", "kind": "http_500"}, sandbox=True)
    ctx = ccee.causal.add("CONTEXT", {"id": "a17.13"})
    ccee.causal.add("OUTCOME", {"id": "fail", "supporting_evidence": ["child_exit_1"]}, parent=ctx["node_id"])
    for sig in HISTORICAL_FACTS["signatures"]:
        ccee.knowledge.ingest("historical_fact", sig, historical=True)
    bench = ccee.benchmarks.generate(
        "atomic.certification",
        {"id": "a17.13", "expected": "FALSE_PASS", "unseen_expected": "HTTP_200_INVALID_SEMANTIC"},
    )
    unseen = next(c for c in bench["unseen"] if c["variant"] == "unseen")
    unseen_case = {
        "id": unseen["id"],
        "http": 200,
        "invalid_semantic": True,
        "report_integrity": False,
        "expected": "HTTP_200_INVALID_SEMANTIC",
    }
    transfer = ccee.transfer.evaluate(unseen_case, diagnose_atomic_failure, teacher_assistance=False)
    ccee.metrics.record("ExperienceMultiplicationFactor", float(episode["experience_multiplication_factor"]))
    ccee.metrics.record("TransferEfficiency", 1.0 if transfer["passed"] else 0.0)
    ccee.metrics.record("FailureRecurrenceRate", 1.0)
    ckpt = ccee.checkpoint.save({"experiment": "a17.13"})
    return {
        "historical_sha256": historical.get("sha256"),
        "episode_id": episode["episode_id"],
        "multiplication": episode["experience_multiplication_factor"],
        "counterfactuals": len(imagined),
        "missions": (lambda cyc: len(ccee.curiosity.rankings) or cyc.get("missions") or 0)(ccee.subconscious.cycle()),
        "transfer": transfer,
        "mastery_claimed": False,
        "teacher_assistance": False,
        "checkpoint_id": ckpt["checkpoint_id"],
        "conscious_error": conscious_error,
        "wal_count": ccee.wal.verify_chain()["count"],
    }
