from __future__ import annotations

import json
from pathlib import Path

from raios.command_center.operational_projection import (
    capability_projection,
    head_truth,
    operational_attention,
)


def test_head_truth_drift_is_not_corruption():
    out = head_truth(
        canonical_head="aaa",
        deployed_head="bbb",
        runtime_head="bbb",
        actor_observed_head="ccc",
        remote_head="UNKNOWN",
    )
    assert out["CANONICAL_HEAD"] == "aaa"
    assert out["DEPLOYED_HEAD"] == "bbb"
    assert out["RUNTIME_HEAD"] == "bbb"
    assert out["ACTOR_OBSERVED_HEAD"] == "ccc"
    assert "CANONICAL_NE_DEPLOYED" in out["drift"]
    assert out["drift_ne_corruption"] is True
    assert out["corruption"] is False
    assert out["generic_head_omitted"] is True
    assert out["auto_commit"] is False


def test_capability_projection_is_capability_first_and_skips_ollama(tmp_path):
    repo = tmp_path / "Greeny-Life"
    mcp = repo / ".ai-os" / "mcp"
    mcp.mkdir(parents=True)
    (mcp / "AI-GATEWAY.json").write_text(json.dumps({
        "providers": [{
            "provider_id": "ollama-local-qwen3-0.6b",
            "model_id": "qwen3:0.6b",
            "local": True,
            "availability": "LIVE",
            "capabilities": ["reasoning"],
        }]
    }), encoding="utf-8")
    (mcp / "HERMES-PROVIDER.json").write_text(json.dumps({
        "provider_id": "hermes-knowledge-ingest",
        "capability": "KnowledgeIngest",
        "enabled": True,
        "not_core": True,
        "ninth_mcp": False,
    }), encoding="utf-8")
    (mcp / "EXECUTION-CHANNEL.json").write_text(json.dumps({
        "runtimes": [
            {"id": "command-center", "adapter": True, "role": "canonical control UI/API", "health": "ONLINE"},
            {"id": "desktop-commander", "adapter": True, "role": "optional host adapter",
             "capabilities": ["RemoteCapability"], "health": "ONLINE", "failure": None},
        ]
    }), encoding="utf-8")
    out = capability_projection(repo)
    assert out["capability_first"] is True
    assert out["ollama_tags_called"] is False
    assert out["model_count"] is None
    assert out["timeout_ne_empty_inventory"] is True
    caps = {row["CAPABILITY"] for row in out["capabilities"]}
    assert "reasoning" in caps
    assert "KnowledgeIngest" in caps
    assert "RemoteCapability" in caps
    providers = {row["PROVIDER"] for row in out["providers"]}
    assert "hermes-knowledge-ingest" in providers
    assert "desktop-commander" in providers
    assert "command-center" not in providers
    hermes = next(row for row in out["providers"] if row["PROVIDER"] == "hermes-knowledge-ingest")
    assert hermes["hermes_is_scheduler"] is False
    assert hermes["raios_core"] is False
    dc = next(row for row in out["providers"] if row["PROVIDER"] == "desktop-commander")
    assert dc["remote_capability"] is True
    assert dc["HEALTH"] == "UNKNOWN"
    assert dc["declared_health_freshness"] == "STALE"


def test_operational_attention_uses_categories_without_scores():
    out = operational_attention(tasks=[
        {"id": "T1", "status": "BLOCKED", "blocker": "AWAITING_C1", "scheduler_priority": "HIGH"},
        {"id": "T2", "status": "IN_PROGRESS", "claimed_by": "C8-ACTOR"},
        {"id": "T3", "status": "BLOCKED", "blocker": "PYTEST_FAILURE"},
    ], mcp={"live": False, "http": 0}, heads={"drift": ["CANONICAL_NE_RUNTIME"]})
    cats = {row["category"] for row in out["items"]}
    assert "C1_APPROVAL_REQUIRED" in cats
    assert "C8_ACTIVATION_PENDING" in cats
    assert "TASK_HANGING" in cats
    assert "TASK_BLOCKED" in cats
    assert "TEST_FAILURE" in cats
    assert "MCP_STATE_UNCERTAINTY" in cats
    assert "HEAD_DRIFT" in cats
    assert out["fabricated_score"] is False
    assert out["c8_activated"] is False
    assert all(row.get("fabricated_score") is False for row in out["items"])
