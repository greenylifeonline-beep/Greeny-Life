"""Extract numbers, identifiers, entities, and terminology that must survive realization."""

from __future__ import annotations

import re

from raios.neuro_lingua.types import CodeSwitchSegment, PreservedSpan

LATN_NUMBER_RE = re.compile(
    r"(?<![A-Za-z])(?:\d{1,3}(?:[ ,.\u00a0]\d{3})+|\d+(?:[.,]\d+)?)(?:%|°)?(?![A-Za-z])"
)
ARABIC_INDIC_RE = re.compile(r"[٠-٩]+(?:[.,٫٬][٠-٩]+)?")
VERSION_RE = re.compile(r"\bv?\d+\.\d+(?:\.\d+)?\b", re.I)

INDIC_TO_LATIN = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def extract_numbers(text: str) -> list[PreservedSpan]:
    spans: list[PreservedSpan] = []
    seen: set[tuple[int, int]] = set()
    for pattern in (VERSION_RE, ARABIC_INDIC_RE, LATN_NUMBER_RE):
        for match in pattern.finditer(text):
            key = (match.start(), match.end())
            if key in seen:
                continue
            seen.add(key)
            spans.append(
                PreservedSpan(
                    kind="number",
                    surface=match.group(0),
                    start=match.start(),
                    end=match.end(),
                )
            )
    spans.sort(key=lambda s: s.start)
    return spans


def canonical_number(surface: str) -> str:
    return surface.translate(INDIC_TO_LATIN).replace("٫", ".").replace("٬", "")


def extract_identifiers(text: str, segments: list[CodeSwitchSegment]) -> list[PreservedSpan]:
    spans: list[PreservedSpan] = []
    for segment in segments:
        if not (segment.preserve or segment.technical):
            continue
        start = text.find(segment.text.split()[0]) if segment.text else -1
        # Prefer exact find of the full segment text
        found = text.find(segment.text)
        if found < 0:
            found = max(start, 0)
        spans.append(
            PreservedSpan(
                kind="identifier",
                surface=segment.text,
                start=found,
                end=found + len(segment.text),
            )
        )
    return spans


_ENTITY_RE = re.compile(
    r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+|RAIOS|GREENY(?:\s+LIFE)?|GL-DOS|EOS)\b"
)


def extract_entities(text: str) -> list[PreservedSpan]:
    return [
        PreservedSpan(kind="entity", surface=m.group(0), start=m.start(), end=m.end())
        for m in _ENTITY_RE.finditer(text)
    ]


def extract_terminology(segments: list[CodeSwitchSegment], text: str) -> list[PreservedSpan]:
    spans: list[PreservedSpan] = []
    for segment in segments:
        if "lexicon_technical" in segment.notes or segment.kind.value == "technical":
            found = text.find(segment.text)
            if found < 0:
                continue
            spans.append(
                PreservedSpan(
                    kind="terminology",
                    surface=segment.text,
                    start=found,
                    end=found + len(segment.text),
                )
            )
    return spans
