"""D4 Root Cause Graph / Classifier.

Deterministic classification first. Causal edges stay hypotheses until
a transfer/negative-control test sets tested=True.
"""
from __future__ import annotations

import json
from typing import Any

from .causal_learning import CausalLearning
from .config import deterministic_id
from .process_kernel import KernelObservation

KERNEL_REPAIR_ID = "repair.encoding_safe_subprocess.v1"
FALSE_PASS_REPAIR_ID = "repair.anti_false_pass.v1"


def classify_failure(case: dict[str, Any]) -> str:
    """Order is evidence-driven: encoding and false-PASS before hash keywords."""
    blob = json.dumps(case, sort_keys=True).lower().replace("-", "_")
    compact = blob.replace("_", "")
    if case.get("http") == 200 and (case.get("invalid_semantic") or case.get("report_integrity") is False):
        return "HTTP_200_INVALID_SEMANTIC"
    if case.get("http") in {500, 502, 503, 504} or "ollama_server_error" in blob:
        return "OLLAMA_SERVER_ERROR"
    if (
        "unicodedecode" in compact
        or case.get("decode_replaced")
        or case.get("integrity") in {"DECODE_REPLACED", "ENCODING_INTEGRITY_FAILURE"}
        or "encoding_integrity" in blob
    ):
        return "UNICODE_DECODE"
    if "stream_none" in blob or ("stdout" in case and case.get("stdout") is None) or (
        "stderr" in case and case.get("stderr") is None and case.get("spawned")
    ):
        return "STREAM_NONE"
    if "false_pass" in blob or (case.get("printed_pass") and case.get("failed")):
        return "FALSE_PASS"
    if case.get("timeout") or "timeout" in blob:
        return "TIMEOUT"
    if "work_gate=open" in blob and case.get("failed"):
        return "SYSTEM_INTEGRITY_FAILURE"
    if "evidence_sha" in blob or "evidencesha256" in compact:
        return "REPORT_INTEGRITY"
    if "responsehash" in compact or "response_hash" in blob:
        return "MISSING_RESPONSE_HASH"
    if "missing_final" in blob:
        return "MISSING_FINAL"
    if case.get("permission_denied") or "permission" in blob and "denied" in blob:
        return "PERMISSION_DENIED"
    if "child" in blob and ("exit" in blob or "returncode" in blob):
        return "CHILD_EXIT_NONZERO"
    if "powershell" in blob and "else" in blob:
        return "INTERACTIVE_PARSE"
    if "timeout" in blob:
        return "TIMEOUT"
    if "model" in blob and "missing" in blob:
        return "MODEL_UNAVAILABLE"
    if "tool" in blob and ("missing" in blob or "unavailable" in blob):
        return "TOOL_UNAVAILABLE"
    return "UNCLASSIFIED"


def diagnose(
    causal: CausalLearning,
    obs: KernelObservation | None,
    *,
    printed_pass: bool = False,
    secondary: str = "",
    error: str = "",
) -> dict[str, Any]:
    """Build an evidence-driven graph. Do not always emit the encoding template."""
    evidence = [
        obs.integrity if obs else "no-observation",
        f"returncode={obs.returncode if obs else 'NA'}",
        f"decode_replaced={obs.decode_replaced if obs else False}",
        f"printed_pass={printed_pass}",
        f"stdout_bytes={obs.stdout_bytes_len if obs else 0}",
        error or secondary,
    ]
    case: dict[str, Any] = {
        "integrity": obs.integrity if obs else "",
        "decode_replaced": bool(obs and obs.decode_replaced),
        "printed_pass": printed_pass,
        "failed": bool(error) or printed_pass or (obs is not None and obs.returncode != 0),
        "child_exit": obs.returncode if obs is not None else None,
        "timeout": bool(obs and obs.timed_out) or "timeout" in error.lower(),
    }
    if obs is not None:
        case["stdout"] = obs.stdout
    family = classify_failure(case)
    confidence = 0.42
    nodes: list[str] = []
    parent: str | None = None

    def add(kind: str, name: str, relation: str, extra: dict[str, Any] | None = None) -> str:
        nonlocal parent
        payload = {
            "id": name,
            "family": family,
            "supporting_evidence": evidence,
            "confidence": confidence,
            **(extra or {}),
        }
        node = causal.add(kind, payload, parent=parent, relation=relation if parent else "causal_parent")
        parent = node["node_id"]
        nodes.append(parent)
        return parent

    add("ENVIRONMENT", "process_environment", "DEPENDS_ON", {"env": (obs.env if obs else {})})
    add("PROCESS", "child_process", "DEPENDS_ON", {"argv": (obs.argv if obs else []), "returncode": (obs.returncode if obs else None)})
    add("SYMPTOM", f"symptom:{family.lower()}", "TRIGGERED")

    root_name = family.lower()
    secondary_name = secondary or "none"
    if family == "FALSE_PASS":
        confidence = 0.78
        add("ASSERTION", "stdout_is_not_authority", "CONTRADICTS")
        add("ROOT_CAUSE", "false_pass_print_used_as_success", "CAUSED")
        if obs and obs.returncode != 0:
            add("SECONDARY_FAILURE", "nonzero_exit_after_success_token", "PROPAGATED_TO")
        else:
            add("SECONDARY_FAILURE", "bare_pass_with_zero_exit", "PROPAGATED_TO")
        repair = FALSE_PASS_REPAIR_ID
    elif family in {"UNICODE_DECODE", "STREAM_NONE"}:
        confidence = 0.74
        add("EXCEPTION", "locale_or_utf8_decode_failure", "TRIGGERED")
        add("ROOT_CAUSE", "implicit_locale_subprocess_decode", "CAUSED")
        add("SECONDARY_FAILURE", secondary or "stdout_none_or_splitlines", "PROPAGATED_TO")
        add("ARTIFACT", "certification_receipt_absent_or_invalid", "BLOCKED")
        repair = KERNEL_REPAIR_ID
    elif family == "TIMEOUT":
        confidence = 0.7
        add("RESOURCE", "time_budget", "DEPENDS_ON")
        add("ROOT_CAUSE", "child_timeout", "CAUSED")
        add("SECONDARY_FAILURE", "partial_streams", "PROPAGATED_TO")
        repair = None
    else:
        add("ROOT_CAUSE", root_name, "CAUSED")
        if secondary_name != "none":
            add("SECONDARY_FAILURE", secondary_name, "PROPAGATED_TO")
        repair = KERNEL_REPAIR_ID if family in {"CHILD_EXIT_NONZERO"} else None

    correction = causal.add(
        "CORRECTION",
        {
            "id": "repair-candidate",
            "family": family,
            "repair": repair,
            "confidence": min(0.85, confidence + 0.08),
            "supporting_evidence": evidence,
        },
        parent=parent,
        relation="CAUSED",
    )
    nodes.append(correction["node_id"])
    kinds = [causal.nodes[n]["kind"] for n in nodes]
    return {
        "graph_id": deterministic_id("rcg", family, nodes[0] if nodes else "none"),
        "family": family,
        "nodes": nodes,
        "edges": list(causal.edges),
        "kinds": kinds,
        "evidence": evidence,
        "confidence": confidence,
        "root_cause": next((causal.nodes[n]["payload"]["id"] for n in nodes if causal.nodes[n]["kind"] == "ROOT_CAUSE"), family),
        "secondary_failure": next((causal.nodes[n]["payload"]["id"] for n in nodes if causal.nodes[n]["kind"] == "SECONDARY_FAILURE"), None),
        "repair_id": repair,
        "tested": False,
        "status": "CAUSAL_HYPOTHESIS",
    }


def graph_from_observation(
    causal: CausalLearning,
    obs: KernelObservation | None,
    *,
    printed_pass: bool = False,
    secondary: str = "",
) -> dict[str, Any]:
    return diagnose(causal, obs, printed_pass=printed_pass, secondary=secondary)
