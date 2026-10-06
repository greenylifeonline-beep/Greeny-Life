"""Generation lineage owns the MCP listener. PID equality does not."""

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

_MODULE = Path(__file__).resolve().parents[2] / "scripts" / "ai-os" / "raios_mcp_generation_identity.py"
_SPEC = importlib.util.spec_from_file_location("raios_mcp_generation_identity", _MODULE)
identity = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(identity)

T0 = datetime(2026, 10, 6, 15, 3, 8, tzinfo=timezone.utc)
SERVER = r"C:\repo\scripts\ai-os\raios_mcp\server.py"
VENV = r"C:\venv\Scripts\python.exe"
BASE = r"C:\Python314\python.exe"
SHA_A = "a" * 64
SHA_B = "b" * 64
HEAD = "9b5f1fb27e65f86daa90f821d32aee21e72d0b1b"


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat()


def _record(**overrides):
    record = {
        "schema": "raios.universal-mcp-launch.v1",
        "generation_id": "gen-1",
        "launcher_pid": 26308,
        "launcher_creation_time": _iso(T0),
        "launcher_command_line": f'"{VENV}" {SERVER} --http --port 8788',
        "launcher_executable": VENV,
        "service_pid": 30416,
        "service_generation": "svc-1",
        "canonical_head": HEAD,
        "server_sha256": SHA_A,
        "gateway_sha256": SHA_A,
        "policy_sha256": SHA_A,
        "tool_contract_sha256": SHA_A,
        "port": 8788,
        "expected_service": "raios-universal-mcp",
        "started_at": _iso(T0),
    }
    record.update(overrides)
    return record


def _observation(**overrides):
    observation = {
        "listener_pid": 26308,
        "listener_creation_time": _iso(T0),
        "listener_command_line": f'"{VENV}" {SERVER} --http --port 8788',
        "listener_executable": VENV,
        "parent_chain": [],
        "port": 8788,
        "listener_count": 1,
        "server_sha256": SHA_A,
        "gateway_sha256": SHA_A,
        "policy_sha256": SHA_A,
        "tool_contract_sha256": SHA_A,
        "canonical_head": HEAD,
        "service_generation": "svc-1",
        "current_generation_id": "gen-1",
        "health_ok": True,
    }
    observation.update(overrides)
    return observation


def test_a_same_pid_is_accepted():
    decision = identity.judge_mcp_generation(_record(), _observation())
    assert decision == {"accept": True, "reason": "ACCEPT_SAME_PROCESS"}


def test_b_venv_launcher_to_base_interpreter_is_accepted():
    decision = identity.judge_mcp_generation(
        _record(),
        _observation(
            listener_pid=22244,
            listener_creation_time=_iso(T0 + timedelta(seconds=1)),
            listener_command_line=f'"{BASE}" {SERVER} --http --port 8788',
            listener_executable=BASE,
            parent_chain=[{"pid": 26308, "creation_time": _iso(T0), "command_line": f'"{VENV}" {SERVER}'}],
        ),
    )
    assert decision == {"accept": True, "reason": "ACCEPT_EXEC_TRANSITION"}
    assert "MCP_LISTENER_PID_NOT_LAUNCH_PID" not in decision["reason"]


def test_c_unrelated_python_is_rejected():
    decision = identity.judge_mcp_generation(
        _record(),
        _observation(listener_pid=99999, parent_chain=[{"pid": 111, "creation_time": _iso(T0)}]),
    )
    assert decision == {"accept": False, "reason": "REJECT_UNRELATED_PROCESS"}


def test_d_descendant_outside_launch_window_is_rejected():
    decision = identity.judge_mcp_generation(
        _record(),
        _observation(
            listener_pid=22244,
            listener_creation_time=_iso(T0 + timedelta(minutes=10)),
            parent_chain=[{"pid": 26308, "creation_time": _iso(T0)}],
        ),
    )
    assert decision == {"accept": False, "reason": "REJECT_OUTSIDE_LAUNCH_WINDOW"}


def test_e_pid_reuse_with_different_creation_time_is_rejected():
    decision = identity.judge_mcp_generation(
        _record(),
        _observation(listener_creation_time=_iso(T0 + timedelta(seconds=30))),
    )
    assert decision == {"accept": False, "reason": "REJECT_PID_REUSE"}


def test_f_wrong_source_hash_is_rejected():
    decision = identity.judge_mcp_generation(
        _record(),
        _observation(
            listener_pid=22244,
            listener_creation_time=_iso(T0 + timedelta(seconds=1)),
            parent_chain=[{"pid": 26308, "creation_time": _iso(T0)}],
            server_sha256=SHA_B,
        ),
    )
    assert decision == {"accept": False, "reason": "REJECT_SOURCE_HASH_MISMATCH"}


def test_g_health_without_generation_is_rejected():
    decision = identity.judge_mcp_generation({"health_ok": True}, _observation())
    assert decision == {"accept": False, "reason": "REJECT_NO_GENERATION_PROVENANCE"}


def test_h_two_listeners_are_rejected():
    decision = identity.judge_mcp_generation(_record(), _observation(listener_count=2))
    assert decision == {"accept": False, "reason": "REJECT_COMPETING_LISTENER"}


def test_i_superseded_generation_cannot_reclaim():
    decision = identity.judge_mcp_generation(_record(superseded=True), _observation())
    assert decision == {"accept": False, "reason": "REJECT_SUPERSEDED_GENERATION"}
    rebound = identity.judge_mcp_generation(
        _record(listener_pid=22244, listener_creation_time=_iso(T0 + timedelta(seconds=1))),
        _observation(listener_pid=6812),
    )
    assert rebound == {"accept": False, "reason": "REJECT_SUPERSEDED_GENERATION"}
