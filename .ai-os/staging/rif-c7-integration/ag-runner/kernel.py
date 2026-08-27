"""Staging-only RIF donor evaluation kernel.

Not a second WAL, canonicalizer, policy authority, evidence store, or UCP.
Adapters are in-memory test doubles or wraps of existing RAIOS modules.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

PROVIDER_ID = "RAIOS_FINGERPRINT_ADAPTER"
SANDBOX_PROVIDER_ID = "C7_SANDBOX_REFERENCE"
MAX_ITERATIONS = 8
NO_PROGRESS_CYCLES = 5
REPEATED_TOOL_THRESHOLD = 3

EVENT_FIELDS = (
    "RUN_ID",
    "TASK_ID",
    "TRACE_ID",
    "CORRELATION_ID",
    "CLAIM_ID",
    "EVIDENCE_ID",
    "MODEL_ID",
    "POLICY_VERSION",
    "SCHEMA_VERSION",
    "PRODUCER",
    "DECISION",
    "REASON",
    "COST",
    "STOP_REASON",
    "EVENT_TYPE",
    "TIMESTAMP",
)

LEGAL_TRANSITIONS = {
    ("RECEIVED", "normalize_complete"): "NORMALIZED",
    ("NORMALIZED", "start_validation"): "VALIDATING",
    ("VALIDATING", "validation.evidence_insufficient"): "EVIDENCE_REQUIRED",
    ("EVIDENCE_REQUIRED", "evidence_complete"): "EVIDENCE_GATHERED",
    ("EVIDENCE_GATHERED", "start_contradiction_check"): "CONTRADICTION_CHECK",
    ("CONTRADICTION_CHECK", "start_evaluate"): "EVALUATING",
    ("EVALUATING", "evaluation.complete"): "GOVERNOR_DECISION",
    ("GOVERNOR_DECISION", "advisory_candidate"): "CANONICAL_CANDIDATE",
}

STOP_PRECEDENCE = (
    "STOP_CRITICAL_CONTRADICTION",
    "STOP_POLICY",
    "STOP_AUTHORITY_REQUIRED",
    "STOP_BUDGET",
    "STOP_NO_PROGRESS",
    "RESOURCE_EXHAUSTION",
    "DEPENDENCY_UNAVAILABLE",
    "GOAL_ACHIEVED",
    "FAIL",
    "PASS",
    "ABSTAIN",
    "ESCALATE",
    "REQUEST_EVIDENCE",
    "CONTINUE",
)


def _sha(obj: Any) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


class RAIOSFingerprintAdapter:
    """External fingerprint provider. Does not claim canonical authority."""

    provider_id = PROVIDER_ID

    def algorithm_id(self) -> str:
        return "sha256-canonical-json-v1"

    def schema_version(self) -> str:
        return "1.1"

    def canonicalize(self, obj: Any) -> dict[str, Any]:
        return {"canonical_form": json.dumps(obj, sort_keys=True, default=str), "canonical": False}

    def fingerprint(self, obj: Any) -> dict[str, Any]:
        return {
            "algorithm_id": self.algorithm_id(),
            "provider": self.provider_id,
            "digest": _sha(obj),
            "canonical": False,
            "authority": False,
        }

    def verify(self, obj: Any, fingerprint: dict[str, Any], expected_schema: str | None = None) -> str:
        schema = None
        if isinstance(obj, dict):
            schema = obj.get("schema_version")
        if expected_schema and schema and str(schema) != str(expected_schema):
            return "VERIFICATION_FAILED"
        expected = self.fingerprint(obj)
        return "OK" if expected["digest"] == fingerprint.get("digest") else "VERIFICATION_FAILED"


class SandboxReferenceFingerprint:
    """C7 historical sandbox reference. Never canonical."""

    def as_claim(self) -> dict[str, Any]:
        return {
            "kind": "sandbox_reference_fingerprint",
            "provider": SANDBOX_PROVIDER_ID,
            "authority": False,
            "canonical": False,
        }


class EvidenceStoreAdapter:
    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self._items: dict[str, dict[str, Any]] = {}

    def store(self, evidence: dict[str, Any]) -> str:
        if not self.available:
            raise RuntimeError("UNAVAILABLE")
        eid = evidence.get("id") or str(uuid4())
        item = dict(evidence)
        item["id"] = eid
        origin = item.get("origin_source_id") or eid
        item["origin_source_id"] = origin
        item["correlation_group"] = item.get("correlation_group") or f"CORR-{origin}"
        parents = item.get("derived_from") or []
        lineage = list(item.get("lineage") or [])
        for parent in parents:
            if parent in self._items:
                lineage.extend(self._items[parent].get("lineage") or [])
                lineage.append(parent)
        item["lineage"] = lineage
        if item.get("truncated"):
            item["trust"] = "UNTRUSTED"
            item["TRUNCATION_DETECTED"] = True
        self._items[eid] = item
        return eid

    def retrieve(self, reference: str) -> dict[str, Any]:
        if not self.available:
            raise RuntimeError("UNAVAILABLE")
        return dict(self._items[reference])

    def lineage(self, evidence_id: str) -> list[str]:
        item = self._items[evidence_id]
        return list(item.get("lineage") or []) + [evidence_id]

    def exists(self, evidence_id: str) -> bool:
        return evidence_id in self._items

    def query(self, **_kwargs: Any) -> list[dict[str, Any]]:
        if not self.available:
            raise RuntimeError("UNAVAILABLE")
        return [dict(v) for v in self._items.values()]


class WALAdapter:
    """Wrap existing WAL conceptually. This phase never writes RAIOS WAL."""

    def __init__(self) -> None:
        self.appends: list[dict[str, Any]] = []
        self.direct_filesystem_writes = 0

    def append(self, entry: dict[str, Any]) -> str:
        self.appends.append(dict(entry))
        return f"WALREF-{len(self.appends)}"


class ObservabilitySinkAdapter:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.local_store = False

    def emit_event(self, event: dict[str, Any]) -> bool:
        self.events.append(dict(event))
        return True


class PolicyAdapter:
    """Wrap existing RAIOS policy posture. C7 is not policy authority."""

    authority = False

    def evaluate_policy(self, risk_assessment: dict[str, Any]) -> dict[str, Any]:
        cls = str(risk_assessment.get("risk_class") or "UNKNOWN").upper()
        if cls == "UNKNOWN":
            return {"POLICY_RESULT": "ESCALATE", "self_authorize": False}
        if cls in {"HIGH", "CRITICAL"}:
            return {"POLICY_RESULT": "ESCALATE", "self_authorize": False}
        return {"POLICY_RESULT": "ALLOW", "self_authorize": False}


class ClaimGraph:
    """Logical view only. Does not persist independently of EvidenceStoreAdapter."""

    def __init__(self, store: EvidenceStoreAdapter) -> None:
        self.store = store

    def independence(self, a: str, b: str) -> bool:
        ea, eb = self.store.retrieve(a), self.store.retrieve(b)
        return ea.get("correlation_group") != eb.get("correlation_group")

    def active_strength(self, claim_id: str) -> list[str]:
        active = []
        superseded = {e["id"] for e in self.store.query() if e.get("superseded_by")}
        for item in self.store.query():
            if item.get("claim_id") != claim_id:
                continue
            if item["id"] in superseded or item.get("superseded"):
                continue
            active.append(item["id"])
        return active


class Governor:
    """Pure decision logic. No WAL/NATS/FS/evidence mutation."""

    def decide(self, inp: dict[str, Any]) -> dict[str, Any]:
        stops: list[str] = []
        if inp.get("contradiction_status") == "CRITICAL":
            stops.append("STOP_CRITICAL_CONTRADICTION")
        if inp.get("policy_status") == "DENIED":
            stops.append("STOP_POLICY")
        if inp.get("authority_status") == "MISSING":
            stops.append("STOP_AUTHORITY_REQUIRED")
        if int(inp.get("iteration_count") or 0) >= int(inp.get("max_iterations") or MAX_ITERATIONS):
            stops.append("STOP_BUDGET")
        history = inp.get("state_history") or []
        if len(history) >= NO_PROGRESS_CYCLES and len(set(json.dumps(x, sort_keys=True) for x in history[-NO_PROGRESS_CYCLES:])) == 1:
            if not inp.get("new_evidence"):
                stops.append("STOP_NO_PROGRESS")
        tools = inp.get("tool_call_history") or []
        if tools:
            last = json.dumps(tools[-1], sort_keys=True)
            if sum(1 for t in tools if json.dumps(t, sort_keys=True) == last) >= REPEATED_TOOL_THRESHOLD:
                stops.append("STOP_NO_PROGRESS")
        if inp.get("adapter_unavailable"):
            stops.append("STOP_AUTHORITY_REQUIRED")
        if not stops:
            return {"decision": "CONTINUE", "side_effects": [], "wal_written": False}
        chosen = min(stops, key=lambda s: STOP_PRECEDENCE.index(s) if s in STOP_PRECEDENCE else 99)
        return {"decision": chosen, "side_effects": [], "wal_written": False}


class EvaluationStateMachine:
    def __init__(self, sink: ObservabilitySinkAdapter) -> None:
        self.state = "RECEIVED"
        self.sink = sink
        self.events: list[str] = []

    def transition(
        self,
        trigger: str,
        *,
        guards: dict[str, Any] | None = None,
        preconditions: dict[str, Any] | None = None,
        llm_suggested: str | None = None,
    ) -> dict[str, Any]:
        guards = guards or {}
        preconditions = preconditions or {}
        if llm_suggested:
            key = (self.state, f"llm:{llm_suggested}")
            if key not in LEGAL_TRANSITIONS:
                self.events.append("UNLISTED_TRANSITION_BLOCKED")
                return {"result": "BLOCKED", "state": self.state, "observability_event": "UNLISTED_TRANSITION_BLOCKED"}
        key = (self.state, trigger)
        if key not in LEGAL_TRANSITIONS:
            self.events.append("ILLEGAL_TRANSITION_ATTEMPT")
            return {"result": "BLOCKED", "state": self.state, "observability_event": "ILLEGAL_TRANSITION_ATTEMPT"}
        if guards.get("evidence_count") is not None and guards.get("minimum") is not None:
            if int(guards["evidence_count"]) < int(guards["minimum"]):
                self.events.append("GUARD_FAILURE")
                return {"result": "BLOCKED", "state": self.state, "observability_event": "GUARD_FAILURE"}
        if preconditions.get("ready") is False:
            self.events.append("PRECONDITION_FAILURE")
            failure = "ABSTAIN"
            self.state = failure
            return {"result": failure, "state": self.state, "observability_event": "PRECONDITION_FAILURE"}
        nxt = LEGAL_TRANSITIONS[key]
        self.state = nxt
        self.events.append("STATE_TRANSITION")
        return {"result": "SUCCESS", "state": self.state, "observability_event": "STATE_TRANSITION"}

    def promote_canonical(self) -> dict[str, Any]:
        if self.state == "CANONICAL_CANDIDATE":
            return {"result": "BLOCKED", "advisory_only": True, "canonical": False}
        return {"result": "BLOCKED", "advisory_only": True, "canonical": False}


class Kernel:
    def __init__(self, fingerprint: RAIOSFingerprintAdapter | None = None) -> None:
        self.fingerprint = fingerprint or RAIOSFingerprintAdapter()
        self.store = EvidenceStoreAdapter()
        self.claims = ClaimGraph(self.store)
        self.wal = WALAdapter()
        self.sink = ObservabilitySinkAdapter()
        self.policy = PolicyAdapter()
        self.governor = Governor()
        self.machine = EvaluationStateMachine(self.sink)
        self.logger_backend = self.sink
        self.owns_nats = False
        self.owns_wal = False
        self.owns_evidence_store = False
        self.owns_policy = False

    def validate_contract(self, contract: dict[str, Any], *, unknown_field_policy: str = "REJECT") -> dict[str, Any]:
        if "schema_version" not in contract:
            return {"result": "REJECT", "error": "missing_field_error"}
        producer = contract.get("producer") or {}
        required_id = ("declared", "verified", "component", "version")
        if contract.get("require_identity") or "producer_declared" in contract:
            if any(k not in producer for k in required_id):
                return {"result": "REJECT", "error": "incomplete_identity"}
        allowed = {
            "schema_version",
            "producer",
            "require_identity",
            "producer_declared",
            "payload",
            "unknown_field_policy",
        }
        extras = [k for k in contract if k not in allowed]
        policy = contract.get("unknown_field_policy") or unknown_field_policy
        if extras and policy == "REJECT":
            return {"result": "REJECT", "error": "unknown_field_error"}
        return {"result": "OK"}

    def classify_schema_change(self, old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
        old_req = set(old.get("required") or [])
        new_req = set(new.get("required") or [])
        if old_req - new_req:
            return {"class": "BREAKING", "migration_required": True}
        return {"class": "NON_BREAKING", "migration_required": False}

    def make_event(self, **fields: Any) -> dict[str, Any]:
        base = {k: None for k in EVENT_FIELDS}
        base.update(
            {
                "RUN_ID": str(uuid4()),
                "TASK_ID": "RAIOS-RIF-C7-INTEGRATION-RECON-02A",
                "TRACE_ID": str(uuid4()),
                "CORRELATION_ID": str(uuid4()),
                "CLAIM_ID": "CLAIM-0",
                "EVIDENCE_ID": "EV-0",
                "MODEL_ID": "NONE",
                "POLICY_VERSION": "raios.policy.v1",
                "SCHEMA_VERSION": "1.1",
                "PRODUCER": {
                    "declared": "C7",
                    "verified": "SERVER_SIDE_UNVERIFIED",
                    "component": "rif-donor-kernel",
                    "version": "1.1",
                },
                "DECISION": "CONTINUE",
                "REASON": "test",
                "COST": 0,
                "STOP_REASON": None,
                "EVENT_TYPE": "EVALUATION_STARTED",
                "TIMESTAMP": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
        base.update(fields)
        self.sink.emit_event(base)
        return base

    def bind_receipt(self, decision: dict[str, Any]) -> dict[str, Any]:
        receipt = {
            "decision_id": decision["id"],
            "decision": deepcopy(decision),
            "bound": True,
        }
        receipt["integrity"] = _sha({"decision_id": decision["id"], "decision": decision})
        return receipt

    def receipt_valid(self, receipt: dict[str, Any]) -> str:
        probe = {"decision_id": receipt.get("decision_id"), "decision": receipt.get("decision")}
        if _sha(probe) != receipt.get("integrity"):
            return "MODIFICATION_DETECTED"
        return "OK"

    def assess_risk(self, risk_class: str, fields: dict[str, Any] | None = None) -> dict[str, Any]:
        cls = (risk_class or "UNKNOWN").upper()
        fields = fields or {}
        separated = {
            "source_trust": fields.get("source_trust", "UNKNOWN"),
            "evidence_strength": fields.get("evidence_strength", "UNKNOWN"),
            "claim_confidence": fields.get("claim_confidence", "UNKNOWN"),
            "model_confidence": fields.get("model_confidence", "UNKNOWN"),
            "uncertainty": fields.get("uncertainty", "UNKNOWN"),
            "contradiction_severity": fields.get("contradiction_severity", "NONE"),
        }
        policy = self.policy.evaluate_policy({"risk_class": cls})
        if cls == "UNKNOWN":
            action = "ESCALATE"
        elif cls in {"HIGH", "CRITICAL"}:
            action = "ESCALATE"
        else:
            action = "CONTINUE"
        return {
            "risk_class": cls,
            "action": action,
            "self_authorize": False,
            "confidence_fields": separated,
            "combination_policy": "KEEP_SEPARATE",
            "policy": policy,
        }

    def contradiction_check(self, e1: dict[str, Any], e2: dict[str, Any]) -> dict[str, Any]:
        if e1.get("relation") == "SUPPORTS" and e2.get("relation") == "REFUTES" and e1.get("claim_id") == e2.get("claim_id"):
            severity = "HIGH"
            if e1.get("strength") == e2.get("strength"):
                severity = "HIGH"
            if e1.get("critical") or e2.get("critical"):
                severity = "CRITICAL"
            return {"result": "CONTRADICTION_DETECTED", "severity": severity}
        return {"result": "NONE"}

    def evaluate_unknown_claim(self, status: str) -> dict[str, Any]:
        if status == "UNKNOWN":
            return {"numeric_value": None, "treated_as_zero": False, "auto_rejected": False}
        return {"numeric_value": 0, "treated_as_zero": True}

    def evaluate_empty_evidence(self) -> dict[str, Any]:
        return {"result": "NEEDS_MORE_EVIDENCE", "proven_negation": False}

    def verify_authority(self, presented: dict[str, Any]) -> dict[str, Any]:
        if presented.get("self_asserted") or presented.get("granted_scopes") or presented.get("role") == "admin":
            return {"result": "REJECTED", "reason": "requires independent verification"}
        if presented.get("trusted_server_side"):
            return {"result": "OK"}
        return {"result": "REJECTED", "reason": "requires independent verification"}

    def a2a_bridge(self, a2a: dict[str, Any], rif: dict[str, Any]) -> dict[str, Any]:
        transport_ok = bool(a2a.get("transport_ok", True))
        semantic_ok = a2a.get("provenance_policy") == rif.get("provenance_policy")
        if a2a.get("provenance_policy") == "BASIC" and rif.get("provenance_policy") == "LINEAGE":
            semantic_ok = False
        if transport_ok and semantic_ok:
            action = "PROCEED"
        elif transport_ok and not semantic_ok:
            action = "ESCALATE"
        else:
            action = "BLOCK"
        out = {
            "transport_compatible": transport_ok,
            "semantically_compatible": semantic_ok,
            "recommended_action": action,
        }
        if not semantic_ok and transport_ok:
            out["mismatches"] = [
                {
                    "a2a_field": "provenance_policy",
                    "rif_expectation": rif.get("provenance_policy"),
                    "a2a_provided": a2a.get("provenance_policy"),
                    "severity": "HIGH",
                    "resolution": "ESCALATE_TO_AUTHORITY",
                }
            ]
        return out

    def map_a2a_task(self, a2a_status: str, evidence_ok: bool) -> dict[str, Any]:
        if a2a_status == "COMPLETED" and not evidence_ok:
            verdict = "ABSTAIN"
        elif a2a_status in {"FAILED", "TIMEOUT", "TRANSPORT_FAIL"}:
            verdict = "BLOCKED"
        else:
            verdict = "ESCALATE"
        return {"a2a_task_status": a2a_status, "rif_verdict": verdict, "decision": "DO_NOT_PROMOTE"}


HARD_GATES = (
    "license_incompatibility",
    "weights_unavailable",
    "unsupported_architecture",
    "minimum_context_failure",
    "schema_adherence_below_minimum",
    "unsafe_tool_behavior",
    "abstention_below_minimum",
    "resource_requirement_impossible",
    "offline_requirement_failure",
    "privacy_requirement_failure",
)

ROLE_PREFS = {
    "FAST_ROUTER": {"latency": 1, "accuracy": 0},
    "DEEP_REASONER": {"latency": 0, "accuracy": 1},
}


def m001_select(role: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    ranked = []
    for c in candidates:
        disq = [g for g in (c.get("disqualifiers") or []) if g in HARD_GATES]
        if role in {"OFFLINE_RESILIENCE"} and c.get("api_only") and c.get("requires_local"):
            disq.append("offline_requirement_failure")
        item = dict(c)
        item["disqualifiers"] = disq
        item["hard_gates_passed"] = not disq
        ranked.append(item)
    viable = [c for c in ranked if c["hard_gates_passed"]]
    prefs = ROLE_PREFS.get(role, {"latency": 0, "accuracy": 1})

    def dominated(a: dict[str, Any], b: dict[str, Any]) -> bool:
        return (
            b.get("accuracy", 0) >= a.get("accuracy", 0)
            and b.get("speed", 0) >= a.get("speed", 0)
            and b.get("cost_inv", 0) >= a.get("cost_inv", 0)
            and (
                b.get("accuracy", 0) > a.get("accuracy", 0)
                or b.get("speed", 0) > a.get("speed", 0)
                or b.get("cost_inv", 0) > a.get("cost_inv", 0)
            )
        )

    frontier = [c for c in viable if not any(dominated(c, o) for o in viable if o is not c)]
    if prefs["latency"]:
        selected_pool = sorted(frontier, key=lambda c: (-c.get("speed", 0), -c.get("accuracy", 0)))
    else:
        selected_pool = sorted(frontier, key=lambda c: (-c.get("accuracy", 0), -c.get("speed", 0)))
    selected = selected_pool[0] if selected_pool else None
    out_candidates = []
    for i, c in enumerate(ranked):
        rec = {
            "model_id": c["model_id"],
            "disqualifiers": c["disqualifiers"],
            "hard_gates_passed": c["hard_gates_passed"],
            "pareto_rank": frontier.index(c) + 1 if c in frontier else None,
            "scenario_rank": i + 1,
            "selection_confidence": None if not c["hard_gates_passed"] else 0.7,
            "selection_reason": "disqualified" if c["disqualifiers"] else "pareto",
            "reproducibility_hash": _sha({"model": c["model_id"], "role": role, "gates": c["disqualifiers"]}),
        }
        out_candidates.append(rec)
    result = {
        "selection_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scenario": "ag-staging-deterministic",
        "role": role,
        "candidates": out_candidates,
        "selected_model": selected["model_id"] if selected else None,
        "selection_rationale": "role-specific Pareto, no scalar mix",
        "invalidation_conditions": ["new_hard_gate", "role_profile_change"],
    }
    if selected is None:
        result["DISQUALIFIED"] = True
        gate = ranked[0]["disqualifiers"][0] if ranked and ranked[0]["disqualifiers"] else None
        result["hard_gate"] = "license" if gate == "license_incompatibility" else gate
    return result
