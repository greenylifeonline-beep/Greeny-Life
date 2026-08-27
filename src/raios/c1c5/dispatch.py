"""C1→C5 task dispatcher. Chat remains chat. Execution requires an explicit envelope."""

from __future__ import annotations

from typing import Any

from raios.a2a.failclosed import (
    AUTH_FAILED,
    AUTHORITY_REQUIRED,
    CAPABILITY_UNKNOWN,
    RISK_POLICY_DENIED,
    SECRET_LEAK_REJECTED,
    FailClosed,
)
from raios.a2a.policy_bridge import DESTRUCTIVE, evaluate, map_risk
from raios.a2a.ucp_adapter import DryRunUCP
from raios.neuro_lingua.schema import RiskLevel

from . import capabilities, envelope, identity, receipts

MUTATING_INTENTS = DESTRUCTIVE | frozenset({"MUTATE", "WRITE", "EXECUTE_WRITE", "CANONICAL_MUTATION"})
SECRET_KEYS = frozenset(
    {"password", "secret", "token", "api_key", "apikey", "private_key", "authorization", "hmac_secret"}
)
ALLOWED_TARGETS = frozenset({"C5", "C5@AG", "C5-PUBLIC"})
DEFAULT_UCP = DryRunUCP()


def _reject(code: str, detail: str = "", **extra: Any) -> dict[str, Any]:
    out = {
        "KIND": "TASK_DISPATCH",
        "STATUS": "REJECTED",
        "FAIL_CLOSED": code,
        "DETAIL": detail,
        "TASK_BOUND": False,
        "POLICY_CHECKED": extra.pop("POLICY_CHECKED", True),
        "UCP_PATH_USED": False,
        "TOOL_OR_CAPABILITY_INVOKED": False,
        "EXECUTION_COMPLETED": False,
        "BOUND_RECEIPT": False,
        "PROVEN": False,
        "CANONICAL_MUTATION": False,
        "WAL_WRITTEN": False,
    }
    out.update(extra)
    return out


def _secret_leak(parameters: dict[str, Any]) -> bool:
    for key, value in parameters.items():
        lowered = str(key).lower()
        if lowered in SECRET_KEYS or "secret" in lowered or "password" in lowered:
            return True
        text = str(value)
        if "BEGIN PRIVATE KEY" in text or "BEGIN RSA PRIVATE KEY" in text:
            return True
    return False


def maybe_dispatch(text: str, **kwargs: Any) -> dict[str, Any] | None:
    if not envelope.looks_like_envelope(text):
        return None
    return dispatch(text, **kwargs)


def dispatch(
    text: str,
    *,
    session: dict[str, Any] | None = None,
    ucp: DryRunUCP | None = None,
    health: capabilities.HealthFn | None = None,
    receipt_dir=None,
    persist_receipt: bool = True,
    channel_attested: bool = False,
) -> dict[str, Any]:
    parsed = envelope.parse(text)
    if parsed is None:
        return {
            "KIND": "NOT_A_TASK",
            "TASK_BOUND": False,
            "PROVEN": False,
            "BOUND_RECEIPT": False,
        }
    try:
        envelope.require_fields(parsed)
    except ValueError as exc:
        return _reject(envelope.MALFORMED, str(exc), POLICY_CHECKED=False)

    if _secret_leak(parsed.get("parameters") or {}):
        return _reject(SECRET_LEAK_REJECTED, POLICY_CHECKED=True)

    try:
        auth = identity.bind_founder(
            actor=str(parsed.get("actor") or ""),
            authority_context_reference=str(parsed.get("authority_context_reference") or ""),
            env=parsed,
            session=session,
            channel_attested=channel_attested,
            founder_binding_hex=str(parsed.get("founder_binding") or ""),
        )
    except PermissionError:
        return _reject(AUTH_FAILED, "authority_context_reference is not a server-side founder bind")

    cap_id = str(parsed.get("requested_capability") or "")
    try:
        contract = capabilities.get_contract(cap_id)
    except ValueError:
        return _reject(CAPABILITY_UNKNOWN, cap_id)

    intent = str(parsed.get("intent") or "").upper()
    writes_allowed = bool(parsed.get("writes_allowed"))
    if intent in MUTATING_INTENTS and not writes_allowed:
        return _reject(RISK_POLICY_DENIED, "writes_allowed=false with mutating intent")
    if writes_allowed:
        return _reject(RISK_POLICY_DENIED, "mutating writes are not authorized in this dispatcher")
    if str(parsed.get("mode") or "").upper() not in {"READ_ONLY", "NOOP"}:
        return _reject(RISK_POLICY_DENIED, "only READ_ONLY/NOOP modes are authorized")
    if str(parsed.get("target") or "") not in ALLOWED_TARGETS:
        return _reject(RISK_POLICY_DENIED, "target not C5")

    risk = map_risk(str(parsed.get("risk_class") or ""), str(contract.get("RISK_CLASS") or "LOW"))
    if risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        return _reject(AUTHORITY_REQUIRED, risk.value)

    try:
        policy = evaluate(
            capability=contract,
            action=intent,
            risk=risk,
            effective_authority=True,
            target_allowed=True,
            evidence={"AUTH_PRINCIPAL": auth["PRINCIPAL"], "AUTHORITY_SOURCE": auth["AUTHORITY_SOURCE"]},
        )
    except FailClosed as exc:
        return _reject(exc.code, str(exc))

    plane = ucp or DEFAULT_UCP
    ucp_intent = {
        "IDEMPOTENCY_KEY": parsed["idempotency_key"],
        "COMMAND_ID": parsed["task_id"],
        "CHANGE_ID": parsed["task_id"],
        "CORRELATION_ID": parsed["correlation_id"],
        "ACTOR": auth["PRINCIPAL"],
        "TARGET_SELECTOR": parsed["target"],
        "INTENT": intent,
        "DESIRED_STATE": {
            "capability": cap_id,
            "mode": parsed["mode"],
            "parameters": parsed.get("parameters") or {},
        },
    }
    ucp_result = plane.submit(ucp_intent)
    already = bool(ucp_result.get("NO_OP") or ucp_result.get("STATUS") == "ALREADY_APPLIED")

    invoked = None
    if not already:
        invoked = capabilities.invoke(cap_id, health=health)
        live = bool((invoked.get("result") or {}).get("LIVE"))
        status = "COMPLETED" if live or health is not None else "COMPLETED_OFFLINE_STUB"
        if health is None and not live:
            status = "COMPLETED_TARGET_UNREACHABLE"
    else:
        status = "ALREADY_APPLIED"

    receipt = receipts.build(
        env=parsed,
        auth=auth,
        policy=policy,
        ucp=ucp_result,
        capability=invoked,
        status=status,
    )
    receipt_path = None
    if persist_receipt:
        existing_path = receipts.receipt_path(str(parsed["idempotency_key"]), directory=receipt_dir)
        if already and existing_path.is_file():
            receipt_path = existing_path
            loaded = receipts.load(str(parsed["idempotency_key"]), directory=receipt_dir)
            if loaded:
                receipt = loaded
        else:
            receipt_path = receipts.persist(receipt, directory=receipt_dir)
    bound = receipts.is_bound(receipt_path)
    proven = bound and status in {"COMPLETED", "ALREADY_APPLIED", "COMPLETED_OFFLINE_STUB", "COMPLETED_TARGET_UNREACHABLE"}
    if status == "COMPLETED_TARGET_UNREACHABLE":
        proven = False

    return {
        "KIND": "TASK_DISPATCH",
        "STATUS": status,
        "TASK_BOUND": True,
        "TASK_ID": parsed["task_id"],
        "CORRELATION_ID": parsed["correlation_id"],
        "IDEMPOTENCY_KEY": parsed["idempotency_key"],
        "POLICY_CHECKED": True,
        "POLICY_RESULT": policy.get("POLICY_RESULT"),
        "UCP_PATH_USED": True,
        "UCP_ADAPTER": "src/raios/a2a/ucp_adapter.py:DryRunUCP",
        "UCP_CONTROL_PLANE": ".ai-os/control/RAIOS-CONTROL-PLANE-V1.py",
        "UCP_STATUS": ucp_result.get("STATUS"),
        "SECOND_EXECUTION_NO_OP": already,
        "ALREADY_APPLIED": already,
        "TOOL_OR_CAPABILITY_INVOKED": bool(invoked and invoked.get("INVOKED")),
        "EXECUTION_COMPLETED": status in {"COMPLETED", "COMPLETED_OFFLINE_STUB", "ALREADY_APPLIED"},
        "BOUND_RECEIPT": bound,
        "RECEIPT_PATH": str(receipt_path) if receipt_path else None,
        "RECEIPT": receipt,
        "AUTH": auth,
        "CAPABILITY": invoked,
        "PROVEN": proven,
        "CANONICAL_MUTATION": False,
        "WAL_WRITTEN": False,
        "COMMAND_FABRIC_E2E_PROVEN": False,
        "HTTP_PRIMARY": True,
        "NATS_PRIMARY": False,
    }
