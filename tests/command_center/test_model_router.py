from __future__ import annotations

import json
from pathlib import Path

from raios.ai_gateway import ModelRouter, RouteRequest


def test_remote_unproven_provider_is_not_selected(tmp_path, monkeypatch):
    repo = tmp_path / "Greeny-Life"
    cfg = repo / ".ai-os" / "mcp" / "AI-GATEWAY.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({"providers": [{
        "provider_id": "deepseek-remote",
        "model_id": "deepseek-v4",
        "availability": "UNPROVEN",
        "enabled": False,
        "local": False,
        "capabilities": ["reasoning"],
        "context_tokens": 100000,
        "tools": False
    }]}), encoding="utf-8")
    router = ModelRouter(repo, cfg)
    monkeypatch.setattr(router, "_ollama_models", lambda: [])
    out = router.route(RouteRequest(capability="reasoning"))
    assert out["decision"] == "NO_LIVE_PROVIDER"
    assert out["selected"] is None


def test_live_local_provider_is_preferred_for_private_work(tmp_path, monkeypatch):
    repo = tmp_path / "Greeny-Life"
    cfg = repo / ".ai-os" / "mcp" / "AI-GATEWAY.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({"providers": []}), encoding="utf-8")
    router = ModelRouter(repo, cfg)
    monkeypatch.setattr(router, "_ollama_models", lambda: [{
        "provider_id": "ollama-local",
        "model_id": "qwen3:0.6b",
        "availability": "LIVE",
        "local": True,
        "cost_class": "LOCAL",
        "privacy_class": "LOCAL_PRIVATE",
        "capabilities": ["reasoning"],
        "context_tokens": 16384,
        "tools": False
    }])
    out = router.route(RouteRequest(capability="reasoning", privacy="local_only", context_tokens=4096))
    assert out["decision"] == "ROUTE_SELECTED"
    assert out["selected"]["model_id"] == "qwen3:0.6b"
    assert out["model_ne_council_seat"] is True
