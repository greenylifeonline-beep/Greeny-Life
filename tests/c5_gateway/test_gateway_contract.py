from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GW = ROOT / "src" / "raios" / "c5_gateway" / "gateway.py"
CLIENT = ROOT / "src" / "raios" / "c5_gateway" / "ollama_client.py"


def test_gateway_source_has_required_routes():
    text = GW.read_text(encoding="utf-8")
    for route in (
        '@app.get("/health")',
        '@app.post("/v1/chat")',
        '@app.post("/api/chat")',
        '@app.websocket("/v1/ws/chat")',
    ):
        assert route in text


def test_gateway_runtime_writes_are_externalized():
    text = GW.read_text(encoding="utf-8")
    assert "RAIOS_RUNTIME_ROOT" in text
    assert "CANONICAL_DEPLOYMENT" in text
    assert "_raios-communication-fabric" not in text


def test_default_cortex_is_lightweight_utility():
    text = CLIENT.read_text(encoding="utf-8")
    assert '"qwen3:0.6b"' in text
    assert '"qwen3.6:35b-a3b"' not in text
