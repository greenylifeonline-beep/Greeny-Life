import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".ai-os" / "control"))
sys.path.insert(0, str(ROOT / "scripts" / "ai-os"))
sys.path.insert(0, str(ROOT / "RAIOS" / "V9"))

from c2_obs import Fabric, diagnose, isolated_channel  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"


def test_d17335a_context_is_this_cloud_clone_not_repair():
    diag = diagnose()
    assert diag["identity"]["seat"] == "C2-OBS"
    assert diag["identity"]["not_repair_executor"] is True
    assert diag["d17335a_context"]["d17335a_is_ancestor"] is True
    assert diag["d17335a_context"]["repair_commit_12603d0"] == "ABSENT"
    assert diag["d17335a_context"]["repair_root_reachable"] is False
    assert diag["ci_d17335a"]["ci_pass_ne_assimilation"] is True
    assert diag["gl005_proven"] is False
    assert diag["new_bus_created"] is False


def test_live_c5_and_mcp_health_without_cursor_agent_or_multimodal_gateway():
    diag = diagnose()
    assert diag["live"]["mcp_health_http"] == 200
    assert diag["live"]["screen_8765"] == 200
    assert diag["live"]["cursor_agent"] is None
    assert diag["live"]["multimodal_gateway"] is None
    assert (diag["live"]["mcp"] or {}).get("tools") == [
        "get_head",
        "read_board",
        "read_inbox",
        "read_receipt",
        "get_diff",
        "post_opinion",
        "send_packet",
        "ack_packet",
    ]
    assert (diag["live"]["mcp"] or {}).get("remote_c2_ready") is False


def test_lease_fencing_and_duplicate_message_suppression(tmp_path):
    fabric = Fabric(tmp_path)
    first = fabric.claim("C2-OBS")
    assert first["ok"] is True
    held = fabric.claim("OTHER-WORKER")
    assert held["ok"] is False
    assert held["reason"] == "LEASE_HELD"
    a = fabric.remember("MSG-1", "body")
    b = fabric.remember("MSG-1", "body")
    assert a["duplicate"] is False
    assert b["duplicate"] is True
    assert b["applied"] is False


def test_isolated_channel_success_and_fail_closed_errors():
    rec = isolated_channel()
    assert rec["ok"] is True
    assert rec["inbox_saw_c1"] is True
    assert rec["c1_outbox_count"] >= 1
    assert rec["ack_moved"] is False
    assert rec["fail_replay"] == "REPLAY"
    assert rec["fail_packet_eq_correlation"] == "INVALID_PACKET"
    assert rec["fail_unauthenticated"] == "UNAUTHENTICATED"
    assert rec["wal_written"] is False
    assert rec["gl005_proven"] is False


def test_flags_receipt_does_not_mint_join_or_gl005():
    flags = json.loads((ROOT / ".ai-os" / "state" / "command-fabric" / "FLAGS.json").read_text(encoding="utf-8"))
    assert flags["GL005_PROVEN"] is False
    assert flags["C2_JOIN_PROVEN"] is False
    assert flags["COMMAND_FABRIC_E2E_PROVEN"] is False
    assert flags["CI_PASS_NE_ASSIMILATION"] is True
    assert flags["new_bus_created"] is False
    assert flags["wal_written"] is False
    assert flags["lease_ok"] is True
    assert flags["channel_isolated_ok"] is True
    wal = WAL
    assert wal.is_file()


def test_ack_is_new_packet_never_a_move():
    ack = json.loads(
        (ROOT / ".ai-os" / "receipts" / "command-fabric" / "ACK-MSG-1787675796720281-e5058327.json").read_text(
            encoding="utf-8"
        )
    )
    assert ack["moved"] is False
    assert ack["status"] == "READ"
    assert ack["from"] == "C2-OBS"
    assert ack["duplicate_retry"]["duplicate"] is True
    assert ack["law"] == "ACK_IS_A_NEW_PACKET_NEVER_A_MOVE"
