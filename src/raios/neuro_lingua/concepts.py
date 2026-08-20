from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml


VALID_LOCALES = {
    "en",
    "ar",
    "ar-EG",
    "ar-GULF",
    "ar-SA",
    "ar-AE",
    "ar-KW",
    "ar-QA",
    "ar-BH",
    "ar-OM",
    "nb-NO",
    "sv-SE",
    "da-DK",
}

LAYERS = ("GLOBAL", "DOMAIN", "ORGANIZATION", "PROJECT", "USER", "SESSION")


class ConceptRegistryError(Exception):
    def __init__(self, diagnostics: list[dict[str, Any]]):
        super().__init__("CONCEPT_REGISTRY_INVALID")
        self.diagnostics = diagnostics


def _walk_aliases(node: Any, acc: list[str]) -> None:
    if isinstance(node, str):
        acc.append(node)
    elif isinstance(node, dict):
        for value in node.values():
            _walk_aliases(value, acc)
    elif isinstance(node, list):
        for value in node:
            _walk_aliases(value, acc)


def _locales_in(node: Any, acc: set[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in VALID_LOCALES or key in {"ar-EG", "ar-GULF"}:
                acc.add(key)
            _locales_in(value, acc)
    elif isinstance(node, list):
        for value in node:
            _locales_in(value, acc)


def load_concept_registry(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}
    concepts = raw.get("concepts") or []
    diagnostics: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    alias_owners: dict[str, str] = {}
    inherits: dict[str, str] = {}

    for concept in concepts:
        concept_id = concept.get("concept_id")
        if not concept_id:
            diagnostics.append({"code": "MISSING_CONCEPT_ID", "concept": concept})
            continue
        if concept_id in by_id:
            diagnostics.append({"code": "DUPLICATE_CONCEPT_ID", "concept_id": concept_id})
            continue
        by_id[concept_id] = concept
        parent = (concept.get("inherits") or concept.get("parent"))
        if parent:
            inherits[concept_id] = str(parent)

        aliases: list[str] = []
        _walk_aliases(concept.get("aliases"), aliases)
        _walk_aliases(concept.get("realizations"), aliases)
        for alias in aliases:
            key = alias.strip().lower()
            if not key:
                continue
            owner = alias_owners.get(key)
            if owner and owner != concept_id:
                diagnostics.append(
                    {
                        "code": "ALIAS_COLLISION",
                        "alias": alias,
                        "concepts": [owner, concept_id],
                    }
                )
            else:
                alias_owners[key] = concept_id

        locales: set[str] = set()
        _locales_in(concept.get("realizations"), locales)
        _locales_in(concept.get("locales"), locales)
        for locale in locales:
            if locale not in VALID_LOCALES:
                diagnostics.append(
                    {
                        "code": "INVALID_LOCALE",
                        "concept_id": concept_id,
                        "locale": locale,
                    }
                )

        if concept.get("override_canonical") or concept.get("redefine_canonical"):
            diagnostics.append(
                {
                    "code": "SEMANTIC_OVERRIDE_ATTEMPT",
                    "concept_id": concept_id,
                    "layer": concept.get("layer"),
                }
            )

        layer = concept.get("layer") or "GLOBAL"
        if layer not in LAYERS:
            diagnostics.append({"code": "INVALID_LAYER", "concept_id": concept_id, "layer": layer})
        if layer in {"PROJECT", "USER", "SESSION"} and concept.get("canonical") and concept.get("override_meaning"):
            diagnostics.append(
                {
                    "code": "PROJECT_OVERRIDE_REDEFINES_MEANING",
                    "concept_id": concept_id,
                }
            )

    for concept_id, parent in inherits.items():
        seen = {concept_id}
        current = parent
        while current:
            if current in seen:
                diagnostics.append(
                    {
                        "code": "CYCLIC_INHERITANCE",
                        "concept_id": concept_id,
                        "cycle": sorted(seen),
                    }
                )
                break
            seen.add(current)
            current = inherits.get(current)

    ambiguous: dict[str, list[str]] = defaultdict(list)
    for alias, owner in alias_owners.items():
        ambiguous[alias].append(owner)
    for alias, owners in ambiguous.items():
        if len(set(owners)) > 1:
            diagnostics.append({"code": "AMBIGUOUS_TERMINOLOGY", "alias": alias, "concepts": owners})

    status = "OK" if not diagnostics else "CONFLICTS"
    result = {
        "status": status,
        "confidence": 1.0 if not diagnostics else 0.4,
        "evidence": [f"concepts={len(by_id)}", f"diagnostics={len(diagnostics)}"],
        "concepts": by_id,
        "diagnostics": diagnostics,
        "warnings": [row["code"] for row in diagnostics],
        "path": str(path),
    }
    return result


def resolve_concepts(text: str, registry: dict[str, Any]) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    evidence: list[str] = []
    for concept_id, concept in (registry.get("concepts") or {}).items():
        aliases: list[str] = []
        _walk_aliases(concept.get("realizations"), aliases)
        _walk_aliases(concept.get("aliases"), aliases)
        for alias in aliases:
            if isinstance(alias, str) and alias and alias in text:
                hits.append({"concept_id": concept_id, "alias": alias})
                evidence.append(f"{concept_id}:{alias}")
    return {
        "status": "OK",
        "confidence": 0.8 if hits else 0.4,
        "evidence": evidence,
        "matches": hits,
        "warnings": [] if hits else ["NO_CONCEPT_MATCH"],
    }
