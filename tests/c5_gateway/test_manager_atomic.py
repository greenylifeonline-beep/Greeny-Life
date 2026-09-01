from __future__ import annotations

import json

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
