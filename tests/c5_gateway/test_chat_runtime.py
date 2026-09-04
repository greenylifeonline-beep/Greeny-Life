from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GW = ROOT / "src" / "raios" / "c5_gateway" / "gateway.py"
OLLAMA = ROOT / "src" / "raios" / "c5_gateway" / "ollama_client.py"


def source():
    return GW.read_text(encoding="utf-8")


def test_request_contract_accepts_legacy_and_ui_aliases():
    text = source()
    assert 'AliasChoices("text","message")' in text
    assert 'AliasChoices("language","locale")' in text
    assert 'stream:bool=False' in text


def test_request_contract_rejects_blank_and_bounds_timeout():
    text = source()
    assert 'raise ValueError("EMPTY_TEXT")' in text
    assert 'timeout_seconds:float=Field' in text
    assert 'ge=1.0' in text
    assert 'le=600.0' in text


def test_arabic_request_gets_an_explicit_unicode_language_instruction():
    text = source()
    assert 'language_key.startswith("ar")' in text
    assert "Respond only in clear Arabic" in text
    assert "Preserve Arabic Unicode" in text


def test_response_mapping_preserves_compatibility():
    text = source()
    assert '"response":result.content' in text
    assert '"content":result.content' in text
    assert '"reply":result.content' in text


def test_small_local_student_uses_memory_bounded_inference_defaults():
    text = OLLAMA.read_text(encoding="utf-8")
    assert 'os.getenv("RAIOS_STUDENT_NUM_CTX","2048")' in text
    assert 'os.getenv("RAIOS_STUDENT_NUM_PREDICT","128")' in text
    assert 'os.getenv("RAIOS_STUDENT_KEEP_ALIVE","30s")' in text
    assert '"think":bool(think)' in text
    assert '"keep_alive":keep_alive' in text


def test_timeout_is_fail_closed_with_gateway_timeout_status():
    text = source()
    assert 'status_code=504 if timeout_failure else 502' in text
    assert '"MAIN_CORTEX_TIMEOUT"' in text