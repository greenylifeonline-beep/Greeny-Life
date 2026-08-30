from src.raios.neuro_lingua import (
    FasterWhisperAdapter,
    SensoryCapability,
    SensoryEvent,
    UtteranceSegmenter,
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


def test_utterance_segmentation_is_backend_neutral() -> None:
    segmenter = UtteranceSegmenter(frame_ms=10, pre_roll_ms=20, end_silence_ms=20, max_seconds=1)
    assert segmenter.push(b"a", speech=False) is None
    assert segmenter.push(b"b", speech=True) is None
    assert segmenter.push(b"c", speech=True) is None
    assert segmenter.push(b"d", speech=False) is None
    assert segmenter.push(b"e", speech=False) == b"abcde"


def test_whisper_adapter_never_invents_success() -> None:
    adapter = FasterWhisperAdapter(model_name="__raios_nonexistent_test_model__")
    if not adapter.capability.available:
        result = adapter.transcribe("does-not-exist.wav")
        assert result["ok"] is False
        assert result["reason"]
