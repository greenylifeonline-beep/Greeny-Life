"""Code-switch segmentation with technical-term preservation.

Technical identifiers are first-class spans. They are never mechanically
translated. Mixed morphology (Norwegian ``deploye``, ``builden``) is marked
as technical hosted by the matrix locale.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from raios.neuro_lingua.types import (
    CodeSwitchSegment,
    Confidence,
    DetectionResult,
    SegmentKind,
)

URL_RE = re.compile(r"https?://[^\s]+|www\.[^\s]+", re.I)
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
PATH_RE = re.compile(
    r"\b[\w.\-]+\.(?:py|ts|tsx|js|json|ya?ml|md|txt|sql|sh|exe)\b"
)
UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
CAMEL_RE = re.compile(r"\b[A-Z][a-z0-9]*[A-Z][A-Za-z0-9]*\b|\b[a-z]+[A-Z][A-Za-z0-9]+\b")
SNAKE_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+\b")
SCREAMING_RE = re.compile(r"\b[A-Z]{2,}(?:_[A-Z0-9]+)+\b")
DOTTED_RE = re.compile(r"\b[A-Za-z][\w]*\.[A-Za-z][\w.]+\b")
SHELL_RE = re.compile(r"\b(?:npm|npx|pip|git|docker|kubectl|curl|ssh|chmod|systemctl)\b")
AR_ARTICLE_LATIN = re.compile(r"(الـ?)([A-Za-z][A-Za-z0-9_\-.]*)")
HYPHEN_TECH = re.compile(r"\b[A-Za-z]+-[A-Za-z][A-Za-z0-9\-]*\b")

TECHNICAL_STEMS = {
    "migration",
    "report",
    "executor",
    "deploy",
    "deploye",
    "build",
    "builden",
    "touch",
    "touche",
    "production",
    "database",
    "databasen",
    "uuid",
    "api",
    "http",
    "json",
    "yaml",
    "sql",
    "prisma",
}

LOAN_VERBS = {"deploye", "touche", "migratе"}  # latin e-verbalizer
LOAN_VERBS = {"deploye", "touche"}
LOAN_DEFINITES = {"builden", "databasen", "reporten", "executorn"}


@dataclass
class RawSpan:
    start: int
    end: int
    locale: str
    kind: SegmentKind
    technical: bool
    preserve: bool
    notes: list[str] = field(default_factory=list)

    def text_of(self, source: str) -> str:
        return source[self.start : self.end]


def _overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def extract_preserved_spans(text: str) -> list[RawSpan]:
    patterns: list[tuple[re.Pattern[str], str]] = [
        (URL_RE, "url"),
        (EMAIL_RE, "email"),
        (UUID_RE, "uuid"),
        (PATH_RE, "filename"),
        (SCREAMING_RE, "constant"),
        (CAMEL_RE, "camelcase"),
        (SNAKE_RE, "snake_case"),
        (DOTTED_RE, "dotted_id"),
        (SHELL_RE, "shell"),
        (HYPHEN_TECH, "hyphenated"),
    ]
    spans: list[RawSpan] = []
    occupied: list[tuple[int, int]] = []

    def add(start: int, end: int, note: str, locale: str = "en/technical") -> None:
        rng = (start, end)
        if any(_overlap(rng, other) for other in occupied):
            return
        occupied.append(rng)
        spans.append(
            RawSpan(
                start=start,
                end=end,
                locale=locale,
                kind=SegmentKind.TECHNICAL,
                technical=True,
                preserve=True,
                notes=[note],
            )
        )

    for pattern, note in patterns:
        for match in pattern.finditer(text):
            add(match.start(), match.end(), note)

    for match in AR_ARTICLE_LATIN.finditer(text):
        add(match.start(2), match.end(2), "latin_after_arabic_article")

    spans.sort(key=lambda s: s.start)
    return spans


_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9_\-\.]+|[\u0600-\u06FFـ]+")


def _classify_word(
    token: str,
    detection: DetectionResult,
) -> tuple[str, SegmentKind, bool, bool, list[str]]:
    lower = token.lower()
    if lower in TECHNICAL_STEMS:
        return "en/technical", SegmentKind.TECHNICAL, True, True, ["lexicon_technical"]
    if lower in LOAN_VERBS or lower in LOAN_DEFINITES:
        host = detection.locale if detection.locale in {"nb-NO", "sv-SE", "da-DK"} else (
            detection.locale or "nb-NO"
        )
        return f"{host}/technical", SegmentKind.MIXED, True, True, ["scandinavian_loan"]
    if re.search(r"[\u0600-\u06FF]", token):
        loc = detection.locale if detection.language == "ar" and detection.locale else "ar"
        if token in {"الـ"} or token.startswith("الـ"):
            return loc or "ar", SegmentKind.LANGUAGE, False, False, ["arabic_article"]
        return loc or "ar", SegmentKind.LANGUAGE, False, False, ["arabic_script"]
    if re.search(r"[A-Za-z]", token):
        if detection.language == "ar":
            return "en/technical", SegmentKind.TECHNICAL, True, True, ["latin_island_in_arabic"]
        if detection.locale in {"nb-NO", "sv-SE", "da-DK"}:
            return detection.locale, SegmentKind.LANGUAGE, False, False, ["matrix_locale"]
        if detection.locale == "en" or detection.language == "en":
            return "en", SegmentKind.LANGUAGE, False, False, ["english"]
        return detection.locale or "en", SegmentKind.LANGUAGE, False, False, ["latin"]
    return detection.locale or "und", SegmentKind.LANGUAGE, False, False, ["other"]


def _covered(index: int, spans: list[RawSpan]) -> RawSpan | None:
    for span in spans:
        if span.start <= index < span.end:
            return span
    return None


def segment(text: str, detection: DetectionResult) -> list[CodeSwitchSegment]:
    preserved = extract_preserved_spans(text)
    raw: list[RawSpan] = []
    for match in _WORD_RE.finditer(text):
        hit = _covered(match.start(), preserved)
        if hit is not None:
            if not raw or raw[-1] is not hit:
                raw.append(hit)
            continue
        locale, kind, technical, preserve, notes = _classify_word(match.group(0), detection)
        raw.append(
            RawSpan(
                start=match.start(),
                end=match.end(),
                locale=locale,
                kind=kind,
                technical=technical,
                preserve=preserve,
                notes=notes,
            )
        )

    merged: list[RawSpan] = []
    for span in raw:
        if (
            merged
            and merged[-1].locale == span.locale
            and merged[-1].kind == span.kind
            and merged[-1].technical == span.technical
        ):
            prev = merged[-1]
            merged[-1] = RawSpan(
                start=prev.start,
                end=span.end,
                locale=prev.locale,
                kind=prev.kind,
                technical=prev.technical,
                preserve=prev.preserve or span.preserve,
                notes=list(dict.fromkeys(prev.notes + span.notes)),
            )
        else:
            merged.append(span)

    segments: list[CodeSwitchSegment] = []
    for index, span in enumerate(merged, start=1):
        surface = span.text_of(text).strip()
        if not surface:
            continue
        method = "preserved_span" if span.preserve else "codeswitch_token_class"
        value = 1.0 if span.preserve else 0.8
        segments.append(
            CodeSwitchSegment(
                index=index,
                text=surface,
                locale=span.locale,
                kind=span.kind,
                confidence=Confidence(
                    value=value,
                    method=method,
                    evidence=span.notes,
                    sample_size=1,
                ),
                technical=span.technical,
                preserve=span.preserve,
                notes=span.notes,
            )
        )
    return segments
