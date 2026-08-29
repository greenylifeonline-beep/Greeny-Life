from unittest.mock import patch

from raios.resource_fabric import live


def test_local_probe_uses_canonical_ollama_and_inventory(monkeypatch):
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    seen = []

    def fake_http(url, payload):
        seen.append(url)
        return {"http": 200, "json": {"models": [
            {"name": "qwen3:0.6b"},
            {"name": "qwen3.6:35b-a3b"},
        ]}}

    with patch.object(live, "_tcp", return_value="SUCCESS"), patch.object(
        live, "_http_json", side_effect=fake_http
    ):
        result = live._probe_local()

    assert "http://127.0.0.1:11434/api/tags" in seen
    assert result["ollama"] == "SUCCESS"
    assert result["ollama_http_status"] == 200
    assert result["ollama_model_count"] == 2
    assert result["qwen35_present"] is True


def test_ninerouter_catalog_is_not_executable_weight_inventory():
    def fake_http(url, payload):
        if url.endswith("/api/health"):
            return {"http": 200, "json": {"status": "ok"}}
        return {"http": 200, "json": {"data": [{"id": str(i)} for i in range(691)]}}

    with patch.object(live, "_tcp", return_value="SUCCESS"), patch.object(
        live, "_http_json", side_effect=fake_http
    ):
        result = live._probe_9router()

    assert result["catalog_model_names"] == 691
    assert result["accounts_connected"] == 0
    assert result["locally_available_weights"] == 0
    assert result["executable_routed_models"] == 0
    assert result["RESOURCE_AUTHORITY"] is False
