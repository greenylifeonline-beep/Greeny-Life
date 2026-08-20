"""Hybrid language / dialect detector.

Tier 0: Unicode script + obvious lexical signals (always on).
Tier 1: Cheap local LID library if installed — never downloaded in tests.
Tier 2: Dialect / code-switch classifier when family is known but dialect is not.
Tier 3: LLM semantic adjudication only for remaining ambiguous cases.

Confidence is computed from evidence. Missing tiers are recorded, not faked.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

from raios.neuro_lingua.types import (
    GULF_CHILDREN,
    Confidence,
    DetectionResult,
    InterpretationContext,
)

ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")
LATIN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]")
LETTER_RE = re.compile(r"[^\W\d_]", re.UNICODE)

# High-signal Egyptian markers (not a phrase dictionary — dialect evidence).
EGYPTIAN_MARKERS = {
    "مش",
    "ايه",
    "ازاي",
    "عايز",
    "عاوز",
    "دلوقتي",
    "كده",
    "بتاع",
    "هتبوظ",
    "هيبوظ",
    "بيتولد",
    "النهارده",
    "النهاردة",
    "مفيش",
    "عشان",
    "علشان",
    "ماشي",
    "اوي",
    "قوي",
    "عامل",
    "الدنيا",
    "عملت",
    "شوف لنا",
}

# Gulf-neutral parent markers. Sub-dialect classifiers are NOT implemented in NL-0.
GULF_MARKERS = {
    "شلون",
    "شنو",
    "ابي",
    "أبي",
    "أبغى",
    "ابغى",
    "زين",
    "الحين",
    "وايد",
    "يبا",
    "مو",
    "مب",
    "جذي",
    "انزين",
    "تري",
    "هلبا",
    "اكو",
}

ENGLISH_MARKERS = {
    "the",
    "and",
    "is",
    "to",
    "of",
    "for",
    "with",
    "not",
    "please",
    "today",
    "report",
    "migration",
    "executor",
    "deploy",
    "build",
    "production",
    "database",
}

NB_MARKERS = {"ikke", "noe", "noen", "gøy", "knekke", "saken", "ferdig", "ikke"}
SV_MARKERS = {"inte", "och", "också", "kanske", "något", "någon", "här", "där", "även", "ska", "lösa"}
DA_MARKERS = {"noget", "nogen", "knække", "sagen", "gøre"}
# Shared Scandinavian function words — useful for family, weak for locale.
SCAN_SHARED = {"kan", "du", "den", "men", "nye", "og", "i", "dag", "ikke"}

# Danish and Norwegian share "ikke" and "og". They are NOT used as the sole
# discriminator. Distinctive sets above are the dialect/locale evidence.


def _normalize_ar(token: str) -> str:
    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ة": "ه",
        "ى": "ي",
        "ؤ": "و",
        "ئ": "ي",
        "ً": "",
        "ٌ": "",
        "ٍ": "",
        "َ": "",
        "ُ": "",
        "ِ": "",
        "ّ": "",
        "ْ": "",
        "ـ": "",
    }
    out = token
    for src, dst in replacements.items():
        out = out.replace(src, dst)
    return out


def tokenize(text: str) -> list[str]:
    return [tok for tok in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9_\-\.]+|[\u0600-\u06FF]+", text) if tok]


def _score_markers(tokens: Iterable[str], markers: set[str], *, arabic: bool = False, text: str = "") -> tuple[int, list[str]]:
    hits: list[str] = []
    marker_norm = {_normalize_ar(m) if arabic else m.lower() for m in markers}
    for token in tokens:
        candidate = _normalize_ar(token) if arabic else token.lower()
        if candidate in marker_norm:
            hits.append(token)
    haystack = _normalize_ar(text) if arabic else text.lower()
    for marker in markers:
        if " " not in marker:
            continue
        needle = _normalize_ar(marker) if arabic else marker.lower()
        if needle and needle in haystack:
            hits.append(marker)
    return len(hits), hits


def _script_profile(text: str) -> tuple[str | None, Confidence, int, int, int]:
    letters = LETTER_RE.findall(text)
    if not letters:
        return None, Confidence(value=0.0, method="no_letters", sample_size=0), 0, 0, 0
    arabic = sum(1 for ch in letters if ARABIC_RE.match(ch))
    latin = sum(1 for ch in letters if LATIN_RE.match(ch))
    total = len(letters)
    if arabic == 0 and latin == 0:
        return None, Confidence(value=0.0, method="unknown_script", sample_size=total), arabic, latin, total
    if arabic > latin:
        return (
            "arab",
            Confidence(
                value=arabic / total,
                method="unicode_script",
                evidence=["arabic_letters"],
                sample_size=total,
            ),
            arabic,
            latin,
            total,
        )
    if latin > arabic:
        return (
            "latn",
            Confidence(
                value=latin / total,
                method="unicode_script",
                evidence=["latin_letters"],
                sample_size=total,
            ),
            arabic,
            latin,
            total,
        )
    # Equal mix: code-switch at script level, confidence is the mix ratio not a guess.
    mix = 0.5 if arabic and latin else 0.0
    return (
        "mixed",
        Confidence(
            value=mix,
            method="unicode_script_mixed",
            evidence=["arabic_letters", "latin_letters"],
            sample_size=total,
        ),
        arabic,
        latin,
        total,
    )


def _try_tier1(text: str) -> tuple[str | None, Confidence]:
    """Cheap local LID. Import is optional; tests must not download models."""
    try:
        import langid  # type: ignore
    except Exception:
        try:
            from langdetect import detect_langs  # type: ignore
        except Exception:
            return None, Confidence(
                value=0.0,
                method="tier1_unavailable",
                unavailable_tiers=["tier1"],
                sample_size=0,
            )
        else:
            try:
                langs = detect_langs(text)
            except Exception:
                return None, Confidence(value=0.0, method="tier1_langdetect_error", sample_size=0)
            if not langs:
                return None, Confidence(value=0.0, method="tier1_langdetect_empty", sample_size=0)
            top = langs[0]
            return str(top.lang), Confidence(
                value=float(top.prob),
                method="tier1_langdetect",
                evidence=[str(top.lang)],
                sample_size=1,
            )
    else:
        lang, score = langid.classify(text)
        # langid returns a log-prob; do not pretend it is a calibrated [0,1]
        # probability. We only keep the label and record the raw score.
        return str(lang), Confidence(
            value=0.0,
            method="tier1_langid_uncalibrated",
            evidence=[f"{lang}:{score}"],
            sample_size=1,
        )


def _locale_from_iso(iso: str | None) -> str | None:
    if not iso:
        return None
    mapping = {
        "ar": None,  # family only — dialect unresolved
        "en": "en",
        "nb": "nb-NO",
        "no": "nb-NO",
        "sv": "sv-SE",
        "da": "da-DK",
    }
    return mapping.get(iso)


class HybridLanguageDetector:
    def detect(self, text: str, context: InterpretationContext | None = None) -> DetectionResult:
        ctx = context or InterpretationContext()
        tiers: list[str] = []
        tokens = tokenize(text)

        script, script_conf, arabic_n, latin_n, _total = _script_profile(text)
        tiers.append("tier0_script")

        eg_n, eg_hits = _score_markers(tokens, EGYPTIAN_MARKERS, arabic=True, text=text)
        gulf_n, gulf_hits = _score_markers(tokens, GULF_MARKERS, arabic=True, text=text)
        en_n, en_hits = _score_markers(tokens, ENGLISH_MARKERS, text=text)
        nb_n, nb_hits = _score_markers(tokens, NB_MARKERS, text=text)
        sv_n, sv_hits = _score_markers(tokens, SV_MARKERS, text=text)
        da_n, da_hits = _score_markers(tokens, DA_MARKERS, text=text)
        scan_n, scan_hits = _score_markers(tokens, SCAN_SHARED, text=text)
        tiers.append("tier0_lexical")

        code_switched = arabic_n > 0 and latin_n > 0

        locale: str | None = None
        language: str | None = None
        dialect: str | None = None
        lang_conf = script_conf
        dialect_conf = Confidence(value=0.0, method="dialect_unresolved", sample_size=0)
        competing: list[tuple[str, float]] = []

        if script in {"arab", "mixed"} and (eg_n + gulf_n > 0 or arabic_n > 0):
            language = "ar"
            dialect_total = eg_n + gulf_n
            if dialect_total == 0:
                locale = None
                dialect = None
                dialect_conf = Confidence(
                    value=0.0,
                    method="arabic_family_no_dialect_markers",
                    evidence=["arabic_script"],
                    sample_size=arabic_n,
                )
            else:
                eg_score = eg_n / dialect_total
                gulf_score = gulf_n / dialect_total
                competing = [("ar-EG", round(eg_score, 4)), ("ar-GULF", round(gulf_score, 4))]
                if eg_n > gulf_n:
                    locale, dialect = "ar-EG", "egyptian"
                    dialect_conf = Confidence(
                        value=eg_score,
                        method="lexical_dialect",
                        evidence=eg_hits,
                        sample_size=dialect_total,
                    )
                elif gulf_n > eg_n:
                    locale, dialect = "ar-GULF", "gulf_neutral"
                    dialect_conf = Confidence(
                        value=gulf_score,
                        method="lexical_dialect",
                        evidence=gulf_hits,
                        sample_size=dialect_total,
                    )
                else:
                    locale, dialect = None, None
                    dialect_conf = Confidence(
                        value=eg_score,
                        method="lexical_dialect_tie",
                        evidence=eg_hits + gulf_hits,
                        sample_size=dialect_total,
                    )
            lang_conf = Confidence(
                value=script_conf.value if script == "arab" else max(script_conf.value, 0.5 if arabic_n else 0.0),
                method="unicode_script+arabic_family",
                evidence=["arabic_script"] + eg_hits + gulf_hits,
                sample_size=arabic_n + dialect_total,
            )

        latin_scores = {
            "en": en_n,
            "nb-NO": nb_n,
            "sv-SE": sv_n,
            "da-DK": da_n,
        }
        latin_hits = {
            "en": en_hits,
            "nb-NO": nb_hits,
            "sv-SE": sv_hits,
            "da-DK": da_hits,
        }
        if script in {"latn", "mixed"}:
            distinctive_total = sum(latin_scores.values())
            ranked = sorted(latin_scores.items(), key=lambda kv: kv[1], reverse=True)
            competing.extend((loc, float(score)) for loc, score in ranked if score)
            top_loc, top_n = ranked[0]
            second_n = ranked[1][1]
            if top_n > 0 and top_n > second_n:
                if language is None:
                    language = top_loc.split("-")[0] if "-" in top_loc else top_loc
                    locale = top_loc
                    lang_conf = Confidence(
                        value=top_n / distinctive_total,
                        method="lexical_language",
                        evidence=latin_hits[top_loc],
                        sample_size=distinctive_total,
                    )
                    dialect_conf = Confidence(
                        value=0.0,
                        method="no_dialect_for_non_arabic",
                        sample_size=0,
                    )
            elif scan_n > 0 and language is None:
                language = "scandinavian"
                locale = None
                lang_conf = Confidence(
                    value=scan_n / max(len(tokens), 1),
                    method="scandinavian_family_unresolved",
                    evidence=scan_hits,
                    sample_size=scan_n,
                )
            elif language is None and en_n == 0 and distinctive_total == 0 and latin_n > 0:
                language = None
                locale = None
                lang_conf = Confidence(
                    value=script_conf.value,
                    method="latin_script_no_lexical_id",
                    sample_size=latin_n,
                )

        # Code-switch: Arabic host with English technical is still the Arabic locale
        # when dialect markers exist; code_switched flag carries the mix.
        if code_switched and language == "ar" and locale:
            pass
        elif code_switched and language is None and arabic_n > latin_n:
            language = "ar"

        unavailable: list[str] = []
        # Tier 1 only when Tier 0 could not assign a locale/language.
        if locale is None and language not in {"ar"} or (language is None):
            if locale is None and language not in {"ar"}:
                t1_lang, t1_conf = _try_tier1(text)
                if t1_conf.method == "tier1_unavailable":
                    unavailable.extend(t1_conf.unavailable_tiers)
                else:
                    tiers.append("tier1")
                    mapped = _locale_from_iso(t1_lang)
                    if mapped and locale is None:
                        locale = mapped
                        language = mapped.split("-")[0] if "-" in mapped else mapped
                        lang_conf = t1_conf
                    elif t1_lang == "ar" and language is None:
                        language = "ar"
                        lang_conf = t1_conf

        ambiguous = False
        if language == "ar" and dialect is None:
            ambiguous = True
        if competing:
            positive = [item for item in competing if item[1] > 0]
            if len(positive) >= 2:
                scores = sorted((item[1] for item in positive), reverse=True)
                if scores[0] > 0 and abs(scores[0] - scores[1]) < 0.15:
                    ambiguous = True

        if ambiguous:
            tiers.append("tier2_needed")
            # NL-0 Tier 2 is the same lexical classifier with an explicit
            # unresolved state — we do not invent a dialect. Gulf children
            # are taxonomy-only.
            if language == "ar" and dialect is None:
                dialect_conf = Confidence(
                    value=dialect_conf.value,
                    method=dialect_conf.method,
                    evidence=dialect_conf.evidence,
                    sample_size=dialect_conf.sample_size,
                    unavailable_tiers=list(dialect_conf.unavailable_tiers) + ["tier2_gulf_children"],
                )

        if (
            ambiguous
            and ctx.allow_llm
            and not ctx.offline
        ):
            tiers.append("tier3_eligible")
        elif ambiguous:
            unavailable.append("tier3_llm_adjudication")

        if unavailable:
            lang_conf = Confidence(
                value=lang_conf.value,
                method=lang_conf.method,
                evidence=lang_conf.evidence,
                sample_size=lang_conf.sample_size,
                unavailable_tiers=sorted(set(lang_conf.unavailable_tiers + unavailable)),
            )

        return DetectionResult(
            locale=locale,
            language=language,
            dialect=dialect,
            script=script,
            code_switched=code_switched,
            language_confidence=lang_conf,
            dialect_confidence=dialect_conf,
            tiers_used=tiers,
            competing=competing,
            gulf_child=None,
            gulf_child_implemented=False,
        )

    def gulf_taxonomy(self) -> dict[str, str]:
        return dict(GULF_CHILDREN)
