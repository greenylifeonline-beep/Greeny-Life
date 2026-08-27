"""A2A request path. NEVER A2A_REQUEST -> EXECUTE."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH, PROTOCOL_VERSION_CURRENT, TransportProtocol

from . import capability as capmod
from . import mcp_bridge
from . import nats_bridge
from . import policy_bridge
from . import receipt_bridge
from . import task_bridge
from .cards import FORBIDDEN_PUBLIC_AGENTS, build_extended_card, build_public_card, card_as_dict
from .failclosed import (
    AUTH_FAILED,
    CAPABILITY_NOT_AUTHORIZED,
    DIRECT_EXECUTION_PATH_FORBIDDEN,
    SEAT_IDENTITY_NOT_PUBLIC_AGENT,
    FailClosed,
)
from .pipeline import PATH
from .semantic import SemanticRegistry, resolve_concept
from .trust import require_trusted, sign_bytes, verify
from .ucp_adapter import DryRunUCP
from . import authority as authz

OFFICIAL_METHODS = (
    "SendMessage",
    "GetTask",
    "CancelTask",
    "GetExtendedAgentCard",
    "ListTasks",
)


@dataclass
class A2ARequest:
    agent_id: str
    capability_id: str
    a2a_task_id: str
    a2a_context_id: str
    desired_state: dict[str, Any]
    idempotency_key: str
    action: str = "NOOP"
    risk: str | None = None
    semantic_contract: dict[str, Any] | None = None
    signature: str | None = None
    issuer: str | None = None
    granted_scopes: tuple[str, ...] = ()
    authority_present: bool = False
    requested_authority: str | None = None
    requested_role: str | None = None
    require_semantic: bool = True
    require_trusted_issuer: bool = False
    mcp_direct: bool = False
    direct_execute: bool = False
    external_concept: str | None = None
    a2a_message_id: str | None = None
    a2a_artifact_id: str | None = None


class Gateway:
    """Bounded A2A edge. No business intelligence. No canonical decisions. No public listener."""

    def __init__(
        self,
        *,
        hmac_secrets: dict[str, bytes] | None = None,
        trusted_issuers: tuple[str, ...] = (),
        principal_by_issuer: dict[str, str] | None = None,
        scopes_by_principal: dict[str, tuple[str, ...]] | None = None,
        high_risk_principals: tuple[str, ...] = (),
        ucp: DryRunUCP | None = None,
    ) -> None:
        self.hmac_secrets = hmac_secrets or {}
        self.trusted_issuers = trusted_issuers
        self.principal_by_issuer = principal_by_issuer or {}
        self.scopes_by_principal = scopes_by_principal or {}
        self.high_risk_principals = frozenset(high_risk_principals)
        self.ucp = ucp or DryRunUCP()
        self.semantics = SemanticRegistry()

    def discovery(self) -> dict[str, Any]:
        return {
            "well_known_path": AGENT_CARD_WELL_KNOWN_PATH,
            "protocol_version": PROTOCOL_VERSION_CURRENT,
            "bindings": [TransportProtocol.JSONRPC.value],
            "public_listener": False,
            "in_process_only": True,
            "agent_card": self.public_agent_card(),
        }

    def public_agent_card(self) -> dict[str, Any]:
        return card_as_dict(build_public_card())

    def extended_agent_card(
        self,
        *,
        agent_id: str | None = None,
        signature: str | None = None,
        issuer: str | None = None,
        granted_scopes: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        if not signature or not agent_id or not issuer:
            raise FailClosed(AUTH_FAILED)
        payload = f"{agent_id}:extended-card".encode()
        trust = verify(
            agent_id=agent_id,
            payload=payload,
            signature=signature,
            issuer=issuer,
            trusted_issuers=self.trusted_issuers,
            hmac_secrets=self.hmac_secrets,
            required_scope="raios.a2a.task",
            authorized_scopes=(),
            allow_unauthenticated_public=False,
        )
        if not trust.SIGNATURE_VALID:
            raise FailClosed(AUTH_FAILED)
        return card_as_dict(build_extended_card())

    def negotiate_protocol(self, requested: str | None) -> dict[str, Any]:
        binding = (requested or TransportProtocol.JSONRPC.value).upper().replace("+", "_")
        supported = {p.value.upper() for p in TransportProtocol}
        ok = requested is None or requested.upper() in supported or requested.upper() == "JSONRPC"
        return {
            "requested": requested or TransportProtocol.JSONRPC.value,
            "selected": TransportProtocol.JSONRPC.value if ok else None,
            "supported": [p.value for p in TransportProtocol],
            "streaming": False,
            "official_methods": list(OFFICIAL_METHODS),
            "listener_bound": False,
        }

    def auth_negotiation(self) -> dict[str, Any]:
        return {
            "public_noop_unauthenticated": True,
            "extended_card_requires_auth": True,
            "non_public_capability_requires_signature": True,
            "jws_module": "a2a.utils.signing",
            "production_trusted_issuers": [],
        }

    def handle(self, req: A2ARequest) -> dict[str, Any]:
        if req.direct_execute:
            raise FailClosed(DIRECT_EXECUTION_PATH_FORBIDDEN)
        if req.mcp_direct:
            mcp_bridge.forbid_direct(req.agent_id)

        self._identity(req)
        trust = self._authenticate(req)
        requested = authz.requested_authority_snapshot(
            authority_present=req.authority_present,
            granted_scopes=req.granted_scopes,
            requested_authority=req.requested_authority,
            requested_role=req.requested_role,
        )
        principal = self._bound_principal(req.issuer, trust.ISSUER_TRUSTED)
        authorized_scopes = authz.server_scopes_for(
            issuer=req.issuer,
            principal=principal,
            scopes_by_principal=self.scopes_by_principal,
        )
        sem = self.semantic_context_validation(req.semantic_contract, required=req.require_semantic)
        contract = self._resolve_capability(req, trust)
        if req.external_concept:
            resolve_concept(req.external_concept)
        risk = policy_bridge.map_risk(req.risk, contract["RISK_CLASS"])
        needs_auth = authz.needs_server_authority(req.action, risk, side_effects=bool(contract.get("SIDE_EFFECTS")))
        decision = authz.derive(
            capability_id=req.capability_id,
            action=req.action,
            risk=risk,
            side_effects=bool(contract.get("SIDE_EFFECTS")),
            signature_valid=trust.SIGNATURE_VALID,
            issuer_identified=trust.ISSUER_IDENTIFIED,
            issuer_trusted=trust.ISSUER_TRUSTED,
            issuer=req.issuer,
            principal=principal,
            authorized_scopes=authorized_scopes,
            high_risk_principals=self.high_risk_principals,
            requested=requested,
            task_id=req.a2a_task_id,
        )
        if needs_auth:
            authz.require_for_policy(decision, needs_authority=True)
        elif req.capability_id != capmod.CAPABILITY_NOOP and trust.ISSUER_TRUSTED and not decision.CAPABILITY_AUTHORIZED:
            raise FailClosed(CAPABILITY_NOT_AUTHORIZED, req.capability_id)
        auth_result = decision.as_auth_result()
        policy_evidence = {
            "AUTH_INPUT": {
                "agent_id": req.agent_id,
                "issuer": req.issuer,
                "capability_id": req.capability_id,
                "action": req.action,
                "REQUESTED_AUTHORITY": requested,
            },
            "TRUST_RESULT": {
                "SIGNATURE_VALID": auth_result["SIGNATURE_VALID"],
                "ISSUER_IDENTIFIED": auth_result["ISSUER_IDENTIFIED"],
                "ISSUER_TRUSTED": auth_result["ISSUER_TRUSTED"],
            },
            "SCOPE_RESULT": {
                "AUTHORIZED_SCOPES": auth_result["AUTHORIZED_SCOPES"],
                "AUTHORIZED_SCOPE_PRESENT": decision.AUTHORIZED_SCOPE_PRESENT,
                "SCOPE_AUTHORIZED": auth_result["SCOPE_AUTHORIZED"],
                "AUTHORITY_SOURCE": auth_result["AUTHORITY_SOURCE"],
            },
            "CAPABILITY_RESULT": {
                "CAPABILITY_ID": req.capability_id,
                "CAPABILITY_AUTHORIZED": auth_result["CAPABILITY_AUTHORIZED"],
            },
            "RISK_RESULT": {"RISK_CLASS": risk.value, "RISK_POLICY_ALLOWED": decision.RISK_POLICY_ALLOWED},
            "AUTHORITY_RESULT": {
                "EFFECTIVE_AUTHORITY": auth_result["EFFECTIVE_AUTHORITY"],
                "EFFECTIVE_AUTHORITY_GRANTED": auth_result["EFFECTIVE_AUTHORITY_GRANTED"],
                "PRINCIPAL_BOUND": auth_result["PRINCIPAL_BOUND"],
                "principal": principal,
                "AUTHORITY_SOURCE": auth_result["AUTHORITY_SOURCE"],
            },
            "DENIAL_REASON": auth_result["DENIAL_REASON"],
            "AUTH_RESULT": auth_result,
        }
        policy = self.policy_forwarding(
            contract, req.action, risk, decision.EFFECTIVE_AUTHORITY_GRANTED, evidence=policy_evidence
        )
        mapped = self.task_mapping(req, risk.value)
        plan = {
            "PATH": list(PATH),
            "STEPS": ["dry-run-ucp", "verify", "receipt"],
            "EXECUTE": False,
        }
        ucp_result = self.ucp.submit(mapped["intent"])
        verification = {
            "VERIFIED": True,
            "EXECUTED": False,
            "mode": "dry-run",
            "plan": policy.get("VERIFICATION_PLAN"),
        }
        tools = mcp_bridge.route_tools(via_control_plane=True, tools_required=list(contract.get("TOOLS_REQUIRED") or []))
        fp = (sem.get("contract") or {}).get("context_fingerprint") or "NOT_APPLICABLE"
        cid = (req.semantic_contract or {}).get("semantic_contract_id") or "NOT_APPLICABLE"
        receipt = self.receipt_mapping(
            req,
            intent=ucp_result["intent"],
            capability_id=req.capability_id,
            semantic_contract_id=cid,
            semantic_fingerprint=fp,
            auth_result=auth_result,
            policy_result=policy,
            status=ucp_result["STATUS"],
        )
        transport = nats_bridge.status()
        result = {
            "A2A_RESULT": ucp_result["STATUS"],
            "NO_OP": ucp_result.get("NO_OP", False),
            "EXECUTED": False,
            "intent": ucp_result["intent"],
            "plan": plan,
            "verification": verification,
            "receipt": receipt,
            "MCP_USED": tools["MCP_USED"],
            "DIRECT_EXECUTED": False,
            "semantic": {k: v for k, v in sem.items() if k != "contract"},
            "message": mapped.get("message"),
            "artifact": mapped.get("artifact"),
            "policy_evidence": policy_evidence,
            "auth_result": auth_result,
            "EFFECTIVE_AUTHORITY_GRANTED": auth_result["EFFECTIVE_AUTHORITY_GRANTED"],
        }
        result.update(transport)
        return result

    def _identity(self, req: A2ARequest) -> None:
        if req.agent_id in FORBIDDEN_PUBLIC_AGENTS:
            raise FailClosed(SEAT_IDENTITY_NOT_PUBLIC_AGENT, req.agent_id)

    def _bound_principal(self, issuer: str | None, issuer_trusted: bool) -> str | None:
        if not issuer or not issuer_trusted:
            return None
        return self.principal_by_issuer.get(issuer)

    def _authenticate(self, req: A2ARequest):
        payload = f"{req.agent_id}:{req.a2a_task_id}:{req.idempotency_key}".encode()
        public = req.signature is None and not req.require_trusted_issuer
        principal = None
        if req.issuer and req.issuer in self.trusted_issuers:
            principal = self.principal_by_issuer.get(req.issuer)
        authorized_scopes = authz.server_scopes_for(
            issuer=req.issuer,
            principal=principal,
            scopes_by_principal=self.scopes_by_principal,
        )
        trust = verify(
            agent_id=req.agent_id,
            payload=payload,
            signature=req.signature,
            issuer=req.issuer,
            trusted_issuers=self.trusted_issuers,
            hmac_secrets=self.hmac_secrets,
            required_scope=authz.required_scope_token(req.capability_id),
            authorized_scopes=authorized_scopes,
            allow_unauthenticated_public=public and req.capability_id == capmod.CAPABILITY_NOOP,
        )
        if req.require_trusted_issuer:
            require_trusted(trust)
        if req.capability_id != capmod.CAPABILITY_NOOP and not trust.SIGNATURE_VALID:
            raise FailClosed(AUTH_FAILED)
        return trust

    def _resolve_capability(self, req: A2ARequest, trust) -> dict[str, Any]:
        allow_non_public = trust.SIGNATURE_VALID
        return capmod.require_authorized(req.capability_id, allow_non_public=allow_non_public)

    def semantic_context_validation(self, incoming: dict[str, Any] | None, *, required: bool) -> dict[str, Any]:
        sem = self.semantics.require(incoming, required=required)
        if required and not sem.get("SEMANTIC_EXECUTION_ALLOWED"):
            from .failclosed import SEMANTIC_CONTRACT_UNKNOWN

            raise FailClosed(SEMANTIC_CONTRACT_UNKNOWN)
        return sem

    def policy_forwarding(
        self,
        capability: dict[str, Any],
        action: str,
        risk,
        effective_authority: bool,
        evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return policy_bridge.evaluate(
            capability=capability,
            action=action,
            risk=risk,
            effective_authority=effective_authority,
            evidence=evidence,
        )

    def task_mapping(self, req: A2ARequest, risk_class: str) -> dict[str, Any]:
        intent = task_bridge.build_intent(
            a2a_task_id=req.a2a_task_id,
            a2a_context_id=req.a2a_context_id,
            actor=req.agent_id,
            capability_id=req.capability_id,
            desired_state=req.desired_state,
            risk_class=risk_class,
            idempotency_key=req.idempotency_key,
        )
        message = task_bridge.map_message(
            a2a_message_id=req.a2a_message_id or req.a2a_task_id,
            a2a_context_id=req.a2a_context_id,
        )
        artifact = None
        if req.a2a_artifact_id:
            artifact = task_bridge.map_artifact(
                a2a_artifact_id=req.a2a_artifact_id,
                a2a_task_id=req.a2a_task_id,
                a2a_context_id=req.a2a_context_id,
            )
        return {"intent": intent, "message": message, "artifact": artifact}

    def receipt_mapping(
        self,
        req: A2ARequest,
        *,
        intent: dict[str, Any],
        capability_id: str,
        semantic_contract_id: str,
        semantic_fingerprint: str,
        auth_result: dict[str, Any],
        policy_result: dict[str, Any],
        status: str,
    ) -> dict[str, Any]:
        return receipt_bridge.build_receipt(
            a2a_task_id=req.a2a_task_id,
            a2a_context_id=req.a2a_context_id,
            intent=intent,
            capability_id=capability_id,
            semantic_contract_id=semantic_contract_id,
            semantic_fingerprint=semantic_fingerprint,
            auth_result=auth_result,
            policy_result=policy_result,
            status=status,
            evidence_refs=["raios.a2a.foundation", receipt_bridge.EXISTING_RECEIPT_DIR],
        )


def forbidden_direct_execute(_req: A2ARequest) -> None:
    """Deliberately uncallable business path. Tests assert it remains forbidden."""
    raise FailClosed(DIRECT_EXECUTION_PATH_FORBIDDEN)


def sign_extended_card_payload(agent_id: str, secret: bytes) -> str:
    return sign_bytes(f"{agent_id}:extended-card".encode(), secret)
