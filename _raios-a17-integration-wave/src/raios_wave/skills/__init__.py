"""Skill provider interface. External extractors emit SKILL_CANDIDATE only."""
from __future__ import annotations

from typing import Any, Protocol

from ..identity import FailClosed, canonical_json, deterministic_id, utc_now
from ..models import AuthorityState, EventType


class SkillExtractor(Protocol):
    name: str

    def extract(self, source: dict[str, Any]) -> list[dict[str, Any]]: ...


class SkillXExtractor:
    name = "SkillX"

    def extract(self, source: dict[str, Any]) -> list[dict[str, Any]]:
        return [{"title": source.get("title") or "skillx-candidate", "steps": source.get("steps") or []}]


class EvoSkillExtractor:
    name = "EvoSkill"

    def extract(self, source: dict[str, Any]) -> list[dict[str, Any]]:
        return [{"title": source.get("title") or "evoskill-candidate", "mutation": True}]


class NativeSkillCompiler:
    name = "native-skill-compiler"

    def extract(self, source: dict[str, Any]) -> list[dict[str, Any]]:
        return [{"title": source.get("title") or "native-candidate", "compiled": False}]


class SkillSPI:
    def __init__(self, store: Any) -> None:
        self.store = store
        self.extractors = {
            "SkillX": SkillXExtractor(),
            "EvoSkill": EvoSkillExtractor(),
            "native": NativeSkillCompiler(),
        }

    def ingest_external(self, extractor_name: str, source: dict[str, Any]) -> dict[str, Any]:
        extractor = self.extractors.get(extractor_name)
        if extractor is None:
            raise FailClosed("UNKNOWN_SKILL_EXTRACTOR")
        extracted = extractor.extract(source)
        created = []
        for item in extracted:
            candidate_id = deterministic_id("skillcand", extractor_name, canonical_json(item))
            payload = {
                "candidate_id": candidate_id,
                "extractor": extractor_name,
                "skill": item,
                "authority_state": AuthorityState.CANDIDATE.value,
                "kind": "SKILL_CANDIDATE",
                "canonical": False,
            }
            self.store.conn.execute(
                """
                INSERT OR REPLACE INTO candidates(
                    candidate_id, kind, capability, authority_state, canonical, payload_json, created_at
                ) VALUES (?, 'SKILL_CANDIDATE', ?, 'CANDIDATE', 0, ?, ?)
                """,
                (candidate_id, source.get("capability"), canonical_json(payload), utc_now()),
            )
            self.store.append_event(EventType.CANDIDATE_CREATED, candidate_id, {"extractor": extractor_name, "canonical": False})
            created.append(payload)
        return {"candidates": created, "canonical": False, "authoritative": False}

    def promote_canonical(self, candidate_id: str) -> None:
        raise FailClosed("SKILL_CANDIDATE_IS_NOT_CANONICAL")
