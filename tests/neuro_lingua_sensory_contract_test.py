from src.raios.neuro_lingua import (
    SensoryCapability,
    SensoryEvent,
    detect_lightweight_language,
)


def test_sensory_event_hash_and_language_contract() -> None:
    event = SensoryEvent(payload={"text": "مرحبا RAIOS"})
    row = event.canonical()
    assert len(row["content_hash"]) == 64
    assert detect_lightweight_language("مرحبا RAIOS") == "ar"
    assert detect_lightweight_language("hei Norge æøå") == "no"


def test_unbound_backend_is_fail_closed() -> None:
    cap = SensoryCapability(name="HEARING_STT")
    assert cap.available is False
    assert cap.backend is None
    assert cap.reason == "NOT_PROVEN"
