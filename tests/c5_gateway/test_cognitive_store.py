from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
RUNTIME = ROOT / "RAIOS" / "V9" / "runtime"


def load_bus(tmp_path, monkeypatch):
    store = tmp_path / "cognitive-store" / "v9"
    monkeypatch.setenv("RAIOS_COGNITIVE_STORE_ROOT", str(store))
    monkeypatch.syspath_prepend(str(RUNTIME))
    sys.modules.pop("cognitive_event_bus", None)
    return importlib.import_module("cognitive_event_bus"), store


def test_event_bus_uses_external_store_for_every_live_artifact(tmp_path, monkeypatch):
    bus, store = load_bus(tmp_path, monkeypatch)
    result = bus.emit(
        event_type="ACTION",
        actor="C3",
        intent="verify external durable cognitive store",
        success=True,
    )
    assert result["result"]["status"] == "WAL_COMMITTED"
    live_paths = (
        bus.WAL_FILE,
        bus.PROCESSED_LEDGER,
        bus.EXPERIENCE_DIR,
        bus.FAILURE_DIR,
        bus.RECOVERY_DIR,
        bus.PERFORMANCE_DIR,
        bus.EVIDENCE_EVENT_DIR,
    )
    assert bus.COGNITIVE_STORE_ROOT == store.resolve()
    assert all(path.resolve().is_relative_to(store.resolve()) for path in live_paths)
    assert bus.WAL_FILE.is_file()


def test_atomic_writer_survives_replace_permission_race(tmp_path, monkeypatch):
    bus, _ = load_bus(tmp_path, monkeypatch)
    target = tmp_path / "registry.json"
    payload = {"worker": "alive", "sequence": 7, "signature": (10, 20)}

    def denied(*_args, **_kwargs):
        raise PermissionError("simulated Windows file pin")

    monkeypatch.setattr(bus.os, "replace", denied)
    monkeypatch.setattr(bus.time, "sleep", lambda _seconds: None)
    bus.atomic_json_write(target, payload)

    assert json.loads(target.read_text(encoding="utf-8")) == {
        "worker": "alive", "sequence": 7, "signature": [10, 20]
    }
    assert not list(tmp_path.glob("registry.json.tmp-*"))


def test_terminal_jsonl_fragment_is_quarantined_and_repaired(tmp_path, monkeypatch):
    bus, _ = load_bus(tmp_path, monkeypatch)
    wal = bus.WAL_FILE
    wal.parent.mkdir(parents=True, exist_ok=True)
    valid = {"event_id": "evt-1", "event_type": "ACTION"}
    wal.write_bytes((json.dumps(valid) + "\n").encode() + b'{"event_id":"partial')

    recovery = bus.repair_terminal_jsonl(wal)

    assert recovery["repaired"] is True
    assert recovery["status"] == "REPAIRED_TERMINAL_FRAGMENT"
    assert bus.load_jsonl(wal) == [valid]
    evidence = Path(recovery["evidence"])
    assert evidence.is_file()
    proof = json.loads(evidence.read_text(encoding="utf-8"))
    assert proof["fragment_bytes"] > 0
    assert proof["line"] == 2


def test_wal_id_cache_avoids_full_rescan_after_local_append(tmp_path, monkeypatch):
    bus, _ = load_bus(tmp_path, monkeypatch)
    first = bus.build_event(event_type="ACTION", actor="C3", intent="first", success=True)
    second = bus.build_event(event_type="ACTION", actor="C3", intent="second", success=True)
    assert bus.emit_event(first, materialize=False)["status"] == "WAL_COMMITTED"

    def unexpected_rescan(_path):
        raise AssertionError("local append must advance the WAL id cache")

    monkeypatch.setattr(bus, "_load_jsonl_snapshot", unexpected_rescan)
    assert bus.emit_event(second, materialize=False)["status"] == "WAL_COMMITTED"


def test_processed_id_cache_avoids_full_rescan_after_materialization(
    tmp_path, monkeypatch
):
    bus, _ = load_bus(tmp_path, monkeypatch)
    first = bus.build_event(event_type="ACTION", actor="C3", intent="first", success=True)
    second = bus.build_event(event_type="ACTION", actor="C3", intent="second", success=True)
    assert bus.emit_event(first)["materialized"]["status"] == "MATERIALIZED"

    def unexpected_rescan(_path):
        raise AssertionError("local materialization must advance both id caches")

    monkeypatch.setattr(bus, "_load_jsonl_snapshot", unexpected_rescan)
    assert bus.emit_event(second)["materialized"]["status"] == "MATERIALIZED"


def test_normal_jsonl_append_uses_fast_tail_not_full_repair(tmp_path, monkeypatch):
    bus, _ = load_bus(tmp_path, monkeypatch)
    target = tmp_path / "events.jsonl"
    first = {"event_id": "evt-1", "status": "PASS"}
    second = {"event_id": "evt-2", "status": "PASS"}
    bus.append_jsonl_sync(target, first)

    def unexpected_full_repair(_path):
        raise AssertionError("valid append must not scan the complete JSONL file")

    monkeypatch.setattr(bus, "_repair_terminal_jsonl_unlocked", unexpected_full_repair)
    bus.append_jsonl_sync(target, second)

    rows = [
        json.loads(line)
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows == [first, second]


def test_append_repairs_only_a_partial_terminal_record(tmp_path, monkeypatch):
    bus, _ = load_bus(tmp_path, monkeypatch)
    target = tmp_path / "events.jsonl"
    first = {"event_id": "evt-1", "status": "PASS"}
    second = {"event_id": "evt-2", "status": "PASS"}
    target.write_bytes((json.dumps(first) + "\n").encode() + b'{"event_id":"partial')

    repairs = {"count": 0}
    real_repair = bus._repair_terminal_jsonl_unlocked

    def counted_repair(path):
        repairs["count"] += 1
        return real_repair(path)

    monkeypatch.setattr(bus, "_repair_terminal_jsonl_unlocked", counted_repair)
    bus.append_jsonl_sync(target, second)

    assert repairs["count"] == 1
    assert bus.load_jsonl(target) == [first, second]


def test_append_adds_separator_after_valid_record_without_newline(tmp_path, monkeypatch):
    bus, _ = load_bus(tmp_path, monkeypatch)
    target = tmp_path / "events.jsonl"
    first = {"event_id": "evt-1", "status": "PASS"}
    second = {"event_id": "evt-2", "status": "PASS"}
    target.write_text(json.dumps(first), encoding="utf-8")

    def unexpected_full_repair(_path):
        raise AssertionError("complete terminal JSON only needs a newline separator")

    monkeypatch.setattr(bus, "_repair_terminal_jsonl_unlocked", unexpected_full_repair)
    bus.append_jsonl_sync(target, second)

    rows = [
        json.loads(line)
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows == [first, second]
