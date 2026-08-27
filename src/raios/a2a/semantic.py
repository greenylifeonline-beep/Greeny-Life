"""Governed semantic context. A2A transport compatibility is not semantic agreement."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .failclosed import (
    SEMANTIC_CONTRACT_MISMATCH,
    SEMANTIC_CONTRACT_UNKNOWN,
    FailClosed,
)

SEMANTIC_EXTENSION_URI = "urn:raios:a2a:semantic-context:v1"

SEMANTIC_CONTRACT_MATCH = "SEMANTIC_CONTRACT_MATCH"
SEMANTIC_CONTRACT_MISMATCH_STATUS = "SEMANTIC_CONTRACT_MISMATCH"
SEMANTIC_CONTRACT_UNKNOWN_STATUS = "SEMANTIC_CONTRACT_UNKNOWN"

# Generic fixtures only. Do not hardcode business concepts.
FIXTURE_CONCEPTS = {
    "fx.concept.alpha": {
        "concept_id": "fx.concept.alpha",
        "semantic_version": "1.0.0",
        "definition": "generic test concept alpha",
        "authority": "raios.foundation.test",
        "tenant": "raios-local-test",
        "time_basis": "utc",
        "inclusion": ("fixture",),
        "exclusion": ("production-business",),
        "lineage_requirement": "deterministic-fixture",
    }
}


def canonicalize(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(contract: dict[str, Any]) -> str:
    payload = {k: v for k, v in contract.items() if k not in {"timestamp", "created_at", "volatile_ts", "context_fingerprint"}}
    return hashlib.sha256(canonicalize(payload).encode("utf-8")).hexdigest()


def complete_contract(contract: dict[str, Any]) -> dict[str, Any]:
    required = (
        "semantic_contract_id",
        "semantic_version",
        "concept_set_hash",
        "schema_hash",
        "provenance_policy",
        "authority_domain",
        "tenant",
    )
    out = dict(contract)
    for key in required:
        if key not in out:
            raise FailClosed("SCHEMA_VALIDATION_FAILED", key)
    out["context_fingerprint"] = fingerprint(out)
    return out


class SemanticRegistry:
    def __init__(self) -> None:
        self._contracts: dict[str, dict[str, Any]] = {}
        self.register(default_contract())

    def register(self, contract: dict[str, Any]) -> dict[str, Any]:
        done = complete_contract(contract)
        self._contracts[done["semantic_contract_id"]] = done
        return done

    def compare(self, incoming: dict[str, Any] | None) -> str:
        if not incoming or not incoming.get("semantic_contract_id"):
            return SEMANTIC_CONTRACT_UNKNOWN_STATUS
        cid = incoming["semantic_contract_id"]
        known = self._contracts.get(cid)
        if known is None:
            return SEMANTIC_CONTRACT_UNKNOWN_STATUS
        incoming_fp = fingerprint(incoming)
        if incoming_fp != known["context_fingerprint"]:
            return SEMANTIC_CONTRACT_MISMATCH_STATUS
        return SEMANTIC_CONTRACT_MATCH

    def require(self, incoming: dict[str, Any] | None, *, required: bool) -> dict[str, Any]:
        status = self.compare(incoming)
        if status == SEMANTIC_CONTRACT_UNKNOWN_STATUS:
            if required:
                raise FailClosed(SEMANTIC_CONTRACT_UNKNOWN)
            return {"status": status, "SEMANTIC_EXECUTION_ALLOWED": False, "INTEROPERABILITY_TRANSPORT_COMPATIBLE": True}
        if status == SEMANTIC_CONTRACT_MISMATCH_STATUS:
            raise FailClosed(SEMANTIC_CONTRACT_MISMATCH)
        return {"status": status, "SEMANTIC_EXECUTION_ALLOWED": True, "INTEROPERABILITY_TRANSPORT_COMPATIBLE": True, "contract": self._contracts[incoming["semantic_contract_id"]]}


def resolve_concept(external_name: str) -> dict[str, Any]:
    if external_name in FIXTURE_CONCEPTS:
        return dict(FIXTURE_CONCEPTS[external_name])
    raise FailClosed("SCHEMA_VALIDATION_FAILED", f"unresolved-concept:{external_name}")


def default_contract() -> dict[str, Any]:
    concept_blob = canonicalize(FIXTURE_CONCEPTS)
    schema_blob = canonicalize(["semantic_contract_id", "semantic_version", "concept_set_hash", "schema_hash"])
    return {
        "semantic_contract_id": SEMANTIC_EXTENSION_URI,
        "semantic_version": "1.0.0",
        "concept_set_hash": hashlib.sha256(concept_blob.encode("utf-8")).hexdigest(),
        "schema_hash": hashlib.sha256(schema_blob.encode("utf-8")).hexdigest(),
        "provenance_policy": "EVIDENCE_REQUIRED",
        "authority_domain": "raios.foundation",
        "tenant": "raios-local-test",
        "time_basis": "utc",
        "units": "none",
        "inclusion_rules": ["fixture-only"],
        "exclusion_rules": ["business-production-concepts"],
        "source_authority": "raios-a2a-foundation",
        "confidence_requirements": "deterministic",
    }
