"""Semantic realization into a target locale without blanket English pivoting."""

from __future__ import annotations

from raios.neuro_lingua.concepts import ConceptRegistry
from raios.neuro_lingua.packet import CognitiveMeaningPacket
from raios.neuro_lingua.scandinavian import ScandinavianIsolator
from raios.neuro_lingua.types import SCANDINAVIAN_LOCALES


class SemanticRealizer:
    def __init__(self, registry: ConceptRegistry, isolator: ScandinavianIsolator) -> None:
        self.registry = registry
        self.isolator = isolator

    def realize(self, meaning: CognitiveMeaningPacket, target_locale: str) -> tuple[str, bool, list[str]]:
        warnings: list[str] = []
        parts: list[str] = []
        complete = True

        prag = meaning.pragmatics
        if prag.politeness_marker:
            please = self.registry.realization("pragmatics.politeness_softener", target_locale)
            if please:
                parts.append(please)

        if prag.action == "resolve":
            action = self.registry.realization("action.resolve", target_locale)
            parts.append(action or "resolve")
        elif prag.action == "inspect":
            action = self.registry.realization("action.inspect", target_locale)
            parts.append(action or "look into")

        if prag.deadline == "today":
            deadline = self.registry.realization("deadline.today", target_locale)
            parts.append(deadline or "today")

        for concept in meaning.concepts:
            record = self.registry.get(concept.concept_id)
            if record is None:
                continue
            if concept.concept_id in {
                "action.resolve",
                "action.inspect",
                "deadline.today",
                "pragmatics.politeness_softener",
            }:
                continue
            if record.preserve_surface:
                parts.append(concept.surface)
                continue
            realized = self.registry.realization(concept.concept_id, target_locale)
            if realized:
                parts.append(realized)
            else:
                complete = False
                warnings.append(f"no_realization:{concept.concept_id}:{target_locale}")

        # Always splice preserved technical spans that are not already present.
        preserved = []
        for span in (*meaning.identifiers, *meaning.terminology):
            if span.surface and span.surface not in preserved:
                preserved.append(span.surface)
        for surface in preserved:
            if surface not in " ".join(parts):
                parts.append(surface)

        for span in meaning.numbers:
            if span.surface not in " ".join(parts):
                parts.append(span.surface)

        if not parts:
            complete = False
            warnings.append("insufficient_concepts_for_fluent_realization")
            # Honest fallback: structured meaning, not a fake translation.
            structured = []
            if prag.action:
                structured.append(f"action={prag.action}")
            if prag.deadline:
                structured.append(f"deadline={prag.deadline}")
            if prag.politeness_marker:
                structured.append("politeness_marker=true")
            for span in meaning.identifiers:
                structured.append(span.surface)
            text = "[" + "; ".join(structured) + "]" if structured else meaning.source_text
            return text, False, warnings

        text = _join_for_locale(parts, target_locale)
        if target_locale in SCANDINAVIAN_LOCALES:
            leak = self.isolator.detect_leakage(text, target_locale)
            if not leak.passed:
                warnings.append("scandinavian_leakage:" + ",".join(leak.leaked_tokens))
        return text, complete, warnings


def _join_for_locale(parts: list[str], locale: str) -> str:
    # Deduplicate while preserving order.
    unique: list[str] = []
    for part in parts:
        if part not in unique:
            unique.append(part)
    if locale.startswith("ar"):
        return " ".join(unique)
    if locale == "nb-NO":
        return _norwegian_join(unique)
    if locale == "sv-SE":
        return _swedish_join(unique)
    if locale == "da-DK":
        return _danish_join(unique)
    return " ".join(unique)


def _norwegian_join(parts: list[str]) -> str:
    please = "vær så snill" if "vær så snill" in parts else None
    rest = [p for p in parts if p != please]
    if please and rest:
        return f"{please}: {' '.join(rest)}"
    return " ".join(parts)


def _swedish_join(parts: list[str]) -> str:
    please = "var snäll" if "var snäll" in parts else None
    rest = [p for p in parts if p != please]
    if please and rest:
        return f"{please}: {' '.join(rest)}"
    return " ".join(parts)


def _danish_join(parts: list[str]) -> str:
    please = "vær venlig" if "vær venlig" in parts else None
    rest = [p for p in parts if p != please]
    if please and rest:
        return f"{please}: {' '.join(rest)}"
    return " ".join(parts)
