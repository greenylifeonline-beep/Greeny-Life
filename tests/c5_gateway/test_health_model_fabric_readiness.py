from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATEWAY = ROOT / "src" / "raios" / "c5_gateway" / "gateway.py"


def source() -> str:
    return GATEWAY.read_text(encoding="utf-8")


def test_health_uses_bounded_model_fabric_registry_not_inference_probe():
    health = source().split('def health():', 1)[1].split('@app.get("/v1/cognitive/status")', 1)[0]
    assert "model_fabric.router.registry(probe_timeout=0.75)" in health
    assert "client.readiness()" not in health
    assert '"system_identity":"RAIOS/C5"' in health
    assert '"model_fabric":True' in health
    assert '"model_fabric_ready":fabric_ready' in health
    assert '"model_fabric_probe_state":local_probe_state' in health


def test_health_distinguishes_inventory_timeout_from_no_engines():
    health = source().split('def health():', 1)[1].split('@app.get("/v1/cognitive/status")', 1)[0]
    assert 'local_probe_state=str(registry.get("local_probe_state") or "CURRENT").upper()' in health
    assert 'fabric_ready=None if local_probe_state == "TIMEOUT" else bool(live_engines)' in health
    assert '"OLLAMA_INVENTORY_PROBE_TIMEOUT"' in health
    assert '"UNKNOWN" if fabric_ready is None else "DEGRADED"' in health
