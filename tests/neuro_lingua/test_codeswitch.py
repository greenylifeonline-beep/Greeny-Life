from raios.neuro_lingua.codeswitch import segment
from raios.neuro_lingua.detection import HybridLanguageDetector


def test_egyptian_english_technical_code_switch():
    text = "أنا عملت migration بس الـreport مش بيتولد بعد الـexecutor"
    detection = HybridLanguageDetector().detect(text)
    segments = segment(text, detection)
    locales = [s.locale for s in segments]
    texts = [s.text for s in segments]
    assert detection.locale == "ar-EG"
    assert any(s.technical and "migration" in s.text for s in segments)
    assert any("report" in s.text and s.technical for s in segments)
    assert any("executor" in s.text and s.technical for s in segments)
    assert "en/technical" in locales
    assert any(loc in {"ar-EG", "ar"} for loc in locales)
    # Technical tokens must keep English surface
    joined = " ".join(texts)
    assert "migration" in joined
    assert "report" in joined
    assert "executor" in joined


def test_norwegian_code_switch_preserves_technical_loans():
    text = "Kan du deploye den nye builden, men ikke touche production-databasen?"
    detection = HybridLanguageDetector().detect(text)
    segments = segment(text, detection)
    preserved = [s.text for s in segments if s.preserve or s.technical]
    blob = " ".join(preserved).lower()
    assert "deploye" in blob
    assert "builden" in blob
    assert "touche" in blob
    assert "production-databasen" in blob


def test_filenames_urls_and_functions_preserved():
    text = "See src/raios/kernel.py and https://example.com/a plus run_job() and PKG.module"
    detection = HybridLanguageDetector().detect(text)
    segments = segment(text, detection)
    surfaces = " ".join(s.text for s in segments)
    assert "src/raios/kernel.py" in text
    assert any("kernel.py" in s.text or s.text.endswith(".py") for s in segments)
    assert any("https://example.com/a" in s.text for s in segments)
