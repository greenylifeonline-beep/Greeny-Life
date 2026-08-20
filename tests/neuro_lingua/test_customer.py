import asyncio

from raios.neuro_lingua.customer import COMPANIES, detect_customer_action, match_product, load_catalog
from raios.neuro_lingua.experience import confidence, may_promote, may_repair, route_path, rung
from raios.neuro_lingua.kernel import NeuroLingua
from raios.neuro_lingua.customer import speak


def test_egyptian_stock_is_professional_not_engineer_slang():
    nl = NeuroLingua()
    rec = asyncio.run(speak(nl, "لو سمحت عندكم عسل البرسيم؟", "GREENY_LIFE_EGYPT"))
    assert rec["ok"] is True
    assert rec["llm_calls"] == 0
    assert rec["wal_written"] is False
    assert rec["gl005_proven"] is False
    assert rec["consult_used"] is False
    assert rec["customer_locale"] == "ar-EG"
    assert rec["trade_locale"] == "en"
    assert rec["facts"]["product_id"] == "H002"
    assert rec["facts"]["quantity"] == 154
    assert "H002" in rec["customer_text"]
    assert "خلّص" not in rec["customer_text"]
    assert "Clover" in rec["trade_text"] or "H002" in rec["trade_text"]


def test_gulf_quote_does_not_invent_price():
    nl = NeuroLingua()
    rec = asyncio.run(speak(nl, "إذا ما عليك أمر نبيه عرض سعر للعسل", "GREENS_NATURE_UAE"))
    assert rec["action"] == "quote_request"
    assert rec["facts"]["price_proven"] is False
    assert rec["facts"]["next_route"] is False
    assert "سعر" in rec["customer_text"] or "PRICE" in rec["customer_text"] or "نختلق" in rec["customer_text"] or "غير مثبت" in rec["customer_text"]


def test_norway_shipment_no_swedish_leakage():
    nl = NeuroLingua()
    rec = asyncio.run(speak(nl, "Har dere shipment status for H001?", "GREEN_LINES_NORWAY_EU"))
    assert rec["customer_locale"] == "nb-NO"
    assert "och" not in rec["customer_text"].split()
    assert rec["llm_calls"] == 0


def test_unknown_company_fail_closed():
    nl = NeuroLingua()
    rec = asyncio.run(speak(nl, "hello", "NOT_A_COMPANY"))
    assert rec["ok"] is False
    assert rec["error"] == "UNKNOWN_COMPANY"


def test_catalog_match_sku_and_arabic_name():
    catalog = load_catalog()
    honey = match_product("عسل البرسيم", catalog)
    sku = match_product("H001", catalog)
    assert honey["id"] == "H002"
    assert sku["id"] == "H001"
    assert detect_customer_action("عندكم مخزون") == "stock_status"
    assert "GREENY_LIFE_EGYPT" in COMPANIES


def test_experience_one_success_is_not_capability():
    ck = confidence(0.95, 0.95, 0.95, 0.95)
    assert ck >= 0.90
    assert rung(ck, reproduced=False) == "PRACTICED"
    assert rung(ck, reproduced=True) in {"PROVEN", "CORE_ELIGIBLE"}
    assert may_promote(ck, verified=True, reproduced=True, owner_approved=False) is False
    assert may_repair(reproduced=False, rollback_available=True, safety=1.0) is False
    path = route_path(complexity=0.2, risk=0.1, novelty=0.1, ck=0.95, deep_available=False)
    assert path["path"] == "FAST"
    deep = route_path(complexity=0.9, risk=0.4, novelty=0.8, ck=0.4, deep_available=False)
    assert deep["path"] == "FAST_FALLBACK"
    assert deep["available"] is False
