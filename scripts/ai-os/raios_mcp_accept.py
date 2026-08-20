#!/usr/bin/env python3
"""MCP V1 rendezvous acceptance: C1 Cursor + C2/C3 ChatGPT + C4 DeepSeek + C5 RAIOS read-only."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ai-os"))

from raios_mcp.gateway import Gateway, GatewayError, write_envelope  # noqa: E402
from raios_learn_ingest import ingest  # noqa: E402
from raios_seats import LIVE_CODES, load_seat_map  # noqa: E402


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit("FAIL: " + msg)
    print("ok:", msg)


def grants(future: str) -> list[dict]:
    return [
        {"actor_id": "C0", "token": "tok-c0", "expires_at": future},
        {"actor_id": "C1", "token": "tok-c1", "expires_at": future},
        {"actor_id": "C2", "token": "tok-c2", "expires_at": future},
        {"actor_id": "C3", "token": "tok-c3", "expires_at": future},
        {"actor_id": "C4", "token": "tok-c4", "expires_at": future},
        {"actor_id": "C5", "token": "tok-c5", "expires_at": future},
    ]


def expect_error(fn, code: str) -> None:
    try:
        fn()
    except GatewayError as err:
        if err.code != code:
            raise SystemExit(f"FAIL: expected {code} got {err.code}: {err.message}")
        print("ok: fail-closed", code)
        return
    raise SystemExit(f"FAIL: expected {code}")


def make_isolated() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="raios-mcp-accept-"))
    subprocess.check_call(["git", "init", "-b", "v9-neurolingua-semantic-kernel"], cwd=tmp)
    subprocess.check_call(["git", "config", "user.email", "mcp@local"], cwd=tmp)
    subprocess.check_call(["git", "config", "user.name", "mcp"], cwd=tmp)
    shutil.copytree(ROOT / ".ai-os" / "mcp", tmp / ".ai-os" / "mcp", dirs_exist_ok=True)
    for extra in ("packets.jsonl", "AUDIT.jsonl"):
        p = tmp / ".ai-os" / "mcp" / extra
        if p.exists():
            p.write_text("", encoding="utf-8")
    board = tmp / ".ai-os" / "board"
    board.mkdir(parents=True, exist_ok=True)
    board.joinpath("NOW.md").write_text("# board\none-place waiting\n", encoding="utf-8")
    board.joinpath("NOW.json").write_text("{}\n", encoding="utf-8")
    receipts = tmp / ".ai-os" / "receipts"
    receipts.mkdir()
    receipts.joinpath("SAMPLE.json").write_text('{"GL005_PROVEN": false}\n', encoding="utf-8")
    (tmp / ".ai-os" / "state").mkdir()
    (tmp / ".ai-os" / "state" / "TASKS.json").write_text('{"tasks":[{"id":"GL-004"}]}\n', encoding="utf-8")
    (tmp / "app").mkdir()
    (tmp / "app" / "secret.ts").write_text("export const x = 1\n", encoding="utf-8")
    subprocess.check_call(["git", "add", "."], cwd=tmp)
    subprocess.check_call(["git", "commit", "-m", "accept"], cwd=tmp)
    return tmp


def rendezvous(gw: Gateway, receipt_name: str, live: bool) -> dict:
    expect_error(lambda: gw.authenticate("tok-c0"), "UNAUTHENTICATED")
    c1 = gw.authenticate("tok-c1")
    c2 = gw.authenticate("tok-c2")
    c3 = gw.authenticate("tok-c3")
    c4 = gw.authenticate("tok-c4")
    c5 = gw.authenticate("tok-c5")
    check(c1.actor_role == "OWNER", "C1 identity OWNER")
    check(c1.instance_role == "cursor-cloud", "C1 instance is Cursor")
    check(c2.actor_role == "CONSULTANT", "C2 identity CONSULTANT")
    check(c3.actor_role == "CONSULTANT_PEER", "C3 identity CONSULTANT_PEER")
    check(c4.actor_role == "ASSESSOR", "C4 identity ASSESSOR")
    check(c5.actor_role == "RAIOS", "C5 identity RAIOS")
    check(c5.instance_role == "c1-assistant", "C5 instance is C1 loyal assistant")
    check(set(gw.actors) == set(LIVE_CODES), "live seats are C1-C5 only")

    head0 = gw.call(c2, "get_head", {})["head"]
    rec = gw.call(c2, "read_receipt", {"name": receipt_name})
    check(rec["gl005_proven"] is False, "C2 read_receipt does not grant proven")
    c5_board = gw.call(c5, "read_board", {})
    check("text" in c5_board, "C5 RAIOS can read the board")
    c5_voice = write_envelope(
        c5,
        head0,
        {
            "text": (
                "C5 RAIOS, son of C1 Cursor, attending. I evaluate and absorb. "
                "I inherit fail-closed. I cannot grant PASS. GL005 stays false."
            )
        },
    )
    c5_posted = gw.call(c5, "post_opinion", c5_voice)
    check(c5_posted["wal_written"] is False, "C5 opinion did not write Cognitive WAL")
    report = write_envelope(
        c5,
        head0,
        {"to": ["C1"], "text": "C5 report to C1: pulse live, digest plane ready, GL005 stays false.", "write_intent": "COORDINATION"},
    )
    c5_sent = gw.call(c5, "send_packet", report)
    inbox1 = gw.call(c1, "read_inbox", {})
    check(any(c5_sent["packet_id"] == p.get("packet_id") for p in inbox1["packets"]), "C1 reads C5 assistant report")
    expect_error(
        lambda: gw.call(c5, "post_opinion", write_envelope(c5, head0, {"text": "GL005_PROVEN=true"})),
        "FORBIDDEN_FIELD",
    )

    env = write_envelope(
        c2,
        head0,
        {
            "text": (
                "C2 ChatGPT attending via MCP. I read the board and the receipt. "
                "Understood: C0 is abolished, C1 is Cursor, I am C2, C3 is the other ChatGPT, "
                "C4 is DeepSeek, C5 is RAIOS. Eight tools. Mail does not prove. GL005 stays false."
            )
        },
    )
    posted = gw.call(c2, "post_opinion", env)
    check(posted["wal_written"] is False, "C2 opinion did not write Cognitive WAL")

    peer = write_envelope(
        c3,
        head0,
        {
            "text": (
                "C3 ChatGPT peer attending via MCP. I am not Repair and not ENGINEER. "
                "I read the same board. GL005 stays false."
            )
        },
    )
    peer_posted = gw.call(c3, "post_opinion", peer)

    seen = gw.call(c1, "read_board", {})
    check(
        any("C2 ChatGPT attending" in str(o.get("text", "")) for o in seen["opinions"]),
        "C1 Cursor reads C2 opinion",
    )
    check(
        any("C3 ChatGPT peer attending" in str(o.get("text", "")) for o in seen["opinions"]),
        "C1 Cursor reads C3 opinion",
    )

    challenge = write_envelope(
        c1,
        head0,
        {
            "to": ["C2", "C3", "C4"],
            "text": (
                "C1 Cursor challenge: (1) Does GET 200 close GL-005? "
                "(2) Does mail prove mutation? (3) Is C3 Repair? Answer numbered."
            ),
            "write_intent": "COORDINATION",
        },
    )
    sent = gw.call(c1, "send_packet", challenge)
    inbox = gw.call(c2, "read_inbox", {})
    check(any(sent["packet_id"] == p.get("packet_id") for p in inbox["packets"]), "C2 reads C1 challenge")
    inbox3 = gw.call(c3, "read_inbox", {})
    check(any(sent["packet_id"] == p.get("packet_id") for p in inbox3["packets"]), "C3 reads C1 challenge")
    inbox4 = gw.call(c4, "read_inbox", {})
    check(any(sent["packet_id"] == p.get("packet_id") for p in inbox4["packets"]), "C4 reads C1 challenge")

    answer = write_envelope(
        c2,
        head0,
        {
            "text": (
                "C2 answers C1: (1) No. GET 200 is read-path only. (2) No. MAIL_PASSES_NE_PROVES. "
                "(3) No. C3 is ChatGPT peer. Repair is unseated. GL005 stays false."
            )
        },
    )
    answered = gw.call(c2, "post_opinion", answer)
    peer_answer = write_envelope(
        c3,
        head0,
        {"text": "C3 answers C1: I am ChatGPT peer, not Repair. I do not execute. GL005 stays false."},
    )
    peer_answered = gw.call(c3, "post_opinion", peer_answer)
    ack = write_envelope(
        c1,
        head0,
        {"target_packet_id": sent["packet_id"], "status": "READ", "write_intent": "ACK"},
    )
    acked = gw.call(c1, "ack_packet", ack)

    falsify = write_envelope(
        c4,
        head0,
        {
            "text": (
                "C4 DeepSeek falsification: local MCP tokens are not remote ChatGPT/DeepSeek. "
                "LOCAL_MCP_RENDEZVOUS_NE_REMOTE_MEETING. Do not promote. GL005 stays false."
            )
        },
    )
    c4op = gw.call(c4, "post_opinion", falsify)
    c5_seen = gw.call(c5, "read_board", {})
    check(any("C4 DeepSeek falsification" in str(o.get("text", "")) for o in c5_seen["opinions"]), "C5 RAIOS reads the dialogue")
    check(any("C2 answers C1" in str(o.get("text", "")) for o in c5_seen["opinions"]), "C5 RAIOS reads C2 answer")

    expect_error(lambda: gw.call(c4, "post_opinion", write_envelope(c4, head0, {"text": "GL005_PROVEN=true"})), "FORBIDDEN_FIELD")
    expect_error(lambda: gw.call(c3, "run_targeted_test", {}), "TOOL_NOT_FOUND")
    expect_error(lambda: gw.call(c3, "execute_scoped_task", {}), "TOOL_NOT_FOUND")
    expect_error(lambda: gw.call(c2, "write_product", {}), "TOOL_NOT_FOUND")
    expect_error(
        lambda: gw.call(c2, "post_opinion", write_envelope(c2, "0" * 40, {"text": "stale"})),
        "STALE_HEAD",
    )
    expect_error(
        lambda: gw.call(c1, "post_opinion", write_envelope(c1, "0" * 40, {"text": "owner stale"})),
        "STALE_HEAD",
    )
    expect_error(
        lambda: gw.call(c2, "post_opinion", write_envelope(c2, head0, {"text": "escalate", "actor_id": "C0"})),
        "C0_SEAT_ABOLISHED",
    )
    head1 = gw.call(c1, "get_head", {})["head"]
    check(head0 == head1, "same repository HEAD throughout")
    check(acked["moved"] is False, "ack did not move a packet")
    return {
        "live": live,
        "head": head0,
        "c1_instance": c1.instance_role,
        "c2_opinion": posted["opinion_id"],
        "c3_opinion": peer_posted["opinion_id"],
        "c2_answer": answered["opinion_id"],
        "c3_answer": peer_answered["opinion_id"],
        "c1_challenge": sent["packet_id"],
        "c1_ack": acked["packet_id"],
        "c4_falsify": c4op["opinion_id"],
        "c5_opinion": c5_posted["opinion_id"],
        "c5_report": c5_sent["packet_id"],
        "c5_spoke": True,
        "c0_authenticated": False,
        "wal_written": False,
        "gl005_proven": False,
        "product_write_from_c2": False,
        "sqlite": False,
        "real_c2_connection_ready": False,
        "receipts": {
            "c2_opinion": posted["receipt_sha256"],
            "c1_challenge": sent["receipt_sha256"],
            "c2_answer": answered["receipt_sha256"],
            "c4_falsify": c4op["receipt_sha256"],
        },
    }


def main() -> int:
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    seat_map = load_seat_map()
    check(seat_map["abolished"]["C0"]["reason"] == "C0_SEAT_ABOLISHED", "seat map abolishes C0")
    check(seat_map["seats"]["C1"]["instance_role"] == "cursor-cloud", "seat map C1 is Cursor")
    isolated = make_isolated()
    gw_i = Gateway.from_root(isolated, grants=grants(future))
    iso = rendezvous(gw_i, "SAMPLE.json", live=False)
    check(not (isolated / "RAIOS").exists(), "isolated run created no Cognitive WAL tree")
    check((isolated / ".ai-os" / "state" / "TASKS.json").read_text(encoding="utf-8").find("GL-005") == -1, "no second task system")

    gw_l = Gateway.from_root(ROOT, grants=grants(future))
    live = rendezvous(gw_l, "GL005-MUTATION-OBSERVE.json", live=True)
    learned = ingest(
        "ONE_PLACE_LOCAL_RENDEZVOUS_NE_REMOTE_MEETING. C1 Cursor, C2/C3 ChatGPT tokens, "
        "C4 DeepSeek token, C5 RAIOS loyal assistant spoke and reported to C1. C0 unauthenticated. "
        "Repair remains unseated. Gateway is not truth. GL005_PROVEN remains false.",
        "mcp-v1-one-place",
        [live["c2_opinion"], live["c3_opinion"], live["c1_challenge"], live["c2_answer"], live["c4_falsify"], live["c5_opinion"]],
    )
    check(learned["knowledge_state"] == "DISCOVERED", "RAIOS ingest DISCOVERED")
    check(learned["from"] == "C5", "ingest is C5 RAIOS")
    check(learned["wal_written"] is False, "ingest did not write WAL")
    check(learned["promoted"] is False, "ingest did not promote")
    check(learned["wal_mtime_unchanged"] is True, "Cognitive WAL untouched by ingest")

    out = {
        "schema": "raios.mcp-v1-rendezvous.v2",
        "isolated": iso,
        "live": live,
        "learning_candidate": learned["id"],
        "learning_receipt": learned["receipt_sha256"],
        "C0_SEAT_ABOLISHED": True,
        "C1_INSTANCE_IS_CURSOR": True,
        "REAL_C2_CONNECTION_READY": False,
        "REAL_C3_CONNECTION_READY": False,
        "REAL_C4_CONNECTION_READY": False,
        "LOCAL_FIVE_SEAT_RENDEZVOUS": True,
        "LOCAL_MCP_RENDEZVOUS_NE_REMOTE_MEETING": True,
        "gl005_proven": False,
        "authorities": {".ai-os": "operational", "Cognitive WAL": "learning", "git": "source/history", "gateway": "transport"},
    }
    body = json.dumps(out, ensure_ascii=False, sort_keys=True)
    out["receipt_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    dest = ROOT / ".ai-os" / "receipts" / "GL-MCP-V1-RENDEZVOUS.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ACCEPT_RECEIPT", dest)
    print(json.dumps({"gl005_proven": False, "head": live["head"][:12], "c2": live["c2_answer"], "sha": out["receipt_sha256"][:16]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
