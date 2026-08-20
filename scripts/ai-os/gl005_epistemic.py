#!/usr/bin/env python3
"""GL-005 mutation epistemic contract. DISCOVERED, not CANONICAL. Never grants PASS."""
from __future__ import annotations

from typing import Any, Iterable

LAWS = (
    "STALE_FAILURE_CAUSE_MUST_NOT_DRIVE_NEW_INFRASTRUCTURE",
    "HTTP_2XX_NE_SEMANTIC_SUCCESS",
    "READ_PATH_PROVEN_NE_ORCHESTRATION_DEMONSTRATED",
    "AUTH_GATE_PRESENT_NE_MUTATION_EXECUTED",
    "AUTH_BLOCKED_NE_CAPABILITY_ABSENT",
    "MUTATION_CLAIM_REQUIRES_OBSERVED_BEFORE_AFTER_DIFFERENCE",
    "RETURNED_SUCCESS_NE_DURABLE_OBSERVABILITY",
    "BOARD_HEAD_NE_GIT_HEAD",
    "PRINTED_PASS_NE_EVIDENCE",
    "POST_401_NE_STATE_TRANSITION",
    "AUTH_GATE_PRESENT_NE_AUTHENTICATED_MUTATION",
    "PASS_CANDIDATE_NE_GL005_PROVEN",
    "EMPTY_PASSWORD_NE_IDENTITY",
    "PASSWORD_VALUE_MUST_NOT_BE_PRINTED",
    "CREDENTIAL_MANUFACTURE_NE_EXISTING_SESSION",
    "PROVISION_ADMIN_NE_ORCHESTRATION_PROOF",
    "LOGIN_HTTP_200_NE_SIGNED_SESSION",
    "CLI_HASH_MATCH_NE_RUNTIME_SESSION",
    "DOCUMENTED_PROVISION_NE_ORCHESTRATION",
    "SECURE_COOKIE_NE_HTTP_SESSION",
    "COOKIE_TRANSPORT_MISMATCH_NE_CREDENTIAL_FAILURE",
    "COOKIE_TRANSPORT_MISMATCH_NE_DB_BINDING_MISMATCH",
    "COOKIE_TRANSPORT_MISMATCH_NE_GL005_PROVEN",
    "DISABLE_SECURE_FLAG_NE_ORCHESTRATION_PROOF",
    "NODE_ENV_PRODUCTION_NE_HTTPS",
)

OBSERVATION_CHAIN = (
    "BIND_LIVE_RUNTIME",
    "CAPTURE_HEAD_PID_PORT",
    "BEFORE_OBSERVATION",
    "ACTION",
    "SEMANTIC_RESULT",
    "AFTER_OBSERVATION",
    "STATE_DIFF",
    "CHILD_EXITS",
    "RECEIPT_HASH",
    "STALE_EVIDENCE_CHECK",
    "PARENT_FAIL_CLOSED",
)


def classify_post_mutation(
    *,
    post_status: int | None,
    semantic_success: bool,
    before_hash: str | None,
    after_hash: str | None,
    returned_id: str | None,
    after_ids: Iterable[str] | None,
) -> dict[str, Any]:
    """Required invariant. PASS_CANDIDATE still requires falsification review."""
    after_set = {str(x) for x in (after_ids or []) if x}

    if post_status == 401:
        rec = {
            "epistemic": "BLOCKED",
            "reason": "AUTH_GATE_PRESENT_IDENTITY_UNAVAILABLE",
            "gl005_proven": False,
            "capability": "PRESENT_BUT_PROTECTED_AND_UNPROVEN",
            "laws": [
                "AUTH_GATE_PRESENT_NE_MUTATION_EXECUTED",
                "AUTH_BLOCKED_NE_CAPABILITY_ABSENT",
                "POST_401_NE_STATE_TRANSITION",
            ],
        }
    elif post_status == 201 and semantic_success:
        if before_hash == after_hash:
            rec = {
                "epistemic": "INVALID_OBSERVATION",
                "reason": "MUTATION_CLAIMED_WITHOUT_OBSERVED_STATE_CHANGE",
                "gl005_proven": False,
                "capability": "CAPABILITY_UNPROVEN",
                "laws": [
                    "MUTATION_CLAIM_REQUIRES_OBSERVED_BEFORE_AFTER_DIFFERENCE",
                    "RETURNED_SUCCESS_NE_DURABLE_OBSERVABILITY",
                ],
            }
        elif not returned_id or str(returned_id) not in after_set:
            rec = {
                "epistemic": "FAILED",
                "reason": "CREATED_ENTITY_NOT_OBSERVABLE_AFTER_MUTATION",
                "gl005_proven": False,
                "capability": "CAPABILITY_BROKEN",
                "laws": ["RETURNED_SUCCESS_NE_DURABLE_OBSERVABILITY"],
            }
        else:
            rec = {
                "epistemic": "PASS_CANDIDATE",
                "reason": "OBSERVED_BEFORE_AFTER_DIFFERENCE_AND_ENTITY_VISIBLE",
                "gl005_proven": False,
                "capability": "CAPABILITY_UNPROVEN",
                "laws": [
                    "PASS_CANDIDATE_NE_GL005_PROVEN",
                    "PRINTED_PASS_NE_EVIDENCE",
                ],
                "requires": "invariant/falsification review",
            }
    else:
        rec = {
            "epistemic": "FAILED",
            "reason": "MUTATION_NOT_IN_PASS_SHAPE",
            "gl005_proven": False,
            "capability": "CAPABILITY_UNPROVEN",
            "laws": ["PARENT_FAIL_CLOSED"],
        }

    rec["post_status"] = post_status
    rec["semantic_success"] = bool(semantic_success)
    rec["returned_id"] = returned_id
    rec["before_hash_equals_after"] = before_hash is not None and before_hash == after_hash
    rec["returned_id_in_after"] = bool(returned_id) and str(returned_id) in after_set
    rec["GL005_PROVEN"] = False
    return rec


def classify_credential_gate(
    *,
    password_length: int,
    password_value_printed: bool,
    login_executed: bool,
    task_mutation_executed: bool,
    thrown: str | None = None,
) -> dict[str, Any]:
    """Pre-POST identity gate. Manufacturing a password is not an existing session."""
    if password_value_printed:
        rec = {
            "epistemic": "INVALID_OBSERVATION",
            "reason": "PASSWORD_VALUE_PRINTED",
            "capability": "CAPABILITY_UNPROVEN",
            "laws": ["PASSWORD_VALUE_MUST_NOT_BE_PRINTED"],
        }
    elif thrown == "NEW_PASSWORD_TOO_SHORT" or password_length < 14:
        rec = {
            "epistemic": "BLOCKED",
            "reason": "NEW_PASSWORD_TOO_SHORT",
            "capability": "PRESENT_BUT_PROTECTED_AND_UNPROVEN",
            "laws": [
                "EMPTY_PASSWORD_NE_IDENTITY",
                "CREDENTIAL_MANUFACTURE_NE_EXISTING_SESSION",
                "AUTH_BLOCKED_NE_CAPABILITY_ABSENT",
            ],
        }
    elif not login_executed:
        rec = {
            "epistemic": "BLOCKED",
            "reason": "LOGIN_NOT_EXECUTED",
            "capability": "PRESENT_BUT_PROTECTED_AND_UNPROVEN",
            "laws": ["AUTH_GATE_PRESENT_NE_MUTATION_EXECUTED"],
        }
    elif not task_mutation_executed:
        rec = {
            "epistemic": "BLOCKED",
            "reason": "AUTHENTICATED_MUTATION_NOT_EXECUTED",
            "capability": "PRESENT_BUT_PROTECTED_AND_UNPROVEN",
            "laws": ["AUTH_GATE_PRESENT_NE_MUTATION_EXECUTED"],
        }
    else:
        rec = {
            "epistemic": "FAILED",
            "reason": "CREDENTIAL_GATE_IS_NOT_MUTATION_PROOF",
            "capability": "CAPABILITY_UNPROVEN",
            "laws": ["PROVISION_ADMIN_NE_ORCHESTRATION_PROOF"],
        }
    rec.update(
        {
            "password_length": password_length,
            "password_value_printed": bool(password_value_printed),
            "login_executed": bool(login_executed),
            "task_mutation_executed": bool(task_mutation_executed),
            "thrown": thrown,
            "gl005_proven": False,
            "GL005_PROVEN": False,
        }
    )
    return rec


def classify_login_session(
    *,
    login_http: int | None,
    login_success: bool,
    session_http: int | None,
    authenticated: bool,
    signed_admin_session_printed: bool,
    atomic_login_proven_printed: bool,
    task_mutation_executed: bool,
    session_role: str | None = None,
    secure_gl_session_count: int | None = None,
    session_over_http: bool | None = None,
) -> dict[str, Any]:
    """Login HTTP 200 is not a signed session. Printed PROVEN is not evidence."""
    write_roles = {"ADMIN", "WAREHOUSE", "EXPORT"}
    cookie_transport = (
        login_http == 200
        and login_success
        and authenticated is False
        and (secure_gl_session_count or 0) >= 1
        and session_over_http is True
    )
    if task_mutation_executed:
        rec = {
            "epistemic": "FAILED",
            "reason": "MUTATION_CLAIMED_WITHOUT_SESSION_BIND_CLASSIFIER",
            "capability": "CAPABILITY_UNPROVEN",
            "laws": ["AUTH_GATE_PRESENT_NE_MUTATION_EXECUTED"],
        }
    elif login_http == 200 and login_success and session_http == 200 and authenticated is True:
        rec = {
            "epistemic": "SESSION_BOUND_CANDIDATE" if (session_role or "").upper() in write_roles else "BLOCKED",
            "reason": "SIGNED_SESSION_OBSERVED" if (session_role or "").upper() in write_roles else "SESSION_ROLE_NOT_WRITE",
            "capability": "PRESENT_BUT_PROTECTED_AND_UNPROVEN",
            "laws": ["PASS_CANDIDATE_NE_GL005_PROVEN"],
        }
    elif cookie_transport:
        rec = {
            "epistemic": "FAILED",
            "reason": "SECURE_SESSION_COOKIE_NOT_USABLE_OVER_CURRENT_HTTP_RUNTIME",
            "capability": "PRESENT_BUT_PROTECTED_AND_UNPROVEN",
            "laws": [
                "SECURE_COOKIE_NE_HTTP_SESSION",
                "COOKIE_TRANSPORT_MISMATCH_NE_CREDENTIAL_FAILURE",
                "COOKIE_TRANSPORT_MISMATCH_NE_DB_BINDING_MISMATCH",
                "COOKIE_TRANSPORT_MISMATCH_NE_GL005_PROVEN",
                "LOGIN_HTTP_200_NE_SIGNED_SESSION",
                "HTTP_2XX_NE_SEMANTIC_SUCCESS",
                "PRINTED_PASS_NE_EVIDENCE",
                "DISABLE_SECURE_FLAG_NE_ORCHESTRATION_PROOF",
                "NODE_ENV_PRODUCTION_NE_HTTPS",
            ],
        }
    elif login_http == 200 and login_success and authenticated is False:
        rec = {
            "epistemic": "FAILED",
            "reason": "LOGIN_HTTP_200_NE_SIGNED_SESSION",
            "capability": "PRESENT_BUT_PROTECTED_AND_UNPROVEN",
            "laws": [
                "LOGIN_HTTP_200_NE_SIGNED_SESSION",
                "CLI_HASH_MATCH_NE_RUNTIME_SESSION",
                "HTTP_2XX_NE_SEMANTIC_SUCCESS",
                "PRINTED_PASS_NE_EVIDENCE",
            ],
        }
    elif login_http == 401:
        rec = {
            "epistemic": "BLOCKED",
            "reason": "AUTH_GATE_PRESENT_IDENTITY_UNAVAILABLE",
            "capability": "PRESENT_BUT_PROTECTED_AND_UNPROVEN",
            "laws": ["AUTH_GATE_PRESENT_NE_MUTATION_EXECUTED"],
        }
    else:
        rec = {
            "epistemic": "FAILED",
            "reason": "LOGIN_SESSION_NOT_IN_PASS_SHAPE",
            "capability": "CAPABILITY_UNPROVEN",
            "laws": ["PARENT_FAIL_CLOSED"],
        }
    rec.update(
        {
            "login_http": login_http,
            "login_success": bool(login_success),
            "session_http": session_http,
            "authenticated": bool(authenticated),
            "session_role": session_role,
            "atomic_login_proven_printed": bool(atomic_login_proven_printed),
            "signed_admin_session_printed": bool(signed_admin_session_printed),
            "printed_atomic_login_proven_falsified": bool(atomic_login_proven_printed) and authenticated is False,
            "task_mutation_executed": bool(task_mutation_executed),
            "secure_gl_session_count": secure_gl_session_count,
            "session_over_http": session_over_http,
            "cookie_transport_mismatch": (
                "PROVEN_CANDIDATE" if cookie_transport else None
            ),
            "gl005_proven": False,
            "GL005_PROVEN": False,
        }
    )
    return rec


def classify_cookie_transport(
    *,
    login_http: int | None,
    login_success: bool,
    session_http: int | None,
    authenticated: bool,
    secure_gl_session_count: int,
    session_over_http: bool,
    cookie_transport_mismatch_printed: str | None,
    db_binding_mismatch: str | None,
    credential_failure: str | None,
    task_mutation_executed: bool,
    password_retained: bool,
    evidence_mutation_executed: bool,
    gl005_proven_printed: bool,
) -> dict[str, Any]:
    """Secure cookie on HTTP is a transport candidate, not a session and not GL-005."""
    printed = (cookie_transport_mismatch_printed or "").strip().upper()
    if password_retained:
        rec = {
            "epistemic": "INVALID_OBSERVATION",
            "reason": "PASSWORD_RETAINED",
            "capability": "CAPABILITY_UNPROVEN",
            "laws": ["PASSWORD_VALUE_MUST_NOT_BE_PRINTED"],
        }
    elif evidence_mutation_executed or task_mutation_executed:
        rec = {
            "epistemic": "FAILED",
            "reason": "MUTATION_CLAIMED_WITHOUT_BOUND_SESSION",
            "capability": "CAPABILITY_UNPROVEN",
            "laws": ["AUTH_GATE_PRESENT_NE_MUTATION_EXECUTED"],
        }
    elif gl005_proven_printed:
        rec = {
            "epistemic": "INVALID_OBSERVATION",
            "reason": "PRINTED_GL005_PROVEN_WITHOUT_MUTATION",
            "capability": "CAPABILITY_UNPROVEN",
            "laws": ["PRINTED_PASS_NE_EVIDENCE", "COOKIE_TRANSPORT_MISMATCH_NE_GL005_PROVEN"],
        }
    else:
        rec = classify_login_session(
            login_http=login_http,
            login_success=login_success,
            session_http=session_http,
            authenticated=authenticated,
            signed_admin_session_printed=False,
            atomic_login_proven_printed=False,
            task_mutation_executed=False,
            secure_gl_session_count=secure_gl_session_count,
            session_over_http=session_over_http,
        )
        rec["db_binding_mismatch"] = db_binding_mismatch
        rec["credential_failure"] = credential_failure
        rec["cookie_transport_mismatch_printed"] = cookie_transport_mismatch_printed
        rec["printed_cookie_transport_mismatch_is_not_gl005"] = printed in {
            "PROVEN_CANDIDATE",
            "PROVEN",
            "TRUE",
        }
        rec["password_retained"] = bool(password_retained)
        rec["evidence_mutation_executed"] = bool(evidence_mutation_executed)
        rec["task_mutation_executed"] = bool(task_mutation_executed)
        rec["gl005_proven_printed"] = bool(gl005_proven_printed)
        rec["gl005_proven"] = False
        rec["GL005_PROVEN"] = False
        return rec
    rec.update(
        {
            "login_http": login_http,
            "login_success": bool(login_success),
            "session_http": session_http,
            "authenticated": bool(authenticated),
            "secure_gl_session_count": secure_gl_session_count,
            "session_over_http": bool(session_over_http),
            "cookie_transport_mismatch_printed": cookie_transport_mismatch_printed,
            "db_binding_mismatch": db_binding_mismatch,
            "credential_failure": credential_failure,
            "password_retained": bool(password_retained),
            "evidence_mutation_executed": bool(evidence_mutation_executed),
            "task_mutation_executed": bool(task_mutation_executed),
            "gl005_proven_printed": bool(gl005_proven_printed),
            "gl005_proven": False,
            "GL005_PROVEN": False,
        }
    )
    return rec


def classify_observe_receipt(payload: dict[str, Any]) -> dict[str, Any]:
    action = payload.get("ACTION_PROCESS_EXIT")
    status = None
    semantic_success = False
    returned_id = None
    if isinstance(action, dict):
        status = action.get("status")
        body = action.get("json") or {}
        if not isinstance(body, dict):
            body = {}
        semantic_success = action.get("status") == 201 and body.get("success") is True
        data = body.get("data")
        if isinstance(data, dict) and data.get("id"):
            returned_id = str(data.get("id"))
        elif action.get("entity_id"):
            returned_id = str(action.get("entity_id"))
    elif isinstance(action, int):
        status = action

    after = payload.get("AFTER_STATE") or {}
    after_sem = after.get("semantic") if isinstance(after, dict) else {}
    after_ids = []
    if isinstance(after_sem, dict):
        after_ids = list(after_sem.get("ids") or [])
    if isinstance(after, dict) and after.get("new_ids"):
        after_ids = list(set(after_ids) | set(after.get("new_ids") or []))

    return classify_post_mutation(
        post_status=status if isinstance(status, int) else None,
        semantic_success=semantic_success,
        before_hash=payload.get("BEFORE_HASH"),
        after_hash=payload.get("AFTER_HASH"),
        returned_id=returned_id,
        after_ids=after_ids,
    )


def stale_evidence_check(
    *,
    captured_head: str | None,
    live_head: str | None,
    board_head: str | None,
    prior_receipt_sha256: str | None = None,
) -> dict[str, Any]:
    head_stale = bool(captured_head and live_head and captured_head != live_head)
    board_is_not_git = bool(board_head and live_head and board_head != live_head)
    return {
        "law": "STALE_FAILURE_CAUSE_MUST_NOT_DRIVE_NEW_INFRASTRUCTURE",
        "BOARD_HEAD_NE_GIT_HEAD": True,
        "captured_head": captured_head,
        "live_head": live_head,
        "board_head": board_head,
        "head_stale": head_stale,
        "board_head_diverges_from_git": board_is_not_git,
        "prior_receipt_sha256": prior_receipt_sha256,
        "status": "FAILED" if head_stale else "PASS",
        "exit": 1 if head_stale else 0,
        "note": (
            "Board HEAD is not git HEAD. A printed or board PASS is not evidence. "
            "A stale GET 500 must not drive new infrastructure."
        ),
    }


def parent_fail_closed(children: list[dict[str, Any]], classification: dict[str, Any]) -> dict[str, Any]:
    missing = [c for c in children if c.get("exit") is None]
    failed = [c for c in children if c.get("exit") not in (0, None)]
    blocked = classification.get("epistemic") == "BLOCKED"
    candidate = classification.get("epistemic") == "PASS_CANDIDATE"
    complete = not missing and not failed
    return {
        "name": "PARENT_FAIL_CLOSED",
        "exit": 1,
        "observation_complete": complete,
        "GL005_PROVEN": False,
        "PASS_CANDIDATE_NE_GL005_PROVEN": True,
        "PRINTED_PASS_NE_EVIDENCE": True,
        "missing_children": [c.get("name") for c in missing],
        "failed_children": [c.get("name") for c in failed],
        "epistemic": classification.get("epistemic"),
        "reason": classification.get("reason"),
        "candidate": candidate,
        "blocked": blocked,
        "gate": "GATE_CLOSED",
    }


def chain_child(name: str, *, ok: bool, detail: Any = None, exit_override: int | None = None) -> dict[str, Any]:
    if name not in OBSERVATION_CHAIN:
        raise ValueError("UNKNOWN_CHAIN_STEP:" + name)
    return {
        "name": name,
        "exit": (0 if ok else 1) if exit_override is None else exit_override,
        "detail": detail,
    }
