#!/usr/bin/env python3
"""V1 vertical slice + protocol/security checks. Not GL-005 proof. No second WAL."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ai-os"))

from raios_mcp.gateway import (  # noqa: E402
    Gateway,
    GatewayError,
    V1_TOOLS,
    payload_hash_of,
    write_envelope,
)
from raios_mcp.server import Handler, handle_rpc  # noqa: E402


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit("FAIL: " + msg)
    print("ok:", msg)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def make_repo() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="raios-mcp-"))
    subprocess.check_call(["git", "init", "-b", "v9-neurolingua-semantic-kernel"], cwd=tmp)
    subprocess.check_call(["git", "config", "user.email", "mcp@local"], cwd=tmp)
    subprocess.check_call(["git", "config", "user.name", "mcp"], cwd=tmp)
    policy_src = ROOT / ".ai-os" / "mcp" / "POLICY.json"
    dest_policy = tmp / ".ai-os" / "mcp"
    dest_policy.mkdir(parents=True)
    shutil.copy(policy_src, dest_policy / "POLICY.json")
    board = tmp / ".ai-os" / "board"
    board.mkdir(parents=True)
    board.joinpath("NOW.md").write_text("# board\nslice=waiting\n", encoding="utf-8")
    board.joinpath("NOW.json").write_text("{}\n", encoding="utf-8")
    receipts = tmp / ".ai-os" / "receipts"
    receipts.mkdir()
    receipts.joinpath("SAMPLE.json").write_text('{"GL005_PROVEN": false, "note": "sample"}\n', encoding="utf-8")
    (tmp / ".ai-os" / "state").mkdir()
    (tmp / ".ai-os" / "state" / "TASKS.json").write_text('{"tasks":[{"id":"GL-004"}]}\n', encoding="utf-8")
    subprocess.check_call(["git", "add", "."], cwd=tmp)
    subprocess.check_call(["git", "commit", "-m", "slice"], cwd=tmp)
    return tmp


def gw_for(tmp: Path, extra_grants: list[dict] | None = None) -> Gateway:
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    grants = [
        {"actor_id": "C0", "token": "tok-c0", "expires_at": future},
        {"actor_id": "C1", "token": "tok-c1", "expires_at": future},
        {"actor_id": "C2", "token": "tok-c2", "expires_at": future},
    ]
    if extra_grants:
        grants.extend(extra_grants)
    return Gateway.from_root(tmp, grants=grants)


def expect_error(fn, code: str) -> None:
    try:
        fn()
    except GatewayError as err:
        if err.code != code:
            raise SystemExit(f"FAIL: expected {code} got {err.code}: {err.message}")
        return
    raise SystemExit(f"FAIL: expected {code} but call succeeded")


def main() -> int:
    tmp = make_repo()
    head = git(tmp, "rev-parse", "HEAD")
    gw = gw_for(tmp)
    c0 = gw.authenticate("tok-c0")
    c1 = gw.authenticate("tok-c1")
    c2 = gw.authenticate("tok-c2")

    board = gw.call(c2, "read_board", {})
    check("slice=waiting" in board["text"], "V1 C2 read_board")
    receipt = gw.call(c2, "read_receipt", {"name": "SAMPLE.json"})
    check("GL005_PROVEN" in receipt["text"], "V1 C2 read_receipt")
    check(receipt["gl005_proven"] is False, "read_receipt does not grant proven")

    env = write_envelope(c2, head, {"text": "C2 slice opinion: connector is not truth.", "write_intent": "OPINION_ONLY"})
    posted = gw.call(c2, "post_opinion", env)
    check(posted["ok"] is True, "V1 C2 post_opinion")
    check(posted["wal_written"] is False, "gateway did not write Cognitive WAL")
    seen = gw.call(c1, "read_board", {})
    check("C2 slice opinion" in seen["text"] or any("C2 slice opinion" in str(o.get("text")) for o in seen["opinions"]), "V1 C1 reads C2 opinion")

    expect_error(lambda: gw.authenticate("nope"), "UNAUTHENTICATED")
    expect_error(lambda: gw.call(c2, "run_targeted_test", {}), "TOOL_NOT_FOUND")
    expect_error(lambda: gw.call(c2, "write_handoff", {}), "TOOL_NOT_FOUND")
    expect_error(lambda: gw.call(c2, "request_task", {}), "TOOL_NOT_FOUND")
    expect_error(lambda: gw.call(c2, "shell", {}), "TOOL_NOT_FOUND")
    expect_error(lambda: gw.call(c2, "run_sandboxed_command", {}), "TOOL_NOT_FOUND")
    expect_error(
        lambda: gw.call(c2, "post_opinion", write_envelope(c2, head, {"text": "GL005_PROVEN=true"})),
        "FORBIDDEN_FIELD",
    )
    stale = write_envelope(c2, "0" * 40, {"text": "stale c2"})
    expect_error(lambda: gw.call(c2, "post_opinion", stale), "STALE_HEAD")
    stale0 = write_envelope(c0, "0" * 40, {"text": "stale c0"})
    expect_error(lambda: gw.call(c0, "post_opinion", stale0), "STALE_HEAD")
    check(True, "C0 cannot bypass stale HEAD")

    expired = write_envelope(c2, head, {"text": "late", "expires_at": "2000-01-01T00:00:00+00:00"})
    expect_error(lambda: gw.call(c2, "post_opinion", expired), "EXPIRED")

    env2 = write_envelope(c2, head, {"text": "replay me"})
    gw.call(c2, "post_opinion", env2)
    expect_error(lambda: gw.call(c2, "post_opinion", env2), "REPLAY")

    same = write_envelope(c2, head, {"text": "same ids"})
    same["correlation_id"] = same["packet_id"]
    same["payload_hash"] = payload_hash_of(same)
    expect_error(lambda: gw.call(c2, "post_opinion", same), "INVALID_PACKET")

    esc = write_envelope(c2, head, {"text": "escalate", "actor_id": "C0"})
    expect_error(lambda: gw.call(c2, "post_opinion", esc), "IDENTITY_MISMATCH")
    exec_yes = write_envelope(c2, head, {"text": "exec", "execution_intent": "YES"})
    expect_error(lambda: gw.call(c2, "post_opinion", exec_yes), "ESCALATION_DENIED")
    secret = write_envelope(c2, head, {"text": "DATABASE_URL=postgres://x"})
    expect_error(lambda: gw.call(c2, "post_opinion", secret), "SECRET_REJECTED")
    bearer_prose = write_envelope(
        c2, head, {"text": "V1 uses scoped bearer tokens with expires_at. Not a secret."}
    )
    check(gw.call(c2, "post_opinion", bearer_prose)["ok"] is True, "prose about bearer tokens is not a secret")
    tokenish = write_envelope(c2, head, {"text": "Authorization: Bearer abcdefghijklmnop1234"})
    expect_error(lambda: gw.call(c2, "post_opinion", tokenish), "SECRET_REJECTED")
    expect_error(lambda: gw.call(c2, "read_receipt", {"name": "../.state/TASKS.json"}), "PATH_TRAVERSAL")
    expect_error(lambda: gw.call(c2, "get_diff", {"path": "../.env"}), "PATH_TRAVERSAL")

    bad_hash = write_envelope(c2, head, {"text": "hash"})
    bad_hash["payload_hash"] = "00" * 32
    expect_error(lambda: gw.call(c2, "post_opinion", bad_hash), "PAYLOAD_HASH_MISMATCH")

    exec_c0 = write_envelope(c0, head, {"text": "c0 exec", "execution_intent": "YES"})
    expect_error(lambda: gw.call(c0, "post_opinion", exec_c0), "ESCALATION_DENIED")

    before_tasks = (tmp / ".ai-os" / "state" / "TASKS.json").read_text(encoding="utf-8")
    send_env = write_envelope(c2, head, {"text": "hello C1", "to": ["C1"], "write_intent": "COORDINATION"})
    sent = gw.call(c2, "send_packet", send_env)
    ack_env = write_envelope(c1, head, {"target_packet_id": sent["packet_id"], "status": "READ", "write_intent": "ACK"})
    acked = gw.call(c1, "ack_packet", ack_env)
    check(acked["moved"] is False, "ack is a new packet, never a move")
    after_tasks = (tmp / ".ai-os" / "state" / "TASKS.json").read_text(encoding="utf-8")
    check(before_tasks == after_tasks, "TASKS.json not mutated")
    check(not (tmp / "RAIOS").exists(), "no RAIOS/SQLite/Cognitive WAL created by gateway")
    check(not list(tmp.glob("**/*.sqlite")), "no sqlite database")
    check("run_build" not in V1_TOOLS, "run_build not in V1")
    check(gw.call(c2, "get_head", {})["head"] == head, "get_head matches live")
    check(gw.call(c2, "get_diff", {"path": ".ai-os/board"})["raw_shell"] is False, "get_diff is semantic")

    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    gw_exp = gw_for(tmp, extra_grants=[{"actor_id": "C2", "token": "tok-expired", "expires_at": past}])
    expect_error(lambda: gw_exp.authenticate("tok-expired"), "EXPIRED")

    Handler.gateway = gw
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address[:2]
    health = json.loads(urlopen(f"http://{host}:{port}/health", timeout=3).read().decode())
    check(health["gl005_proven"] is False, "health proven stays false")
    check(health["sqlite"] is False, "health sqlite false")
    check(health["websocket"] is False, "health websocket false")
    check(health["transport"] == "streamable-http", "streamable HTTP advertised")

    init = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}).encode()
    sse_req = Request(
        f"http://{host}:{port}/mcp",
        data=init,
        headers={"Accept": "text/event-stream", "Content-Type": "application/json"},
        method="POST",
    )
    sse_raw = urlopen(sse_req, timeout=3).read().decode()
    check(sse_raw.startswith("event: message"), "SSE streamable HTTP initialize")

    call = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "read_board", "arguments": {}},
        }
    ).encode()
    rpc_req = Request(
        f"http://{host}:{port}/mcp",
        data=call,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer tok-c2",
        },
        method="POST",
    )
    rpc = json.loads(urlopen(rpc_req, timeout=3).read().decode())
    check(rpc["result"]["isError"] is False, "HTTP tools/call read_board")

    denied = json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "run_build", "arguments": {}}}).encode()
    den_req = Request(
        f"http://{host}:{port}/mcp",
        data=denied,
        headers={"Content-Type": "application/json", "Authorization": "Bearer tok-c2"},
        method="POST",
    )
    den = json.loads(urlopen(den_req, timeout=3).read().decode())
    check(den["result"]["isError"] is True, "HTTP run_build denied")

    try:
        urlopen(
            Request(
                f"http://{host}:{port}/mcp",
                data=call,
                headers={"Content-Type": "application/json", "Authorization": "Bearer nope"},
                method="POST",
            ),
            timeout=3,
        )
        # JSON-RPC still 200 with error object
    except HTTPError:
        pass
    unauth = handle_rpc(gw, "nope", {"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {"name": "read_board"}})
    check("UNAUTHENTICATED" in json.dumps(unauth), "unauthenticated JSON-RPC")

    httpd.shutdown()

    print("raios_mcp_check: PASS")
    print(
        json.dumps(
            {
                "slice": "C2 read_board/read_receipt/post_opinion; C1 read opinion",
                "gl005_proven": False,
                "wal_written": False,
                "sqlite": False,
                "websocket": False,
                "tools": list(V1_TOOLS),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
