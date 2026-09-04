from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import raios.c5_gateway.cognitive_loop as cognitive_loop

from raios.c5_gateway.cognitive_loop import (
    assimilate_turn,
    format_grounded_user_message,
    learning_root,
    loop_status,
    retrieve_grounding,
)


def test_learning_root_follows_the_external_cognitive_store(tmp_path, monkeypatch):
    store = tmp_path / "cognitive-store" / "v9"
    monkeypatch.delenv("RAIOS_LEARNING_ROOT", raising=False)
    monkeypatch.setenv("RAIOS_COGNITIVE_STORE_ROOT", str(store))
    assert learning_root() == store / "learning"


def test_retrieve_fail_open_without_digests(tmp_path, monkeypatch):
    monkeypatch.setenv("RAIOS_CANONICAL_REPO", str(tmp_path))
    (tmp_path / ".ai-os" / "learning").mkdir(parents=True)
    env = retrieve_grounding("C5 GRANT")
    assert env["schema"] == "raios.grounding-envelope.v2"
    assert env["wal_written"] is False
    assert env["shared_search_cortex"] is True
    assert all(row["source"] != "LEARNING_DIGEST" for row in env["results"])


def test_assimilate_and_retrieve_closed_loop(tmp_path, monkeypatch):
    monkeypatch.setenv("RAIOS_CANONICAL_REPO", str(tmp_path))
    (tmp_path / ".ai-os" / "learning").mkdir(parents=True)
    (tmp_path / "RAIOS" / "V9" / "wal").mkdir(parents=True)
    wal = tmp_path / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
    wal.write_text("", encoding="utf-8")
    before = wal.stat().st_mtime
    rec = assimilate_turn(
        prompt="what is the assimilation rule?",
        response="ABSORB_DIGEST_NE_WAL_DUMP",
        conversation_id="cid-test",
        model="qwen3:0.6b",
        grounding={"count": 0},
    )
    assert rec["wal_written"] is False
    assert rec["canonical"] is False
    assert rec["kae_ok"] is True
    assert rec["replayed"] is True
    assert rec["review_state"] in {"READY_FOR_VALIDATION", "NEEDS_REVIEW"}
    assert wal.stat().st_mtime == before
    env = retrieve_grounding("assimilation rule WAL")
    assert env["count"] >= 1
    assert env["results"][0]["source"] == "LEARNING_DIGEST"
    assert env["shared_search_cortex"] is True
    assert env["wal_written"] is False
    msg = format_grounded_user_message("سؤال", env)
    assert "GROUNDING_ENVELOPE" in msg
    assert "USER_MESSAGE" in msg
    status = loop_status()
    assert status["planes"]["retrieve"] is True
    assert status["artifacts"]["digests_exist"] is True
    digests = (tmp_path / ".ai-os" / "learning" / "DIGESTS.jsonl").read_text(encoding="utf-8")
    assert "LIVE_CHAT_TURN" in digests
    candidates = json.loads((tmp_path / ".ai-os" / "learning" / "CANDIDATES.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert candidates["promoted"] is False
    assert candidates["schema"] == "raios.learning-candidate.v2"


def test_assimilation_deduplicates_same_turn(tmp_path, monkeypatch):
    monkeypatch.setenv("RAIOS_CANONICAL_REPO", str(tmp_path))
    (tmp_path / ".ai-os" / "learning").mkdir(parents=True)
    (tmp_path / "RAIOS" / "V9" / "wal").mkdir(parents=True)
    kwargs = dict(prompt="same prompt", response="same rule", conversation_id="cid", model="student")
    first = assimilate_turn(**kwargs)
    second = assimilate_turn(**kwargs)
    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert second["candidate_id"] is None
    assert len((tmp_path / ".ai-os" / "learning" / "DIGESTS.jsonl").read_text(encoding="utf-8").splitlines()) == 1


def test_evolution_liveness_requires_current_process_and_single_wal(tmp_path, monkeypatch):
    evolution = tmp_path / "evolution"
    store = tmp_path / "cognitive-store" / "v9"
    evolution.mkdir()
    wal = store / "wal" / "cognitive-events.jsonl"
    wal.parent.mkdir(parents=True)
    wal.write_text("", encoding="utf-8")
    (evolution / "heartbeat.json").write_text(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
        "state": "ACTIVE",
        "wal": str(wal),
    }), encoding="utf-8")
    monkeypatch.setenv("RAIOS_COGNITIVE_STORE_ROOT", str(store))
    monkeypatch.setattr(cognitive_loop, "evolution_root", lambda: evolution)

    status = cognitive_loop.evolution_liveness()

    assert status["alive"] is True
    assert status["single_wal"] is True
    assert status["reason"] == "OK"


def test_loop_status_exposes_complete_maintenance_assimilation(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    learning = tmp_path / "learning"
    learning.mkdir(parents=True)
    for name in ("DIGESTS.jsonl", "CANDIDATES.jsonl"):
        (learning / name).write_text("", encoding="utf-8")
    (learning / "INDEX.json").write_text("{}", encoding="utf-8")
    receipt = runtime / "c5" / "maintenance-assimilation.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text(json.dumps({
        "law_count": 2,
        "all_wal_clean": True,
        "results": [
            {"review_state": "READY_FOR_VALIDATION"},
            {"review_state": "DEDUPED"},
        ],
    }), encoding="utf-8")
    monkeypatch.setenv("RAIOS_RUNTIME_BASE", str(runtime))
    monkeypatch.setenv("RAIOS_LEARNING_ROOT", str(learning))
    status = loop_status()
    assert status["maintenance_assimilation"]["complete"] is True
    assert status["maintenance_assimilation"]["ready_or_deduped"] == 2
