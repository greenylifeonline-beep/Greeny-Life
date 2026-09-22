from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATEWAY = ROOT / "src" / "raios" / "c5_gateway" / "gateway.py"


def source() -> str:
    return GATEWAY.read_text(encoding="utf-8")


def test_raios_c5_uses_single_model_fabric_as_default_inference_path():
    text = source()
    assert "from .model_fabric import C5ModelFabric" in text
    assert "model_fabric=C5ModelFabric()" in text
    assert "model_fabric.chat(" in text
    assert '"system_identity":"RAIOS/C5"' in text
    assert '"model_fabric":True' in text


def test_legacy_ollama_client_is_fallback_not_primary_chat_path():
    text = source()
    helper = text.split("def _raios_inference(", 1)[1].split("def execute_chat(", 1)[0]
    execute = text.split("def execute_chat(", 1)[1].split("@app.get", 1)[0]
    assert helper.index("model_fabric.chat(") < helper.index("client.chat(")
    assert "result=_raios_inference(" in execute
    assert "result=client.chat(" not in execute
