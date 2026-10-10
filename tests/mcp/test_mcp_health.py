from pathlib import Path
import json
import os
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_mcp.gateway import REGISTERED_TOOLS, Gateway, V1_TOOLS  # noqa: E402
from raios_mcp.server import CENSUS_PORT, Handler, canonical_head  # noqa: E402


def test_census_port_is_8788_one_gateway():
    assert CENSUS_PORT == 8788


def test_policy_manifest_matches_registered_nine_tool_contract():
    policy = json.loads(
        (Path(__file__).resolve().parents[2] / ".ai-os/mcp/POLICY.json").read_text(
            encoding="utf-8"
        )
    )
    assert policy["v1_tools"] == list(V1_TOOLS)
    assert policy["v1_tools"] == list(REGISTERED_TOOLS)
    assert policy["v1_tools"][-1] == "execute_scoped_task"
    assert len(policy["v1_tools"]) == 9


def test_canonical_head_does_not_trust_env_without_git(monkeypatch, tmp_path):
    monkeypatch.setenv("RAIOS_CANONICAL_HEAD", "a" * 40)
    assert canonical_head(tmp_path) == ("unknown", "unknown")


def test_canonical_head_tracks_git_when_env_is_stale(monkeypatch, tmp_path):
    monkeypatch.setenv("RAIOS_CANONICAL_HEAD", "a" * 40)
    git = tmp_path / ".git"
    ref = git / "refs" / "heads" / "main"
    ref.parent.mkdir(parents=True)
    (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    ref.write_text("b" * 40, encoding="utf-8")
    assert canonical_head(tmp_path) == ("b" * 40, "git-file")
    ref.write_text("c" * 40, encoding="utf-8")
    assert canonical_head(tmp_path) == ("c" * 40, "git-file")


def test_canonical_head_rejects_malformed_git_with_env(monkeypatch, tmp_path):
    monkeypatch.setenv("RAIOS_CANONICAL_HEAD", "a" * 40)
    git = tmp_path / ".git"
    git.mkdir()
    (git / "HEAD").write_text("z" * 40, encoding="utf-8")
    assert canonical_head(tmp_path) == ("unknown", "unknown")


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


def test_health_http_lists_nine_tools(tmp_path):
    Handler.gateway = Gateway.from_root(tmp_path, grants=[])
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = httpd.server_address[:2]
        health = json.loads(urlopen(f"http://{host}:{port}/health", timeout=3).read().decode())
        assert health["ok"] is True
        assert health["tool_count"] == 9
        assert health["tools"] == list(V1_TOOLS)
        assert health["tools"] == [
            "get_head",
            "read_board",
            "read_inbox",
            "read_receipt",
            "get_diff",
            "post_opinion",
            "send_packet",
            "ack_packet",
            "execute_scoped_task",
        ]
        assert "compiled_service_marker" not in health
        assert health["execute_scoped_task"] is True
        assert health["ninth_tool"] is True
        assert health["raw_shell"] is False
        assert health["shell_via_mcp"] is False
        assert health["send_packet_execution"] == "TEMPORARY_COMPATIBILITY"
        assert health["tools"] == list(REGISTERED_TOOLS)
        assert health["duplicate_mcp"] is False
        assert health["generation_duplicate_mcp"] is False
        assert health["generation_duplicate_mcp"] == health["duplicate_mcp"]
        assert health["hosted_dcr_required"] is False
        assert health["second_gateway"] is False
        assert health["head_source"] in {"env", "git-file", "unknown"}
        assert health["external_connector_state_valid"] is True
        assert health["external_connector_contract_valid"] is False
        assert health["external_connector_binding_count"] == 0
        assert health["external_connector_active_binding_count"] == 0
        assert health["external_connector_pending_count"] == 0
        assert health["chatgpt_native_binding_active"] is False
        assert health["chatgpt_native_delegate_token_present"] is False
        assert health["chatgpt_native_delegate_binding_matches"] is False
        assert health["external_connector_token_store_valid"] is False
        assert health["external_connector_error"] == "CONNECTOR_CONTRACT_INVALID"
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


def test_get_head_reads_git_file_inside_deadline(tmp_path):
    subprocess.run(["git", "init", "-b", "test-mcp"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.name=MCP Test", "-c", "user.email=mcp@test.invalid", "commit", "--allow-empty", "-m", "fixture"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    Handler.gateway = Gateway.from_root(tmp_path, grants=[])
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = httpd.server_address[:2]
        body = json.dumps(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "get_head", "arguments": {}}}
        ).encode()
        from urllib.request import Request
        reply = json.loads(urlopen(Request(
            f"http://{host}:{port}/mcp",
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        ), timeout=20).read().decode())
        assert reply["result"]["isError"] is False
        metadata = json.loads(reply["result"]["content"][0]["text"])
        expected = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
        assert metadata["head"] == expected
        assert metadata["head_source"] == "git-file"
        assert metadata["branch"] == "test-mcp"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=3)


def test_loopback_cannot_execute_scoped_task(tmp_path):
    Handler.gateway = Gateway.from_root(tmp_path, grants=[])
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = httpd.server_address[:2]
        body = json.dumps({
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "execute_scoped_task",
                "arguments": {
                    "provider": "desktop_commander",
                    "capability": "remote",
                    "operation": "__list_tools__",
                    "execution_intent": "SCOPED",
                    "authority_scope": "REMOTE_CAPABILITY_READ",
                },
            },
        }).encode()
        from urllib.request import Request
        reply = json.loads(urlopen(Request(
            f"http://{host}:{port}/mcp",
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        ), timeout=3).read().decode())
        assert "UNAUTHENTICATED" in str(reply.get("error") or reply)
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=3)
