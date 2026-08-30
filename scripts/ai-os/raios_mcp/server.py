"""RAIOS Universal MCP V1: Streamable HTTP + stdio. No WebSocket. No SQLite. No second WAL."""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from raios_mcp.gateway import LAW, V1_TOOLS, Gateway, GatewayError  # noqa: E402

PROTOCOL = "2025-03-26"


def default_gateway() -> Gateway:
    tokens = {}
    actor = os.environ.get("RAIOS_MCP_ACTOR")
    token = os.environ.get("RAIOS_MCP_TOKEN")
    if actor and token:
        tokens[actor] = token
    return Gateway.from_root(ROOT, tokens or None)


def jsonrpc_result(req_id, result=None, error=None) -> dict:
    if error is not None:
        return {"jsonrpc": "2.0", "id": req_id, "error": error}
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def handle_rpc(gw: Gateway, actor_token: str | None, message: dict) -> dict | None:
    method = message.get("method")
    req_id = message.get("id")
    if method is None:
        return jsonrpc_result(req_id, error={"code": -32600, "message": "invalid request"})
    if str(method).startswith("notifications/"):
        return None
    if method == "initialize":
        return jsonrpc_result(
            req_id,
            {
                "protocolVersion": PROTOCOL,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "raios-universal-mcp", "version": "1.0.0"},
                "instructions": (
                    f"{LAW}. Streamable HTTP. ChatGPT Apps / Developer Mode remote MCP. "
                    "No WebSocket. No SQLite. No raw shell. No PASS writes. Authority ≠ bypass invariants."
                ),
            },
        )
    if method == "ping":
        return jsonrpc_result(req_id, {})
    if method == "tools/list":
        return jsonrpc_result(req_id, {"tools": gw.tool_schemas()})
    if method == "tools/call":
        try:
            actor = gw.authenticate(actor_token)
        except GatewayError as err:
            return jsonrpc_result(req_id, error={"code": -32001, "message": err.code + ": " + err.message})
        params = message.get("params") or {}
        try:
            result = gw.call(actor, params.get("name"), params.get("arguments") or {})
            return jsonrpc_result(
                req_id,
                {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}], "isError": False},
            )
        except GatewayError as err:
            payload = {"ok": False, "error": err.code, "message": err.message, "gl005_proven": False, "law": LAW}
            return jsonrpc_result(
                req_id,
                {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}], "isError": True},
            )
    return jsonrpc_result(req_id, error={"code": -32601, "message": f"method not found: {method}"})


def _read_stdio_message() -> dict | None:
    header = b""
    while b"\r\n\r\n" not in header:
        chunk = sys.stdin.buffer.read(1)
        if not chunk:
            return None
        header += chunk
        if header.endswith(b"\n") and b"Content-Length:" not in header and header.count(b"\n") == 1:
            line = header.decode("utf-8").strip()
            return json.loads(line) if line else None
    length = None
    for raw in header.decode("utf-8", errors="replace").split("\r\n"):
        if raw.lower().startswith("content-length:"):
            length = int(raw.split(":", 1)[1].strip())
    if length is None:
        return None
    body = sys.stdin.buffer.read(length)
    return json.loads(body.decode("utf-8"))


def _write_stdio_message(msg: dict) -> None:
    data = json.dumps(msg, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(data)}\r\n\r\n".encode("ascii") + data)
    sys.stdout.buffer.flush()


def serve_stdio(gw: Gateway) -> int:
    token = os.environ.get("RAIOS_MCP_TOKEN")
    while True:
        message = _read_stdio_message()
        if message is None:
            return 0
        reply = handle_rpc(gw, token, message)
        if reply is not None:
            _write_stdio_message(reply)


def sse_wrap(payload: dict) -> bytes:
    return f"event: message\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    gateway: Gateway

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("mcp-http: " + (fmt % args) + "\n")

    def _token(self) -> str | None:
        header = self.headers.get("Authorization") or ""
        if header.lower().startswith("bearer "):
            return header.split(" ", 1)[1].strip()
        return self.headers.get("X-RAIOS-TOKEN")

    def _send_bytes(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("mcp-session-id", self.headers.get("mcp-session-id") or "stateless")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, code: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(code, data, "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/health", "/"}:
            import subprocess

            try:
                head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
            except Exception:
                head = "unknown"
            self._send_json(
                200,
                {
                    "ok": True,
                    "service": "raios-universal-mcp",
                    "transport": "streamable-http",
                    "websocket": False,
                    "sqlite": False,
                    "law": LAW,
                    "gl005_proven": False,
                    "remote_c2_ready": False,
                    "endpoint_local": True,
                    "head": head,
                    "tools": list(V1_TOOLS),
                },
            )
            return
        if path in {"/council/live", "/council"}:
            live = ROOT / ".ai-os" / "council" / "LIVE.md"
            body = live.read_text(encoding="utf-8") if live.exists() else "NO_MEETING\n"
            self._send_bytes(200, body.encode("utf-8"), "text/markdown; charset=utf-8")
            return
        if path == "/council/call.json":
            meeting = ROOT / ".ai-os" / "council" / "MEETING.json"
            payload = json.loads(meeting.read_text(encoding="utf-8")) if meeting.exists() else {}
            payload = {
                "ok": True,
                "door": "whisper-seal",
                "gl005_proven": False,
                "council_operation_proven": False,
                "meeting_id": payload.get("meeting_id"),
                "case_hash": payload.get("case_hash"),
                "reply": "one line: SEAL Cx meeting_id challenge_id nonce SALT=... WORD=...",
            }
            self._send_json(200, payload)
            return
        if path == "/mcp":
            self._send_json(405, {"ok": False, "error": "GET_SSE_NOT_REQUIRED_STATELESS_V1"})
            return
        self._send_json(404, {"ok": False, "error": "NOT_FOUND"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/mcp":
            self._send_json(404, {"ok": False, "error": "NOT_FOUND", "hint": "POST /mcp Streamable HTTP"})
            return
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            message = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json(400, {"ok": False, "error": "INVALID_JSON"})
            return
        reply = handle_rpc(self.gateway, self._token(), message) or {"jsonrpc": "2.0", "result": None}
        accept = (self.headers.get("Accept") or "").lower()
        if "text/event-stream" in accept and "application/json" not in accept:
            self._send_bytes(200, sse_wrap(reply), "text/event-stream")
            return
        self._send_json(200, reply)


def serve_http(gw: Gateway, host: str, port: int, tls_cert: str | None = None, tls_key: str | None = None) -> None:
    Handler.gateway = gw
    httpd = ThreadingHTTPServer((host, port), Handler)
    scheme = "http"
    if tls_cert and tls_key:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(tls_cert, tls_key)
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
        scheme = "https"
    sys.stderr.write(
        f"raios-mcp streamable-http {scheme}://{host}:{port}/mcp health=/health "
        f"gl005_proven=false remote_c2_ready=false\n"
    )
    httpd.serve_forever()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--stdio", action="store_true")
    p.add_argument("--http", action="store_true")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8787)
    p.add_argument("--tls-cert", default=None)
    p.add_argument("--tls-key", default=None)
    args = p.parse_args()
    gw = default_gateway()
    if args.http:
        serve_http(gw, args.host, args.port, args.tls_cert, args.tls_key)
        return 0
    return serve_stdio(gw)


if __name__ == "__main__":
    raise SystemExit(main())
