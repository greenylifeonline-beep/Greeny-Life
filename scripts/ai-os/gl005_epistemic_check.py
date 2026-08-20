#!/usr/bin/env python3
"""Fail-closed checks for GL-005 mutation epistemic contract. Not GL-005 proof."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gl005_epistemic import (  # noqa: E402
    LAWS,
    OBSERVATION_CHAIN,
    classify_observe_receipt,
    classify_post_mutation,
    parent_fail_closed,
    stale_evidence_check,
)


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit("FAIL: " + msg)
    print("ok:", msg)


def main() -> int:
    blocked = classify_post_mutation(
        post_status=401,
        semantic_success=False,
        before_hash="aa",
        after_hash="aa",
        returned_id=None,
        after_ids=[],
    )
    check(blocked["epistemic"] == "BLOCKED", "401 epistemic BLOCKED")
    check(blocked["reason"] == "AUTH_GATE_PRESENT_IDENTITY_UNAVAILABLE", "401 reason")
    check(blocked["gl005_proven"] is False, "401 does not prove")
    check(blocked["capability"] == "PRESENT_BUT_PROTECTED_AND_UNPROVEN", "401 not missing capability")

    invalid = classify_post_mutation(
        post_status=201,
        semantic_success=True,
        before_hash="same",
        after_hash="same",
        returned_id="e1",
        after_ids=["e1"],
    )
    check(invalid["epistemic"] == "INVALID_OBSERVATION", "201 same hash is invalid")
    check(invalid["reason"] == "MUTATION_CLAIMED_WITHOUT_OBSERVED_STATE_CHANGE", "201 same-hash reason")
    check(invalid["GL005_PROVEN"] is False, "invalid observation cannot prove")

    missing = classify_post_mutation(
        post_status=201,
        semantic_success=True,
        before_hash="b",
        after_hash="a",
        returned_id="e1",
        after_ids=["e2"],
    )
    check(missing["epistemic"] == "FAILED", "201 id absent after is FAILED")
    check(missing["reason"] == "CREATED_ENTITY_NOT_OBSERVABLE_AFTER_MUTATION", "missing entity reason")

    candidate = classify_post_mutation(
        post_status=201,
        semantic_success=True,
        before_hash="b",
        after_hash="a",
        returned_id="e1",
        after_ids=["e1"],
    )
    check(candidate["epistemic"] == "PASS_CANDIDATE", "201 + diff + visible id is candidate")
    check(candidate["gl005_proven"] is False, "PASS_CANDIDATE is not GL005_PROVEN")
    check(candidate["requires"] == "invariant/falsification review", "candidate still needs review")

    http2xx = classify_post_mutation(
        post_status=200,
        semantic_success=True,
        before_hash="b",
        after_hash="a",
        returned_id=None,
        after_ids=[],
    )
    check(http2xx["epistemic"] == "FAILED", "HTTP 2xx GET-shape is not mutation PASS")
    check("HTTP_2XX_NE_SEMANTIC_SUCCESS" in LAWS, "HTTP_2XX law present")
    check("READ_PATH_PROVEN_NE_ORCHESTRATION_DEMONSTRATED" in LAWS, "read-path law present")
    check("BOARD_HEAD_NE_GIT_HEAD" in LAWS, "board-head law present")
    check("PRINTED_PASS_NE_EVIDENCE" in LAWS, "printed-pass law present")
    check(len(OBSERVATION_CHAIN) == 11, "observation chain has 11 required steps")
    check(OBSERVATION_CHAIN[0] == "BIND_LIVE_RUNTIME", "chain starts at bind-live-runtime")
    check(OBSERVATION_CHAIN[-1] == "PARENT_FAIL_CLOSED", "chain ends parent fail-closed")

    observe = json.loads((ROOT / ".ai-os" / "receipts" / "GL005-MUTATION-OBSERVE.json").read_text(encoding="utf-8"))
    live = classify_observe_receipt(observe)
    check(live["epistemic"] == "BLOCKED", "existing Instance B observe is BLOCKED")
    check(live["reason"] == "AUTH_GATE_PRESENT_IDENTITY_UNAVAILABLE", "existing observe reason")
    check(observe.get("GL005_PROVEN") is False, "stored observe did not grant proven")

    git_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    board = json.loads((ROOT / ".ai-os" / "board" / "NOW.json").read_text(encoding="utf-8"))
    stale = stale_evidence_check(
        captured_head=observe.get("HEAD"),
        live_head=git_head,
        board_head=board.get("head"),
        prior_receipt_sha256=(ROOT / ".ai-os" / "receipts" / "GL005-MUTATION-OBSERVE.sha256").read_text().strip(),
    )
    check(stale["BOARD_HEAD_NE_GIT_HEAD"] is True, "board HEAD is not git HEAD")
    check("STALE_FAILURE_CAUSE_MUST_NOT_DRIVE_NEW_INFRASTRUCTURE" == stale["law"], "stale-failure law")
    if observe.get("HEAD") != git_head:
        check(stale["head_stale"] is True, "historical observe HEAD diverges from live git")
        check(stale["status"] == "FAILED", "stale HEAD fails stale-evidence check")
    if board.get("head") != git_head:
        check(stale["board_head_diverges_from_git"] is True, "board HEAD currently diverges from git")

    parent = parent_fail_closed(
        [{"name": "BIND_LIVE_RUNTIME", "exit": 0}, {"name": "ACTION", "exit": 0}],
        live,
    )
    check(parent["exit"] == 1, "BLOCKED parent is fail-closed")
    check(parent["GL005_PROVEN"] is False, "parent cannot print PASS")
    check(parent["gate"] == "GATE_CLOSED", "GL-005 gate stays closed")

    parent_cand = parent_fail_closed(
        [{"name": n, "exit": 0} for n in OBSERVATION_CHAIN[:-1]],
        candidate,
    )
    check(parent_cand["exit"] == 1, "PASS_CANDIDATE still fail-closes GL-005 parent")
    check(parent_cand["GL005_PROVEN"] is False, "candidate is not evidence of proven")
    check(parent_cand["observation_complete"] is True, "candidate may complete observation without opening the gate")
    check(parent_cand["gate"] == "GATE_CLOSED", "printed PASS is not the gate")

    print("gl005_epistemic_check: PASS")
    print(json.dumps({"gl005_proven": False, "epistemic": live["epistemic"], "laws": list(LAWS)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
