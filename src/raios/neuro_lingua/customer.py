"""Professional customer-language layer. Deterministic. No LLM. No WAL. No invented prices."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .schema import CognitiveMeaningPacket


COMPANIES = {
    "GREENY_LIFE_EGYPT": {
        "customer_locale": "ar-EG",
        "trade_locale": "en",
        "territory": "Egypt",
        "next_route": True,
        "name_ar": "جريني لايف مصر",
        "name_en": "Greeny-Life Egypt",
    },
    "GREENS_NATURE_UAE": {
        "customer_locale": "ar-GULF",
        "trade_locale": "en",
        "territory": "UAE / GCC",
        "next_route": False,
        "name_ar": "جرينز ناتشر الإمارات",
        "name_en": "Greens Nature UAE",
    },
    "GREEN_LINES_NORWAY_EU": {
        "customer_locale": "nb-NO",
        "trade_locale": "en",
        "territory": "Norway / EU",
        "next_route": False,
        "name_ar": "جرين لاينز النرويج وأوروبا",
        "name_en": "Green Lines Norway/EU",
    },
}

CUSTOMER_ACTS = ("stock_status", "shipment_status", "invoice_status", "quote_request", "greet")

STOCK_MARKERS = ("مخزون", "متاح", "عندكم", "عندكوا", "stock", "lager", "på lager", "available", "كمية")
SHIP_MARKERS = ("شحنة", "شحن", "تتبع", "shipment", "sending", "tracking", "levering")
INVOICE_MARKERS = ("فاتورة", "invoice", "faktura")
QUOTE_MARKERS = ("عرض سعر", "سعر الوحدة", "quote", "tilbud", "quotation")
GREET_MARKERS = ("السلام عليكم", "صباح الخير", "hello", "hi ", "god dag", "مرحبا")


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "canonical" / "inventory" / "stock-levels.json").exists():
            return parent
    return Path.cwd()


def detect_customer_action(text: str) -> str | None:
    lower = text.lower()
    if any(m in text or m in lower for m in QUOTE_MARKERS):
        return "quote_request"
    if any(m in text or m in lower for m in SHIP_MARKERS):
        return "shipment_status"
    if any(m in text or m in lower for m in INVOICE_MARKERS):
        return "invoice_status"
    if any(m in text or m in lower for m in STOCK_MARKERS):
        return "stock_status"
    if any(m in text or m in lower for m in GREET_MARKERS):
        return "greet"
    return None


def load_catalog() -> dict[str, Any]:
    root = _repo_root()
    products = json.loads((root / "canonical" / "data" / "master_products.json").read_text(encoding="utf-8"))
    stock = json.loads((root / "canonical" / "inventory" / "stock-levels.json").read_text(encoding="utf-8"))
    warehouses = json.loads((root / "canonical" / "inventory" / "warehouses.json").read_text(encoding="utf-8"))
    shipments = json.loads((root / "canonical" / "logistics" / "shipments.json").read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in products.get("products") or [] if p.get("id")}
    stock_by_id = {row["product_id"]: row for row in stock.get("stock") or []}
    wh_by_id = {row["id"]: row for row in warehouses.get("warehouses") or []}
    return {
        "products": by_id,
        "stock": stock_by_id,
        "warehouses": wh_by_id,
        "shipments": list(shipments.get("shipments") or []),
    }


def match_product(text: str, catalog: dict[str, Any]) -> dict[str, Any] | None:
    sku = re.search(r"\b[HBSO]\d{3}\b", text, re.I)
    if sku:
        pid = sku.group(0).upper()
        if pid in catalog["products"]:
            return catalog["products"][pid]
    compact = re.sub(r"\s+", " ", text).strip()
    hits: list[tuple[int, dict[str, Any]]] = []
    for product in catalog["products"].values():
        names = product.get("name") or {}
        for label in (names.get("ar"), names.get("en"), product.get("id")):
            if not label:
                continue
            if str(label) in compact or str(label).lower() in compact.lower():
                hits.append((len(str(label)), product))
    if not hits:
        return None
    hits.sort(key=lambda row: row[0], reverse=True)
    return hits[0][1]


def match_shipment(text: str, catalog: dict[str, Any]) -> dict[str, Any] | None:
    for ship in catalog["shipments"]:
        for key in ("shipment_id", "tracking_code", "order_id"):
            val = ship.get(key)
            if val and val in text:
                return ship
    product = match_product(text, catalog)
    if product:
        for ship in catalog["shipments"]:
            if ship.get("product_id") == product.get("id"):
                return ship
    return catalog["shipments"][0] if catalog["shipments"] else None


def customer_facts(text: str, company: str) -> dict[str, Any]:
    if company not in COMPANIES:
        return {"ok": False, "error": "UNKNOWN_COMPANY", "company": company}
    catalog = load_catalog()
    product = match_product(text, catalog)
    stock_row = catalog["stock"].get(product["id"]) if product else None
    warehouse = catalog["warehouses"].get((stock_row or {}).get("warehouse_id") or "")
    shipment = match_shipment(text, catalog)
    return {
        "ok": True,
        "company": company,
        "meta": COMPANIES[company],
        "product": {
            "id": product.get("id"),
            "name_ar": (product.get("name") or {}).get("ar"),
            "name_en": (product.get("name") or {}).get("en"),
        }
        if product
        else None,
        "stock": stock_row,
        "warehouse": warehouse,
        "shipment": {
            "shipment_id": shipment.get("shipment_id"),
            "status": shipment.get("status"),
            "tracking_code": shipment.get("tracking_code"),
            "destination_city": shipment.get("destination_city"),
            "product_id": shipment.get("product_id"),
        }
        if shipment
        else None,
        "price_proven": False,
        "next_route": COMPANIES[company]["next_route"],
    }


def realize_customer(
    meaning: CognitiveMeaningPacket,
    target_locale: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = context or {}
    facts = context.get("customer_facts") or {}
    action = meaning.semantics.action or "greet"
    meta = facts.get("meta") or {}
    product = facts.get("product") or {}
    stock = facts.get("stock") or {}
    warehouse = facts.get("warehouse") or {}
    shipment = facts.get("shipment") or {}
    pid = product.get("id") or ""
    name = product.get("name_ar") if str(target_locale).startswith("ar") else product.get("name_en")
    name = name or product.get("name_en") or pid or ""
    qty = stock.get("quantity")
    wh = warehouse.get("name") or warehouse.get("id") or "WH-001"

    lines = {
        "ar-EG": {
            "greet": f"أهلاً بحضرتك في {meta.get('name_ar') or 'جريني لايف'}. تحت أمرك في الاستفسار عن الصنف أو الشحنة.",
            "stock_ok": f"الصنف {name} ({pid}) متاح حالياً: {qty} وحدة في {wh}. حد إعادة الطلب {stock.get('reorder_level')}.",
            "stock_miss": "لم أطابق صنفاً معتمداً في النص. أرسل كود الصنف مثل H002 ولا أخترع أرقاماً.",
            "ship_ok": f"الشحنة {shipment.get('shipment_id')} حالتها {shipment.get('status')}. التتبع {shipment.get('tracking_code')}. الوجهة {shipment.get('destination_city')}.",
            "ship_miss": "لا شحنة مطابقة في السجل المعتمد. أرسل رقم SHIP- أو رمز التتبع.",
            "invoice": "طلب الفاتورة مسجَّل كلغة. إصدار الفاتورة المالية يحتاج موافقة المالك. لا أنفّذ دفعاً.",
            "quote": "عرض السعر بوحدة نقدية غير مثبت هنا. لا أخترع سعراً. أرفع الطلب للمالك.",
            "shadow": "مسار Next لهذه الشركة غير موجود بعد. أردّ من السجل المعتمد فقط ولا أكتب منتج الإمارات/النرويج.",
        },
        "ar-GULF": {
            "greet": f"حياك الله في {meta.get('name_ar') or 'جرينز ناتشر'}. نخدمك في الصنف والشحنة بدون اختراع أرقام.",
            "stock_ok": f"الصنف {name} ({pid}) متوفر: {qty} وحدة في {wh}.",
            "stock_miss": "ما قدرنا نطابق الصنف من النص. أرسل كود الصنف مثل H002.",
            "ship_ok": f"الشحنة {shipment.get('shipment_id')} حالتها {shipment.get('status')}. التتبع {shipment.get('tracking_code')}.",
            "ship_miss": "لا توجد شحنة مطابقة. أرسل رقم الشحنة أو التتبع.",
            "invoice": "طلب الفاتورة مفهوم. الإصدار المالي بعد اعتماد المالك. لا تنفيذ دفع.",
            "quote": "سعر الوحدة غير مثبت في هذا السجل. لا نختلق سعراً. نرفع الطلب للمالك.",
            "shadow": "مسار التشغيل الحي لهذه الشركة ناقص. الرد من السجل المعتمد فقط.",
        },
        "en": {
            "greet": f"Hello from {meta.get('name_en') or 'Greeny-Life'}. I can report catalog stock and shipment status. I will not invent prices.",
            "stock_ok": f"{name} ({pid}) is on hand: {qty} units at {wh}. Reorder level {stock.get('reorder_level')}.",
            "stock_miss": "No canonical product matched that text. Send a SKU such as H002. I will not invent stock.",
            "ship_ok": f"Shipment {shipment.get('shipment_id')} is {shipment.get('status')}. Tracking {shipment.get('tracking_code')} to {shipment.get('destination_city')}.",
            "ship_miss": "No matching canonical shipment. Send a SHIP- id or tracking code.",
            "invoice": "Invoice language understood. Financial issue requires owner approval. No payment execution.",
            "quote": "Unit price is unproven in this slice. I will not invent a quote. Escalating to the owner.",
            "shadow": "Live Next route for this company is still a gap. Reply uses canonical records only.",
        },
        "nb-NO": {
            "greet": f"Hei fra {meta.get('name_en') or 'Green Lines'}. Jeg kan svare på lager og sending. Jeg dikter ikke priser.",
            "stock_ok": f"{name} ({pid}) på lager: {qty} enheter hos {wh}.",
            "stock_miss": "Ingen kanonisk vare traff teksten. Send SKU som H002.",
            "ship_ok": f"Sending {shipment.get('shipment_id')} har status {shipment.get('status')}. Sporing {shipment.get('tracking_code')}.",
            "ship_miss": "Ingen treff i sendingene. Send SHIP-id eller sporingskode.",
            "invoice": "Faktura er forstått. Utstedelse krever eiergodkjenning. Ingen betaling.",
            "quote": "Enhetspris er ikke bevist her. Jeg dikter ikke tilbud. Saken går til eier.",
            "shadow": "Live Next-rute for dette selskapet mangler. Svar bruker kun kanoniske poster.",
        },
    }
    table = lines.get(target_locale) or lines["en"]
    if action == "stock_status":
        text = table["stock_ok"] if pid and qty is not None else table["stock_miss"]
    elif action == "shipment_status":
        text = table["ship_ok"] if shipment.get("shipment_id") else table["ship_miss"]
    elif action == "invoice_status":
        text = table["invoice"]
    elif action == "quote_request":
        text = table["quote"]
    else:
        text = table["greet"]
    if facts.get("next_route") is False:
        text = f"{text} {table['shadow']}"
    warnings: list[str] = []
    if action == "quote_request":
        warnings.append("PRICE_UNPROVEN")
    if pid and pid not in text:
        text = f"{text} {pid}".strip()
    return {
        "status": "OK",
        "confidence": 0.86 if pid or action == "greet" else 0.7,
        "evidence": [f"customer-realizer:{target_locale}", f"action:{action}"],
        "text": text.strip(),
        "target_locale": target_locale,
        "warnings": warnings,
        "provider": f"deterministic-customer:{target_locale}",
        "price_invented": False,
        "gl005_proven": False,
    }


async def speak(nl: Any, text: str, company: str, target_locale: str | None = None) -> dict[str, Any]:
    if company not in COMPANIES:
        return {
            "ok": False,
            "error": "UNKNOWN_COMPANY",
            "company": company,
            "wal_written": False,
            "gl005_proven": False,
            "llm_calls": 0,
        }
    meta = COMPANIES[company]
    target = target_locale or meta["customer_locale"]
    facts = customer_facts(text, company)
    interpreted = await nl.interpret(text, context={"domain": "customer", "company": company}, target_locale=target)
    action = interpreted.meaning.semantics.action
    if action not in CUSTOMER_ACTS:
        detected = detect_customer_action(text)
        if detected:
            interpreted.meaning.semantics.action = detected
            action = detected
        else:
            interpreted.meaning.semantics.action = "greet"
            action = "greet"
    ctx = {"customer_facts": facts, "register": "professional"}
    customer = await nl.realize(interpreted.meaning, target, context=ctx)
    trade = await nl.realize(interpreted.meaning, meta["trade_locale"], context=ctx)
    metrics = nl.router.metrics()
    return {
        "ok": facts.get("ok") is True,
        "company": company,
        "territory": meta["territory"],
        "source_locale": interpreted.meaning.source_locale,
        "customer_locale": target,
        "trade_locale": meta["trade_locale"],
        "action": action,
        "customer_text": customer.text,
        "trade_text": trade.text,
        "facts": {
            "product_id": (facts.get("product") or {}).get("id"),
            "quantity": (facts.get("stock") or {}).get("quantity"),
            "shipment_id": (facts.get("shipment") or {}).get("shipment_id"),
            "next_route": facts.get("next_route"),
            "price_proven": False,
        },
        "verification": customer.verification.get("status"),
        "llm_calls": metrics.get("llm_calls", 0),
        "wal_written": False,
        "gl005_proven": False,
        "consult_used": False,
        "knowledge_state": "DISCOVERED",
    }
