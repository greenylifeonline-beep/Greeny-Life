"""Server-side A2A authority. Caller self-assertion is request data only.

Reuses:
- trusted issuer registry (Gateway.trusted_issuers / trust.py)
- NeuroLingua RiskLevel + policy_bridge (no second policy engine)
- existing FailClosed AUTHORITY_REQUIRED / RISK_POLICY_DENIED
- Unified Control Plane remains the execution authority; this module only
  derives EFFECTIVE_AUTHORITY_GRANTED for the UCP dry-run adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from raios.neuro_lingua.schema import RiskLevel

from .failclosed import AUTH_SCOPE_MISSING, AUTHORITY_REQUIRED, CAPABILITY_NOT_AUTHORIZED, FailClosed
from .policy_bridge import DESTRUCTIVE

# Capability -> server-side scopes that may invoke it. Public noop requires none.
CAPABILITY_REQUIRED_SCOPES: dict[str, frozenset[str]] = {
    "raios.foundation.noop_intent": frozenset(),
    "raios.foundation.high_risk_mutate": frozenset({"raios.a2a.high_risk"}),
    "raios.foundation.critical_delete": frozenset({"raios.a2a.destructive"}),
}

CALLER_AUTHORITY_FIELDS = (
    "authority",
    "authority_class",
    "authority_present",
    "role",
    "admin",
    "is_authorized",
    "scope",
    "granted_scopes",
    "trusted",
    "privileged",
    "requested_authority",
    "requested_role",
)

REUSED_AUTHORITY_SOURCES = (
    "src/raios/a2a/trust.py:trusted_issuers",
    "src/raios/a2a/authority.py:principal_by_issuer+scopes_by_principal+high_risk_principals+high_risk_task_grants",
    "src/raios/neuro_lingua/schema.py:RiskLevel",
    "src/raios/a2a/policy_bridge.py",
    ".ai-os/control/RAIOS-CONTROL-PLANE-V1.py:DryRunUCP wrap (no A2A authority DB)",
)

AUTHORITY_SOURCE_NONE = "NONE"
AUTHORITY_SOURCE_NOT_REQUIRED = "NOT_REQUIRED"
AUTHORITY_SOURCE_SERVER_SCOPE_MAP = "SERVER_SIDE_SCOPE_MAP"
AUTHORITY_SOURCE_C1_TASK_GATE = "EXPLICIT_C1_TASK_GATE"


@dataclass(frozen=True)
class AuthorityDecision:
    SIGNATURE_VALID: bool
    ISSUER_IDENTIFIED: bool
    ISSUER_TRUSTED: bool
    PRINCIPAL_BOUND: bool
    AUTHORIZED_SCOPES: tuple[str, ...]
    AUTHORIZED_SCOPE_PRESENT: bool
    SCOPE_AUTHORIZED: bool
    CAPABILITY_AUTHORIZED: bool
    RISK_POLICY_ALLOWED: bool
    EFFECTIVE_AUTHORITY: bool
    EFFECTIVE_AUTHORITY_GRANTED: bool
    AUTHORITY_SOURCE: str
    DENIAL_REASON: str | None
    principal: str | None
    issuer: str | None
    REQUESTED_AUTHORITY: dict[str, Any] = field(default_factory=dict)
    AUTHORITY_SOURCE_PROVENANCE: dict[str, Any] = field(default_factory=dict)

    def as_auth_result(self) -> dict[str, Any]:
        """Single serialized auth state for policy, receipt, and evidence."""
        return {
            "SIGNATURE_VALID": self.SIGNATURE_VALID,
            "ISSUER_IDENTIFIED": self.ISSUER_IDENTIFIED,
            "ISSUER_TRUSTED": self.ISSUER_TRUSTED,
            "SCOPE_AUTHORIZED": self.SCOPE_AUTHORIZED,
            "TRUSTED_ORGANIZATION": False,
            "PRINCIPAL_BOUND": self.PRINCIPAL_BOUND,
            "AUTHORIZED_SCOPES": list(self.AUTHORIZED_SCOPES),
            "CAPABILITY_AUTHORIZED": self.CAPABILITY_AUTHORIZED,
            "EFFECTIVE_AUTHORITY": self.EFFECTIVE_AUTHORITY,
            "EFFECTIVE_AUTHORITY_GRANTED": self.EFFECTIVE_AUTHORITY_GRANTED,
            "AUTHORITY_SOURCE": self.AUTHORITY_SOURCE,
            "AUTHORITY_SOURCE_PROVENANCE": dict(self.AUTHORITY_SOURCE_PROVENANCE),
            "DENIAL_REASON": self.DENIAL_REASON,
        }

    def as_evidence(self) -> dict[str, Any]:
        return self.as_auth_result()


def requested_authority_snapshot(
    *,
    authority_present: bool,
    granted_scopes: tuple[str, ...],
    requested_authority: str | None,
    requested_role: str | None,
) -> dict[str, Any]:
    """Record caller claims. Never used as grants."""
    return {
        "authority_present": bool(authority_present),
        "granted_scopes": list(granted_scopes),
        "requested_authority": requested_authority,
        "requested_role": requested_role,
        "NOTE": "REQUEST_DATA_ONLY; REQUESTED_AUTHORITY!=GRANTED_AUTHORITY",
    }


def server_scopes_for(*, issuer: str | None, principal: str | None, scopes_by_principal: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    if not principal:
        return ()
    return tuple(scopes_by_principal.get(principal) or ())


def capability_allowed_for_scopes(capability_id: str, scopes: tuple[str, ...]) -> bool:
    required = CAPABILITY_REQUIRED_SCOPES.get(capability_id)
    if required is None:
        return False
    if not required:
        return True
    return bool(required & set(scopes))


def required_scope_token(capability_id: str) -> str:
    """Server-side scope token for the capability. Never a caller claim."""
    required = CAPABILITY_REQUIRED_SCOPES.get(capability_id) or frozenset()
    if not required:
        return "raios.a2a.task"
    return sorted(required)[0]


def task_gate_granted(
    *,
    principal: str | None,
    task_id: str | None,
    high_risk_principals: frozenset[str],
    high_risk_task_grants: dict[str, tuple[str, ...]] | None,
) -> bool:
    """Principal membership is eligibility only. Grant is (principal, task_id)."""
    if not principal or principal not in high_risk_principals:
        return False
    if not task_id:
        return False
    allowed = (high_risk_task_grants or {}).get(principal) or ()
    return task_id in allowed


def derive(
    *,
    capability_id: str,
    action: str,
    risk: RiskLevel,
    side_effects: bool,
    signature_valid: bool,
    issuer_identified: bool,
    issuer_trusted: bool,
    issuer: str | None,
    principal: str | None,
    authorized_scopes: tuple[str, ...],
    high_risk_principals: frozenset[str],
    requested: dict[str, Any],
    task_id: str | None = None,
    high_risk_task_grants: dict[str, tuple[str, ...]] | None = None,
) -> AuthorityDecision:
    principal_bound = bool(principal)
    scope_present = bool(authorized_scopes)
    cap_ok = capability_allowed_for_scopes(capability_id, authorized_scopes)
    needs_authority = needs_server_authority(action, risk, side_effects=side_effects)
    # Caller claims never satisfy the gate.
    _ = requested
    principal_eligible = bool(principal and principal in high_risk_principals)
    server_high_risk = task_gate_granted(
        principal=principal,
        task_id=task_id,
        high_risk_principals=high_risk_principals,
        high_risk_task_grants=high_risk_task_grants,
    )
    # SCOPE_AUTHORIZED is server-side capability coverage, never TrustResult's generic token.
    scope_authorized = bool(issuer_trusted and principal_bound and cap_ok)
    chain = (
        signature_valid
        and issuer_identified
        and issuer_trusted
        and principal_bound
        and scope_authorized
        and cap_ok
    )
    if needs_authority:
        effective = chain and server_high_risk
        risk_ok = effective
    else:
        effective = False
        risk_ok = True
        if capability_id == "raios.foundation.noop_intent":
            risk_ok = True
        elif chain:
            risk_ok = True

    denial = None
    if needs_authority and not issuer_trusted and signature_valid:
        denial = "UNTRUSTED_ISSUER"
    elif needs_authority and issuer_trusted and not scope_present:
        denial = AUTH_SCOPE_MISSING
    elif needs_authority and issuer_trusted and not cap_ok:
        denial = CAPABILITY_NOT_AUTHORIZED
    elif needs_authority and not effective:
        denial = AUTHORITY_REQUIRED

    granted = bool(effective) if needs_authority else False
    # Protected grant cannot report SCOPE_AUTHORIZED=false.
    if granted and (not scope_authorized or not cap_ok):
        granted = False
        risk_ok = False
        denial = AUTH_SCOPE_MISSING if not scope_authorized else CAPABILITY_NOT_AUTHORIZED

    if not needs_authority:
        authority_source = AUTHORITY_SOURCE_NOT_REQUIRED
    elif granted and server_high_risk:
        authority_source = AUTHORITY_SOURCE_C1_TASK_GATE
    elif scope_authorized:
        authority_source = AUTHORITY_SOURCE_SERVER_SCOPE_MAP
    else:
        authority_source = AUTHORITY_SOURCE_NONE

    provenance = {
        "principal": principal,
        "issuer": issuer,
        "server_scopes": list(authorized_scopes),
        "principal_eligible_for_task_gate": principal_eligible,
        "c1_task_gate": bool(server_high_risk),
        "task_scoped": bool(server_high_risk),
        "granted_task_id": task_id if server_high_risk else None,
        "task_id": task_id,
        "NOTE": "SERVER_SIDE_ONLY; EXPLICIT_C1_TASK_GATE requires (principal, a2a_task_id) grant; caller granted_scopes/role/admin ignored",
    }

    return AuthorityDecision(
        SIGNATURE_VALID=signature_valid,
        ISSUER_IDENTIFIED=issuer_identified,
        ISSUER_TRUSTED=issuer_trusted,
        PRINCIPAL_BOUND=principal_bound,
        AUTHORIZED_SCOPES=authorized_scopes,
        AUTHORIZED_SCOPE_PRESENT=scope_present,
        SCOPE_AUTHORIZED=scope_authorized,
        CAPABILITY_AUTHORIZED=cap_ok,
        RISK_POLICY_ALLOWED=risk_ok,
        EFFECTIVE_AUTHORITY=granted,
        EFFECTIVE_AUTHORITY_GRANTED=granted,
        AUTHORITY_SOURCE=authority_source,
        DENIAL_REASON=denial,
        principal=principal,
        issuer=issuer,
        REQUESTED_AUTHORITY=dict(requested),
        AUTHORITY_SOURCE_PROVENANCE=provenance,
    )


def require_for_policy(decision: AuthorityDecision, *, needs_authority: bool) -> None:
    if not needs_authority:
        return
    if decision.DENIAL_REASON == AUTH_SCOPE_MISSING:
        raise FailClosed(AUTH_SCOPE_MISSING)
    if decision.DENIAL_REASON == CAPABILITY_NOT_AUTHORIZED:
        raise FailClosed(CAPABILITY_NOT_AUTHORIZED)
    if not decision.EFFECTIVE_AUTHORITY_GRANTED:
        raise FailClosed(AUTHORITY_REQUIRED, decision.DENIAL_REASON or "server-side")


def needs_server_authority(action: str, risk: RiskLevel, *, side_effects: bool) -> bool:
    action_u = (action or "").upper()
    if action_u in DESTRUCTIVE:
        return True
    if risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        return True
    return bool(side_effects) and risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)
