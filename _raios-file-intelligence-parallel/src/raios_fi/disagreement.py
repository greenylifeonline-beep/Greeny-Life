"""Persist disagreements. Never hide them by averaging."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .config import deterministic_id
from .store import IndexStore

PROVIDERS = (
    "path_rules",
    "signatures",
    "magika",
    "parser",
    "tree_sitter",
    "ctags",
    "dependency_graph",
    "git",
    "semantic_retrieval",
    "qwen",
    "teachers",
)


@dataclass
class DisagreementObject:
    disagreement_id: str
    file_id: str
    relative_path: str
    votes: dict[str, str]
    disagreeing_providers: list[str]
    resolution: str
    averaged: bool
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_votes(votes: dict[str, str], *, file_id: str, relative_path: str) -> DisagreementObject:
    present = {k: v for k, v in votes.items() if v and v != "UNAVAILABLE"}
    values = list(present.values())
    unique = sorted(set(values))
    disagreeing = []
    if len(unique) > 1:
        disagreeing = sorted(present.keys())
        resolution = "UNRESOLVED_DISAGREEMENT"
    elif not unique:
        resolution = "NO_VOTES"
    else:
        resolution = f"AGREE:{unique[0]}"
    return DisagreementObject(
        disagreement_id=deterministic_id("disagree", file_id, relative_path, ",".join(unique)),
        file_id=file_id,
        relative_path=relative_path,
        votes={p: votes.get(p, "UNAVAILABLE") for p in PROVIDERS},
        disagreeing_providers=disagreeing,
        resolution=resolution,
        averaged=False,
        evidence=[f"{k}={v}" for k, v in present.items()],
    )


def persist_disagreement(store: IndexStore, obj: DisagreementObject) -> None:
    payload = obj.to_dict()
    payload["averaged"] = False
    store.insert_disagreement(payload)
