from __future__ import annotations

import re
import unicodedata
from typing import Any


ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")
LATIN_RE = re.compile(r"[A-Za-zÅÄÖåäöÆØÅæøå]")
DIGIT_RE = re.compile(r"\d")

EGYPTIAN_MARKERS = (
    "مش",
    "ده",
    "دي",
    "بتاع",
    "عايز",
    "عاوز",
    "خلصلي",
    "هتبوظ",
    "بيتولد",
    "إزاي",
    "ازاي",
    "كده",
    "علشان",
    "عشان",
    "واقفة",
)

GULF_MARKERS = (
    "زين",
    "وايد",
    "يبيلنا",
    "شوف لنا",
    "ما عليك أمر",
    "إذا ما عليك أمر",
    "ابي",
    "أبي",
    "حجي",
    "يبي",
    "محجوزة",
)

NB_POSITIVE = ("ikke", "kan", "den", "nye", "ikke", "bokmål", "ikke")
SV_POSITIVE = ("och", "inte", "påverka", "ändringen", "produktion", "kontrollera")
DA_POSITIVE = ("ikke", "tjek", "ændringen", "uden", "påvirke", "produktionen")


def _script_counts(text: str) -> dict[str, int]:
    arabic = len(ARABIC_RE.findall(text))
    latin = len(LATIN_RE.findall(text))
    digits = len(DIGIT_RE.findall(text))
    return {"arabic": arabic, "latin": latin, "digits": digits, "total": max(len(text), 1)}


def normalize_text(text: str) -> dict[str, Any]:
    original = text
    stripped = unicodedata.normalize("NFC", text).strip()
    collapsed = re.sub(r"[ \t]+", " ", stripped)
    collapsed = re.sub(r"\n{3,}", "\n\n", collapsed)
    evidence = ["unicode_nfc", "whitespace_collapse"]
    return {
        "status": "OK",
        "confidence": 1.0,
        "evidence": evidence,
        "text": collapsed,
        "original": original,
        "warnings": [] if collapsed else ["EMPTY_AFTER_NORMALIZE"],
    }


def identify_language(text: str) -> dict[str, Any]:
    counts = _script_counts(text)
    lower = text.lower()
    evidence: list[str] = [f"script_arabic={counts['arabic']}", f"script_latin={counts['latin']}"]
    languages: list[dict[str, Any]] = []
    warnings: list[str] = []

    arabic_ratio = counts["arabic"] / counts["total"]
    latin_ratio = counts["latin"] / counts["total"]

    if counts["arabic"] > 0:
        conf = min(0.98, 0.55 + arabic_ratio)
        languages.append(
            {
                "language": "ar",
                "confidence": round(conf, 3),
                "source": "deterministic+script",
                "evidence": ["arabic_script"],
            }
        )
        evidence.append("arabic_script")

    scandi_hits = {
        "nb-NO": sum(1 for w in ("ikke", "deploye", "builden", "databasen", "forsendelse", "tollen", "sending") if w in lower),
        "sv-SE": sum(1 for w in ("påverka", "ändringen", "kontrollera", "och", "försändelse", "tullen", "stoppad") if w in lower),
        "da-DK": sum(1 for w in ("tjek", "ændringen", "påvirke", "uden", "tolden", "tilbageholdt") if w in lower),
    }
    en_hits = sum(
        1
        for w in ("the", "and", "only", "if", "remove", "runtime", "behavior", "migration", "report", "executor", "deploy", "build", "production")
        if re.search(rf"\b{re.escape(w)}\b", lower)
    )

    if latin_ratio > 0.04:
        best_scandi = max(scandi_hits, key=lambda k: scandi_hits[k])
        if scandi_hits[best_scandi] >= 2 and scandi_hits[best_scandi] > en_hits:
            locale = best_scandi
            lang = {"nb-NO": "nb", "sv-SE": "sv", "da-DK": "da"}[locale]
            conf = min(0.93, 0.55 + 0.12 * scandi_hits[best_scandi])
            languages.append(
                {
                    "language": lang,
                    "locale": locale,
                    "confidence": round(conf, 3),
                    "source": "deterministic+lexical",
                    "evidence": [f"scandi_hits:{best_scandi}={scandi_hits[best_scandi]}"],
                }
            )
            evidence.append(f"locale_lexical:{locale}")
        elif en_hits or latin_ratio > 0.12:
            conf = min(0.95, 0.5 + 0.08 * max(en_hits, 1) + latin_ratio)
            languages.append(
                {
                    "language": "en",
                    "locale": "en",
                    "confidence": round(conf, 3),
                    "source": "deterministic+lexical",
                    "evidence": [f"en_hits={en_hits}"],
                }
            )
            evidence.append("english_lexical")

    if not languages:
        warnings.append("LANGUAGE_UNKNOWN")
        return {
            "status": "UNKNOWN",
            "confidence": None,
            "evidence": evidence,
            "languages": [],
            "warnings": warnings,
        }

    languages.sort(key=lambda row: row.get("confidence") or 0, reverse=True)
    primary = languages[0]
    return {
        "status": "OK",
        "confidence": primary.get("confidence"),
        "evidence": evidence,
        "languages": languages,
        "warnings": warnings,
        "code_switch_likely": counts["arabic"] > 0 and counts["latin"] > 0,
    }
