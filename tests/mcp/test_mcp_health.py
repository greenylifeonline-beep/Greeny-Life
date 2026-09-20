from pathlib import Path
import json
import os
import sys
import threading
from http.server import ThreadingHTTPServer
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_mcp.gateway import Gateway, V1_TOOLS  # noqa: E402
from raios_mcp.server import CENSUS_PORT, Handler, canonical_head  # noqa: E402


def test_census_port_is_8788_one_gateway():
    assert CENSUS_PORT == 8788


def test_canonical_head_prefers_env(monkeypatch, tmp_path):
    monkeypatch.setenv("RAIOS_CANONICAL_HEAD", "abc123def456")
    sha, source = canonical_head(tmp_path)
    assert sha == "abc123def456"
    assert source == "env"


def test_canonical_head_reads_git_file_not_subprocess(monkeypatch, tmp_path):
    monkeypatch.delenv("RAIOS_CANONICAL_HEAD", raising=False)
    git = tmp_path / ".git"
    (git / "refs" / "heads").mkdir(parents=True)
    (git / "HEAD").write_text("ref: refs/heads/ai-evolution-202608051809\n", encoding="utf-8")
    (git / "refs" / "heads" / "ai-evolution-202608051809").write_text(
        "0fd7022a7b92ccc3d001a2e8041506cd4596468d\n", encoding="utf-8"
    )
    sha, source = canonical_head(tmp_path)
    assert sha == "0fd7022a7b92ccc3d001a2e8041506cd4596468d"
    assert source == "git-file"


def test_canonical_head_unknown_without_git(monkeypatch, tmp_path):
    monkeypatch.delenv("RAIOS_CANONICAL_HEAD", raising=False)
    sha, source = canonical_head(tmp_path)
    assert sha == "unknown"
    assert source == "unknown"


def test_health_http_is_fast_and_lists_eight_tools(tmp_path):
    Handler.gateway = Gateway.from_root(tmp_path, grants=[])
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = httpd.server_address[:2]
        health = json.loads(urlopen(f"http://{host}:{port}/health", timeout=3).read().decode())
        assert health["ok"] is True
        assert health["tool_count"] == 8
        assert health["tools"] == list(V1_TOOLS)
        assert health["ninth_tool"] is False
        assert health["second_gateway"] is False
        assert health["head_source"] in {"env", "git-file", "unknown"}
        init = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}).encode()
        from urllib.request import Request
        rpc = json.loads(
            urlopen(
                Request(
                    f"http://{host}:{port}/mcp",
                    data=init,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                    method="POST",
                ),
                timeout=3,
            ).read().decode()
        )
        assert rpc["result"]["serverInfo"]["name"] == "raios-universal-mcp"
        head_call = json.dumps(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "get_head", "arguments": {}}}
        ).encode()
        from urllib.request import Request
        read_rpc = json.loads(
            urlopen(
                Request(
                    f"http://{host}:{port}/mcp",
                    data=head_call,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                    method="POST",
                ),
                timeout=3,
            ).read().decode()
        )
        assert read_rpc["result"]["isError"] is False
        deny = json.dumps(
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "send_packet", "arguments": {"to": ["C2"], "text": "x"}}}
        ).encode()
        write_rpc = json.loads(
            urlopen(
                Request(
                    f"http://{host}:{port}/mcp",
                    data=deny,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                    method="POST",
                ),
                timeout=3,
            ).read().decode()
        )
        assert "UNAUTHENTICATED" in str(write_rpc.get("error") or write_rpc)
        assert health["get_sse"] is True
        assert health["stateless"] is False
        assert health["channel"] == "streamable-http-session"
    finally:
        httpd.shutdown()


def test_streamable_http_session_channel(tmp_path):
    import http.client

    Handler.gateway = Gateway.from_root(tmp_path, grants=[])
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = httpd.server_address[:2]
        conn = http.client.HTTPConnection(host, port, timeout=3)
        conn.request("GET", "/mcp", headers={"Accept": "application/json"})
        resp = conn.getresponse()
        payload = json.loads(resp.read().decode())
        sid = resp.getheader("mcp-session-id")
        assert resp.status == 200
        assert payload["ok"] is True
        assert payload["channel"] == "streamable-http-session"
        assert payload["get_sse"] is True
        assert sid and sid != "stateless"
        conn.close()

        conn = http.client.HTTPConnection(host, port, timeout=3)
        conn.request("GET", "/mcp", headers={"Accept": "text/event-stream", "mcp-session-id": sid})
        resp = conn.getresponse()
        assert resp.status == 200
        assert "text/event-stream" in (resp.getheader("Content-Type") or "")
        assert resp.getheader("mcp-session-id") == sid
        line = resp.fp.readline()
        assert line.startswith(b":")
        conn.close()

        init = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}},
            }
        ).encode()
        conn = http.client.HTTPConnection(host, port, timeout=3)
        conn.request(
            "POST",
            "/mcp",
            body=init,
            headers={"Content-Type": "application/json", "Accept": "application/json", "mcp-session-id": sid},
        )
        resp = conn.getresponse()
        body = json.loads(resp.read().decode())
        assert resp.status == 200
        assert resp.getheader("mcp-session-id") == sid
        assert body["result"]["protocolVersion"] == "2025-06-18"
        conn.close()

        note = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}).encode()
        conn = http.client.HTTPConnection(host, port, timeout=3)
        conn.request(
            "POST",
            "/mcp",
            body=note,
            headers={"Content-Type": "application/json", "Accept": "application/json", "mcp-session-id": sid},
        )
        resp = conn.getresponse()
        assert resp.status == 202
        conn.close()
    finally:
        httpd.shutdown()


def test_session_ttl_prunes_and_unknown_session_is_not_adopted(monkeypatch):
    import raios_mcp.server as server
    server.SESSIONS.clear()
    monkeypatch.setattr(server, "SESSION_TTL_SECONDS", 10)
    server.SESSIONS["expired"] = 1.0
    assert server.prune_sessions(now=20.0) == 1
    assert "expired" not in server.SESSIONS
    sid = server.issue_session("attacker-chosen-session")
    assert sid != "attacker-chosen-session"
    assert sid in server.SESSIONS


def test_http_rejects_oversize_request_and_does_not_wildcard_cors(tmp_path, monkeypatch):
    import http.client
    import raios_mcp.server as server
    monkeypatch.setattr(server, "MAX_REQUEST_BYTES", 64)
    server.Handler.gateway = Gateway.from_root(tmp_path, grants=[])
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = httpd.server_address[:2]
        conn = http.client.HTTPConnection(host, port, timeout=3)
        conn.request("POST", "/mcp", body=b"x" * 65, headers={"Content-Type": "application/json", "Origin": "https://evil.example"})
        resp = conn.getresponse()
        body = json.loads(resp.read().decode())
        assert resp.status == 413
        assert body["error"] == "REQUEST_TOO_LARGE"
        assert body["max_bytes"] == 64
        assert resp.getheader("Access-Control-Allow-Origin") != "*"
        assert resp.getheader("Access-Control-Allow-Origin") is None
        conn.close()
    finally:
        httpd.shutdown()


def test_session_capacity_evicts_oldest(monkeypatch):
    import raios_mcp.server as srv
    monkeypatch.setattr(srv, "MAX_SESSIONS", 2)
    srv.SESSIONS.clear()
    srv.SESSIONS.update({"old": 1.0, "newer": 2.0})
    monkeypatch.setattr(srv.time, "time", lambda: 3.0)
    sid = srv.issue_session(None)
    assert sid in srv.SESSIONS
    assert len(srv.SESSIONS) == 2
    assert "old" not in srv.SESSIONS


def test_health_exposes_production_bounds(tmp_path):
    import raios_mcp.server as srv
    srv.Handler.gateway = Gateway.from_root(tmp_path, grants=[])
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), srv.Handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = httpd.server_address[:2]
        body = json.loads(urlopen(f"http://{host}:{port}/ready", timeout=3).read().decode())
        assert body["ok"] is True
        assert body["session_limit"] == srv.MAX_SESSIONS
        assert body["max_concurrent_requests"] == srv.MAX_CONCURRENT_REQUESTS
        assert body["max_request_bytes"] == srv.MAX_REQUEST_BYTES
        assert "metrics" in body
        assert "uptime_seconds" in body
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=3)
