"""Student-executable diagnosis for the gateway false-PASS incident.

Reads persisted evidence. Does not invent a live gateway. Does not emit LIVE.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import canonical_json, contains_forbidden_success, native_root, sha256_obj
from .ollama_runtime import OllamaRuntimeManager
from .process_kernel import encoding_safe_run
from .root_cause import classify_failure, diagnose

INCIDENT_REL = Path("evidence") / "failures" / "HISTORICAL-GL-GW-001.json"
TOKEN_PATTERN = r"HEALTH_CHECK|/v1/chat|GATEWAY_LIVE|QWEN_CHAT|ARABIC_CHAT|RAIOS_MULTIMODAL_GATEWAY_LIVE"


def incident_path(repo_root: Path) -> Path:
    return native_root(repo_root) / INCIDENT_REL


def load_incident(repo_root: Path) -> dict[str, Any]:
    path = incident_path(repo_root)
    if not path.is_file():
        return {"ok": False, "error": "INCIDENT_EVIDENCE_MISSING", "path": str(path)}
    data = json.loads(path.read_text(encoding="utf-8"))
    data["_path"] = str(path)
    data["_sha256"] = sha256_obj({k: v for k, v in data.items() if not str(k).startswith("_")})
    return data


def case_from_incident(incident: dict[str, Any]) -> dict[str, Any]:
    observed = incident.get("observed") or {}
    emitted = observed.get("script_emitted") or {}
    chat = str(observed.get("POST_/v1/chat") or "")
    http = 500 if "500" in chat else None
    return {
        "http": http,
        "printed_pass": any(str(v).upper() == "PASS" for v in [observed.get("HEALTH_CHECK"), *emitted.values()]),
        "live_claim": "LIVE" in str(emitted.get("STATUS") or "").upper(),
        "failed": True,
        "chat_failed": "500" in chat,
        "health_check": observed.get("HEALTH_CHECK"),
        "false_pass": True,
        "child_exit": 1,
    }


def live_token_detectable(text: str) -> bool:
    return bool(contains_forbidden_success(text))


def student_diagnosis(repo_root: Path, *, causal: Any | None = None) -> dict[str, Any]:
    """Deterministic student diagnosis. Family comes from current D4, even if incomplete."""
    incident = load_incident(repo_root)
    if incident.get("error"):
        return {"ok": False, "overall_status": "FAILED", **incident}
    case = case_from_incident(incident)
    family = classify_failure(case)
    emitted = (incident.get("observed") or {}).get("script_emitted") or {}
    live_text = canonical_json(emitted)
    detector_hits = contains_forbidden_success(live_text)
    live_status = str(emitted.get("STATUS") or "")
    live_bypasses_detector = "LIVE" in live_status.upper() and "LIVE" not in detector_hits
    graph = None
    if causal is not None:
        graph = diagnose(causal, None, printed_pass=bool(case.get("printed_pass")), error=f"http={case.get('http')}", secondary="live_claim")
    contradictions = list(incident.get("contradictions") or [])
    missing = list(incident.get("missing_from_incident_report") or [])
    checkout = incident.get("checkout_probes") or {}
    return {
        "ok": True,
        "overall_status": "STRUCTURED",
        "task_id": incident.get("id") or "GL-GW-001",
        "evidence_path": incident.get("_path"),
        "evidence_sha256": incident.get("_sha256"),
        "certification_invalidated": True,
        "live_claim_rejected": True,
        "d4_family": family,
        "d4_case": case,
        "d4_graph": graph,
        "detector_hits_on_emitted": detector_hits,
        "live_status_bypasses_pass_detector": live_bypasses_detector,
        "observed": incident.get("observed"),
        "contradictions": contradictions,
        "missing_evidence": missing,
        "checkout_probes": checkout,
        "canonical": False,
        "mastery_claimed": False,
    }


def classify_gw_hit(line: str) -> str:
    lowered = line.replace("\\", "/")
    path = lowered.split(":", 1)[0]
    if "HISTORICAL-GL-GW-001" in lowered or "/evidence/failures/" in lowered:
        return "incident_evidence"
    name = path.rsplit("/", 1)[-1]
    if name in {
        "gateway_incident.py",
        "test_gateway_incident.py",
        "training_loop.py",
        "shadow_lab.py",
        "gateway_cert.py",
        "config.py",
        "root_cause.py",
        "test_false_pass.py",
        "live_bridge.py",
        "test_live_bridge.py",
    }:
        return "detector_or_harness"
    if "/_raios-assimilation-runtime/" in lowered or "/_raios-learning-observatory/" in lowered:
        return "detector_or_harness"
    if "/reports/" in lowered or path.endswith(".md"):
        return "detector_or_harness"
    if "/archive/" in lowered:
        return "archive_skip"
    if "RAIOS/V9/" in lowered:
        return "v9_forbidden"
    return "needs_review"


def execute_incident_probe(repo_root: Path, *, causal: Any | None = None, ollama: OllamaRuntimeManager | None = None) -> dict[str, Any]:
    """Student execution: read evidence, search tokens, probe cortex, classify."""
    diagnosis = student_diagnosis(repo_root, causal=causal)
    argv = ["rg", "-n", "--max-count", "200", "-g", "!archive/**", TOKEN_PATTERN, str(repo_root)]
    obs = encoding_safe_run(argv, cwd=repo_root, timeout=45.0)
    runtime = ollama or OllamaRuntimeManager()
    inventory = runtime.inventory()
    hits = [ln for ln in obs.stdout.splitlines() if ln.strip()]
    buckets: dict[str, list[str]] = {}
    for line in hits:
        buckets.setdefault(classify_gw_hit(line), []).append(line)
    in_repo = bool(buckets.get("needs_review"))
    diagnosis["action_taken"] = [
        {"tool": "read_evidence", "path": diagnosis.get("evidence_path"), "executed": True, "mutating": False},
        {"tool": "rg", "argv": argv, "executed": True, "mutating": False, "returncode": obs.returncode, "hit_count": len(hits)},
        {"tool": "ollama.inventory", "executed": True, "mutating": False, "ok": bool(inventory.get("ok"))},
    ]
    diagnosis["token_search"] = {
        "returncode": obs.returncode,
        "integrity": obs.integrity,
        "hit_count": len(hits),
        "hits_preview": hits[:40],
        "buckets": {k: v[:8] for k, v in buckets.items()},
        "gateway_source_found_outside_incident_file": in_repo,
    }
    diagnosis["ollama"] = {
        "ok": bool(inventory.get("ok")),
        "reason": inventory.get("reason"),
        "main_cortex_present": bool(inventory.get("main_cortex_present")),
        "models": inventory.get("models") or [],
    }
    diagnosis["student_claims"] = {
        "primary_failure_d4": diagnosis.get("d4_family"),
        "note": "D4 family is current classifier output, not teacher verdict",
        "gateway_source_found_outside_incident_file": in_repo,
        "ollama_ok": bool(inventory.get("ok")),
        "emitted_status": ((diagnosis.get("observed") or {}).get("script_emitted") or {}).get("STATUS"),
        "chat_observation": ((diagnosis.get("observed") or {}).get("POST_/v1/chat")),
        "health_observation": ((diagnosis.get("observed") or {}).get("HEALTH_CHECK")),
    }
    diagnosis["confidence"] = 0.45 if diagnosis.get("ok") else 0.2
    return diagnosis
