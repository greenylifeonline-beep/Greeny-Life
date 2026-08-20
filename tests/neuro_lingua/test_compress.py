import asyncio

from raios.neuro_lingua.compress import compress_meaning
from raios.neuro_lingua.experience import learning_score
from raios.neuro_lingua.kernel import NeuroLingua


def test_language_is_pattern_not_word_list():
    ship = compress_meaning("The supplier shipped the products to Norway.")
    recv = compress_meaning("The customer received the products in Norway.")
    arabic = compress_meaning("المورد شحن المنتجات إلى النرويج.")
    assert ship["word_list"] is False
    assert ship["pattern"]["actor"] == "supplier"
    assert ship["pattern"]["action"] == "ship"
    assert ship["pattern"]["object"] == "product"
    assert ship["pattern"]["destination"] == "norway"
    assert recv["pattern"]["actor"] == "customer"
    assert recv["pattern"]["action"] == "receive"
    assert recv["pattern"]["object"] == "product"
    assert recv["pattern"]["destination"] == "norway"
    assert arabic["pattern"]["actor"] == "supplier"
    assert arabic["pattern"]["action"] == "ship"
    assert arabic["pattern"]["destination"] == "norway"


def test_delta_learns_only_unknown():
    rec = compress_meaning("The supplier shipped the products to Norway xyzzy.")
    assert "xyzzy" in rec["delta"]
    assert rec["known_ratio"] < 1.0
    assert rec["known_ratio"] > 0.5


def test_kernel_attaches_compression():
    nl = NeuroLingua()
    result = asyncio.run(nl.interpret("The supplier shipped the products to Norway."))
    compression = result.meaning.metadata.get("compression") or {}
    pattern = compression.get("pattern") or {}
    assert compression.get("word_list") is False
    assert pattern.get("actor") == "supplier"
    assert pattern.get("action") == "ship"


def test_learning_score_zero_if_any_factor_missing():
    assert learning_score(1, 1, 1, 1, 1, 1) == 1.0
    assert learning_score(1, 1, 1, 1, 1, 0) == 0.0
