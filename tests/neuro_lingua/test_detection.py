from raios.neuro_lingua.detection import HybridLanguageDetector
from raios.neuro_lingua.types import GULF_CHILDREN, INITIAL_LOCALES, InterpretationContext


def test_initial_locales_represented():
    assert set(INITIAL_LOCALES) == {"ar-EG", "ar-GULF", "en", "nb-NO", "sv-SE", "da-DK"}


def test_gulf_taxonomy_extensible_without_classifiers():
    detector = HybridLanguageDetector()
    taxonomy = detector.gulf_taxonomy()
    assert taxonomy == GULF_CHILDREN
    assert "ar-SA" in taxonomy
    result = detector.detect("شلون حالج الحين")
    assert result.locale == "ar-GULF"
    assert result.dialect == "gulf_neutral"
    assert result.gulf_child is None
    assert result.gulf_child_implemented is False


def test_egyptian_vs_gulf_distinct():
    detector = HybridLanguageDetector()
    eg = detector.detect("مش بيتولد دلوقتي")
    gulf = detector.detect("شلون الحال وايد زين الحين")
    assert eg.locale == "ar-EG"
    assert gulf.locale == "ar-GULF"
    assert eg.dialect != gulf.dialect
    assert eg.dialect_confidence.value > 0
    assert gulf.dialect_confidence.value > 0


def test_zero_confidence_when_no_dialect_markers():
    detector = HybridLanguageDetector()
    result = detector.detect("هذا نص عربي فصيح بدون لهجة واضحة")
    assert result.language == "ar"
    assert result.dialect is None
    assert result.dialect_confidence.value == 0.0
    assert result.dialect_confidence.method == "arabic_family_no_dialect_markers"


def test_norwegian_not_swedish():
    detector = HybridLanguageDetector()
    nb = detector.detect("Kan du løse saken, men ikke knekke noe?")
    sv = detector.detect("Kan du lösa saken, men inte kanske något här?")
    assert nb.locale == "nb-NO"
    assert sv.locale == "sv-SE"


def test_english_detection():
    detector = HybridLanguageDetector()
    result = detector.detect("please deploy the report today")
    assert result.locale == "en"
    assert result.language_confidence.value > 0


def test_tier1_unavailable_is_recorded_not_faked():
    detector = HybridLanguageDetector()
    # Highly ambiguous latin with no lexicon hits.
    result = detector.detect("xyz qqq zzz")
    assert result.language_confidence.value >= 0.0
    if result.locale is None:
        assert (
            "tier1" in result.language_confidence.unavailable_tiers
            or result.language_confidence.method.startswith("latin")
            or "tier1" in "".join(result.tiers_used)
        )


def test_llm_tier_not_used_offline():
    detector = HybridLanguageDetector()
    ctx = InterpretationContext(offline=True, allow_llm=False)
    result = detector.detect("هذا نص عربي", ctx)
    assert "tier3_eligible" not in result.tiers_used
