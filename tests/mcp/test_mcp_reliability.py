import http.client
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/ai-os"))
from raios_mcp import gateway, server


def request(tool="read_board", arguments=None):
    return {"jsonrpc": "2.0", "id": 77, "method": "tools/call",
            "params": {"name": tool, "arguments": arguments or {}}}


def payload(reply):
    assert reply["id"] == 77
    assert reply["result"]["isError"] is True
    data = json.loads(reply["result"]["content"][0]["text"])
    assert data["ok"] is False
    assert data["gl005_proven"] is False
    return data


@pytest.fixture
def gw(tmp_path):
    return gateway.Gateway.from_root(tmp_path, grants=[])


@pytest.fixture
def http_server(gw):
    handler = type("TestHandler", (server.Handler,), {"gateway": gw})
    httpd = server.ReuseHTTPServer(("127.0.0.1", 0), handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=3)


def post(httpd, body, accept="application/json", session=None):
    conn = http.client.HTTPConnection(*httpd.server_address[:2], timeout=3)
    try:
        headers = {"Content-Type": "application/json", "Accept": accept}
        if session:
            headers["mcp-session-id"] = session
        conn.request("POST", "/mcp", body=body, headers=headers)
        resp = conn.getresponse()
        return resp.status, resp.read().decode(), resp.getheader("mcp-session-id")
    finally:
        conn.close()


def test_git_timeout_terminates_real_child(gw, monkeypatch, tmp_path):
    # Redirect only process launch to a deliberately stalled real child. Preserve
    # the production timeout and subprocess.run cleanup, rather than mocking them.
    real_run = subprocess.run
    started = tmp_path / "started"
    finished = tmp_path / "finished"
    child = ("import time; from pathlib import Path; "
             f"Path({str(started)!r}).touch(); time.sleep(1.5); Path({str(finished)!r}).touch()")
    def launch(cmd, **kwargs):
        return real_run([sys.executable, "-c", child], **kwargs)
    monkeypatch.setattr(gateway, "GIT_TIMEOUT_SECONDS", 0.3, raising=False)
    monkeypatch.setattr(gateway.subprocess, "run", launch)
    before = time.monotonic()
    reply = server.handle_rpc(gw, None, request("get_head"), loopback=True)
    assert payload(reply)["error"] == "GIT_TIMEOUT"
    assert time.monotonic() - before < 1.3
    assert started.exists()
    time.sleep(1.6)
    assert not finished.exists(), "Timed-out child must be killed and reaped"


def test_git_nonzero_does_not_return_empty_success(gw):
    assert payload(server.handle_rpc(gw, None, request("get_head"), loopback=True))["error"] == "GIT_FAILED"


def test_git_missing_is_structured(gw, monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError("PRIVATE_TOKEN_DO_NOT_PRINT")
    monkeypatch.setattr(gateway.subprocess, "run", missing)
    reply = server.handle_rpc(gw, None, request("get_head"), loopback=True)
    assert payload(reply)["error"] == "GIT_UNAVAILABLE"
    assert "PRIVATE_TOKEN" not in json.dumps(reply)


def test_corrupt_board_json_is_structured(gw, capsys):
    board = gw.root / ".ai-os/board"
    board.mkdir(parents=True)
    (board / "opinions.jsonl").write_text('PRIVATE_TOKEN_DO_NOT_PRINT', encoding="utf-8")
    reply = server.handle_rpc(gw, None, request(), loopback=True)
    data = payload(reply)
    assert data["error"] == "INTERNAL_ERROR"
    assert data["error_id"]
    diagnostic = capsys.readouterr().err
    assert data["error_id"] in diagnostic
    assert "JSONDecodeError" in diagnostic
    assert "PRIVATE_TOKEN" not in diagnostic + json.dumps(reply)


def test_board_read_failure_is_structured(gw, monkeypatch, capsys):
    board = gw.root / ".ai-os/board/NOW.md"
    board.parent.mkdir(parents=True)
    board.write_text("board", encoding="utf-8")
    read = Path.read_text
    def denied(path, *args, **kwargs):
        if path == board:
            raise PermissionError("PRIVATE_TOKEN_DO_NOT_PRINT")
        return read(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", denied)
    reply = server.handle_rpc(gw, None, request(), loopback=True)
    assert payload(reply)["error"] == "INTERNAL_ERROR"
    assert "PRIVATE_TOKEN" not in capsys.readouterr().err + json.dumps(reply)


def test_audit_failure_never_reports_success(gw):
    gw.audit_path.mkdir(parents=True)  # Deterministic filesystem failure, even under root.
    reply = server.handle_rpc(gw, None, request(), loopback=True)
    data = payload(reply)
    assert data["error"] == "AUDIT_UNAVAILABLE"
    assert "reconcil" in data["message"].lower()


def test_generic_execution_failure_does_not_escape(gw, monkeypatch, capsys):
    def broken(*args, **kwargs):
        raise RuntimeError("PRIVATE_TOKEN_DO_NOT_PRINT")
    monkeypatch.setattr(gw, "tool_read_board", broken)
    reply = server.handle_rpc(gw, None, request(), loopback=True)
    assert payload(reply)["error"] == "INTERNAL_ERROR"
    assert "PRIVATE_TOKEN" not in capsys.readouterr().err + json.dumps(reply)


def test_authentication_internal_failure_is_structured(gw, monkeypatch, capsys):
    def broken(*args):
        raise ValueError("PRIVATE_TOKEN_DO_NOT_PRINT")
    monkeypatch.setattr(gw, "authenticate", broken)
    reply = server.handle_rpc(gw, "token", request())
    assert reply["id"] == 77
    assert reply["error"]["code"] == -32603
    assert "PRIVATE_TOKEN" not in capsys.readouterr().err + json.dumps(reply)


def test_diagnostic_sink_failure_does_not_break_rpc_error(gw, monkeypatch):
    class BrokenSink:
        def write(self, text):
            raise OSError("diagnostic sink unavailable")
    def broken(*args, **kwargs):
        raise RuntimeError("PRIVATE_TOKEN_DO_NOT_PRINT")
    monkeypatch.setattr(gw, "tool_read_board", broken)
    monkeypatch.setattr(server.sys, "stderr", BrokenSink())
    assert payload(server.handle_rpc(gw, None, request(), loopback=True))["error"] == "INTERNAL_ERROR"


def test_policy_denial_remains_a_tool_error(gw):
    assert payload(server.handle_rpc(gw, None, request("read_receipt"), loopback=True))["error"] == "MISSING_IDENTITY"


def test_audit_failure_does_not_repeat_mutation(tmp_path):
    root = Path(__file__).resolve().parents[2]
    policy_dir = tmp_path / ".ai-os/mcp"
    policy_dir.mkdir(parents=True)
    (policy_dir / "POLICY.json").write_text((root / ".ai-os/mcp/POLICY.json").read_text(), encoding="utf-8")
    subprocess.run(["git", "init", "-b", "test-mcp"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "-c", "user.name=MCP Test", "-c", "user.email=mcp@test.invalid",
                    "commit", "--allow-empty", "-m", "fixture"], cwd=tmp_path, check=True, capture_output=True)
    gw = gateway.Gateway.from_root(tmp_path, grants=[{"actor_id": "C2", "token": "test-only-token"}])
    actor = gw.authenticate("test-only-token")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    envelope = gateway.write_envelope(actor, head, {"text": "Record exactly one opinion", "branch": "test-mcp"})
    gw.audit_path.mkdir()
    reply = server.handle_rpc(gw, "test-only-token", request("post_opinion", envelope))
    assert payload(reply)["error"] == "AUDIT_UNAVAILABLE"
    opinions = (tmp_path / ".ai-os/board/opinions.jsonl").read_text().splitlines()
    assert len(opinions) == 1
    assert json.loads(opinions[0])["packet_id"] == envelope["packet_id"]
    packets = (policy_dir / "packets.jsonl").read_text().splitlines()
    assert len(packets) == 1


@pytest.mark.parametrize("message", [[], None, "text", 42])
def test_invalid_rpc_shape_is_structured(gw, message):
    reply = server.handle_rpc(gw, None, message, loopback=True)
    assert reply["error"]["code"] == -32600


@pytest.mark.parametrize("params", [[], "text", {"name": "read_board", "arguments": []},
                                    {"name": "read_board", "arguments": "text"}, {"name": None}])
def test_invalid_tool_params_are_structured(gw, params):
    message = request()
    message["params"] = params
    assert server.handle_rpc(gw, None, message, loopback=True)["error"]["code"] == -32602


@pytest.mark.parametrize("accept", ["application/json", "text/event-stream"])
def test_http_runtime_failure_preserves_session_and_server(gw, http_server, accept):
    gw.audit_path.mkdir(parents=True)
    status, raw, sid = post(http_server, json.dumps(request()), accept)
    assert status == 200 and sid
    reply = json.loads(raw.split("data: ", 1)[1]) if accept == "text/event-stream" else json.loads(raw)
    assert payload(reply)["error"] == "AUDIT_UNAVAILABLE"
    gw.audit_path.rmdir()
    status, raw, next_sid = post(http_server, json.dumps(request()), session=sid)
    assert status == 200 and next_sid == sid
    assert json.loads(raw)["result"]["isError"] is False


def test_invalid_utf8_is_structured_and_http_survives(http_server):
    status, raw, sid = post(http_server, b'\xff')
    assert status == 400
    assert json.loads(raw)["error"] == "INVALID_JSON"
    status, raw, _ = post(http_server, json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}))
    assert status == 200 and json.loads(raw)["result"] == {}


def test_stdio_recovers_after_runtime_error(tmp_path):
    root = Path(__file__).resolve().parents[2]
    policy_dir = tmp_path / ".ai-os/mcp"
    policy_dir.mkdir(parents=True)
    (policy_dir / "POLICY.json").write_text((root / ".ai-os/mcp/POLICY.json").read_text(), encoding="utf-8")
    (policy_dir / "AUDIT.jsonl").mkdir()
    code = ("import sys, os; from pathlib import Path; "
            f"sys.path.insert(0, {str(root / 'scripts/ai-os')!r}); "
            "from raios_mcp.gateway import Gateway; from raios_mcp.server import serve_stdio; "
            f"gw=Gateway.from_root(Path({str(tmp_path)!r}), grants=[{{'actor_id':'C2','token':'test-only-token'}}]); "
            "os.environ['RAIOS_MCP_TOKEN']='test-only-token'; serve_stdio(gw)")
    messages = [request(), {"jsonrpc": "2.0", "id": 78, "method": "ping"}]
    stream = b""
    for message in messages:
        body = json.dumps(message).encode()
        stream += f"Content-Length: {len(body)}\r\n\r\n".encode() + body
    proc = subprocess.run([sys.executable, "-c", code], input=stream, capture_output=True, timeout=5)
    assert proc.returncode == 0, proc.stderr.decode()
    replies = []
    remaining = proc.stdout
    while remaining:
        header, body = remaining.split(b"\r\n\r\n", 1)
        length = int(header.split(b":", 1)[1])
        replies.append(json.loads(body[:length]))
        remaining = body[length:]
    assert len(replies) == 2
    assert payload(replies[0])["error"] == "AUDIT_UNAVAILABLE"
    assert replies[1] == {"jsonrpc": "2.0", "id": 78, "result": {}}
    assert b"test-only-token" not in proc.stdout + proc.stderr
