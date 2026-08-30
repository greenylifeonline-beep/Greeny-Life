"""Stage-0 fabric discovery: no Challenge, no new fabric, auth and routing unproven."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / ".ai-os" / "receipts" / "command-fabric" / "D083-STAGE0-FABRIC-DISCOVERY.json"


def test_d083_does_not_run_challenge_or_flip_sovereign_flags():
    rec = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert rec["stage"] == 0
    assert rec["challenge_run"] is False
    assert rec["C2_SESSION_STATUS"] == "ACTIVE"
    assert rec["C2_ENDPOINT"] == ""
    assert rec["C2_CALLBACK_CAPABILITY"] is False
    assert rec["C2_CAN_RETURN_TO_AG"] == "UNPROVEN"
    assert rec["CHANGE_CLASS"] == "FORWARDER_ONLY"
    assert rec["FILES_TOUCHED"] == []
    assert rec["CROSS_HOST_AUTH_PROVEN"] is False
    assert rec["NEW_BUILD_REQUIRED"] is False
    assert rec["PATCH_EXISTING"] is False
    assert rec["ROUND_TRIP_1_VERDICT"] == "NOT_RUN"
    assert rec["PORT_FORWARD_8787_PROVEN"] is False
    assert rec["C2_JOIN_PROVEN"] is False
    assert rec["COMMAND_FABRIC_E2E_PROVEN"] is False
    assert rec["CROSS_HOST_ROUND_TRIP_PROVEN"] is False
    assert rec["WAL_WRITTEN"] is False
    assert rec["GL005_PROVEN"] is False
    assert rec["secrets_present"] is False
    blob = json.dumps(rec)
    assert "sk-" not in blob
    assert "Bearer " not in blob
