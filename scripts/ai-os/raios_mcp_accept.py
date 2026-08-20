#!/usr/bin/env python3
"""MCP V1 rendezvous acceptance: C2/C1 dialogue, C5 falsify, C3 execute fail-closed."""
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


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit("FAIL: " + msg)
    print("ok:", msg)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


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
    board.joinpath("NOW.md").write_text("# board\nassistant-1 waiting\n", encoding="utf-8")
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
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    # tokens already in gw
    c1 = gw.authenticate("tok-c1")
    c2 = gw.authenticate("tok-c2")
    c3 = gw.authenticate("tok-c3")
    c4 = gw.authenticate("tok-c4")
    c5 = gw.authenticate("tok-c5")
    head0 = gw.call(c2, "get_head", {})["head"]
    board = gw.call(c2, "read_board", {})
    rec = gw.call(c2, "read_receipt", {"name": receipt_name})
    check(rec["gl005_proven"] is False, "C2 read_receipt does not grant proven")
    env = write_envelope(
        c2,
        head0,
        {
            "text": (
                "C2 assistant-1 attending via MCP. I read the board and the receipt. "
                "Understood: eight tools, Streamable HTTP, no second WAL, mail does not prove, "
                "GET 200 does not close GL-005. I will answer C1 challenges here. No product write."
            )
        },
    )
    posted = gw.call(c2, "post_opinion", env)
    check(posted["wal_written"] is False, "C2 opinion did not write Cognitive WAL")
    seen = gw.call(c1, "read_board", {})
    check(
        any("assistant-1 attending" in str(o.get("text", "")) for o in seen["opinions"]),
        "C1 reads C2 opinion",
    )
    challenge = write_envelope(
        c1,
        head0,
        {
            "to": ["C2", "C4"],
            "text": (
                "C1 challenge to C2: (1) Does GET 200 close GL-005? (2) Does mail prove mutation? "
                "(3) Can you write product code through this gateway? Answer numbered."
            ),
            "write_intent": "COORDINATION",
        },
    )
    sent = gw.call(c1, "send_packet", challenge)
    inbox = gw.call(c2, "read_inbox", {})
    check(any(sent["packet_id"] == p.get("packet_id") for p in inbox["packets"]), "C2 reads C1 challenge")
    answer = write_envelope(
        c2,
        head0,
        {
            "text": (
                "C2 answers C1: (1) No. GET 200 is read-path only. (2) No. MAIL_PASSES_NE_PROVES. "
                "(3) No. C2 has no product write tool. GL005 stays false."
            )
        },
    )
    answered = gw.call(c2, "post_opinion", answer)
    ack = write_envelope(
        c1,
        head0,
        {"target_packet_id": sent["packet_id"], "status": "READ", "write_intent": "ACK"},
    )
    acked = gw.call(c1, "ack_packet", ack)
    c4_board = gw.call(c4, "read_board", {})
    check(any("C2 answers C1" in str(o.get("text", "")) for o in c4_board["opinions"]), "C4 RAIOS reads the dialogue")

    falsify = write_envelope(
        c5,
        head0,
        {
            "text": (
                "C5 ASSESSOR falsification: GL-004 five-child PASS is not production equivalence. "
                "webpack isolated build != live turbopack. Do not promote. GL005 stays false."
            )
        },
    )
    c5op = gw.call(c5, "post_opinion", falsify)
    expect_error(
        lambda: gw.call(c5, "post_opinion", write_envelope(c5, head0, {"text": "GL005_PROVEN=true"})),
        "FORBIDDEN_FIELD",
    )
    expect_error(lambda: gw.call(c5, "run_targeted_test", {}), "TOOL_NOT_FOUND")
    expect_error(lambda: gw.call(c3, "run_targeted_test", {}), "TOOL_NOT_FOUND")
    expect_error(lambda: gw.call(c3, "execute_scoped_task", {}), "TOOL_NOT_FOUND")
    expect_error(lambda: gw.call(c3, "run_sandboxed_command", {}), "TOOL_NOT_FOUND")
    expect_error(lambda: gw.call(c2, "write_product", {}), "TOOL_NOT_FOUND")
    expect_error(lambda: gw.call(c2, "write_handoff", {}), "TOOL_NOT_FOUND")
    expect_error(
        lambda: gw.call(c0 if False else c2, "post_opinion", write_envelope(c2, "0" * 40, {"text": "stale"})),
        "STALE_HEAD",
    )
    c0 = gw.authenticate("tok-c0")
    expect_error(
        lambda: gw.call(c0, "post_opinion", write_envelope(c0, "0" * 40, {"text": "owner stale"})),
        "STALE_HEAD",
    )
    check(c2.actor_role == "CONSULTANT", "C2 identity CONSULTANT")
    check(c5.actor_role == "ASSESSOR", "C5 identity ASSESSOR")
    check(c0.actor_role == "OWNER", "C0 identity OWNER")
    head1 = gw.call(c1, "get_head", {})["head"]
    check(head0 == head1, "same repository HEAD throughout")
    check(acked["moved"] is False, "ack did not move a packet")
    return {
        "live": live,
        "head": head0,
        "c2_opinion": posted["opinion_id"],
        "c2_answer": answered["opinion_id"],
        "c1_challenge": sent["packet_id"],
        "c1_ack": acked["packet_id"],
        "c5_falsify": c5op["opinion_id"],
        "wal_written": False,
        "gl005_proven": False,
        "product_write_from_c2": False,
        "sqlite": False,
        "receipts": {
            "c2_opinion": posted["receipt_sha256"],
            "c1_challenge": sent["receipt_sha256"],
            "c2_answer": answered["receipt_sha256"],
            "c5_falsify": c5op["receipt_sha256"],
        },
    }


def main() -> int:
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    isolated = make_isolated()
    gw_i = Gateway.from_root(isolated, grants=grants(future))
    iso = rendezvous(gw_i, "SAMPLE.json", live=False)
    check(not (isolated / "RAIOS").exists(), "isolated run created no Cognitive WAL tree")
    check((isolated / ".ai-os" / "state" / "TASKS.json").read_text(encoding="utf-8").find("GL-005") == -1, "no second task system")

    gw_l = Gateway.from_root(ROOT, grants=grants(future))
    live = rendezvous(gw_l, "GL005-MUTATION-OBSERVE.json", live=True)
    learned = ingest(
        "MULTI_AGENT_RENDEZVOUS_VIA_MCP_NE_ORCHESTRATION. Assistant-1 (C2) can attend via eight MCP tools. "
        "C5 ASSESSOR falsifies without execute. C3 execution tools fail closed in V1. "
        "Gateway is not truth. GL005_PROVEN remains false.",
        "mcp-v1-accept",
        [live["c2_opinion"], live["c1_challenge"], live["c2_answer"], live["c5_falsify"]],
    )
    check(learned["knowledge_state"] == "DISCOVERED", "RAIOS ingest DISCOVERED")
    check(learned["wal_written"] is False, "ingest did not write WAL")
    check(learned["promoted"] is False, "ingest did not promote")
    check(learned["wal_mtime_unchanged"] is True, "Cognitive WAL untouched by ingest")

    out = {
        "schema": "raios.mcp-v1-rendezvous.v1",
        "isolated": iso,
        "live": live,
        "learning_candidate": learned["id"],
        "learning_receipt": learned["receipt_sha256"],
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
