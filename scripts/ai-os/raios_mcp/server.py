"""RAIOS Universal MCP V1: Streamable HTTP + stdio. No WebSocket. No SQLite. No second WAL."""
from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import time
import uuid
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from raios_mcp.gateway import LAW, LOOPBACK_READ_TOOLS, REGISTERED_TOOLS, Gateway, GatewayError  # noqa: E402

PROTOCOL = "2025-03-26"
SUPPORTED_PROTOCOL = ("2024-11-05", "2025-03-26", "2025-06-18")
CENSUS_PORT = 8788
SESSION_TTL_SECONDS = int(os.getenv("RAIOS_MCP_SESSION_TTL_SECONDS") or "3600")
MAX_REQUEST_BYTES = int(os.getenv("RAIOS_MCP_MAX_REQUEST_BYTES") or str(1024 * 1024))
MAX_SESSIONS = max(1, int(os.getenv("RAIOS_MCP_MAX_SESSIONS") or "4096"))
MAX_CONCURRENT_REQUESTS = max(1, int(os.getenv("RAIOS_MCP_MAX_CONCURRENT_REQUESTS") or "64"))
REQUEST_IO_TIMEOUT_SECONDS = max(.1, float(os.getenv("RAIOS_MCP_REQUEST_IO_TIMEOUT_SECONDS") or "5"))
SESSIONS: dict[str, float] = {}
SESSIONS_LOCK = threading.RLock()
REQUEST_SLOTS = threading.BoundedSemaphore(MAX_CONCURRENT_REQUESTS)
METRICS_LOCK = threading.Lock()
METRICS = {"requests_total": 0, "rejected_busy_total": 0, "sessions_evicted_total": 0}
STARTED_AT = time.time()
CORS_HEADERS = "Content-Type, Authorization, X-RAIOS-TOKEN, Accept, mcp-session-id, Mcp-Session-Id, Mcp-Protocol-Version"


def negotiate_protocol(requested: object) -> str:
    ver = str(requested or "").strip()
    if ver in SUPPORTED_PROTOCOL:
        return ver
    return PROTOCOL


def _metric(name: str, amount: int = 1) -> None:
    with METRICS_LOCK:
        METRICS[name] = METRICS.get(name, 0) + amount


def prune_sessions(now: float | None = None) -> int:
    current = time.time() if now is None else now
    with SESSIONS_LOCK:
        expired = [sid for sid, touched in SESSIONS.items() if current - touched > SESSION_TTL_SECONDS]
        for sid in expired:
            SESSIONS.pop(sid, None)
        overflow = max(0, len(SESSIONS) - MAX_SESSIONS)
        if overflow:
            oldest = sorted(SESSIONS.items(), key=lambda item: item[1])[:overflow]
            for sid, _ in oldest:
                SESSIONS.pop(sid, None)
            _metric("sessions_evicted_total", overflow)
        return len(expired) + overflow


def issue_session(existing: str | None) -> str:
    now = time.time()
    prune_sessions(now)
    sid = str(existing or "").strip()
    with SESSIONS_LOCK:
        if sid and sid.lower() != "stateless" and sid in SESSIONS:
            SESSIONS[sid] = now
            return sid
        if len(SESSIONS) >= MAX_SESSIONS:
            oldest = min(SESSIONS, key=SESSIONS.get)
            SESSIONS.pop(oldest, None)
            _metric("sessions_evicted_total")
        sid = uuid.uuid4().hex
        SESSIONS[sid] = now
        return sid


def canonical_head(root: Path | None = None) -> tuple[str, str]:
    """Read real Git metadata, including worktrees, without Git or stale env."""
    git_dir = (root or ROOT) / '.git'
    try:
        if git_dir.is_file():
            marker = git_dir.read_text(encoding='utf-8').strip()
            if not marker.startswith('gitdir:'):
                return 'unknown', 'unknown'
            target = Path(marker.split(':', 1)[1].strip())
            git_dir = target if target.is_absolute() else git_dir.parent / target
        common_dir = git_dir
        if (git_dir / 'commondir').is_file():
            target = Path((git_dir / 'commondir').read_text(encoding='utf-8').strip())
            common_dir = target if target.is_absolute() else git_dir / target
        raw = (git_dir / 'HEAD').read_text(encoding='utf-8').strip()
        if raw.startswith('ref:'):
            ref = raw.split(':', 1)[1].strip()
            if not ref.startswith('refs/') or any(p in {'', '.', '..'} for p in ref.split('/')) or '\\' in ref:
                return 'unknown', 'unknown'
            sha = None
            for directory in (git_dir, common_dir):
                path = directory.joinpath(*ref.split('/'))
                if path.is_file():
                    sha = path.read_text(encoding='utf-8').strip()
                    break
            if sha is None:
                for line in (common_dir / 'packed-refs').read_text(encoding='utf-8').splitlines():
                    if line.startswith(('#', '^')):
                        continue
                    fields = line.split()
                    if len(fields) == 2 and fields[1] == ref:
                        sha = fields[0]
                        break
        else:
            sha = raw
        if isinstance(sha, str) and re.fullmatch(r'[0-9a-fA-F]{40}', sha):
            return sha.lower(), 'git-file'
    except (OSError, UnicodeError, ValueError):
        pass
    return 'unknown', 'unknown'


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


def _log_rpc_failure(err: Exception) -> str:
    """Correlate failures without logging tokens, arguments, file contents or stderr."""
    error_id = uuid.uuid4().hex
    cause = err.__cause__ or err
    try:
        sys.stderr.write(f"mcp-rpc: error_id={error_id} exception={type(cause).__name__}\n")
    except (OSError, ValueError):
        # A diagnostic sink failure must not break the protocol error response.
        pass
    return error_id


def _tool_error(req_id, code: str, message: str, error_id: str | None = None) -> dict:
    payload = {"ok": False, "error": code, "message": message, "gl005_proven": False, "law": LAW}
    if error_id:
        payload["error_id"] = error_id
    return jsonrpc_result(
        req_id,
        {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}], "isError": True},
    )


def handle_rpc(gw: Gateway, actor_token: str | None, message: object, loopback: bool = False) -> dict | None:
    """Shared HTTP/stdio exception boundary; ordinary failures never close the channel."""
    if not isinstance(message, dict):
        return jsonrpc_result(None, error={"code": -32600, "message": "invalid request"})
    req_id = message.get("id")
    if req_id is not None and (isinstance(req_id, bool) or not isinstance(req_id, (str, int, float))):
        return jsonrpc_result(None, error={"code": -32600, "message": "invalid request id"})
    try:
        return _handle_rpc(gw, actor_token, message, loopback)
    except Exception as err:
        error_id = _log_rpc_failure(err)
        return jsonrpc_result(req_id, error={
            "code": -32603, "message": "Internal server error",
            "data": {"error_id": error_id, "gl005_proven": False},
        })


def _handle_rpc(gw: Gateway, actor_token: str | None, message: dict, loopback: bool) -> dict | None:
    method = message.get("method")
    req_id = message.get("id")
    if not isinstance(method, str) or not method:
        return jsonrpc_result(req_id, error={"code": -32600, "message": "invalid request"})
    if str(method).startswith("notifications/"):
        return None
    if method == "initialize":
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        proto = negotiate_protocol(params.get("protocolVersion"))
        return jsonrpc_result(
            req_id,
            {
                "protocolVersion": proto,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "raios-universal-mcp", "version": "1.1.0"},
                "instructions": (
                    f"{LAW}. Streamable HTTP session channel. POST /mcp JSON-RPC; GET /mcp SSE; "
                    "loopback reads without token; writes need an actor grant. Remote execution uses "
                    "execute_scoped_task through policy-allowlisted providers only. No WebSocket. "
                    "No SQLite. No raw shell. No PASS writes. Authority ≠ bypass invariants."
                ),
            },
        )
    if method == "ping":
        return jsonrpc_result(req_id, {})
    if method == "tools/list":
        return jsonrpc_result(req_id, {"tools": gw.tool_schemas()})
    if method == "tools/call":
        params = message.get("params", {})
        if not isinstance(params, dict):
            return jsonrpc_result(req_id, error={"code": -32602, "message": "tool params must be an object"})
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or not name or not isinstance(arguments, dict):
            return jsonrpc_result(req_id, error={"code": -32602, "message": "tool name and object arguments required"})
        try:
            actor = gw.authenticate(actor_token)
        except GatewayError as err:
            if loopback and not actor_token and name in LOOPBACK_READ_TOOLS:
                actor = gw.loopback_reader()
            else:
                return jsonrpc_result(req_id, error={"code": -32001, "message": err.code + ": " + err.message})
        try:
            result = gw.call(actor, name, arguments)
            return jsonrpc_result(
                req_id,
                {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}], "isError": False},
            )
        except GatewayError as err:
            error_id = _log_rpc_failure(err) if err.__cause__ else None
            return _tool_error(req_id, err.code, err.message, error_id)
        except Exception as err:
            return _tool_error(
                req_id, "INTERNAL_ERROR",
                "Tool execution failed. The operation may have completed; reconcile mutation outcomes before retrying.",
                _log_rpc_failure(err),
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
    try:
        while True:
            message = _read_stdio_message()
            if message is None:
                return 0
            reply = handle_rpc(gw, token, message)
            if reply is not None:
                _write_stdio_message(reply)
    finally:
        gw.close()


def sse_wrap(payload: dict) -> bytes:
    return f"event: message\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    gateway: Gateway

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(REQUEST_IO_TIMEOUT_SECONDS)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("mcp-http: " + (fmt % args) + "\n")

    def _token(self) -> str | None:
        header = self.headers.get("Authorization") or ""
        if header.lower().startswith("bearer "):
            return header.split(" ", 1)[1].strip()
        return self.headers.get("X-RAIOS-TOKEN")

    def _loopback(self) -> bool:
        host = str(self.client_address[0] if self.client_address else "")
        return host in {"127.0.0.1", "::1", "localhost"}

    def _session(self) -> str:
        return issue_session(self.headers.get("mcp-session-id") or self.headers.get("Mcp-Session-Id"))

    def _cors(self, session: str | None = None) -> None:
        if session is None:
            raw = (self.headers.get("mcp-session-id") or self.headers.get("Mcp-Session-Id") or "").strip()
            sid = raw if raw and raw.lower() != "stateless" else "none"
        else:
            sid = session
        self.send_header("mcp-session-id", sid)
        self.send_header("Mcp-Protocol-Version", PROTOCOL)
        origin = (self.headers.get("Origin") or "").strip()
        if origin and self._loopback() and origin.startswith(("http://127.0.0.1", "http://localhost", "https://127.0.0.1", "https://localhost")):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", CORS_HEADERS)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")

    def _send_bytes(self, code: int, body: bytes, content_type: str, session: str | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self._cors(session)
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()

    def _send_json(self, code: int, payload: dict, session: str | None = None) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(code, data, "application/json; charset=utf-8", session=session)

    def _open_sse_channel(self, session: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self._cors(session)
        self.end_headers()
        sock = self.connection
        try:
            sock.settimeout(2.0)
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()
            while True:
                try:
                    chunk = sock.recv(1)
                except TimeoutError:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    continue
                except OSError:
                    return
                if not chunk:
                    return
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError, OSError):
            return

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/health", "/", "/ready"}:
            head, head_source = canonical_head(ROOT)
            tools = [tool["name"] for tool in self.gateway.tool_schemas()]
            self._send_json(
                200,
                {
                    "ok": True,
                    "service": "raios-universal-mcp",
                    "transport": "streamable-http",
                    "websocket": False,
                    "sqlite": False,
                    "ninth_tool": "execute_scoped_task" in tools,
                    "transport_ready": True,
                    "execution_mode": "READ_ONLY",
                    "execution_ready": False,
                    "execution_ready_reason": "provider runtime must be probed through an authenticated scoped call",
                    "second_gateway": False,
                    "law": LAW,
                    "gl005_proven": False,
                    "remote_c2_ready": False,
                    "endpoint_local": str(self.server.server_address[0]) in {"127.0.0.1", "::1", "localhost"},
                    "external_gateway": str(self.server.server_address[0]) not in {"127.0.0.1", "::1", "localhost"},
                    "hosted_dcr_required": False,
                    "head": head,
                    "head_source": head_source,
                    "tool_count": len(tools),
                    "tools": tools,
                    "channel": "streamable-http-session",
                    "get_sse": True,
                    "stateless": False,
                    "session_count": len(SESSIONS),
                    "session_limit": MAX_SESSIONS,
                    "max_request_bytes": MAX_REQUEST_BYTES,
                    "max_concurrent_requests": MAX_CONCURRENT_REQUESTS,
                    "uptime_seconds": round(time.time() - STARTED_AT, 3),
                    "metrics": dict(METRICS),
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
            session = self._session()
            accept = (self.headers.get("Accept") or "").lower()
            if "text/event-stream" in accept:
                self._open_sse_channel(session)
                return
            self._send_json(
                200,
                {
                    "ok": True,
                    "service": "raios-universal-mcp",
                    "channel": "streamable-http-session",
                    "session": session,
                    "get_sse": True,
                    "stateless": False,
                    "ninth_tool": True,
                    "second_gateway": False,
                    "hosted_dcr_required": False,
                    "transport": "streamable-http",
                },
                session=session,
            )
            return
        self._send_json(404, {"ok": False, "error": "NOT_FOUND"})

    def do_DELETE(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/mcp":
            self._send_json(404, {"ok": False, "error": "NOT_FOUND"})
            return
        sid = (self.headers.get("mcp-session-id") or self.headers.get("Mcp-Session-Id") or "").strip()
        if sid:
            with SESSIONS_LOCK:
                SESSIONS.pop(sid, None)
        self.send_response(204)
        self._cors(sid or "closed")
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        _metric("requests_total")
        if not REQUEST_SLOTS.acquire(blocking=False):
            _metric("rejected_busy_total")
            self._send_json(503, {"ok": False, "error": "SERVER_BUSY", "retryable": True})
            return
        try:
            self._do_POST_bounded()
        finally:
            REQUEST_SLOTS.release()

    def _do_POST_bounded(self) -> None:
        path = urlparse(self.path).path
        session = self._session()
        if path != "/mcp":
            self._send_json(404, {"ok": False, "error": "NOT_FOUND", "hint": "POST /mcp Streamable HTTP"}, session=session)
            return
        try:
            length = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            self._send_json(400, {"ok": False, "error": "INVALID_CONTENT_LENGTH"}, session=session)
            return
        if length < 0 or length > MAX_REQUEST_BYTES:
            # Never drain an untrusted declared length. Close after the response.
            self.close_connection = True
            self._send_json(413, {"ok": False, "error": "REQUEST_TOO_LARGE", "max_bytes": MAX_REQUEST_BYTES}, session=session)
            return
        chunks = []
        remaining = length
        deadline = time.monotonic() + REQUEST_IO_TIMEOUT_SECONDS
        try:
            while remaining:
                budget = deadline - time.monotonic()
                if budget <= 0:
                    raise TimeoutError()
                self.connection.settimeout(budget)
                chunk = self.rfile.read1(min(remaining, 64 * 1024))
                if not chunk:
                    self.close_connection = True
                    self._send_json(400, {"ok": False, "error": "INCOMPLETE_BODY"}, session=session)
                    return
                chunks.append(chunk)
                remaining -= len(chunk)
        except TimeoutError:
            self.close_connection = True
            self._send_json(408, {"ok": False, "error": "REQUEST_TIMEOUT"}, session=session)
            return
        finally:
            self.connection.settimeout(REQUEST_IO_TIMEOUT_SECONDS)
        raw = b''.join(chunks) if length else b'{}'
        try:
            message = json.loads(raw.decode("utf-8") or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"ok": False, "error": "INVALID_JSON"}, session=session)
            return
        reply = handle_rpc(self.gateway, self._token(), message, loopback=self._loopback())
        if reply is None:
            self.send_response(202)
            self._cors(session)
            self.end_headers()
            return
        accept = (self.headers.get("Accept") or "").lower()
        if "text/event-stream" in accept and "application/json" not in accept:
            self._send_bytes(200, sse_wrap(reply), "text/event-stream", session=session)
            return
        self._send_json(200, reply, session=session)


class ReuseHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def serve_http(gw: Gateway, host: str, port: int, tls_cert: str | None = None, tls_key: str | None = None) -> None:
    Handler.gateway = gw
    httpd = ReuseHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
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
    stopping = threading.Event()
    def _stop(signum, frame):
        if stopping.is_set():
            return
        stopping.set()
        threading.Thread(target=httpd.shutdown, name="raios-mcp-shutdown", daemon=True).start()
    previous = {}
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            previous[sig] = signal.signal(sig, _stop)
        except (ValueError, OSError):
            pass
    try:
        httpd.serve_forever(poll_interval=0.25)
    finally:
        httpd.server_close()
        gw.close()
        for sig, handler in previous.items():
            try:
                signal.signal(sig, handler)
            except (ValueError, OSError):
                pass


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--stdio", action="store_true")
    p.add_argument("--http", action="store_true")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=CENSUS_PORT)
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
