"""CCEE doctor. Nonzero exit if a critical gate fails. stdout is not evidence."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from .certification import AssertionRegistry, AtomicCertificationRunner, EvidenceLedger
from .config import ORGANISM_ID, FailClosed, authoritative_exit, canonical_json, contains_forbidden_success, native_root, repo_root_from, sha256_text, utc_now
from .engine import CCEE
from .first_experiment import run_experiment
from .ollama_runtime import OllamaRuntimeManager
from .process_kernel import encoding_safe_run
from .schemas import CortexResponse, CognitiveEvent


def v9_clean(repo_root: Path) -> bool:
    proc = encoding_safe_run(
        ["git", "-C", str(repo_root), "status", "--porcelain", "--", "RAIOS/V9"],
        cwd=repo_root,
    )
    return proc.returncode == 0 and proc.stdout.strip() == ""


def run_doctor(root: Path, repo_root: Path, evidence: Path) -> dict[str, Any]:
    registry = AssertionRegistry()
    ledger = EvidenceLedger(evidence, repo_root=repo_root)
    runner = AtomicCertificationRunner(ledger)
    ccee = CCEE(root, repo_root=repo_root)
    result: dict[str, Any] = {"organism_id": ORGANISM_ID, "created_at": utc_now(), "canonical": False}
    try:
        CortexResponse.model_validate(
            {
                "assessment": {},
                "uncertainty": [],
                "claims": [],
                "evidence_needed": [],
                "plan": [],
                "tool_requests": [],
                "hypotheses": [],
                "skill_candidates": [],
                "learning_signals": [],
                "stop_reason": "doctor",
            }
        )
        registry.require("schemas", True)
        chain = ccee.wal.append("OBSERVATION", "doctor", {"probe": True})
        verified = ccee.wal.verify_chain()
        registry.require("wal", verified["ok"] and verified["count"] >= 1, "chain")
        ccee.ledger.put("skills", "skill_id", "doctor:probe", {"skill_id": "doctor:probe", "kind": "MICRO_SKILL"}, extra={"kind": "MICRO_SKILL"})
        registry.require("ledger", ccee.ledger.get("skills", "doctor:probe") is not None)
        restored = ccee.checkpoint.save()
        registry.require("checkpoint", bool(restored.get("checkpoint_id")))
        registry.require("hash_chain", verified["ok"])
        liar_fp = False
        try:
            runner.run_child([sys.executable, "-c", "print('PASS'); raise SystemExit(1)"])
        except FailClosed as exc:
            liar_fp = "FALSE_PASS" in str(exc)
        registry.require("false_pass_protection", liar_fp, "liar_child")
        bare0 = False
        try:
            runner.run_child([sys.executable, "-c", "print('PASS')"])
        except FailClosed as exc:
            bare0 = "FALSE_PASS" in str(exc)
        registry.require("bare_pass_exit_zero_blocked", bare0, "bare_pass")
        registry.require("v9_unchanged", v9_clean(repo_root))
        ollama = OllamaRuntimeManager(ccee.bus)
        inv = ollama.inventory()
        registry.observe("ollama", bool(inv.get("ok")), str(inv.get("reason") or ""))
        registry.observe("main_cortex", bool(inv.get("main_cortex_present")), "environment")
        teachers = ccee.teachers.corpus_status()
        registry.observe("teacher_corpus", teachers["status"] == "FOUND", teachers["status"])
        experiment = run_experiment(ccee, repo_root)
        registry.require("first_experiment", experiment["transfer"]["passed"] and not experiment["mastery_claimed"])
        ns = ccee.nervous.certify_self(root / "ns-lab")
        registry.require("nervous_system_lab", bool(ns["lab"]["executed"] and ns["lab"]["positive"]["ok"]))
        registry.require("encoding_negative_control", bool(ns["lab"]["negative"]["ok"]))
        registry.require("integrity_lab", bool((ns.get("integrity_lab") or {}).get("repair_success")))
        if not inv.get("main_cortex_present"):
            registry.require(
                "work_gate_closed_without_cortex",
                ns["boot"]["gate"]["state"] != "READY_FOR_REAL_PROJECT_WORK",
                ns["boot"]["gate"]["state"],
            )
        registry.require("wal_after_experiment", ccee.wal.verify_chain()["ok"])
        snap = ccee.metrics.snapshot()
        result.update(
            {
                "gates": registry.gates,
                "wal": ccee.wal.verify_chain(),
                "experiment": experiment,
                "metrics": snap,
                "ollama": inv,
                "teachers": teachers,
                "identity": ccee.identity(),
                "nervous": {
                    "family": ns.get("family"),
                    "episode_id": ns.get("episode_id"),
                    "work_gate": (ns.get("boot") or {}).get("gate", {}).get("state"),
                    "lab": ns.get("lab"),
                },
            }
        )
        certified = runner.certify("ccee-doctor", lambda reg: _copy_gates(reg, registry), run_id=ccee.wal.run_id)
        result["certification"] = {k: certified[k] for k in certified if k != "stdout"}
        if not certified.get("ok"):
            raise FailClosed("DOCTOR_CERTIFICATION_FAILED:" + str(certified.get("error")))
        result["overall_status"] = "GATES_SATISFIED"
        result["exit_code"] = 0
    except Exception as exc:
        ledger.persist_failure({"name": "doctor", "error": f"{type(exc).__name__}:{exc}", "gates": registry.gates})
        result["overall_status"] = "FAILED"
        result["exit_code"] = 1
        result["error"] = f"{type(exc).__name__}:{exc}"
        result["gates"] = registry.gates
    finally:
        ccee.close()
    text = canonical_json(result)
    result["sha256"] = sha256_text(text)
    return result


def _copy_gates(target: AssertionRegistry, source: AssertionRegistry) -> bool:
    for name, gate in source.gates.items():
        if gate["mandatory"]:
            target.require(name, gate["ok"], gate.get("reason") or "")
        else:
            target.observe(name, gate["ok"], gate.get("reason") or "")
    return True


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    repo = repo_root_from()
    native = native_root(repo)
    root = Path(argv[argv.index("--root") + 1]) if "--root" in argv else native / "ccee" / "var" / "doctor"
    evidence = native / "evidence"
    report = run_doctor(root, repo, evidence)
    out = native / "reports" / "A18-CCEE-FOUNDATION-REPORT.json"
    if "--report" in argv:
        out.parent.mkdir(parents=True, exist_ok=True)
        # final status token is written only after gates
        if report.get("exit_code") == 0 and report.get("overall_status") == "GATES_SATISFIED":
            report["final_status"] = "A18_CCEE_FOUNDATION_PASS"
        else:
            report["final_status"] = "A18_CCEE_FOUNDATION_FAILED"
        payload = canonical_json(report)
        report["sha256"] = sha256_text(payload)
        out.write_text(canonical_json(report), encoding="utf-8")
    sys.stdout.write(canonical_json({"overall_status": report.get("overall_status"), "exit_code": report.get("exit_code")}) + "\n")
    if contains_forbidden_success(canonical_json(report)) and report.get("exit_code") != 0:
        return 1
    return authoritative_exit(report.get("exit_code"))


if __name__ == "__main__":
    raise SystemExit(main())
