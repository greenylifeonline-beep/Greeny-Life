from __future__ import annotations

import json
from datetime import datetime, timezone

from raios.c5_gateway import cognitive_loop
from raios.manager import live_manager


def test_manager_atomic_json_retries_transient_permission_race(tmp_path, monkeypatch):
    target = tmp_path / "heartbeat.json"
    real_replace = live_manager.os.replace
    attempts = {"count": 0}

    def flaky_replace(source, destination):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise PermissionError("transient reader lock")
        return real_replace(source, destination)

    monkeypatch.setattr(live_manager.os, "replace", flaky_replace)
    live_manager.atomic_json(target, {"status": "STARTING"})

    assert attempts["count"] == 3
    assert json.loads(target.read_text(encoding="utf-8")) == {"status": "STARTING"}
    assert list(tmp_path.glob("heartbeat.json.tmp-*")) == []


def test_manager_heartbeat_uses_versioned_fallback_when_stable_name_is_pinned(
    tmp_path, monkeypatch
):
    target = tmp_path / "heartbeat.json"
    real_atomic = live_manager.atomic_json

    def stable_name_pinned(path, value):
        if path == target:
            raise PermissionError("reader pins stable name")
        return real_atomic(path, value)

    monkeypatch.setattr(live_manager, "HEARTBEAT", target)
    monkeypatch.setattr(live_manager, "atomic_json", stable_name_pinned)
    written = live_manager.write_heartbeat(
        {"generated_at": datetime.now(timezone.utc).isoformat(), "state": "STARTING"}
    )

    assert written.name.startswith("heartbeat.live-")
    assert json.loads(written.read_text(encoding="utf-8"))["state"] == "STARTING"


def test_c5_liveness_reads_freshest_versioned_manager_heartbeat(tmp_path, monkeypatch):
    (tmp_path / "heartbeat.json").write_text(
        json.dumps({"generated_at": "2020-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )
    fresh = tmp_path / "heartbeat.live-7-1.json"
    fresh.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "state": "STARTING",
                "manager_pid": cognitive_loop.os.getpid(),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cognitive_loop, "manager_root", lambda: tmp_path)
    result = cognitive_loop.manager_liveness()

    assert result["alive"] is True
    assert result["state"] == "STARTING"
    assert result["process_alive"] is True
    assert result["heartbeat_file"] == fresh.name


def test_c5_rejects_fresh_heartbeat_for_missing_manager_process(tmp_path, monkeypatch):
    heartbeat = tmp_path / "heartbeat.live-dead-1.json"
    heartbeat.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "state": "RUNNING",
                "manager_pid": 99999999,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cognitive_loop, "manager_root", lambda: tmp_path)
    result = cognitive_loop.manager_liveness()

    assert result["alive"] is False
    assert result["process_alive"] is False
    assert result["reason"] == "PROCESS_MISSING"


def test_manager_presence_requires_a_current_lease():
    expired = {
        "presence": "PRESENT",
        "lease_expires_at": "2020-01-01T00:00:00Z",
    }
    assert live_manager.safe_council_presence_live(expired) is False
    assert live_manager.safe_council_presence_live({"presence": "PRESENT"}) is False
    assert live_manager.safe_council_presence_live({"presence": "ABSENT"}) is False
    assert live_manager.safe_council_presence_live(
        {"presence": "PRESENT", "lease_expires_at": "not-a-date"}
    ) is False


def test_manager_ignores_telemetry_only_source_changes(monkeypatch):
    manager = object.__new__(live_manager.LiveManager)
    manager.state = {"last_hashes": {}}
    emitted = []
    monkeypatch.setattr(live_manager, "emit_event", emitted.append)

    first = live_manager.Source(
        "C5_LIVE_BRAIN",
        "PRIVATE_INTERNAL",
        "RAIOS_INTERNAL",
        "HIGH",
        True,
        "LIVE",
        {
            "live": True,
            "http_status": 200,
            "latency_ms": 12.5,
            "body": {"status": "ONLINE", "generated_at": "2026-09-02T01:00:00Z"},
        },
        ["http://127.0.0.1:8766/health"],
    )
    latency_only = live_manager.Source(
        "C5_LIVE_BRAIN",
        "PRIVATE_INTERNAL",
        "RAIOS_INTERNAL",
        "HIGH",
        True,
        "LIVE",
        {
            "live": True,
            "http_status": 200,
            "latency_ms": 987.0,
            "body": {"status": "ONLINE", "generated_at": "2026-09-02T01:01:00Z"},
        },
        ["http://127.0.0.1:8766/health"],
    )
    real_change = live_manager.Source(
        "C5_LIVE_BRAIN",
        "PRIVATE_INTERNAL",
        "RAIOS_INTERNAL",
        "HIGH",
        False,
        "UNAVAILABLE_OR_STALE",
        {
            "live": False,
            "http_status": None,
            "latency_ms": 1500.0,
            "error": "TimeoutError",
        },
        ["http://127.0.0.1:8766/health"],
    )

    assert manager._emit_changes([first]) == 1
    assert manager._emit_changes([latency_only]) == 0
    assert manager._emit_changes([real_change]) == 1
    assert len(emitted) == 2


def test_manager_reuses_active_gap_task_across_new_snapshots(tmp_path, monkeypatch):
    task_file = tmp_path / "TASKS.json"
    task_file.write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "id": "RAIOS-MGR-RESTORE_C5-existing",
                        "status": "READY",
                        "manager_gap_code": "RESTORE_C5",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(live_manager, "TASKS", task_file)
    manager = object.__new__(live_manager.LiveManager)
    manager.allow_task_write = True
    gap = {
        "code": "RESTORE_C5",
        "title": "Restore C5 live brain",
        "objective": "Reuse the active repair task.",
        "scope": ["src/raios"],
        "blocked_by": None,
        "required_capabilities": ["runtime_repair"],
        "risk_class": "LOW",
        "severity": 100,
    }

    assert manager._write_tasks([gap], "different-snapshot-hash") == []
    assert len(json.loads(task_file.read_text(encoding="utf-8"))["tasks"]) == 1


def test_semantic_observation_ignores_heartbeat_at_timestamp():
    left = {"status": "ONLINE", "at": "2026-09-04T01:00:00Z", "age_seconds": 1.0, "value": 7}
    right = {"status": "ONLINE", "at": "2026-09-04T01:00:15Z", "age_seconds": 18.0, "value": 7}
    assert live_manager.semantic_observation(left) == live_manager.semantic_observation(right)


def test_semantic_observation_still_detects_real_state_change():
    left = {"status": "ONLINE", "at": "2026-09-04T01:00:00Z", "value": 7}
    right = {"status": "DEGRADED", "at": "2026-09-04T01:00:15Z", "value": 7}
    assert live_manager.semantic_observation(left) != live_manager.semantic_observation(right)
