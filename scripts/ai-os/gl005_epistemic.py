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
