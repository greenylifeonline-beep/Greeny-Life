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


ENCODING_FALSE_PASS_GRAPH = (
    ("CONTEXT", "windows_or_locale_process_environment"),
    ("ACTION", "subprocess_stream_capture"),
    ("OBSERVATION", "locale_or_strict_utf8_decode"),
    ("OUTCOME", "reader_failure_or_mojibake"),
    ("OUTCOME", "stdout_stderr_none_or_invalid"),
    ("OUTCOME", "secondary_exception"),
    ("OUTCOME", "certification_failure"),
    ("OUTCOME", "possible_false_pass_print"),
)


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
    if "work_gate=open" in blob and case.get("failed"):
        return "SYSTEM_INTEGRITY_FAILURE"
    if "evidence_sha" in blob or "evidencesha256" in compact:
        return "REPORT_INTEGRITY"
    if "responsehash" in compact or "response_hash" in blob:
        return "MISSING_RESPONSE_HASH"
    if "missing_final" in blob:
        return "MISSING_FINAL"
    if "child" in blob and ("exit" in blob or "returncode" in blob):
        return "CHILD_EXIT_NONZERO"
    if "powershell" in blob and "else" in blob:
        return "INTERACTIVE_PARSE"
    if "timeout" in blob:
        return "TIMEOUT"
    return "UNCLASSIFIED"


def graph_from_observation(
    causal: CausalLearning,
    obs: KernelObservation | None,
    *,
    printed_pass: bool = False,
    secondary: str = "",
) -> dict[str, Any]:
    parent = None
    nodes: list[str] = []
    payload_base = {
        "id": "encoding-false-pass-incident",
        "supporting_evidence": [
            obs.integrity if obs else "no-observation",
            f"returncode={obs.returncode if obs else 'NA'}",
            f"decode_replaced={obs.decode_replaced if obs else False}",
            f"printed_pass={printed_pass}",
            secondary,
        ],
        "confidence": 0.55,
    }
    for kind, name in ENCODING_FALSE_PASS_GRAPH:
        node = causal.add(kind, {**payload_base, "id": name, "step": name}, parent=parent)
        parent = node["node_id"]
        nodes.append(parent)
    family = classify_failure(
        {
            "integrity": obs.integrity if obs else "",
            "decode_replaced": bool(obs and obs.decode_replaced),
            "printed_pass": printed_pass,
            "failed": True,
            "child_exit": obs.returncode if obs else 1,
        }
    )
    correction = causal.add(
        "CORRECTION",
        {
            "id": "d1-encoding-safe-kernel",
            "family": family,
            "repair": KERNEL_REPAIR_ID,
            "confidence": 0.7,
        },
        parent=parent,
    )
    return {
        "graph_id": deterministic_id("rcg", family, nodes[0] if nodes else "none"),
        "family": family,
        "nodes": nodes + [correction["node_id"]],
        "tested": False,
        "status": "CAUSAL_HYPOTHESIS",
    }


KERNEL_REPAIR_ID = "repair.encoding_safe_subprocess.v1"
