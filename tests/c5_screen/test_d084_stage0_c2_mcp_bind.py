"""Stage-0 Mission 1 bind evidence; stop before grant/Challenge without AG reachability."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / ".ai-os" / "receipts" / "command-fabric" / "D084-STAGE0-C2-MCP-BIND.json"


def test_d084_records_runtime_bind_and_stops_before_challenge():
    rec = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert rec["stage"] == 0
    assert rec["challenge_run"] is False
    assert rec["code_patched"] is False
    assert rec["MCP_BIND_HOST"] == "127.0.0.1"
    assert rec["MCP_BIND_PORT"] == 8787
    assert rec["MCP_HEALTH"] == "PASS"
    assert rec["TOOLS_COUNT"] == 8
    assert rec["C2_MCP_PROTOCOL"] == "streamable HTTP MCP"
    assert rec["C2_SESSION_ID"] == "bc-0e394199-3277-4061-808d-28fd2bee4540"
    assert rec["FORWARD_STATUS"] == "NOT_PERFORMABLE_FROM_C2_CLOUD_AGENT"
    assert rec["AG_FORWARDED_PORT"] is None
    assert rec["AG_TO_C2_MCP_REACHABLE"] is False
    assert rec["MISSION3_STOP"] is True
    assert rec["C1_GRANT_CREATED"] is False
    assert rec["C1_ACTOR_PRESENT"] is False
    assert rec["CROSS_HOST_AUTH_PROVEN"] is False
    assert rec["PACKET_ID"] == ""
    assert rec["C2_MCP_FORWARD_PROVEN"] is False
    assert rec["C2_JOIN_PROVEN"] is False
    assert rec["REMOTE_DELIVERY_PROVEN"] is False
    assert rec["CROSS_HOST_ROUND_TRIP_PROVEN"] is False
    assert rec["COMMAND_FABRIC_E2E_PROVEN"] is False
    assert rec["PORT_FORWARD_8787_PROVEN"] is False
    assert rec["WAL_WRITTEN"] is False
    assert rec["GL005_PROVEN"] is False
    assert rec["C2_TREE001_PRESENT"] is False
    assert rec["ENVIRONMENT_DIVERGENCE"] is True
    assert rec["COMMAND_FABRIC_READY_FOR_NEXT_STAGE"] is False
    blob = json.dumps(rec)
    assert "sk-" not in blob
    assert "Bearer " not in blob
