from hypothesis import given, settings
from hypothesis import strategies as st
from pathlib import Path
import tempfile

from raios.neuro_lingua.detection import HybridLanguageDetector
from raios.neuro_lingua.preservation import extract_numbers
from raios.wal import CognitiveWAL


@settings(max_examples=40, deadline=None)
@given(st.integers(min_value=0, max_value=10_000))
def test_property_integers_are_extracted(n: int):
    text = f"replica count is {n} now"
    spans = extract_numbers(text)
    assert any(span.surface == str(n) for span in spans)


@settings(max_examples=25, deadline=None)
@given(st.text(min_size=1, max_size=40, alphabet=st.characters(whitelist_categories=("Lu", "Ll"))))
def test_property_detector_never_invents_confidence_outside_unit_interval(text: str):
    result = HybridLanguageDetector().detect(text)
    assert 0.0 <= result.language_confidence.value <= 1.0
    assert 0.0 <= result.dialect_confidence.value <= 1.0


@settings(max_examples=20, deadline=None)
@given(st.text(min_size=1, max_size=20))
def test_property_wal_idempotent_on_same_payload(payload: str):
    with tempfile.TemporaryDirectory() as tmp:
        wal = CognitiveWAL(Path(tmp) / "wal.jsonl")
        wal.append("user_correction", {"note": payload})
        wal.append("user_correction", {"note": payload})
        assert len(wal.replay()) == 1
