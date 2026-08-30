from __future__ import annotations

from typing import Any

from .protected import preserve_in_text
from .schema import CognitiveMeaningPacket, ProtectedToken


REALIZATIONS = {
    "ar-EG": {
        "resolve": "خلّص لنا الموضوع",
        "inspect": "بص على الموضوع",
        "remove": "شيل الجزء ده",
        "avoid_regression": "من غير ما تبوّظ حاجة في المشروع",
        "deadline_today": "اليوم",
        "polite": "لو سمحت",
    },
    "ar-GULF": {
        "resolve": "شوف لنا الموضوع",
        "inspect": "راجع الموضوع",
        "remove": "احذف الجزء هذا",
        "avoid_regression": "بدون ما يتأثر النظام",
        "deadline_today": "اليوم",
        "polite": "إذا ما عليك أمر",
    },
    "en": {
        "resolve": "Please resolve this",
        "inspect": "Please inspect this",
        "remove": "Remove this",
        "avoid_regression": "without causing a regression",
        "deadline_today": "today",
        "polite": "please",
    },
    "nb-NO": {
        "resolve": "Kan du løse dette",
        "inspect": "Kan du kontrollere dette",
        "remove": "Fjern dette",
        "avoid_regression": "uten å påvirke produksjonen",
        "deadline_today": "i dag",
        "polite": "vennligst",
    },
    "sv-SE": {
        "resolve": "Kan du lösa detta",
        "inspect": "Kontrollera detta",
        "remove": "Ta bort detta",
        "avoid_regression": "utan att påverka produktionen",
        "deadline_today": "i dag",
        "polite": "snälla",
    },
    "da-DK": {
        "resolve": "Kan du løse dette",
        "inspect": "Tjek dette",
        "remove": "Fjern dette",
        "avoid_regression": "uden at påvirke produktionen",
        "deadline_today": "i dag",
        "polite": "venligst",
    },
}

# Positive locale evidence used together with leakage checks.
POSITIVE_LOCALE = {
    "nb-NO": ("løse", "uten", "produksjonen", "vennligst", "ikke", "kan"),
    "sv-SE": ("lösa", "utan", "produktionen", "snälla", "inte", "ändringen"),
    "da-DK": ("løse", "uden", "produktionen", "venligst", "ikke", "tjek"),
}

LEAKAGE = {
    "nb-NO": {"sv": ("och", "ändringen", "snälla", "inte"), "da": ("tjek", "ændringen")},
    "sv-SE": {"nb": ("bokmål", "ikkje"), "da": ("tjek", "ændringen")},
    "da-DK": {"nb": ("bokmål",), "sv": ("och", "ändringen", "snälla")},
}


def realize_meaning(
    meaning: CognitiveMeaningPacket,
    target_locale: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    action = meaning.semantics.action or (meaning.actions[0]["action"] if meaning.actions else "resolve")
    from .customer import CUSTOMER_ACTS, realize_customer

    if action in CUSTOMER_ACTS:
        rec = realize_customer(meaning, target_locale, context)
        tokens: list[ProtectedToken] = list(meaning.preserved_tokens)
        text = str(rec.get("text") or "")
        text, preserve_warnings = preserve_in_text(meaning.source_text, text, tokens)
        rec["text"] = text
        rec["warnings"] = list(rec.get("warnings") or []) + preserve_warnings
        rec["leakage"] = detect_scandinavian_leakage(text, target_locale)
        return rec

    table = REALIZATIONS.get(target_locale) or REALIZATIONS["en"]
    parts = []
    if meaning.pragmatics.politeness_marker:
        parts.append(table["polite"])
    parts.append(table.get(action, table["resolve"]))
    if "avoid_regression" in meaning.constraints:
        parts.append(table["avoid_regression"])
    if meaning.temporal.deadline == "today" or meaning.pragmatics.deadline == "today":
        parts.append(table["deadline_today"])

    text = " ".join(parts).strip()
    tokens: list[ProtectedToken] = list(meaning.preserved_tokens)
    if tokens:
        preserved = " ".join(token.text for token in tokens if token.kind in {"technical_term", "identifier", "filename", "qualified_ident"})
        if preserved:
            text = f"{text} {preserved}".strip()
    text, warnings = preserve_in_text(meaning.source_text, text, tokens)
    leakage = detect_scandinavian_leakage(text, target_locale)
    warnings.extend(leakage.get("warnings") or [])
    return {
        "status": "OK",
        "confidence": 0.74,
        "evidence": [f"realizer:{target_locale}", f"action:{action}"],
        "text": text,
        "target_locale": target_locale,
        "leakage": leakage,
        "warnings": warnings,
        "provider": f"deterministic-realizer:{target_locale}",
    }


def detect_scandinavian_leakage(text: str, target_locale: str) -> dict[str, Any]:
    lower = text.lower()
    warnings: list[str] = []
    evidence: list[str] = []
    positive = 0
    for token in POSITIVE_LOCALE.get(target_locale, ()):
        if token in lower:
            positive += 1
            evidence.append(f"positive:{token}")
    leaked = []
    tokens = set(lower.replace(".", " ").split())
    for other, words in LEAKAGE.get(target_locale, {}).items():
        for word in words:
            if word in tokens:
                leaked.append({"from": other, "token": word})
                warnings.append(f"LEAKAGE:{other}:{word}")
    status = "LEAKAGE" if leaked else "OK"
    confidence = None
    if positive or leaked:
        confidence = max(0.2, min(0.9, 0.4 + 0.1 * positive - 0.2 * len(leaked)))
    return {
        "status": status,
        "positive_hits": positive,
        "leaks": leaked,
        "warnings": warnings,
        "evidence": evidence,
        "confidence": confidence,
    }
