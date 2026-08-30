"""Cloud-session public-channel receipt must not merge AG 8766 or claim MCP/GL-005."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / ".ai-os" / "receipts" / "c5-screen" / "C5-PUBLIC-CHANNEL-CLOUD-SESSION.json"


def test_public_channel_receipt_is_cursor_session_not_ag():
    rec = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert rec["ok"] is True
    assert rec["evidence_class"] == "CURSOR_CLOUD_SESSION"
    assert rec["not_evidence_class"] == "AG_CONTROL_PLANE_PROCESS"
    assert rec["cursor_cloud_bind"] == "127.0.0.1:8765"
    assert rec["ag_local_bind"] == "127.0.0.1:8766"
    assert rec["same_process_as_ag_8766"] is False
    assert rec["do_not_merge_8765_and_8766"] is True
    assert rec["C5_PUBLIC_CHANNEL_PROVEN"] is True
    assert rec["C4_SEAT_CARD_DISPLAY_PROVEN"] is True
    assert rec["MODEL_MISSING_HANDLED_SAFELY"] is True
    assert rec["C5_SAFE_MISSING_DATA_BEHAVIOR_PROVEN"] is True
    assert rec["HONEY_MODEL_AVAILABLE"] is False
    assert rec["HONEY_PRICE_AVAILABLE"] is False
    assert rec["C5_BUSINESS_HONEY_MODEL_PROVEN"] is False
    assert rec["C5_FOUNDER_CHANNEL_PROVEN"] is False
    assert rec["C5_MAIN_CORTEX_PROVEN"] is False
    assert rec["C5_MCP_E2E_PROVEN"] is False
    assert rec["C5_MCP_FORMAL_JOIN_PROVEN"] is False
    assert rec["COMMAND_FABRIC_E2E_PROVEN"] is False
    assert rec["CROSS_HOST_ROUND_TRIP_PROVEN"] is False
    assert rec["WAL_WRITTEN"] is False
    assert rec["GL005_PROVEN"] is False
    assert rec["challenge_run"] is False
    assert rec["artifacts"] == [
        "/opt/cursor/artifacts/c5_public_screen_loaded.webp",
        "/opt/cursor/artifacts/c5_public_chat_c4_and_honey.webp",
    ]
