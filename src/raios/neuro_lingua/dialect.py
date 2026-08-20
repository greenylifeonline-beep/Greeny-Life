from __future__ import annotations

from typing import Any

from .language import EGYPTIAN_MARKERS, GULF_MARKERS


FUTURE_GULF_CHILDREN = ("ar-SA", "ar-AE", "ar-KW", "ar-QA", "ar-BH", "ar-OM")


def resolve_dialect(text: str, languages: list[dict[str, Any]]) -> dict[str, Any]:
    ar_present = any(row.get("language") == "ar" for row in languages)
    if not ar_present:
        primary = languages[0] if languages else {}
        locale = primary.get("locale") or primary.get("language") or "und"
        return {
            "status": "OK",
            "confidence": primary.get("confidence"),
            "evidence": ["non_arabic_passthrough"],
            "dialect": {
                "parent": primary.get("language") or "und",
                "profile": locale,
                "confidence": primary.get("confidence"),
                "evidence": ["passthrough"],
                "alternatives": [],
                "country_claimed": False,
            },
            "warnings": [],
        }

    eg_hits = [m for m in EGYPTIAN_MARKERS if m in text]
    gulf_hits = [m for m in GULF_MARKERS if m in text]
    evidence = [f"egyptian_markers={eg_hits}", f"gulf_markers={gulf_hits}"]
    alternatives: list[dict[str, Any]] = []
    warnings: list[str] = []
    country_claimed = False

    if eg_hits and (not gulf_hits or len(eg_hits) >= len(gulf_hits)):
        profile = "ar-EG"
        conf = min(0.92, 0.62 + 0.08 * len(eg_hits))
        parent = "ar"
        if gulf_hits:
            alternatives.append({"profile": "ar-GULF", "confidence": min(0.7, 0.45 + 0.08 * len(gulf_hits))})
            warnings.append("MIXED_ARABIC_DIALECT_EVIDENCE")
    elif gulf_hits:
        profile = "ar-GULF"
        conf = min(0.88, 0.58 + 0.08 * len(gulf_hits))
        parent = "ar"
        alternatives.append({"profile": "ar", "note": "msa_possible", "confidence": 0.4})
        warnings.append("GULF_PARENT_ONLY_NO_COUNTRY")
    else:
        profile = "ar"
        conf = 0.55 if text else None
        parent = "ar"
        warnings.append("ARABIC_DIALECT_UNSPECIFIED")
        alternatives = [
            {"profile": "ar-EG", "confidence": None},
            {"profile": "ar-GULF", "confidence": None},
        ]

    return {
        "status": "OK",
        "confidence": conf,
        "evidence": evidence,
        "dialect": {
            "parent": parent,
            "profile": profile,
            "confidence": conf,
            "evidence": evidence,
            "alternatives": alternatives,
            "country_claimed": country_claimed,
            "future_children": list(FUTURE_GULF_CHILDREN) if profile == "ar-GULF" else [],
        },
        "warnings": warnings,
    }
