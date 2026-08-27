"""Capability contracts. Extends NeuroLingua ProviderCapability conceptually; does not mutate NL0 files."""

from __future__ import annotations

from typing import Any

from .failclosed import CAPABILITY_NOT_AUTHORIZED, CAPABILITY_UNKNOWN, FailClosed

# WRAP: existing NeuroLingua ProviderCapability shape is reused as provenance, not copied as a second engine.
NL_PROVIDER_CONTRACT_PATH = "src/raios/neuro_lingua/provider_contracts.py"

CAPABILITY_NOOP = "raios.foundation.noop_intent"


def _contract(
    capability_id: str,
    *,
    authority_class: str,
    risk_class: str,
    side_effects: bool,
    reversible: bool,
    public: bool,
) -> dict[str, Any]:
    return {
        "CAPABILITY_ID": capability_id,
        "SEMANTIC_VERSION": "1.0.0",
        "INPUT_SCHEMA": {"type": "object", "properties": {"idempotency_key": {"type": "string"}, "desired_state": {"type": "object"}}},
        "OUTPUT_SCHEMA": {"type": "object", "properties": {"status": {"type": "string"}, "intent": {"type": "object"}}},
        "AUTHORITY_CLASS": authority_class,
        "RISK_CLASS": risk_class,
        "DATA_DOMAINS": ["raios.foundation.fixture"],
        "TOOLS_REQUIRED": [],
        "MODEL_REQUIRED": False,
        "OFFLINE_CAPABLE": True,
        "SIDE_EFFECTS": side_effects,
        "REVERSIBLE": reversible,
        "COST_CLASS": "ZERO",
        "EVIDENCE_REQUIREMENTS": ["receipt"],
        "TIMEOUT": 5,
        "IDEMPOTENCY_SUPPORTED": True,
        "PUBLIC_SAFE_SUBSET": public,
    }


CONTRACTS: dict[str, dict[str, Any]] = {
    CAPABILITY_NOOP: _contract(
        CAPABILITY_NOOP,
        authority_class="FOUNDATION",
        risk_class="LOW",
        side_effects=False,
        reversible=True,
        public=True,
    ),
    "raios.foundation.high_risk_mutate": _contract(
        "raios.foundation.high_risk_mutate",
        authority_class="C1_GATE",
        risk_class="HIGH",
        side_effects=True,
        reversible=False,
        public=False,
    ),
    "raios.foundation.critical_delete": _contract(
        "raios.foundation.critical_delete",
        authority_class="C1_GATE",
        risk_class="CRITICAL",
        side_effects=True,
        reversible=False,
        public=False,
    ),
}


def get_contract(capability_id: str) -> dict[str, Any]:
    if capability_id not in CONTRACTS:
        raise FailClosed(CAPABILITY_UNKNOWN, capability_id)
    return dict(CONTRACTS[capability_id])


def public_skill_subset(capability_id: str) -> dict[str, Any]:
    c = get_contract(capability_id)
    if not c.get("PUBLIC_SAFE_SUBSET"):
        raise FailClosed(CAPABILITY_NOT_AUTHORIZED, capability_id)
    return {
        "id": c["CAPABILITY_ID"],
        "name": c["CAPABILITY_ID"],
        "description": "Governed foundation capability (safe public subset).",
        "tags": ["raios", "foundation", "noop"],
        "input_modes": ["application/json"],
        "output_modes": ["application/json"],
    }


def require_authorized(capability_id: str, *, allow_non_public: bool) -> dict[str, Any]:
    c = get_contract(capability_id)
    if not c.get("PUBLIC_SAFE_SUBSET") and not allow_non_public:
        raise FailClosed(CAPABILITY_NOT_AUTHORIZED, capability_id)
    return c
