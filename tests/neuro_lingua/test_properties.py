from hypothesis import given, settings
from hypothesis import strategies as st

from raios.neuro_lingua.protected import extract_protected_tokens
from raios.neuro_lingua.language import normalize_text


@settings(max_examples=40)
@given(st.text(min_size=0, max_size=80))
def test_normalize_never_raises(text: str):
    result = normalize_text(text)
    assert result["status"] == "OK"
    assert "text" in result


@settings(max_examples=40)
@given(st.from_regex(r"[A-Za-z][A-Za-z0-9_-]{2,10}\.py", fullmatch=True))
def test_python_filenames_are_protected(name: str):
    result = extract_protected_tokens(f"see {name} please")
    texts = [tok.text for tok in result["tokens"]]
    assert name in texts
