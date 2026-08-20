#!/usr/bin/env python3
"""Security acceptance for MCP V1. Local contract only. Does not prove external ChatGPT C2."""
from __future__ import annotations

import json
import ssl
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ai-os"))

from raios_mcp.gateway import Gateway, write_envelope  # noqa: E402
from raios_mcp.server import Handler  # noqa: E402


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit("FAIL: " + msg)
    print("ok:", msg)


def grants(future: str) -> list[dict]:
    return [
        {"actor_id": "C1", "token": "tok-c1", "expires_at": future},
        {"actor_id": "C2", "token": "tok-c2", "expires_at": future},
    ]


def rpc_call(gw: Gateway, token: str | None, tool: str, arguments: dict | None = None) -> dict:
    return handle_rpc(
        gw,
        token,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments or {}},
        },
    )


def is_denied(reply: dict) -> bool:
    blob = json.dumps(reply)
    return (
        reply.get("error", {}).get("code") == -32001
        or '"isError": true' in blob.replace(" ", "")
        or "UNAUTHENTICATED" in blob
        or "CAPABILITY_DENIED" in blob
        or "TOOL_NOT_FOUND" in blob
        or "STALE_HEAD" in blob
        or "IDENTITY_MISMATCH" in blob
        or "ESCALATION_DENIED" in blob
    )


def is_ok_tool(reply: dict) -> bool:
    result = reply.get("result") or {}
    if result.get("isError"):
        return False
    text = (result.get("content") or [{}])[0].get("text") or "{}"
    payload = json.loads(text)
    return payload.get("ok") is True


def payload(reply: dict) -> dict:
    text = (reply.get("result") or {}).get("content", [{}])[0].get("text") or "{}"
    return json.loads(text)


def make_tls_pair(dirpath: Path) -> tuple[str, str]:
    cert = dirpath / "cert.pem"
    key = dirpath / "key.pem"
    subprocess.check_call(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            "1",
            "-nodes",
            "-subj",
            "/CN=localhost",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return str(cert), str(key)


def main() -> int:
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    wal = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
    wal_before = wal.stat().st_mtime if wal.exists() else None
    gw = Gateway.from_root(ROOT, grants=grants(future))
    c2 = gw.authenticate("tok-c2")
    c1 = gw.authenticate("tok-c1")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()

    anon = rpc_call(gw, None, "get_head")
    check(is_denied(anon), "1 anonymous request DENIED")

    got = rpc_call(gw, "tok-c2", "get_head")
    check(is_ok_tool(got) and payload(got)["head"] == head, "2 C2 get_head ALLOWED")

    board = rpc_call(gw, "tok-c2", "read_board")
    check(is_ok_tool(board), "3 C2 read_board ALLOWED")

    receipt = rpc_call(gw, "tok-c2", "read_receipt", {"name": "GL005-MUTATION-OBSERVE.json"})
    check(is_ok_tool(receipt) and payload(receipt)["gl005_proven"] is False, "C2 read_receipt ALLOWED, proven false")

    env = write_envelope(c2, head, {"text": "C2 local security-accept opinion. Not external ChatGPT. GL005 stays false."})
    posted = rpc_call(gw, "tok-c2", "post_opinion", env)
    check(is_ok_tool(posted) and payload(posted)["wal_written"] is False, "4 C2 post_opinion ALLOWED")
    check(payload(posted).get("receipt_sha256"), "9 write produces receipt")

    seen = gw.call(c1, "read_board", {})
    local_seen = any("security-accept opinion" in str(o.get("text", "")) for o in seen["opinions"])
    check(local_seen, "C1 reads local C2 opinion (not external)")

    check(is_denied(rpc_call(gw, "tok-c2", "write_product", {})), "5 C2 product-code write DENIED")
    check(is_denied(rpc_call(gw, "tok-c2", "run_targeted_test", {})), "6 C2 execute test DENIED")
    check(is_denied(rpc_call(gw, "tok-c2", "run_build", {})), "6b C2 execute build DENIED")
    stale = write_envelope(c2, "0" * 40, {"text": "stale mutation"})
    check(is_denied(rpc_call(gw, "tok-c2", "post_opinion", stale)), "7 C2 stale-head mutation DENIED")
    esc = write_envelope(c2, head, {"text": "role change", "actor_id": "C0", "actor_role": "OWNER"})
    check(is_denied(rpc_call(gw, "tok-c2", "post_opinion", esc)), "8 C2 cannot self-change role/scope")

    Handler.gateway = gw
    with tempfile.TemporaryDirectory() as tmp:
        cert, key = make_tls_pair(Path(tmp))
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(cert, key)
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        host, port = httpd.server_address[:2]
        ssl_ctx = ssl._create_unverified_context()
        health = json.loads(
            urlopen(f"https://{host}:{port}/health", context=ssl_ctx, timeout=3).read().decode()
        )
        check(health.get("remote_c2_ready") is False, "health remote_c2_ready false")
        check(health.get("sqlite") is False, "no sqlite advertised")
        req = Request(
            f"https://{host}:{port}/mcp",
            data=json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "get_head", "arguments": {}}}).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer tok-c2"},
            method="POST",
        )
        tls_reply = json.loads(urlopen(req, context=ssl_ctx, timeout=3).read().decode())
        check(is_ok_tool(tls_reply), "9 TLS request to SAME server produces normal result")
        httpd.shutdown()

    wal_after = wal.stat().st_mtime if wal.exists() else None
    check(wal_before == wal_after, "10 no Cognitive WAL write from transport")
    check(not list(ROOT.glob("**/*.sqlite")), "no sqlite db")

    out = {
        "schema": "raios.mcp-v1-security-accept.v1",
        "MCP_HEAD": head,
        "MCP_ENDPOINT_LOCAL": "http://127.0.0.1:8787/mcp",
        "MCP_ENDPOINT_REMOTE": "NONE",
        "REMOTE_AUTH": "SCOPED_BEARER_NOT_OAUTH",
        "REAL_C2_CONNECTION_READY": False,
        "C2_READ_HEAD": True,
        "C2_READ_BOARD": True,
        "C2_READ_RECEIPT": True,
        "C2_POST_OPINION": True,
        "C1_READ_EXTERNAL_C2_OPINION": False,
        "C2_PRODUCT_WRITE_DENIED": True,
        "C2_EXECUTION_DENIED": True,
        "STALE_HEAD_DENIED": True,
        "SECOND_WAL_CREATED": False,
        "SECOND_DB_CREATED": False,
        "GL005_PROVEN": False,
        "NEXT_TRUE_GAP": "PROVE_REAL_EXTERNAL_C2_CONNECTIVITY",
        "tls_local_same_server": True,
        "public_https_hostname": None,
    }
    dest = ROOT / ".ai-os" / "receipts" / "GL-MCP-V1-REMOTE-GAP.json"
    dest.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print("SECURITY_RECEIPT", dest)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
