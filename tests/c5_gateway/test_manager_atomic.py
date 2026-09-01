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
