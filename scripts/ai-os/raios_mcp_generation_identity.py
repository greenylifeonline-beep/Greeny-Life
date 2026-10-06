"""MCP ownership is a launch generation, not a PID.

Laws:
PID_NE_PROCESS_IDENTITY
HEALTH_NE_OWNERSHIP
DESCENDANT_NE_OWNED_UNLESS_GENERATION_BOUND
VENV_LAUNCHER_NE_SOCKET_OWNER_IS_VALID
LAUNCH_PID_NE_LISTENER_PID
PROCESS_GENERATION_IS_AUTHORITY
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

LAUNCH_WINDOW = timedelta(seconds=20)
SAME_PROCESS_SKEW = timedelta(seconds=2)
SERVER_MARK_POSIX = "raios_mcp/server.py"


def _parse_time(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _exe_name(command: object, executable: object = None) -> str:
    if executable:
        return Path(str(executable).strip().strip('"')).name.lower()
    text = str(command or "").strip()
    if not text:
        return ""
    if text.startswith('"'):
        end = text.find('"', 1)
        token = text[1:end] if end > 1 else text
    else:
        token = text.split()[0]
    return Path(token.strip('"')).name.lower()


def _is_python(command: object, executable: object = None) -> bool:
    name = _exe_name(command, executable)
    return name in {"python.exe", "python", "pythonw.exe"}


def _command_has_server(command: object) -> bool:
    text = str(command or "").replace("/", "\\").lower()
    return "raios_mcp\\server.py" in text or SERVER_MARK_POSIX in str(command or "").lower()


def _as_int(value: object) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _hash_mismatch(record: dict, observation: dict, key: str, observed_key: str | None = None) -> bool:
    expected = str(record.get(key) or "").strip().lower()
    if not expected:
        return False
    observed = str(observation.get(observed_key or key) or "").strip().lower()
    if not observed:
        return True
    return expected != observed


def normalize_record(raw: dict | None) -> dict | None:
    if not isinstance(raw, dict) or not raw:
        return None
    if raw.get("health_ok") and not raw.get("pid") and not raw.get("launcher_pid") and not raw.get("generation_id"):
        return None
    launcher_pid = _as_int(raw.get("launcher_pid"))
    if launcher_pid is None:
        launcher_pid = _as_int(raw.get("pid"))
    if launcher_pid is None and not raw.get("generation_id"):
        return None
    command = raw.get("launcher_command_line") or raw.get("command_line")
    started = raw.get("launcher_creation_time") or raw.get("started_at")
    return {
        "schema": raw.get("schema") or "",
        "generation_id": raw.get("generation_id")
        or (
            f"legacy::{raw.get('c5_generation') or raw.get('service_generation')}::"
            f"{launcher_pid}::{started}"
        ),
        "launcher_pid": launcher_pid,
        "launcher_creation_time": started,
        "launcher_command_line": command,
        "launcher_executable": raw.get("launcher_executable") or _exe_name(command),
        "service_pid": _as_int(raw.get("service_pid")),
        "service_generation": raw.get("service_generation") or raw.get("c5_generation"),
        "canonical_head": raw.get("canonical_head"),
        "server_sha256": raw.get("server_sha256"),
        "gateway_sha256": raw.get("gateway_sha256"),
        "policy_sha256": raw.get("policy_sha256"),
        "tool_contract_sha256": raw.get("tool_contract_sha256"),
        "port": _as_int(raw.get("port")) or 8788,
        "expected_service": raw.get("expected_service") or "raios-universal-mcp",
        "started_at": raw.get("started_at") or started,
        "listener_pid": _as_int(raw.get("listener_pid")),
        "listener_creation_time": raw.get("listener_creation_time"),
        "listener_command_line": raw.get("listener_command_line"),
        "superseded": bool(raw.get("superseded") or raw.get("revoked")),
    }


def _chain_entry_matches_launcher(entry: dict, record: dict) -> str | None:
    if _as_int(entry.get("pid")) != record.get("launcher_pid"):
        return None
    observed = _parse_time(entry.get("creation_time"))
    expected = _parse_time(record.get("launcher_creation_time"))
    if observed is None or expected is None:
        return "REJECT_PID_REUSE"
    if abs(observed - expected) >= SAME_PROCESS_SKEW:
        return "REJECT_PID_REUSE"
    return "MATCH"


def judge_mcp_generation(record: dict | None, observation: dict | None) -> dict:
    """Return accept/reason. Health is ignored. PID equality is not required."""
    observation = observation or {}
    if observation.get("health_ok") and not record:
        return {"accept": False, "reason": "REJECT_NO_GENERATION_PROVENANCE"}
    normalized = normalize_record(record)
    if normalized is None or not normalized.get("generation_id") or not normalized.get("launcher_pid"):
        return {"accept": False, "reason": "REJECT_NO_GENERATION_PROVENANCE"}
    if normalized.get("superseded"):
        return {"accept": False, "reason": "REJECT_SUPERSEDED_GENERATION"}
    current_generation = observation.get("current_generation_id")
    if current_generation and normalized.get("generation_id") and str(current_generation) != str(normalized["generation_id"]):
        if not str(normalized["generation_id"]).startswith("legacy::"):
            return {"accept": False, "reason": "REJECT_SUPERSEDED_GENERATION"}
    service_generation = observation.get("service_generation")
    if service_generation and normalized.get("service_generation") and str(service_generation) != str(normalized["service_generation"]):
        return {"accept": False, "reason": "REJECT_SUPERSEDED_GENERATION"}
    try:
        listener_count = int(observation.get("listener_count") or 0)
    except (TypeError, ValueError):
        listener_count = 0
    if listener_count != 1 or observation.get("competing_generation"):
        return {"accept": False, "reason": "REJECT_COMPETING_LISTENER"}
    if _as_int(observation.get("port")) not in (None, 8788) or int(normalized.get("port") or 0) != 8788:
        return {"accept": False, "reason": "REJECT_PORT"}
    for key in ("server_sha256", "gateway_sha256", "policy_sha256", "tool_contract_sha256", "canonical_head"):
        if _hash_mismatch(normalized, observation, key):
            return {"accept": False, "reason": "REJECT_SOURCE_HASH_MISMATCH"}
    listener_pid = _as_int(observation.get("listener_pid"))
    listener_started = _parse_time(observation.get("listener_creation_time"))
    launcher_started = _parse_time(normalized.get("launcher_creation_time"))
    if listener_pid is None or listener_started is None or launcher_started is None:
        return {"accept": False, "reason": "REJECT_NO_GENERATION_PROVENANCE"}
    if not _is_python(observation.get("listener_command_line"), observation.get("listener_executable")):
        return {"accept": False, "reason": "REJECT_COMMAND_MISMATCH"}
    if not _command_has_server(observation.get("listener_command_line")):
        return {"accept": False, "reason": "REJECT_COMMAND_MISMATCH"}
    if listener_pid == normalized["launcher_pid"]:
        if abs(listener_started - launcher_started) >= SAME_PROCESS_SKEW:
            return {"accept": False, "reason": "REJECT_PID_REUSE"}
        if not _command_has_server(normalized.get("launcher_command_line")):
            return {"accept": False, "reason": "REJECT_COMMAND_MISMATCH"}
        return {"accept": True, "reason": "ACCEPT_SAME_PROCESS"}
    bound = normalized.get("listener_pid")
    if bound is not None and listener_pid == bound:
        bound_started = _parse_time(normalized.get("listener_creation_time"))
        if bound_started is None or abs(listener_started - bound_started) >= SAME_PROCESS_SKEW:
            return {"accept": False, "reason": "REJECT_PID_REUSE"}
        return {"accept": True, "reason": "ACCEPT_BOUND_LISTENER"}
    if bound is not None and listener_pid != bound:
        return {"accept": False, "reason": "REJECT_SUPERSEDED_GENERATION"}
    chain = observation.get("parent_chain") or []
    lineage = None
    for entry in chain:
        if not isinstance(entry, dict):
            continue
        matched = _chain_entry_matches_launcher(entry, normalized)
        if matched == "MATCH":
            lineage = entry
            break
        if matched == "REJECT_PID_REUSE":
            return {"accept": False, "reason": "REJECT_PID_REUSE"}
    if lineage is None:
        return {"accept": False, "reason": "REJECT_UNRELATED_PROCESS"}
    if listener_started < launcher_started - SAME_PROCESS_SKEW:
        return {"accept": False, "reason": "REJECT_OUTSIDE_LAUNCH_WINDOW"}
    if listener_started - launcher_started > LAUNCH_WINDOW:
        return {"accept": False, "reason": "REJECT_OUTSIDE_LAUNCH_WINDOW"}
    if not _is_python(normalized.get("launcher_command_line"), normalized.get("launcher_executable")):
        return {"accept": False, "reason": "REJECT_COMMAND_MISMATCH"}
    if not _command_has_server(normalized.get("launcher_command_line")):
        return {"accept": False, "reason": "REJECT_COMMAND_MISMATCH"}
    return {"accept": True, "reason": "ACCEPT_EXEC_TRANSITION"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", required=True)
    parser.add_argument("--observation", required=True)
    args = parser.parse_args()
    record = json.loads(Path(args.record).read_text(encoding="utf-8"))
    observation = json.loads(Path(args.observation).read_text(encoding="utf-8"))
    decision = judge_mcp_generation(record, observation)
    print(("ACCEPT " if decision["accept"] else "") + decision["reason"])
    return 0 if decision["accept"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
