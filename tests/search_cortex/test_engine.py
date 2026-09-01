from __future__ import annotations

import json

from raios.search_cortex import engine


def test_plan_is_inspectable_and_separates_public_query():
    plan = engine.plan_query("افحص حالة RAIOS الآن ثم تحقق من الدليل", deep=True)
    assert "DIAGNOSE" in plan["intents"]
    assert "CURRENT_STATE" in plan["intents"]
    assert plan["deep_history"] is True
    assert plan["currentness_required"] is True
    assert "PRIVATE_QUERY_NE_PUBLIC_QUERY" in plan["gates"]


def test_search_cites_deduplicates_and_surfaces_conflict(tmp_path, monkeypatch):
    online = {
        "source": "CANONICAL_REPO",
        "path": "state.json",
        "line": 4,
        "excerpt": "SERVICE STATE ONLINE",
        "trust": "HIGH",
        "freshness": "CURRENT_WORKTREE_INDEX",
        "score": 2.0,
    }
    offline = {
        "source": "DERIVED_RETRIEVAL",
        "source_id": "runtime-state",
        "excerpt": "SERVICE STATE OFFLINE",
        "trust": "DERIVED",
        "freshness": "DERIVED_CURRENT",
        "score": 1.5,
    }
    monkeypatch.setattr(engine, "LATEST", tmp_path / "latest.json")
    monkeypatch.setattr(engine, "_repo_search", lambda query, limit: [online, dict(online)])
    monkeypatch.setattr(engine, "_derived_search", lambda query, limit: [offline])
    monkeypatch.setattr(engine, "_learning_search", lambda query, limit: [])
    monkeypatch.setattr(engine, "_wal_search", lambda query, limit: [])
    result = engine.search(
        "current service status",
        include_official=False,
        include_history=False,
        emit_trace=False,
        limit=10,
    )
    assert result["schema"] == "raios.search-cortex.result.v2"
    assert result["verification"]["status"] == "CONFLICT"
    assert result["verification"]["contradiction_count"] == 1
    assert result["private_query_sent_to_web"] is False
    assert result["wal_written"] is False
    assert [row["evidence_id"] for row in result["results"]] == ["E001", "E002"]
    assert result["results"][0]["citation"] == "CANONICAL_REPO::state.json:4"
    assert json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))["count"] == 2


def test_learning_digest_is_part_of_shared_cortex(tmp_path, monkeypatch):
    learning = tmp_path / ".ai-os" / "learning"
    learning.mkdir(parents=True)
    row = {
        "schema": "raios.absorb-digest.v2",
        "path": "live-chat/cid/abc",
        "sha256": "a" * 64,
        "status": "ABSORBED",
        "knowledge_state": "DISCOVERED",
        "text": "قانون الاستيعاب يمنع الترقية التلقائية",
        "ts": "2026-09-01T00:00:00Z",
    }
    (learning / "DIGESTS.jsonl").write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setenv("RAIOS_CANONICAL_REPO", str(tmp_path))
    found = engine._learning_search("قانون الاستيعاب", 5)
    assert len(found) == 1
    assert found[0]["source"] == "LEARNING_DIGEST"
    assert found[0]["knowledge_state"] == "DISCOVERED"
