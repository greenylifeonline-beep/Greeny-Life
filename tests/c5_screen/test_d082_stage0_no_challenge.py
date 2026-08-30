"""Stage 0: no Challenge, no new Command Fabric, sovereign flags stay false."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / ".ai-os" / "receipts" / "command-fabric" / "D082-STAGE0-NO-CHALLENGE.json"


def test_d082_stage0_forbids_challenge_and_new_fabric():
    rec = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert rec["stage"] == 0
    assert rec["challenge_run"] is False
    assert rec["SAFE_TO_BUILD_NEW_COMMAND_FABRIC"] is False
    assert rec["NEW_BUILD_REQUIRED"] is False
    assert rec["MERGE_REQUIRED"] is False
    assert rec["REUSE_EXISTING"] is True
    assert rec["do_not_create_bridge_on_8788"] is True
    assert rec["cloud_mcp_ne_ag_mcp"] is True
    assert rec["powershell_cannot_create_c2_cloud_session"] is True
    assert rec["ag_ports"]["8787"]["status"] == "BLOCKED_ROUTING"
    assert rec["ag_ports"]["8788"]["status"] == "LOCAL_ONLY"
    assert rec["ag_ports"]["8766"]["status"] == "LOCAL_ONLY"
    assert rec["COMMAND_FABRIC_STATUS"] == "PRESENT_NOT_PROVEN"
    assert rec["COMMAND_FABRIC_PROVEN"] is False
    assert rec["INTERNAL_COMMS_PROVEN"] is False
    assert rec["EXTERNAL_COMMS_PROVEN"] is False
    assert rec["PORT_FORWARD_8787_PROVEN"] is False
    assert rec["C2_JOIN_PROVEN"] is False
    assert rec["COMMAND_FABRIC_E2E_PROVEN"] is False
    assert rec["CROSS_HOST_ROUND_TRIP_PROVEN"] is False
    assert rec["WAL_WRITTEN"] is False
    assert rec["GL005_PROVEN"] is False
    assert rec["secrets_present"] is False
    blob = json.dumps(rec)
    assert "sk-" not in blob
    assert "Bearer" not in blob
