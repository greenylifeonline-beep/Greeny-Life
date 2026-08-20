"""Concept Registry loader with scoped realization overlays.

Precedence: Global → Domain → Organization → Project → User → Session.
Lower levels may customize realization. They may NOT silently redefine
canonical semantics. Collisions are raised, not swallowed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

import yaml

from raios.neuro_lingua.types import BoundConcept, Confidence, InterpretationContext

PRECEDENCE = ("global", "domain", "organization", "project", "user", "session")


class ConceptRegistryError(ValueError):
    pass


class ConceptCollisionError(ConceptRegistryError):
    pass


class CanonicalRedefinitionError(ConceptRegistryError):
    pass


@dataclass
class ConceptRecord:
    concept_id: str
    canonical_meaning: str
    aliases: dict[str, list[str]]
    realizations: dict[str, str]
    domains: list[str] = field(default_factory=list)
    flags: dict[str, Any] = field(default_factory=dict)
    preserve_surface: bool = False
    contextual_only: bool = False
    source_scope: str = "global"

    def all_aliases(self) -> Iterable[tuple[str, str]]:
        for locale, forms in self.aliases.items():
            for form in forms:
                yield locale, form


@dataclass
class Collision:
    kind: str
    concept_ids: list[str]
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "concept_ids": list(self.concept_ids), "detail": self.detail}


def _norm(text: str) -> str:
    return " ".join(text.strip().casefold().split())


class ConceptRegistry:
    def __init__(self, records: Sequence[ConceptRecord], *, collisions: list[Collision] | None = None) -> None:
        self._records = {record.concept_id: record for record in records}
        self.collisions = list(collisions or [])
        self._alias_index: dict[str, list[str]] = {}
        for record in self._records.values():
            for _locale, form in record.all_aliases():
                self._alias_index.setdefault(_norm(form), []).append(record.concept_id)
            self._alias_index.setdefault(_norm(record.concept_id), []).append(record.concept_id)

    def get(self, concept_id: str) -> ConceptRecord | None:
        return self._records.get(concept_id)

    def __contains__(self, concept_id: str) -> bool:
        return concept_id in self._records

    def __len__(self) -> int:
        return len(self._records)

    def ids(self) -> list[str]:
        return sorted(self._records)

    def realization(self, concept_id: str, locale: str) -> str | None:
        record = self.get(concept_id)
        if record is None:
            return None
        if locale in record.realizations:
            return record.realizations[locale]
        language = locale.split("-")[0]
        for key, value in record.realizations.items():
            if key.split("-")[0] == language:
                return value
        return record.realizations.get("en")

    def bind(self, text: str, context: InterpretationContext | None = None) -> list[BoundConcept]:
        ctx = context or InterpretationContext()
        bound: list[BoundConcept] = []
        seen: set[str] = set()
        haystack = text
        # Longer aliases first so "إذا ما عليك أمر" wins over "أمر".
        catalog: list[tuple[int, str, str, ConceptRecord]] = []
        for record in self._records.values():
            if record.contextual_only:
                if ctx.domain is None or ctx.domain not in record.domains:
                    continue
            for locale, form in record.all_aliases():
                catalog.append((len(form), form, locale, record))
        catalog.sort(key=lambda item: item[0], reverse=True)
        remaining = haystack
        for _length, form, locale, record in catalog:
            if record.concept_id in seen:
                continue
            if form and form in remaining:
                seen.add(record.concept_id)
                bound.append(
                    BoundConcept(
                        concept_id=record.concept_id,
                        canonical_meaning=record.canonical_meaning,
                        surface=form,
                        locale=locale,
                        scope="global",
                        confidence=Confidence(
                            value=1.0,
                            method="alias_substring",
                            evidence=[form],
                            sample_size=1,
                        ),
                    )
                )
        return bound

    def apply_scope_overlay(
        self,
        concept_id: str,
        *,
        scope: str,
        realizations: dict[str, str] | None = None,
        canonical_meaning: str | None = None,
    ) -> ConceptRecord:
        if scope not in PRECEDENCE or scope == "global":
            raise ConceptRegistryError(f"Invalid overlay scope {scope!r}")
        record = self.get(concept_id)
        if record is None:
            raise ConceptRegistryError(f"Unknown concept {concept_id}")
        if canonical_meaning is not None and _norm(canonical_meaning) != _norm(record.canonical_meaning):
            raise CanonicalRedefinitionError(
                f"Scope {scope!r} attempted to redefine canonical meaning of {concept_id}. "
                "Lower layers may customize realization only."
            )
        if realizations:
            record.realizations = {**record.realizations, **realizations}
            record.source_scope = scope
        return record


def _parse_record(raw: dict[str, Any], *, scope: str) -> ConceptRecord:
    concept_id = raw.get("concept_id")
    meaning = raw.get("canonical_meaning")
    if not concept_id or not meaning:
        raise ConceptRegistryError(f"Concept in scope {scope} missing concept_id or canonical_meaning")
    aliases = raw.get("aliases") or {}
    if not isinstance(aliases, dict):
        raise ConceptRegistryError(f"{concept_id}: aliases must be a mapping")
    realizations = raw.get("realizations") or {}
    flags = raw.get("flags") or {}
    return ConceptRecord(
        concept_id=str(concept_id),
        canonical_meaning=str(meaning),
        aliases={str(k): [str(x) for x in v] for k, v in aliases.items()},
        realizations={str(k): str(v) for k, v in realizations.items()},
        domains=[str(x) for x in (raw.get("domains") or [])],
        flags=dict(flags),
        preserve_surface=bool(raw.get("preserve_surface", False)),
        contextual_only=bool(raw.get("contextual_only", False)),
        source_scope=scope,
    )


def detect_collisions(records: Sequence[ConceptRecord]) -> list[Collision]:
    collisions: list[Collision] = []
    by_id: dict[str, list[ConceptRecord]] = {}
    for record in records:
        by_id.setdefault(record.concept_id, []).append(record)
    for concept_id, group in by_id.items():
        if len(group) > 1:
            meanings = {_norm(item.canonical_meaning) for item in group}
            if len(meanings) > 1:
                collisions.append(
                    Collision(
                        kind="canonical_meaning_conflict",
                        concept_ids=[concept_id],
                        detail="Duplicate concept_id with different canonical_meaning",
                    )
                )
            else:
                collisions.append(
                    Collision(
                        kind="duplicate_concept_id",
                        concept_ids=[concept_id],
                        detail="Duplicate concept_id with identical canonical_meaning",
                    )
                )
    alias_map: dict[str, set[str]] = {}
    for record in records:
        for _locale, form in record.all_aliases():
            key = _norm(form)
            if not key:
                continue
            alias_map.setdefault(key, set()).add(record.concept_id)
    for form, ids in alias_map.items():
        if len(ids) > 1:
            collisions.append(
                Collision(
                    kind="alias_collision",
                    concept_ids=sorted(ids),
                    detail=f"Alias {form!r} maps to multiple concept_ids",
                )
            )
    return collisions


def load_concept_registry(path: Path, *, raise_on_collision: bool = True) -> ConceptRegistry:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ConceptRegistryError(f"Expected mapping in {path}")
    records = [_parse_record(item, scope="global") for item in payload.get("concepts") or []]
    for overlay in payload.get("scopes") or []:
        scope = overlay.get("scope")
        if scope not in PRECEDENCE:
            raise ConceptRegistryError(f"Unknown scope {scope!r}")
        for item in overlay.get("concepts") or []:
            parsed = _parse_record(item, scope=scope)
            existing = next((r for r in records if r.concept_id == parsed.concept_id), None)
            if existing is None:
                # Overlays cannot introduce a new canonical concept silently.
                raise ConceptRegistryError(
                    f"Scope {scope!r} referenced unknown concept {parsed.concept_id}"
                )
            if _norm(parsed.canonical_meaning) != _norm(existing.canonical_meaning):
                raise CanonicalRedefinitionError(
                    f"Scope {scope!r} redefines canonical meaning of {parsed.concept_id}"
                )
            existing.realizations.update(parsed.realizations)
            for locale, forms in parsed.aliases.items():
                existing.aliases.setdefault(locale, [])
                for form in forms:
                    if form not in existing.aliases[locale]:
                        existing.aliases[locale].append(form)
            existing.source_scope = scope
    collisions = detect_collisions(records)
    fatal = [c for c in collisions if c.kind in {"canonical_meaning_conflict", "alias_collision"}]
    if raise_on_collision and fatal:
        details = "; ".join(c.detail for c in fatal)
        raise ConceptCollisionError(details)
    unique: dict[str, ConceptRecord] = {}
    for record in records:
        unique.setdefault(record.concept_id, record)
    return ConceptRegistry(list(unique.values()), collisions=collisions)
