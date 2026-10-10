"""RAIOS Universal MCP V1: Streamable HTTP + stdio. No WebSocket. No SQLite. No second WAL."""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import uuid
import signal
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from raios_mcp.gateway import (  # noqa: E402
    LAW,
    LOOPBACK_READ_TOOLS,
    V1_TOOLS,
    Gateway,
    GatewayError,
    read_canonical_head,
    read_generation_handoff,
)

PROTOCOL = "2025-03-26"
SUPPORTED_PROTOCOL = ("2024-11-05", "2025-03-26", "2025-06-18")
CENSUS_PORT = 8788
SESSION_TTL_SECONDS = int(os.getenv("RAIOS_MCP_SESSION_TTL_SECONDS") or "3600")
MAX_REQUEST_BYTES = int(os.getenv("RAIOS_MCP_MAX_REQUEST_BYTES") or str(1024 * 1024))
MAX_SESSIONS = max(1, int(os.getenv("RAIOS_MCP_MAX_SESSIONS") or "4096"))
MAX_CONCURRENT_REQUESTS = max(1, int(os.getenv("RAIOS_MCP_MAX_CONCURRENT_REQUESTS") or "64"))
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
    """Live repository projection; launch-time env is not current Git truth."""
    return read_canonical_head(root or ROOT)


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
    """Correlate failures without logging tokens, arguments, file contents, or stderr bodies."""
    error_id = uuid.uuid4().hex
    cause = err.__cause__ or err
    frame_file = ""
    frame_line = 0
    frame_function = ""
    try:
        frames = traceback.extract_tb(cause.__traceback__ or err.__traceback__)
        if frames:
            frame = frames[-1]
            try:
                frame_file = str(Path(frame.filename).resolve().relative_to(ROOT.resolve()))
            except (OSError, ValueError):
                frame_file = Path(frame.filename).name
            frame_line = int(frame.lineno)
            frame_function = str(frame.name)
    except Exception:
        pass

    diagnostic = {
        "error_id": error_id,
        "exception": type(cause).__name__,
        "frame_file": frame_file,
        "frame_line": frame_line,
        "frame_function": frame_function,
    }

    try:
        sys.stderr.write(
            "mcp-rpc: "
            f"error_id={error_id} "
            f"exception={diagnostic['exception']} "
            f"frame={frame_file}:{frame_line} "
            f"function={frame_function}\n"
        )
    except (OSError, ValueError):
        pass

    # Durable, bounded-detail diagnostic receipt. Never include arguments,
    # exception messages, tokens, payloads, file contents, or environment.
    try:
        path = ROOT / ".ai-os" / "receipts" / "command-fabric" / "mcp-rpc-errors.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(diagnostic, ensure_ascii=False) + "\n")
    except (OSError, ValueError, TypeError):
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
    """Shared HTTP/stdio exception boundary. Ordinary failures do not close the channel."""
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
            "code": -32603,
            "message": "Internal server error",
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
                    "loopback reads without token; writes need an actor grant. "
                    "Governed execution is execute_scoped_task. send_packet execution is temporary compatibility. "
                    "Short grant, nonce, lease, and fence are required. No shell. No WebSocket. "
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
                req_id,
                "INTERNAL_ERROR",
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
        if path in {"/.well-known/oauth-protected-resource", "/.well-known/oauth-protected-resource/mcp"}:
            host = (self.headers.get("Host") or f"127.0.0.1:{CENSUS_PORT}").strip()
            scheme = "https" if isinstance(self.connection, ssl.SSLSocket) else "http"
            self._send_json(
                200,
                {
                    "resource": f"{scheme}://{host}/mcp",
                    "resource_name": "RAIOS Universal MCP",
                    "scopes_supported": [],
                },
            )
            return
        if path in {"/health", "/", "/ready"}:
            head, head_source = canonical_head(ROOT)
            tools = list(V1_TOOLS)
            connector_health = self.gateway.external_connector_health()
            generation_handoff = read_generation_handoff()
            self._send_json(
                200,
                {
                    "ok": True,
                    "service": "raios-universal-mcp",
                    "transport": "streamable-http",
                    "websocket": False,
                    "sqlite": False,
                    "ninth_tool": True,
                    "execute_scoped_task": True,
                    "raw_shell": False,
                    "shell_via_mcp": False,
                    "duplicate_mcp": bool(generation_handoff.get("duplicate_mcp") is True),
                    "generation_duplicate_mcp": bool(generation_handoff.get("duplicate_mcp") is True),
                    "generation_handoff": generation_handoff,
                    "generation_handoff_complete": generation_handoff.get("handoff_complete", False),
                    "generation_singleton_verdict": generation_handoff.get("singleton_verdict", "UNKNOWN"),
                    "generation_orphan_count": generation_handoff.get("orphan_generation_count"),
                    "generation_active_pid": generation_handoff.get("active_pid"),
                    "generation_candidate_pid": generation_handoff.get("candidate_pid"),
                    "generation_candidate_state": generation_handoff.get("candidate_state"),
                    "generation_candidate_relationship": generation_handoff.get("candidate_relationship"),
                    "generation_candidate_retirement_attempted": generation_handoff.get("candidate_retirement_attempted", False),
                    "generation_candidate_retirement_proven": generation_handoff.get("candidate_retirement_proven", False),
                    "generation_candidate_retirement_reason": generation_handoff.get("candidate_retirement_reason"),
                    "generation_repair_applied": generation_handoff.get("repair_applied", False),
                    "generation_previous_pid": generation_handoff.get("previous_pid"),
                    "mcp_process_pid": os.getpid(),
                    "scoped_execution": "EXECUTE_SCOPED_TASK",
                    "send_packet_execution": "TEMPORARY_COMPATIBILITY",
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
                    "external_connector_state_valid": bool(connector_health.get("state_valid")),
                    "external_connector_contract_valid": bool(connector_health.get("contract_valid")),
                    "external_connector_binding_count": int(connector_health.get("binding_count") or 0),
                    "external_connector_active_binding_count": int(connector_health.get("active_binding_count") or 0),
                    "external_connector_pending_count": int(connector_health.get("pending_count") or 0),
                    "chatgpt_native_binding_active": bool(connector_health.get("chatgpt_native_binding_active")),
                    "chatgpt_native_delegate_token_present": bool(connector_health.get("chatgpt_native_delegate_token_present")),
                    "chatgpt_native_delegate_binding_matches": bool(connector_health.get("chatgpt_native_delegate_binding_matches")),
                    "external_connector_token_store_valid": bool(connector_health.get("token_store_valid")),
                    "external_connector_error": connector_health.get("error"),
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
                    "execute_scoped_task": True,
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
            # Do not leave unread request bytes on Windows: that can reset the TCP
            # connection before the client receives the structured 413 response.
            remaining = max(length, 0)
            while remaining:
                chunk = self.rfile.read(min(remaining, 64 * 1024))
                if not chunk:
                    break
                remaining -= len(chunk)
            self._send_json(413, {"ok": False, "error": "REQUEST_TOO_LARGE", "max_bytes": MAX_REQUEST_BYTES}, session=session)
            return
        raw = self.rfile.read(length) if length else b"{}"
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
