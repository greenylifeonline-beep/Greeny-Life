"""Compress language to concepts+patterns+relations+context. Not a word list. Not a second engine."""
from __future__ import annotations

import re
from typing import Any


INTENTS = ("greeting", "request", "warning", "question", "command")

ACTORS = {
    "supplier": ("supplier", "suppliers", "المورد", "مورد", "leverandør", "proveedor", "fournisseur", "lieferant"),
    "customer": ("customer", "customers", "العميل", "عميل", "kunde", "الزبون"),
    "warehouse": ("warehouse", "المخزن", "مخزن", "lager"),
    "carrier": ("carrier", "الناقل", "ناقل", "speditør"),
}

ACTIONS = {
    "ship": ("ship", "ships", "shipped", "shipping", "شحن", "يشحن", "شُحن", "لم يشحن"),
    "receive": ("receive", "receives", "received", "استلم", "يستلم", "استلام"),
    "store": ("store", "stores", "stored", "يخزن", "تخزين"),
    "transport": ("transport", "transports", "transported", "ينقل", "نقل"),
}

OBJECTS = {
    "product": ("product", "products", "المنتج", "المنتجات", "منتج", "produkt", "produkter"),
    "order": ("order", "orders", "طلب", "الطلب", "ordre"),
    "shipment": ("shipment", "شحنة", "الشحنة", "sending"),
    "inventory": ("inventory", "stock", "مخزون", "المخزون", "lagerbeholdning"),
}

PLACES = {
    "norway": ("norway", "النرويج", "norge"),
    "uae": ("uae", "emirates", "الإمارات", "dubai"),
    "egypt": ("egypt", "مصر", "cairo"),
}

TIMES = {
    "past": ("shipped", "received", "stored", "transported", "لم", "yet", "already"),
    "future": ("will", "سوف", "will ship"),
    "present": ("ships", "stores", "receives", "يشحن"),
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _hit(text: str, lexicon: dict[str, tuple[str, ...]]) -> str | None:
    lower = text.lower()
    best: tuple[int, str] | None = None
    for key, surfaces in lexicon.items():
        for surface in surfaces:
            if surface.lower() in lower or surface in text:
                size = len(surface)
                if best is None or size > best[0]:
                    best = (size, key)
    return best[1] if best else None


def _intent(text: str, prag: dict[str, Any], action: str | None) -> str:
    if prag.get("domain_warning") or prag.get("pragmatics") and getattr(prag.get("pragmatics"), "warning", False):
        return "warning"
    if action in {"greet"}:
        return "greeting"
    if "?" in text or "هل" in text or text.strip().endswith("؟"):
        return "question"
    if action in {"remove"} or getattr(prag.get("modality"), "imperative", False):
        return "command"
    if action in {"resolve", "inspect", "stock_status", "shipment_status", "quote_request", "invoice_status"}:
        return "request"
    if prag.get("action"):
        return "request"
    return "request" if any(w in text.lower() for w in ("please", "لو سمحت", "kan du")) else "command"


def _context_band(register: dict[str, Any]) -> str:
    row = register.get("register") or register
    spoken = float(row.get("spoken") or 0)
    professional = float(row.get("professional") or 0)
    if professional >= 0.65:
        return "business" if spoken < 0.5 else "technical"
    if spoken >= 0.5:
        return "casual"
    return "formal"


def compress_meaning(
    text: str,
    concepts: dict[str, Any] | None = None,
    prag: dict[str, Any] | None = None,
    register: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prag = prag or {}
    register = register or {}
    working = _norm(text)
    actor = _hit(working, ACTORS)
    action = _hit(working, ACTIONS) or prag.get("action")
    obj = _hit(working, OBJECTS)
    dest = _hit(working, PLACES)
    time = _hit(working, TIMES)
    intent = _intent(working, prag, prag.get("action"))
    context_band = _context_band(register)
    known_ids = [m.get("concept_id") for m in (concepts or {}).get("matches") or [] if m.get("concept_id")]
    pattern = {
        "actor": actor,
        "action": action,
        "object": obj,
        "destination": dest,
        "time": time,
        "intent": intent,
        "context": context_band,
    }
    bound = sum(1 for v in (actor, action, obj, dest, time) if v)
    tokens = [t for t in re.findall(r"[A-Za-zÅÄÖåäöÆØÅæøå]{2,}|[\u0600-\u06FF]{2,}", working)]
    mapped_surfaces = set()
    for lex in (ACTORS, ACTIONS, OBJECTS, PLACES, TIMES):
        for surfaces in lex.values():
            mapped_surfaces.update(s.lower() for s in surfaces)
    unknown = [t for t in tokens if t.lower() not in mapped_surfaces]
    known_ratio = round(1.0 - (len(unknown) / max(len(tokens), 1)), 4)
    delta = unknown[:12]
    return {
        "status": "OK",
        "confidence": round(0.5 + 0.1 * bound, 3),
        "evidence": [f"pattern:{k}={v}" for k, v in pattern.items() if v],
        "pattern": pattern,
        "concepts": known_ids,
        "relations": [f"{actor}:{action}:{obj}"] if actor and action else [],
        "context": context_band,
        "delta": delta,
        "known_ratio": known_ratio,
        "word_list": False,
        "law": "WORD_LIST_NE_LANGUAGE",
        "warnings": [] if bound else ["NO_PATTERN_BOUND"],
    }
